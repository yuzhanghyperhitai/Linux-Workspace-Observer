"""Git context awareness collector for LWO."""

import re
import subprocess
import time
from typing import Optional, Tuple

from lwo.config import get_config
from lwo.storage.database import get_database
from lwo.utils.logger import setup_logger

logger = setup_logger(__name__)


class GitContextCollector:
    """Collect Git repository context information."""
    
    # Branch type patterns
    BRANCH_PATTERNS = {
        'feat': re.compile(r'^(feat|feature)/'),
        'fix': re.compile(r'^(fix|bugfix|hotfix)/'),
        'refactor': re.compile(r'^refactor/'),
        'docs': re.compile(r'^docs?/'),
        'test': re.compile(r'^test/'),
        'chore': re.compile(r'^chore/'),
    }
    
    def __init__(self):
        """Initialize Git context collector."""
        self.config = get_config()
        self.db = get_database()
        self.last_pwd = None
        self.last_check_time = 0
    
    @staticmethod
    def is_git_repo(path: str) -> bool:
        """Check if path is inside a Git repository.
        
        Args:
            path: Directory path to check
            
        Returns:
            True if path is in a Git repo
        """
        try:
            result = subprocess.run(
                ['git', 'rev-parse', '--git-dir'],
                cwd=path,
                capture_output=True,
                text=True,
                timeout=2
            )
            return result.returncode == 0
        except Exception:
            return False
    
    @staticmethod
    def get_git_branch(path: str) -> Optional[str]:
        """Get current Git branch.
        
        Args:
            path: Repository path
            
        Returns:
            Branch name or None
        """
        try:
            result = subprocess.run(
                ['git', 'branch', '--show-current'],
                cwd=path,
                capture_output=True,
                text=True,
                timeout=2
            )
            if result.returncode == 0:
                return result.stdout.strip()
        except Exception as e:
            logger.debug(f"Failed to get Git branch: {e}")
        
        return None
    
    def classify_branch(self, branch: str) -> Optional[str]:
        """Classify branch type based on name.
        
        Args:
            branch: Branch name
            
        Returns:
            Branch type (feat/fix/refactor/docs/test/chore) or None
        """
        for branch_type, pattern in self.BRANCH_PATTERNS.items():
            if pattern.match(branch):
                return branch_type
        
        return None
    
    def check_pwd_change(self, pwd: str) -> bool:
        """Check if PWD has changed and enough time has passed.
        
        Args:
            pwd: Current working directory
            
        Returns:
            True if should check Git context
        """
        current_time = time.time()
        
        # Check if PWD changed or 5 minutes passed
        if pwd != self.last_pwd or (current_time - self.last_check_time) > 300:
            self.last_pwd = pwd
            self.last_check_time = current_time
            return True
        
        return False
    
    def collect_git_context(self, pwd: str) -> Optional[Tuple[str, str, Optional[str]]]:
        """Collect Git context for given directory.
        
        Args:
            pwd: Working directory
            
        Returns:
            Tuple of (repo_path, branch, branch_type) or None
        """
        if not self.is_git_repo(pwd):
            return None
        
        # Get repository root
        try:
            result = subprocess.run(
                ['git', 'rev-parse', '--show-toplevel'],
                cwd=pwd,
                capture_output=True,
                text=True,
                timeout=2
            )
            if result.returncode != 0:
                return None
            
            repo_path = result.stdout.strip()
        except Exception:
            return None
        
        # Get current branch
        branch = self.get_git_branch(pwd)
        if not branch:
            return None
        
        # Classify branch type
        branch_type = self.classify_branch(branch)
        
        return (repo_path, branch, branch_type)
    
    def save_git_context(self, repo_path: str, branch: str, branch_type: Optional[str]):
        """Save Git context to database.
        
        Args:
            repo_path: Repository root path
            branch: Branch name
            branch_type: Branch type classification
        """
        ts = int(time.time())
        
        try:
            self.db.insert_git_context(
                ts=ts,
                repo_path=repo_path,
                branch=branch,
                branch_type=branch_type or 'other'
            )
            logger.debug(f"Recorded Git context: {branch} ({branch_type}) in {repo_path}")
        except Exception as e:
            logger.error(f"Failed to save Git context: {e}")
    
    def on_pwd_change(self, pwd: str):
        """Handle PWD change event.
        
        Args:
            pwd: New working directory
        """
        if not self.check_pwd_change(pwd):
            return
        
        git_context = self.collect_git_context(pwd)
        
        if git_context:
            repo_path, branch, branch_type = git_context
            self.save_git_context(repo_path, branch, branch_type)

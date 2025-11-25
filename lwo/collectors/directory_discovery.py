"""Smart directory discovery for file monitoring."""

import time
from typing import List, Dict
from collections import defaultdict

from lwo.config import get_config
from lwo.storage.database import get_database
from lwo.storage.models import ShellCommand, GitContext
from lwo.utils.logger import setup_logger

logger = setup_logger(__name__)


class DirectoryDiscovery:
    """Discover directories for file monitoring based on usage patterns."""
    
    def __init__(self):
        """Initialize directory discovery."""
        self.config = get_config()
        self.db = get_database()
    
    def discover_directories(self, lookback_days: int = 7, max_dirs: int = 5) -> List[str]:
        """Discover frequently accessed directories.
        
        Args:
            lookback_days: How many days to look back
            max_dirs: Maximum directories to return
            
        Returns:
            List of directory paths sorted by score
        """
        cutoff_time = int(time.time()) - (lookback_days * 86400)
        directory_scores = defaultdict(float)
        
        with self.db.session() as session:
            # Score directories from shell commands
            commands = (
                session.query(ShellCommand)
                .filter(ShellCommand.ts >= cutoff_time)
                .all()
            )
            
            for cmd in commands:
                pwd = cmd.pwd
                if pwd and pwd != '/':
                    directory_scores[pwd] += 1.0
            
            # Score Git repositories higher
            git_contexts = (
                session.query(GitContext)
                .filter(GitContext.ts >= cutoff_time)
                .all()
            )
            
            git_repos = set()
            for ctx in git_contexts:
                if ctx.repo_path:
                    git_repos.add(ctx.repo_path)
                    directory_scores[ctx.repo_path] += 10.0  # Higher weight for Git repos
        
        # Sort by score and return top N
        sorted_dirs = sorted(
            directory_scores.items(),
            key=lambda x: x[1],
            reverse=True
        )
        
        discovered = [path for path, score in sorted_dirs[:max_dirs]]
        
        if discovered:
            logger.info(f"Discovered {len(discovered)} directories for monitoring")
            for path in discovered:
                logger.debug(f"  - {path} (score: {directory_scores[path]:.1f})")
        else:
            logger.warning("No directories discovered for monitoring")
        
        return discovered

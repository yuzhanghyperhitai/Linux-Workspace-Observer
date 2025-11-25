"""AI Agent tools for LWO."""

import subprocess
from pathlib import Path
from typing import Optional

from langchain.tools import tool

from lwo.storage.database import get_database
from lwo.storage.models import ShellCommand
from lwo.utils.logger import setup_logger

logger = setup_logger(__name__)


@tool
def read_file(filepath: str, max_lines: Optional[int] = None) -> str:
    """Read the contents of a file.
    
    Args:
        filepath: Path to the file to read
        max_lines: Maximum number of lines to read (None for all)
        
    Returns:
        File contents as string
    """
    try:
        path = Path(filepath).expanduser()
        
        if not path.exists():
            return f"Error: File not found: {filepath}"
        
        if not path.is_file():
            return f"Error: Not a file: {filepath}"
        
        with open(path, 'r', encoding='utf-8', errors='ignore') as f:
            if max_lines:
                lines = [f.readline() for _ in range(max_lines)]
                content = ''.join(lines)
                return content if content else "Error: File is empty"
            else:
                content = f.read()
                return content if content else "Note: File is empty"
    
    except PermissionError:
        return f"Error: Permission denied: {filepath}"
    except Exception as e:
        logger.error(f"Failed to read file {filepath}: {e}")
        return f"Error reading file: {str(e)}"


@tool
def get_error_logs(command_pattern: str, limit: int = 5) -> str:
    """Get error logs for failed commands matching a pattern.
    
    Args:
        command_pattern: Pattern to match in command (e.g., "git", "python")
        limit: Maximum number of errors to return
        
    Returns:
        Formatted error logs
    """
    try:
        db = get_database()
        
        with db.session() as session:
            # Query failed commands using ORM
            failed_commands = session.query(ShellCommand).filter(
                ShellCommand.exit_code != 0,
                ShellCommand.sanitized_command.like(f'%{command_pattern}%')
            ).order_by(ShellCommand.ts.desc()).limit(limit).all()
            
            if not failed_commands:
                return f"No recent errors found for pattern: {command_pattern}"
            
            # Format results
            results = []
            for cmd in failed_commands:
                from datetime import datetime
                dt = datetime.fromtimestamp(cmd.ts)
                results.append(
                    f"Time: {dt.strftime('%Y-%m-%d %H:%M:%S')}\n"
                    f"Command: {cmd.sanitized_command}\n"
                    f"Exit code: {cmd.exit_code}\n"
                    f"Directory: {cmd.pwd}\n"
                )
            
            return "\n---\n".join(results)
    
    except Exception as e:
        logger.error(f"Failed to get error logs: {e}")
        return f"Error: {str(e)}"


@tool
def get_git_diff(filepath: Optional[str] = None) -> str:
    """Get git diff for a file or entire repository.
    
    Args:
        filepath: Specific file to get diff for (None for all changes)
        
    Returns:
        Git diff output
    """
    try:
        cmd = ['git', 'diff']
        if filepath:
            cmd.append(filepath)
        
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=5
        )
        
        if result.returncode != 0:
            return f"Error: {result.stderr or 'Git diff failed'}"
        
        return result.stdout if result.stdout else "No changes detected"
    
    except subprocess.TimeoutExpired:
        return "Error: Git command timed out"
    except Exception as e:
        logger.error(f"Failed to get git diff: {e}")
        return f"Error: {str(e)}"


@tool
def get_recent_commands(count: int = 10) -> str:
    """Get recent shell commands.
    
    Args:
        count: Number of recent commands to retrieve
        
    Returns:
        Formatted command history
    """
    try:
        db = get_database()
        
        with db.session() as session:
            commands = session.query(ShellCommand).order_by(
                ShellCommand.ts.desc()
            ).limit(count).all()
            
            if not commands:
                return "No recent commands found"
            
            results = []
            for cmd in commands:
                from datetime import datetime
                dt = datetime.fromtimestamp(cmd.ts)
                status = "✓" if cmd.exit_code == 0 else "✗"
                results.append(
                    f"{status} [{dt.strftime('%H:%M:%S')}] {cmd.sanitized_command}"
                )
            
            return "\n".join(results)
    
    except Exception as e:
        logger.error(f"Failed to get recent commands: {e}")
        return f"Error: {str(e)}"


@tool
def list_directory(dirpath: str) -> str:
    """List contents of a directory.
    
    Args:
        dirpath: Path to directory
        
    Returns:
        Directory listing
    """
    try:
        path = Path(dirpath).expanduser()
        
        if not path.exists():
            return f"Error: Directory not found: {dirpath}"
        
        if not path.is_dir():
            return f"Error: Not a directory: {dirpath}"
        
        items = list(path.iterdir())
        if not items:
            return "Directory is empty"
        
        # Sort: directories first, then files
        dirs = sorted([i for i in items if i.is_dir()], key=lambda x: x.name)
        files = sorted([i for i in items if i.is_file()], key=lambda x: x.name)
        
        results = []
        for d in dirs:
            results.append(f"📁 {d.name}/")
        for f in files:
            size_kb = f.stat().st_size / 1024
            results.append(f"📄 {f.name} ({size_kb:.1f}KB)")
        
        return "\n".join(results[:50])  # Limit to 50 items
    
    except Exception as e:
        logger.error(f"Failed to list directory {dirpath}: {e}")
        return f"Error: {str(e)}"


@tool  
def search_in_file(filepath: str, pattern: str, max_results: int = 10) -> str:
    """Search for a pattern in a file.
    
    Args:
        filepath: Path to the file
        pattern: Pattern to search for
        max_results: Maximum number of results to return
        
    Returns:
        Matching lines with line numbers
    """
    try:
        path = Path(filepath).expanduser()
        
        if not path.exists():
            return f"Error: File not found: {filepath}"
        
        results = []
        with open(path, 'r', encoding='utf-8', errors='ignore') as f:
            for line_num, line in enumerate(f, 1):
                if pattern in line:
                    results.append(f"Line {line_num}: {line.rstrip()}")
                    if len(results) >= max_results:
                        break
        
        if not results:
            return f"No matches found for pattern: {pattern}"
        
        return "\n".join(results)
    
    except Exception as e:
        logger.error(f"Failed to search in file {filepath}: {e}")
        return f"Error: {str(e)}"


# Export all tools
AGENT_TOOLS = [
    read_file,
    get_error_logs,
    get_git_diff,
    get_recent_commands,
    list_directory,
    search_in_file,
]

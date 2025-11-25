"""AI Agent tools for LWO."""

import subprocess
from pathlib import Path
from typing import Optional, List

from langchain.tools import tool

from lwo.storage.database import get_database
from lwo.storage.models import ShellCommand
from lwo.utils.logger import setup_logger

logger = setup_logger(__name__)


@tool
def read_file(filepath: str, max_lines: Optional[int] = None) -> str:
    """Read the contents of a file.
    
    IMPORTANT: This tool ONLY accepts absolute file paths.
    
    Args:
        filepath: ABSOLUTE path to the file (e.g., /home/user/project/file.py)
                 DO NOT use relative paths like 'file.py' or './file.py'
        max_lines: Maximum number of lines to read (None for all)
        
    Returns:
        File contents as string
        
    Example:
        Correct:   read_file("/home/user/test.py")
        Incorrect: read_file("test.py")
    """
    path = Path(filepath).expanduser()
    
    if not path.is_absolute():
        return f"Error: Only absolute paths are accepted. Got: {filepath}"
    
    if not path.exists():
        return f"Error: File not found: {filepath}"
    
    if not path.is_file():
        return f"Error: Not a file: {filepath}"
    
    try:
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



@tool
def run_safe_command(command: str, cwd: str = ".") -> str:
    """Execute a safe read-only command.
    
    Args:
        command: Command to execute (must be in whitelist)
        cwd: Working directory
        
    Returns:
        Command output
    """
    import subprocess
    from pathlib import Path
    
    # Whitelist of safe read-only commands
    safe_commands = {'grep', 'find', 'ls', 'cat', 'head', 'tail', 'wc', 'tree', 'file', 'stat'}
    
    # Extract command name
    cmd_parts = command.split()
    if not cmd_parts:
        return "Error: Empty command"
    
    cmd_name = cmd_parts[0]
    if cmd_name not in safe_commands:
        return f"Error: Command '{cmd_name}' not in whitelist. Allowed: {', '.join(safe_commands)}"
    
    # Execute command
    try:
        result = subprocess.run(
            command,
            shell=True,
            cwd=Path(cwd).expanduser(),
            capture_output=True,
            text=True,
            timeout=5
        )
        
        if result.returncode != 0:
            return f"Command failed (exit {result.returncode}):\n{result.stderr}"
        
        return result.stdout if result.stdout else "(no output)"
    
    except subprocess.TimeoutExpired:
        return "Error: Command timed out (5s limit)"
    except Exception as e:
        logger.error(f"Failed to run command {command}: {e}")
        return f"Error: {str(e)}"


@tool
def analyze_git_log(filepath: str = None, limit: int = 10) -> str:
    """Get recent git commits for a file or repository.
    
    Args:
        filepath: Specific file to get commits for (None for all)
        limit: Number of commits to return
        
    Returns:
        Git log output
    """
    import subprocess
    
    cmd = ['git', 'log', f'--max-count={limit}', '--oneline']
    if filepath:
        cmd.extend(['--', filepath])
    
    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=5
        )
        
        if result.returncode != 0:
            return f"Error: {result.stderr or 'Git log failed'}"
        
        return result.stdout if result.stdout else "No commits found"
    
    except subprocess.TimeoutExpired:
        return "Error: Git command timed out"
    except Exception as e:
        logger.error(f"Failed to get git log: {e}")
        return f"Error: {str(e)}"


@tool
def find_similar_files(pattern: str, directory: str = ".", max_results: int = 20) -> str:
    """Find files matching a pattern.
    
    Args:
        pattern: Pattern to match (e.g., "*.py", "*test*")
        directory: Directory to search in
        max_results: Maximum results to return
        
    Returns:
        List of matching files
    """
    from pathlib import Path
    
    try:
        path = Path(directory).expanduser()
        
        if not path.exists():
            return f"Error: Directory not found: {directory}"
        
        # Use glob to find files
        matches = list(path.rglob(pattern))[:max_results]
        
        if not matches:
            return f"No files found matching pattern: {pattern}"
        
        results = [str(m.relative_to(path)) for m in matches]
        return "\n".join(results)
    
    except Exception as e:
        logger.error(f"Failed to find files: {e}")
        return f"Error: {str(e)}"


@tool
def get_project_structure(directory: str = ".", max_depth: int = 3) -> str:
    """Get project directory structure.
    
    Args:
        directory: Root directory
        max_depth: Maximum depth to traverse
        
    Returns:
        Directory tree structure
    """
    from pathlib import Path
    
    def build_tree(path: Path, prefix: str = "", depth: int = 0) -> List[str]:
        """Recursively build directory tree."""
        if depth >= max_depth:
            return []
        
        lines = []
        try:
            items = sorted(path.iterdir(), key=lambda x: (not x.is_dir(), x.name))
            
            for i, item in enumerate(items):
                # Skip hidden files and common ignore patterns
                if item.name.startswith('.') or item.name in {'__pycache__', 'node_modules', 'venv', '.venv'}:
                    continue
                
                is_last = i == len(items) - 1
                current_prefix = "└── " if is_last else "├── "
                lines.append(f"{prefix}{current_prefix}{item.name}")
                
                if item.is_dir() and depth < max_depth - 1:
                    next_prefix = prefix + ("    " if is_last else "│   ")
                    lines.extend(build_tree(item, next_prefix, depth + 1))
        
        except PermissionError:
            pass
        
        return lines
    
    try:
        path = Path(directory).expanduser()
        
        if not path.exists():
            return f"Error: Directory not found: {directory}"
        
        lines = [str(path)]
        lines.extend(build_tree(path))
        
        return "\n".join(lines)
    
    except Exception as e:
        logger.error(f"Failed to get project structure: {e}")
        return f"Error: {str(e)}"


# Export all tools
AGENT_TOOLS = [
    read_file,
    get_error_logs,
    get_git_diff,
    get_recent_commands,
    list_directory,
    search_in_file,
    run_safe_command,
    analyze_git_log,
    find_similar_files,
    get_project_structure,
]

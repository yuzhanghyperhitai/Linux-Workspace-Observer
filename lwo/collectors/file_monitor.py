"""File monitoring using watchdog."""

import time
import asyncio
from pathlib import Path
from typing import List, Set, Dict
from collections import defaultdict

from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler, FileSystemEvent

from lwo.config import get_config
from lwo.storage.database import get_database
from lwo.storage.models import FileEvent
from lwo.utils.logger import setup_logger

logger = setup_logger(__name__)


class FileMonitor(FileSystemEventHandler):
    """Monitor file changes using watchdog."""
    
    def __init__(self, monitored_paths: List[str]):
        """Initialize file monitor.
        
        Args:
            monitored_paths: List of directory paths to monitor
        """
        super().__init__()
        self.config = get_config()
        self.db = get_database()
        self.monitored_paths = monitored_paths
        self.observer = None
        
        # Debouncing: track recent events to avoid duplicates
        self.recent_events: Dict[str, float] = {}
        self.debounce_seconds = 2.0
        
        # File extensions to monitor (from config would be ideal, hardcode for now)
        self.monitored_extensions = {
            '.py', '.js', '.ts', '.jsx', '.tsx',
            '.java', '.c', '.cpp', '.h', '.hpp',
            '.go', '.rs', '.rb', '.php',
            '.md', '.rst', '.txt',
            '.toml', '.yaml', '.yml', '.json', '.xml'
        }
    
    def should_monitor_file(self, filepath: str) -> bool:
        """Check if file should be monitored.
        
        Args:
            filepath: Path to file
            
        Returns:
            True if file should be monitored
        """
        path = Path(filepath)
        
        # Directories to skip (dependencies, build artifacts, caches)
        skip_dirs = {
            'node_modules', '__pycache__', '.venv', 'venv',
            '.git', '.pytest_cache', '.mypy_cache', '.tox',
            'dist', 'build', 'target', 'out', 'bin',
            '.next', '.nuxt', '.cache', 'vendor',
            'coverage', '.coverage', '.eggs'
        }
        
        # Skip if any part of the path matches skip directories
        if any(part in skip_dirs for part in path.parts):
            return False
        
        # Skip hidden files and directories (starting with .)
        if any(part.startswith('.') and part not in {'.', '..'} for part in path.parts):
            return False
        
        # Check extension
        return path.suffix in self.monitored_extensions
    
    def should_record_event(self, filepath: str) -> bool:
        """Check if event should be recorded (debouncing).
        
        Args:
            filepath: Path to file
            
        Returns:
            True if event should be recorded
        """
        current_time = time.time()
        last_event_time = self.recent_events.get(filepath, 0)
        
        if current_time - last_event_time < self.debounce_seconds:
            return False
        
        self.recent_events[filepath] = current_time
        return True
    
    def record_event(self, filepath: str, event_type: str):
        """Record file event to database.
        
        Args:
            filepath: Path to file
            event_type: Type of event (CREATED, MODIFIED, DELETED, MOVED)
        """
        with self.db.session() as session:
            file_event = FileEvent(
                ts=int(time.time()),
                file_path=filepath,
                event_type=event_type
            )
            session.add(file_event)
            session.commit()
            
        logger.debug(f"File event: {event_type} - {filepath}")
    
    def on_created(self, event: FileSystemEvent):
        """Handle file creation event."""
        if event.is_directory:
            return
        
        if not self.should_monitor_file(event.src_path):
            return
        
        if self.should_record_event(event.src_path):
            self.record_event(event.src_path, 'CREATED')
    
    def on_modified(self, event: FileSystemEvent):
        """Handle file modification event."""
        if event.is_directory:
            return
        
        if not self.should_monitor_file(event.src_path):
            return
        
        if self.should_record_event(event.src_path):
            self.record_event(event.src_path, 'MODIFIED')
    
    def on_deleted(self, event: FileSystemEvent):
        """Handle file deletion event."""
        if event.is_directory:
            return
        
        if not self.should_monitor_file(event.src_path):
            return
        
        if self.should_record_event(event.src_path):
            self.record_event(event.src_path, 'DELETED')
    
    def on_moved(self, event: FileSystemEvent):
        """Handle file move event."""
        if event.is_directory:
            return
        
        # Record as MOVED for destination
        if hasattr(event, 'dest_path'):
            if self.should_monitor_file(event.dest_path):
                if self.should_record_event(event.dest_path):
                    self.record_event(event.dest_path, 'MOVED')
    
    async def start(self):
        """Start file monitoring."""
        self.observer = Observer()
        
        for path in self.monitored_paths:
            if Path(path).exists():
                self.observer.schedule(self, path, recursive=True)
                logger.info(f"Monitoring directory: {path}")
            else:
                logger.warning(f"Directory not found, skipping: {path}")
        
        if self.observer.emitters:
            self.observer.start()
            logger.info(f"File monitor started for {len(self.monitored_paths)} directories")
        else:
            logger.warning("No valid directories to monitor")
    
    async def stop(self):
        """Stop file monitoring."""
        if self.observer:
            self.observer.stop()
            self.observer.join(timeout=2.0)
            logger.info("File monitor stopped")

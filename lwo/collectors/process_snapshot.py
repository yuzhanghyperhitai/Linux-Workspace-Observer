"""Process snapshot collector for LWO."""

import time
import psutil
from typing import List, Dict, Any

from lwo.config import get_config
from lwo.storage.database import get_database
from lwo.utils.logger import setup_logger

logger = setup_logger(__name__)


class ProcessSnapshotCollector:
    """Collect snapshots of active processes."""
    
    # Process name whitelist (heavy processes we care about)
    PROCESS_WHITELIST = [
        'code', 'pycharm', 'idea', 'intellij', 'eclipse',  # IDEs
        'docker', 'dockerd', 'containerd',  # Docker
        'node', 'npm', 'yarn', 'pnpm',  # Node.js
        'python', 'python3', 'java', 'javac',  # Languages
        'gcc', 'g++', 'clang', 'make', 'cmake',  # Compilers
        'cargo', 'rustc',  # Rust
        'go', 'gopls',  # Go
        'postgres', 'mysql', 'redis', 'mongodb',  # Databases
        'chrome', 'firefox', 'chromium',  # Browsers
    ]
    
    def __init__(self):
        """Initialize process snapshot collector."""
        self.config = get_config()
        self.db = get_database()
        self.interval = self.config.get('collectors', 'process_snapshot_interval', 60)
    
    def is_interesting_process(self, proc: psutil.Process) -> bool:
        """Check if process is interesting to monitor.
        
        Args:
            proc: Process object
            
        Returns:
            True if process should be monitored
        """
        try:
            name = proc.name().lower()
            
            # Check whitelist
            for pattern in self.PROCESS_WHITELIST:
                if pattern in name:
                    return True
            
            # Check resource usage
            cpu_percent = proc.cpu_percent(interval=0.1)
            memory_info = proc.memory_info()
            memory_mb = memory_info.rss / 1024 / 1024
            
            # High CPU or memory usage
            if cpu_percent > 25.0 or memory_mb > 1024:
                return True
            
            return False
        
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            return False
    
    def collect_snapshot(self) -> List[Dict[str, Any]]:
        """Collect current process snapshot.
        
        Returns:
            List of process info dicts
        """
        processes = []
        
        for proc in psutil.process_iter(['pid', 'name', 'cpu_percent', 'memory_info']):
            try:
                if self.is_interesting_process(proc):
                    memory_mb = proc.info['memory_info'].rss / 1024 / 1024
                    
                    processes.append({
                        'pid': proc.info['pid'],
                        'name': proc.info['name'],
                        'cpu_percent': proc.info['cpu_percent'],
                        'memory_mb': memory_mb,
                    })
            
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                continue
        
        return processes
    
    def save_snapshot(self, processes: List[Dict[str, Any]]):
        """Save process snapshot to database.
        
        Args:
            processes: List of process info dicts
        """
        ts = int(time.time())
        
        for proc in processes:
            try:
                self.db.insert_process_snapshot(
                    ts=ts,
                    process_name=proc['name'],
                    pid=proc['pid'],
                    cpu_percent=proc['cpu_percent'],
                    memory_mb=proc['memory_mb']
                )
            except Exception as e:
                logger.error(f"Failed to save process snapshot: {e}")
    
    async def run(self):
        """Run process snapshot collector."""
        import asyncio
        
        logger.info(f"Process snapshot collector started (interval: {self.interval}s)")
        
        # Wait a bit before first collection to avoid blocking daemon startup
        await asyncio.sleep(1)
        
        while True:
            try:
                # Run blocking collection in thread pool to avoid blocking event loop
                loop = asyncio.get_event_loop()
                processes = await loop.run_in_executor(None, self.collect_snapshot)
                
                if processes:
                    self.save_snapshot(processes)
                    logger.debug(f"Collected snapshot of {len(processes)} processes")
                
                await asyncio.sleep(self.interval)
            
            except Exception as e:
                logger.error(f"Error in process snapshot collector: {e}")
                await asyncio.sleep(self.interval)

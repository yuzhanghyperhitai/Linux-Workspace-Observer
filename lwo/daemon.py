"""Daemon process management for LWO."""

import asyncio
import os
import signal
import sys
from typing import Optional

from lwo.config import get_config
from lwo.collectors.shell_hook import ShellHookReceiver
from lwo.storage.database import get_database
from lwo.utils.logger import setup_logger

logger = setup_logger(__name__)


class Daemon: # Renamed from LWODaemon
    """LWO daemon process manager."""
    
    _instance = None # Added for singleton pattern
    
    @classmethod
    def get_instance(cls): # Added for singleton pattern
        """Get daemon instance.
        
        Returns:
            Daemon instance or None
        """
        return cls._instance
    
    def __init__(self):
        """Initialize daemon."""
        Daemon._instance = self # Set instance for singleton
        self.config = get_config()
        self.db = get_database() # Added database initialization
        self.pid_file = self.config.data_dir / 'lwo.pid'
        self.log_file = self.config.data_dir / 'lwo.log'
        
        # Collectors
        self.shell_hook_receiver: Optional[ShellHookReceiver] = None
        
        # Running flag
        self.running = False
        
        # Setup logger with file output
        global logger
        logger = setup_logger(
            __name__,
            level=self.config.get('general', 'log_level', 'INFO'),
            log_file=self.log_file
        )
    
    def is_running(self) -> bool:
        """Check if daemon is already running.
        
        Returns:
            True if daemon is running
        """
        if not self.pid_file.exists():
            return False
        
        try:
            with open(self.pid_file, 'r') as f:
                pid = int(f.read().strip())
            
            # Check if process exists
            os.kill(pid, 0)
            return True
        
        except (OSError, ValueError):
            # Process doesn't exist or invalid PID
            return False
    
    def write_pid(self):
        """Write current PID to file."""
        with open(self.pid_file, 'w') as f:
            f.write(str(os.getpid()))
    
    def remove_pid(self):
        """Remove PID file."""
        if self.pid_file.exists():
            self.pid_file.unlink()
    
    def setup_signal_handlers(self):
        """Setup signal handlers for graceful shutdown."""
        def signal_handler(signum, frame):
            logger.info(f"Received signal {signum}, shutting down...")
            self.running = False
        
        signal.signal(signal.SIGTERM, signal_handler)
        signal.signal(signal.SIGINT, signal_handler)
    
    async def start_collectors(self):
        """Start all data collectors."""
        logger.info("Starting data collectors...")
        
        # Start Shell Hook receiver
        self.shell_hook_receiver = ShellHookReceiver()
        asyncio.create_task(self.shell_hook_receiver.start())
        
        # Start Process Snapshot collector
        from lwo.collectors.process_snapshot import ProcessSnapshotCollector
        self.process_collector = ProcessSnapshotCollector()
        asyncio.create_task(self.process_collector.run())
        
        # Start Event Aggregator
        from lwo.processors.aggregator import EventAggregator
        self.event_aggregator = EventAggregator()
        asyncio.create_task(self.event_aggregator.run())
        
        # Initialize Anomaly Monitor (event-driven, not polling)
        from lwo.inference.anomaly_monitor import AnomalyMonitor
        self.anomaly_monitor = AnomalyMonitor()
        # Note: AnomalyMonitor is event-driven, triggered by collectors
        
        logger.info("All collectors started")
    
    async def stop_collectors(self):
        """Stop all data collectors."""
        logger.info("Stopping data collectors...")
        
        if self.shell_hook_receiver:
            await self.shell_hook_receiver.stop()
        
        logger.info("All collectors stopped")
    
    async def run(self):
        """Run the daemon."""
        self.running = True
        self.write_pid()
        self.setup_signal_handlers()
        
        logger.info(f"LWO daemon started (PID: {os.getpid()})")
        
        try:
            # Start collectors
            await self.start_collectors()
            
            # Keep running until signal received
            while self.running:
                await asyncio.sleep(1)
        
        except Exception as e:
            logger.error(f"Daemon error: {e}")
            raise
        
        finally:
            # Cleanup
            await self.stop_collectors()
            self.remove_pid()
            logger.info("LWO daemon stopped")
    
    def start(self):
        """Start the daemon process."""
        if self.is_running():
            print("LWO daemon is already running")
            return
        
        print("Starting LWO daemon...")
        
        # Run daemon
        try:
            asyncio.run(self.run())
        except KeyboardInterrupt:
            print("\nDaemon interrupted by user")
        except Exception as e:
            print(f"Failed to start daemon: {e}")
            sys.exit(1)
    
    def stop(self):
        """Stop the daemon process."""
        if not self.is_running():
            print("LWO daemon is not running")
            return
        
        try:
            with open(self.pid_file, 'r') as f:
                pid = int(f.read().strip())
            
            print(f"Stopping LWO daemon (PID: {pid})...")
            os.kill(pid, signal.SIGTERM)
            
            # Wait for process to terminate
            import time
            for _ in range(10):
                try:
                    os.kill(pid, 0)
                    time.sleep(0.5)
                except OSError:
                    break
            
            print("LWO daemon stopped")
        
        except Exception as e:
            print(f"Failed to stop daemon: {e}")
            sys.exit(1)


def start_daemon():
    """Start LWO daemon."""
    daemon = Daemon()
    daemon.start()


def stop_daemon():
    """Stop LWO daemon."""
    daemon = Daemon()
    daemon.stop()

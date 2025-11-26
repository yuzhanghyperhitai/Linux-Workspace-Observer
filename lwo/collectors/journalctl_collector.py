"""Journalctl-based log collector for systemd systems."""

import asyncio
import json
import re
from typing import Optional

from lwo.config import get_config
from lwo.storage.database import get_database
from lwo.storage.models import HostLog
from lwo.collectors.log_collector import LogCollector
from lwo.utils.logger import setup_logger

logger = setup_logger(__name__)

# Noise patterns to exclude from logging
EXCLUDE_PATTERNS = [
    # DHCP routine
    r"DHCP.*renewal",
    r"DHCPDISCOVER",
    
    # Cron routine
    r"CRON.*pam_unix.*session (opened|closed)",
    
    # NetworkManager routine
    r"NetworkManager.*state changed",
    r"NetworkManager.*link became (ready|not-ready)",
    
    # Systemd sessions
    r"systemd.*Started Session",
    r"systemd.*Stopped Session",
    r"systemd.*Starting Session",
    r"systemd.*Created slice",
    r"systemd.*Removed slice",
    
    # Bluetooth scanning
    r"bluetoothd.*",
]


class JournalctlCollector(LogCollector):
    """Collects logs from systemd journal using journalctl."""
    
    def __init__(self):
        """Initializes journalctl collector."""
        self.config = get_config()
        self.db = get_database()
        self.process: Optional[asyncio.subprocess.Process] = None
        self.task: Optional[asyncio.Task] = None
        
        # Compile exclusion patterns once
        self.exclude_regexes = [re.compile(pattern) for pattern in EXCLUDE_PATTERNS]
        
        # Get min level from config
        self.min_level = self.config.get('host_log', 'min_level', 'WARNING')
    
    @staticmethod
    def is_available() -> bool:
        """Checks if journalctl is available on this system.
        
        Returns:
            True if journalctl command exists
        """
        import subprocess
        
        try:
            subprocess.run(
                ['which', 'journalctl'],
                capture_output=True,
                check=True,
                timeout=1.0
            )
            return True
        except (subprocess.CalledProcessError, FileNotFoundError, subprocess.TimeoutExpired):
            return False
    
    async def start(self) -> bool:
        """Starts journalctl log collection.
        
        Returns:
            True if started successfully
        """
        if not self.is_available():
            logger.warning("journalctl not available, cannot start log collection")
            return False
        
        # Map config level to journalctl priority
        priority_map = {
            'INFO': 'info',
            'WARNING': 'warning',
            'ERROR': 'err',
            'CRITICAL': 'crit'
        }
        priority = priority_map.get(self.min_level, 'warning')
        
        # Start journalctl process
        try:
            self.process = await asyncio.create_subprocess_exec(
                'journalctl',
                '-f',  # Follow mode
                '--priority', priority,
                '--output', 'json',
                '--no-pager',
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            
            # Start reading task
            self.task = asyncio.create_task(self._read_logs())
            
            logger.info(f"Journalctl collector started (min_level: {self.min_level})")
            return True
        
        except Exception as e:
            logger.error(f"Failed to start journalctl collector: {e}")
            return False
    
    async def stop(self):
        """Stops journalctl log collection."""
        # Cancel reading task
        if self.task:
            self.task.cancel()
            try:
                await self.task
            except asyncio.CancelledError:
                pass
        
        # Terminate process
        if self.process:
            self.process.terminate()
            try:
                await asyncio.wait_for(self.process.wait(), timeout=2.0)
            except asyncio.TimeoutError:
                self.process.kill()
        
        logger.info("Journalctl collector stopped")
    
    async def _read_logs(self):
        """Reads and processes log entries from journalctl."""
        if not self.process or not self.process.stdout:
            return
        
        try:
            while True:
                line = await self.process.stdout.readline()
                if not line:
                    break
                
                # Parse and record log entry
                self._process_line(line.decode('utf-8', errors='ignore').strip())
        
        except asyncio.CancelledError:
            logger.debug("Log reading task cancelled")
        except Exception as e:
            logger.error(f"Error reading journalctl output: {e}")
    
    def _process_line(self, line: str):
        """Processes a single log line from journalctl.
        
        Args:
            line: JSON-formatted log entry
        """
        if not line:
            return
        
        try:
            entry = json.loads(line)
        except json.JSONDecodeError:
            logger.debug(f"Failed to parse journalctl JSON: {line[:100]}")
            return
        
        # Extract fields
        message = entry.get('MESSAGE', '')
        service = entry.get('SYSLOG_IDENTIFIER', entry.get('_COMM', 'unknown'))
        priority = entry.get('PRIORITY', 6)  # 6 = INFO
        timestamp = entry.get('__REALTIME_TIMESTAMP')
        
        # Map priority to level
        priority_levels = {
            0: 'CRITICAL',  # emerg
            1: 'CRITICAL',  # alert
            2: 'CRITICAL',  # crit
            3: 'ERROR',     # err
            4: 'WARN',      # warning
            5: 'INFO',      # notice
            6: 'INFO',      # info
            7: 'DEBUG'      # debug
        }
        level = priority_levels.get(int(priority), 'INFO')
        
        # Apply noise filtering
        if self._is_noise(message):
            return
        
        # Convert timestamp (microseconds) to seconds
        ts = int(timestamp) // 1000000 if timestamp else int(asyncio.get_event_loop().time())
        
        # Record to database
        self._record_log(ts, level, service, message, line)
    
    def _is_noise(self, message: str) -> bool:
        """Checks if message matches noise patterns.
        
        Args:
            message: Log message to check
            
        Returns:
            True if message is noise and should be excluded
        """
        for regex in self.exclude_regexes:
            if regex.search(message):
                return True
        return False
    
    def _record_log(self, ts: int, level: str, service: str, message: str, raw_line: str):
        """Records log entry to database.
        
        Args:
            ts: Unix timestamp
            level: Log level (ERROR/WARN/INFO)
            service: Service name
            message: Log message
            raw_line: Full JSON line
        """
        try:
            with self.db.session() as session:
                host_log = HostLog(
                    ts=ts,
                    level=level,
                    service=service,
                    message=message,
                    raw_line=raw_line
                )
                session.add(host_log)
                session.commit()
                
            logger.debug(f"Recorded host log: {level} - {service} - {message[:50]}")
        
        except Exception as e:
            logger.error(f"Failed to record host log: {e}")

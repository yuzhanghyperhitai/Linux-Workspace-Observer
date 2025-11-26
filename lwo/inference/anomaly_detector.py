"""Anomaly detection system for LWO."""

import time
from typing import Dict, Any, List, Optional
from collections import defaultdict, deque

from lwo.config import get_config
from lwo.storage.database import get_database
from lwo.storage.models import ShellCommand, FileEvent
from lwo.utils.logger import setup_logger

logger = setup_logger(__name__)


class AnomalyDetector:
    """Detect anomalies in user behavior that may indicate issues."""
    
    def __init__(self):
        """Initialize anomaly detector."""
        self.config = get_config()
        self.db = get_database()
        
        # Recent activity tracking
        self.command_history = deque(maxlen=100)
        self.file_edit_history = deque(maxlen=100)
        
        # Cooldown tracking (prevent duplicate triggers)
        self.last_trigger_time = {}
        self.cooldown_seconds = 1800  # 30 minutes
    
    def check_repeated_command(self, lookback_seconds: int = 300) -> Optional[Dict[str, Any]]:
        """Checks if user is repeatedly executing the same command.
        
        Args:
            lookback_seconds: Time window to check
            
        Returns:
            Anomaly context if detected, None otherwise
        """
        cutoff_time = int(time.time()) - lookback_seconds
        
        # Query recent commands using ORM
        with self.db.session() as session:
            recent_commands = (
                session.query(ShellCommand)
                .filter(ShellCommand.ts >= cutoff_time)
                .order_by(ShellCommand.ts.desc())
                .limit(50)
                .all()
            )
            
            if len(recent_commands) < 3:
                return None
            
            # Get the most recent command
            latest_command = recent_commands[0].sanitized_command or recent_commands[0].command
            
            # Count command repetitions
            command_counts = defaultdict(lambda: {'count': 0, 'pwds': set(), 'failed': []})
            
            for cmd in recent_commands:
                sanitized = cmd.sanitized_command or cmd.command
                command_counts[sanitized]['count'] += 1
                if cmd.pwd:
                    command_counts[sanitized]['pwds'].add(cmd.pwd)
                
                if cmd.exit_code != 0:
                    command_counts[sanitized]['failed'].append({
                        'command': sanitized,
                        'exit_code': cmd.exit_code,
                        'ts': cmd.ts,
                        'pwd': cmd.pwd
                    })
            
            # Find most repeated command
            most_common = max(command_counts.items(), key=lambda x: x[1]['count'])
            command, data = most_common
            count = data['count']
            
            # CRITICAL: Only trigger if the most recent command matches the repeated command
            # This prevents triggering on old repetitions
            if latest_command != command:
                return None
            
            # Trigger if repeated 3+ times and currently repeating
            if count >= 3:
                # Get working directory (prefer from failed commands, fallback to any pwd)
                pwd = None
                if data['failed']:
                    pwd = data['failed'][0]['pwd']
                elif data['pwds']:
                    pwd = list(data['pwds'])[0]
                
                return {
                    'type': 'repeated_command',
                    'command': command,
                    'count': count,
                    'pwd': pwd,
                    'failed_commands': data['failed'],
                    'time_window': lookback_seconds,
                    'severity': 'high' if count >= 5 else 'medium'
                }
        
        return None
    
    def check_file_thrashing(self, lookback_seconds: int = 600) -> Optional[Dict[str, Any]]:
        """Check if user is repeatedly editing the same file.
        
        Args:
            lookback_seconds: Time window to check
            
        Returns:
            Anomaly context if detected, None otherwise
        """
        cutoff_time = int(time.time()) - lookback_seconds
        
        with self.db.session() as session:
            recent_edits = session.query(FileEvent).filter(
                FileEvent.ts >= cutoff_time,
                FileEvent.event_type.in_(['MODIFIED', 'CREATED'])
            ).order_by(FileEvent.ts.desc()).limit(100).all()
            
            if len(recent_edits) < 5:
                return None
            
            # Count edits per file
            file_counts = defaultdict(int)
            for event in recent_edits:
                file_counts[event.file_path] += 1
            
            # Find most edited file
            most_edited = max(file_counts.items(), key=lambda x: x[1])
            filepath, edit_count = most_edited
            
            # Trigger if edited 5+ times
            if edit_count >= 5:
                return {
                    'type': 'file_thrashing',
                    'file': filepath,
                    'edit_count': edit_count,
                    'time_window': lookback_seconds,
                    'severity': 'high' if edit_count >= 10 else 'medium'
                }
        
        return None
    
    def check_high_error_rate(self, lookback_seconds: int = 300) -> Optional[Dict[str, Any]]:
        """Check if user has high command failure rate.
        
        Args:
            lookback_seconds: Time window to check
            
        Returns:
            Anomaly context if detected, None otherwise
        """
        cutoff_time = int(time.time()) - lookback_seconds
        
        with self.db.session() as session:
            recent_commands = session.query(ShellCommand).filter(
                ShellCommand.ts >= cutoff_time
            ).all()
            
            if len(recent_commands) < 5:
                return None
            
            failed = sum(1 for cmd in recent_commands if cmd.exit_code != 0)
            error_rate = failed / len(recent_commands)
            
            # Trigger if error rate > 50%
            if error_rate > 0.5 and failed >= 3:
                failed_details = [
                    {
                        'command': cmd.sanitized_command or cmd.command,
                        'exit_code': cmd.exit_code,
                        'ts': cmd.ts,
                        'pwd': cmd.pwd
                    }
                    for cmd in recent_commands if cmd.exit_code != 0
                ]
                
                return {
                    'type': 'high_error_rate',
                    'error_rate': error_rate,
                    'failed_count': failed,
                    'total_count': len(recent_commands),
                    'failed_commands': failed_details[:10],
                    'severity': 'high' if error_rate > 0.7 else 'medium'
                }
        
        return None
    
    def should_trigger(self, anomaly_type: str) -> bool:
        """Check if anomaly should trigger AI intervention (cooldown check).
        
        Args:
            anomaly_type: Type of anomaly
            
        Returns:
            True if should trigger
        """
        last_trigger = self.last_trigger_time.get(anomaly_type, 0)
        current_time = time.time()
        
        if current_time - last_trigger < self.cooldown_seconds:
            logger.debug(f"Anomaly {anomaly_type} in cooldown, skipping")
            return False
        
        self.last_trigger_time[anomaly_type] = current_time
        return True
    
    def detect_anomalies(self) -> List[Dict[str, Any]]:
        """Run all anomaly detection checks.
        
        Returns:
            List of detected anomalies
        """
        anomalies = []
        
        # Check repeated commands
        anomaly = self.check_repeated_command()
        if anomaly and self.should_trigger(anomaly['type']):
            anomalies.append(anomaly)
            logger.info(f"Detected anomaly: {anomaly['type']}")
        
        # Check file thrashing
        anomaly = self.check_file_thrashing()
        if anomaly and self.should_trigger(anomaly['type']):
            anomalies.append(anomaly)
            logger.info(f"Detected anomaly: {anomaly['type']}")
        
        # Check high error rate
        anomaly = self.check_high_error_rate()
        if anomaly and self.should_trigger(anomaly['type']):
            anomalies.append(anomaly)
            logger.info(f"Detected anomaly: {anomaly['type']}")
        
        # Check host errors
        anomaly = self.check_host_errors()
        if anomaly and self.should_trigger(anomaly['type']):
            anomalies.append(anomaly)
            logger.info(f"Detected anomaly: {anomaly['type']}")
        
        return anomalies
    
    def check_host_errors(self, lookback_seconds: int = 300) -> Optional[Dict[str, Any]]:
        """Checks for multiple host errors in short time.
        
        Args:
            lookback_seconds: Time window to check
            
        Returns:
            Anomaly context if detected, None otherwise
        """
        cutoff_time = int(time.time()) - lookback_seconds
        
        with self.db.session() as session:
            from lwo.storage.models import HostLog
            
            # Query ERROR-level logs
            error_logs = session.query(HostLog).filter(
                HostLog.ts >= cutoff_time,
                HostLog.level == 'ERROR'
            ).order_by(HostLog.ts.desc()).limit(20).all()
            
            if len(error_logs) < 3:
                return None
            
            # Count errors by service
            service_counts = {}
            for log in error_logs:
                service_counts[log.service] = service_counts.get(log.service, 0) + 1
            
            # Trigger if same service has 3+ errors or total 5+ errors
            max_service_errors = max(service_counts.values()) if service_counts else 0
            total_errors = len(error_logs)
            
            if max_service_errors >= 3 or total_errors >= 5:
                # Get most problematic service
                problem_service = max(service_counts.items(), key=lambda x: x[1])[0] if service_counts else 'unknown'
                
                return {
                    'type': 'host_errors',
                    'error_count': total_errors,
                    'problem_service': problem_service,
                    'service_counts': service_counts,
                    'recent_logs': [
                        {
                            'ts': log.ts,
                            'service': log.service,
                            'message': log.message
                        }
                        for log in error_logs[:5]
                    ],
                    'severity': 'high' if max_service_errors >= 5 else 'medium'
                }
        
        return None


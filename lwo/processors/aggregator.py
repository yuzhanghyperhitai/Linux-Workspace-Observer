"""Event aggregation engine for LWO."""

import time
from typing import List, Dict, Any
from collections import defaultdict

from lwo.config import get_config
from lwo.storage.database import get_database
from lwo.utils.logger import setup_logger

logger = setup_logger(__name__)


class EventAggregator:
    """Aggregate raw events into semantic events."""
    
    def __init__(self):
        """Initialize event aggregator."""
        self.config = get_config()
        self.db = get_database()
        self.time_window = 600  # 10 minutes in seconds
    
    def get_recent_commands(self, start_time: int, end_time: int) -> List[Dict[str, Any]]:
        """Get shell commands in time window.
        
        Args:
            start_time: Window start timestamp
            end_time: Window end timestamp
            
        Returns:
            List of command records
        """
        with self.db.session() as session:
            results = session.execute(
                """
                SELECT command, sanitized_command, pwd, ts, duration, exit_code
                FROM shell_commands
                WHERE ts >= :start AND ts <= :end
                ORDER BY ts
                """,
                {'start': start_time, 'end': end_time}
            ).fetchall()
            
            return [
                {
                    'command': r[0],
                    'sanitized_command': r[1],
                    'pwd': r[2],
                    'ts': r[3],
                    'duration': r[4],
                    'exit_code': r[5],
                }
                for r in results
            ]
    
    def get_recent_file_events(self, start_time: int, end_time: int) -> List[Dict[str, Any]]:
        """Get file events in time window.
        
        Args:
            start_time: Window start timestamp
            end_time: Window end timestamp
            
        Returns:
            List of file event records
        """
        with self.db.session() as session:
            results = session.execute(
                """
                SELECT file_path, event_type, ts
                FROM file_events
                WHERE ts >= :start AND ts <= :end
                ORDER BY ts
                """,
                {'start': start_time, 'end': end_time}
            ).fetchall()
            
            return [
                {
                    'file_path': r[0],
                    'event_type': r[1],
                    'ts': r[2],
                }
                for r in results
            ]
    
    def detect_high_intensity_debugging(self, commands: List[Dict[str, Any]]) -> Dict[str, Any] | None:
        """Detect high intensity debugging pattern.
        
        Pattern: 5+ failed builds/runs in 10 minutes
        
        Args:
            commands: Command records
            
        Returns:
            Event dict or None
        """
        # Build/compile/run commands
        build_patterns = ['make', 'gcc', 'g++', 'cargo build', 'npm run', 'pytest', 'python', 'java', 'mvn']
        
        failed_builds = []
        for cmd in commands:
            if cmd['exit_code'] != 0:
                for pattern in build_patterns:
                    if pattern in cmd['sanitized_command'].lower():
                        failed_builds.append(cmd)
                        break
        
        if len(failed_builds) >= 5:
            return {
                'type': 'high_intensity_debugging',
                'description': f"High intensity debugging detected: {len(failed_builds)} failed builds/runs",
                'details': {
                    'failed_count': len(failed_builds),
                    'commands': [c['sanitized_command'] for c in failed_builds[:5]],
                }
            }
        
        return None
    
    def detect_continuous_development(self, file_events: List[Dict[str, Any]]) -> Dict[str, Any] | None:
        """Detect continuous development pattern.
        
        Pattern: 10+ file modifications in 10 minutes
        
        Args:
            file_events: File event records
            
        Returns:
            Event dict or None
        """
        # Count unique modified files
        modified_files = set()
        for event in file_events:
            if event['event_type'] == 'MODIFIED':
                modified_files.add(event['file_path'])
        
        if len(modified_files) >= 10:
            # Get file extensions
            extensions = defaultdict(int)
            for path in modified_files:
                if '.' in path:
                    ext = path.rsplit('.', 1)[-1]
                    extensions[ext] += 1
            
            return {
                'type': 'continuous_development',
                'description': f"Continuous development: {len(modified_files)} files modified",
                'details': {
                    'file_count': len(modified_files),
                    'extensions': dict(extensions),
                }
            }
        
        return None
    
    def detect_documentation_writing(self, file_events: List[Dict[str, Any]]) -> Dict[str, Any] | None:
        """Detect documentation writing pattern.
        
        Pattern: 5+ markdown file modifications in 10 minutes
        
        Args:
            file_events: File event records
            
        Returns:
            Event dict or None
        """
        md_files = set()
        for event in file_events:
            if event['event_type'] in ['MODIFIED', 'CREATED']:
                if event['file_path'].endswith('.md'):
                    md_files.add(event['file_path'])
        
        if len(md_files) >= 5:
            return {
                'type': 'documentation_writing',
                'description': f"Documentation writing: {len(md_files)} markdown files edited",
                'details': {
                    'file_count': len(md_files),
                }
            }
        
        return None
    
    def detect_git_operations(self, commands: List[Dict[str, Any]]) -> Dict[str, Any] | None:
        """Detect Git operations pattern.
        
        Pattern: 3+ git commits/pushes in 10 minutes
        
        Args:
            commands: Command records
            
        Returns:
            Event dict or None
        """
        git_ops = []
        for cmd in commands:
            cmd_lower = cmd['sanitized_command'].lower()
            if 'git commit' in cmd_lower or 'git push' in cmd_lower:
                git_ops.append(cmd)
        
        if len(git_ops) >= 3:
            return {
                'type': 'git_operations',
                'description': f"Active Git operations: {len(git_ops)} commits/pushes",
                'details': {
                    'operation_count': len(git_ops),
                }
            }
        
        return None
    
    def aggregate_events(self, start_time: int, end_time: int) -> List[Dict[str, Any]]:
        """Aggregate events in time window.
        
        Args:
            start_time: Window start timestamp
            end_time: Window end timestamp
            
        Returns:
            List of aggregated events
        """
        # Get raw data
        commands = self.get_recent_commands(start_time, end_time)
        file_events = self.get_recent_file_events(start_time, end_time)
        
        aggregated = []
        
        # Apply detection rules
        event = self.detect_high_intensity_debugging(commands)
        if event:
            aggregated.append(event)
        
        event = self.detect_continuous_development(file_events)
        if event:
            aggregated.append(event)
        
        event = self.detect_documentation_writing(file_events)
        if event:
            aggregated.append(event)
        
        event = self.detect_git_operations(commands)
        if event:
            aggregated.append(event)
        
        return aggregated
    
    def save_aggregated_events(self, events: List[Dict[str, Any]], start_time: int, end_time: int):
        """Save aggregated events to database.
        
        Args:
            events: List of aggregated events
            start_time: Window start timestamp
            end_time: Window end timestamp
        """
        for event in events:
            try:
                self.db.insert_aggregated_event(
                    event_type=event['type'],
                    description=event['description'],
                    start_time=start_time,
                    end_time=end_time,
                    details=event.get('details', {})
                )
                logger.info(f"Aggregated event: {event['description']}")
            except Exception as e:
                logger.error(f"Failed to save aggregated event: {e}")
    
    async def run(self):
        """Run event aggregator periodically."""
        import asyncio
        
        logger.info("Event aggregator started")
        
        # Run every 10 minutes
        while True:
            try:
                await asyncio.sleep(self.time_window)
                
                # Aggregate events from last 10 minutes
                end_time = int(time.time())
                start_time = end_time - self.time_window
                
                events = self.aggregate_events(start_time, end_time)
                
                if events:
                    self.save_aggregated_events(events, start_time, end_time)
                    logger.debug(f"Aggregated {len(events)} events")
            
            except Exception as e:
                logger.error(f"Error in event aggregator: {e}")

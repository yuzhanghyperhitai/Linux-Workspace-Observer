"""Event aggregation engine for LWO."""

import time
import asyncio
from typing import List, Dict, Any

from lwo.config import get_config
from lwo.storage.database import get_database
from lwo.storage.models import ShellCommand, FileEvent,AggregatedEvent
from lwo.utils.logger import setup_logger

logger = setup_logger(__name__)


class EventAggregator:
    """Aggregate raw events into semantic events."""
    
    def __init__(self):
        """Initialize event aggregator."""
        self.config = get_config()
        self.db = get_database()
        self.time_window = 600  # 10 minutes in seconds
    
    def aggregate_events(self, start_time: int, end_time: int) -> List[Dict[str, Any]]:
        """Aggregate events within time window.
        
        Args:
            start_time: Window start timestamp
            end_time: Window end timestamp
            
        Returns:
            List of aggregated events
        """
        events = []
        
        with self.db.session() as session:
            # Rule 1: Detect high-intensity debugging using ORM
            failed_builds = (
                session.query(ShellCommand)
                .filter(
                    ShellCommand.ts >= start_time,
                    ShellCommand.ts <= end_time,
                    ShellCommand.exit_code != 0,
                    ShellCommand.sanitized_command.like('%build%') |
                    ShellCommand.sanitized_command.like('%compile%') |
                    ShellCommand.sanitized_command.like('%test%')
                )
                .count()
            )
            
            if failed_builds >= 5:
                events.append({
                    'event_type': 'high_intensity_debugging',
                    'description': f'High-intensity debugging: {failed_builds} failed builds/tests',
                    'start_time': start_time,
                    'end_time': end_time,
                    'details': {'failed_count': failed_builds}
                })
            
            # Rule 2: Continuous development using ORM
            file_events = (
                session.query(FileEvent)
                .filter(
                    FileEvent.ts >= start_time,
                    FileEvent.ts <= end_time,
                    FileEvent.event_type.in_(['MODIFIED', 'CREATED'])
                )
                .all()
            )
            
            unique_files = set(event.file_path for event in file_events)
            if len(unique_files) >= 10:
                events.append({
                    'event_type': 'continuous_development',
                    'description': f'Continuous development: {len(unique_files)} files modified',
                    'start_time': start_time,
                    'end_time': end_time,
                    'details': {'file_count': len(unique_files)}
                })
            
            # Rule 3: Documentation writing using ORM
            doc_files_count = (
                session.query(FileEvent)
                .filter(
                    FileEvent.ts >= start_time,
                    FileEvent.ts <= end_time,
                    FileEvent.file_path.like('%.md') |
                    FileEvent.file_path.like('%.rst') |
                    FileEvent.file_path.like('%.txt')
                )
                .count()
            )
            
            if doc_files_count >= 5:
                events.append({
                    'event_type': 'documentation_writing',
                    'description': f'Documentation writing: {doc_files_count} doc files modified',
                    'start_time': start_time,
                    'end_time': end_time,
                    'details': {'doc_count': doc_files_count}
                })
            
            # Rule 4: Git operations using ORM
            git_commands = (
                session.query(ShellCommand)
                .filter(
                    ShellCommand.ts >= start_time,
                    ShellCommand.ts <= end_time,
                    ShellCommand.sanitized_command.like('git commit%') |
                    ShellCommand.sanitized_command.like('git push%')
                )
                .count()
            )
            
            if git_commands >= 3:
                events.append({
                    'event_type': 'git_operations',
                    'description': f'Git operations: {git_commands} commits/pushes',
                    'start_time': start_time,
                    'end_time': end_time,
                    'details': {'git_count': git_commands}
                })
        
        return events
    
    def save_aggregated_events(self, events: List[Dict[str, Any]]):
        """Save aggregated events to database using ORM.
        
        Args:
            events: List of aggregated events
        """
        with self.db.session() as session:
            for event in events:
                try:
                    aggregated_event = AggregatedEvent(
                        event_type=event['event_type'],
                        description=event['description'],
                        start_time=event['start_time'],
                        end_time=event['end_time'],
                        details=event.get('details', {})
                    )
                    session.add(aggregated_event)
                    session.commit()
                    logger.info(f"Aggregated event: {event['description']}")
                except Exception as e:
                    logger.error(f"Failed to save aggregated event: {e}")
                    session.rollback()
    
    async def run(self):
        """Run event aggregator periodically."""
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
                    self.save_aggregated_events(events)
                    logger.debug(f"Aggregated {len(events)} events")
            
            except Exception as e:
                logger.error(f"Error in event aggregator: {e}")

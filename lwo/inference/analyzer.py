"""Work status analyzer for LWO."""

import time
from typing import Dict, Any, List

from sqlalchemy import text

from lwo.config import get_config
from lwo.storage.database import get_database
from lwo.inference.openai_client import LWOOpenAIClient
from lwo.utils.logger import setup_logger

logger = setup_logger(__name__)


class WorkStatusAnalyzer:
    """Analyze work status using OpenAI."""
    
    def __init__(self):
        """Initialize work status analyzer."""
        self.config = get_config()
        self.db = get_database()
        self.openai_client = LWOOpenAIClient()
        self.analysis_interval = 600  # 10 minutes
    
    def get_recent_data(self, lookback_seconds: int = 600) -> Dict[str, List[Dict[str, Any]]]:
        """Get recent data for analysis.
        
        Args:
            lookback_seconds: How far back to look (default: 10 minutes)
            
        Returns:
            Dict with commands, git_contexts, events, processes
        """
        end_time = int(time.time())
        start_time = end_time - lookback_seconds
        
        data = {
            'commands': [],
            'git_contexts': [],
            'aggregated_events': [],
            'process_snapshots': []
        }
        
        with self.db.session() as session:
            # Get shell commands
            cmd_results = session.execute(
                text("""
                SELECT sanitized_command, exit_code, ts, duration
                FROM shell_commands
                WHERE ts >= :start AND ts <= :end
                ORDER BY ts DESC
                LIMIT 50
                """),
                {'start': start_time, 'end': end_time}
            ).fetchall()
            
            data['commands'] = [
                {
                    'sanitized_command': r[0],
                    'exit_code': r[1],
                    'ts': r[2],
                    'duration': r[3]
                }
                for r in cmd_results
            ]
            
            # Get Git contexts
            git_results = session.execute(
                text("""
                SELECT repo_path, branch, branch_type, ts
                FROM git_contexts
                WHERE ts >= :start AND ts <= :end
                ORDER BY ts DESC
                LIMIT 10
                """),
                {'start': start_time, 'end': end_time}
            ).fetchall()
            
            data['git_contexts'] = [
                {
                    'repo_path': r[0],
                    'branch': r[1],
                    'branch_type': r[2],
                    'ts': r[3]
                }
                for r in git_results
            ]
            
            # Get aggregated events
            event_results = session.execute(
                text("""
                SELECT event_type, description, details
                FROM aggregated_events
                WHERE start_time >= :start
                ORDER BY start_time DESC
                LIMIT 10
                """),
                {'start': start_time}
            ).fetchall()
            
            data['aggregated_events'] = [
                {
                    'event_type': r[0],
                    'description': r[1],
                    'details': r[2]
                }
                for r in event_results
            ]
            
            # Get process snapshots (unique processes in time window)
            proc_results = session.execute(
                text("""
                SELECT DISTINCT ON (process_name) 
                    process_name, cpu_percent, memory_mb
                FROM process_snapshots
                WHERE ts >= :start AND ts <= :end
                ORDER BY process_name, ts DESC
                """),
                {'start': start_time, 'end': end_time}
            ).fetchall()
            
            data['process_snapshots'] = [
                {
                    'process_name': r[0],
                    'cpu_percent': r[1],
                    'memory_mb': r[2]
                }
                for r in proc_results
            ]
        
        return data
    
    def analyze(self) -> Dict[str, Any]:
        """Perform work status analysis.
        
        Returns:
            Analysis result with status, summary, confidence
        """
        try:
            # Get recent data
            data = self.get_recent_data()
            
            # Check if we have any data
            total_data = sum(len(v) for v in data.values())
            if total_data == 0:
                logger.info("No recent activity to analyze")
                return {
                    'status': 'Idle',
                    'summary': 'No recent activity detected',
                    'confidence': 1.0
                }
            
            # Analyze with OpenAI
            result = self.openai_client.analyze_work_status(
                commands=data['commands'],
                git_contexts=data['git_contexts'],
                aggregated_events=data['aggregated_events'],
                process_snapshots=data['process_snapshots']
            )
            
            # Save to database
            ts = int(time.time())
            self.db.insert_analysis(
                ts=ts,
                status=result['status'],
                summary=result['summary'],
                confidence=result.get('confidence', 0.5)
            )
            
            logger.info(f"Analysis completed: {result['status']} - {result['summary']}")
            return result
        
        except Exception as e:
            logger.error(f"Failed to perform analysis: {e}")
            return {
                'status': 'Error',
                'summary': f'Analysis failed: {str(e)}',
                'confidence': 0.0
            }
    
    async def run(self):
        """Run periodic analysis."""
        import asyncio
        
        logger.info(f"Work status analyzer started (interval: {self.analysis_interval}s)")
        
        # Wait a bit before first analysis
        # await asyncio.sleep(self.analysis_interval)
        
        while True:
            try:
                # Run analysis in thread pool to avoid blocking
                loop = asyncio.get_event_loop()
                await loop.run_in_executor(None, self.analyze)
                
                await asyncio.sleep(self.analysis_interval)
            
            except Exception as e:
                logger.error(f"Error in analyzer: {e}")
                await asyncio.sleep(self.analysis_interval)

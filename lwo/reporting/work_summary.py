"""Work summary generator with AI-powered analysis."""

import time
from datetime import datetime
from typing import Dict, Any
from collections import defaultdict

from lwo.config import get_config
from lwo.storage.database import get_database
from lwo.storage.models import ShellCommand, FileEvent, GitContext, HostLog
from lwo.inference.agent_intervention import AIAgentIntervention
from lwo.utils.logger import setup_logger

logger = setup_logger(__name__)


class WorkSummaryGenerator:
    """Generates AI-powered work summaries from activity data."""
    
    def __init__(self):
        """Initializes work summary generator."""
        self.config = get_config()
        self.db = get_database()
        self.ai_agent = AIAgentIntervention()
    
    def generate_summary(self, hours: int = 4) -> Dict[str, Any]:
        """Generates work summary for recent activity.
        
        Args:
            hours: Number of hours to look back
            
        Returns:
            Summary dict with statistics and AI narrative
        """
        cutoff_time = int(time.time()) - (hours * 3600)
        
        # Collect activity data
        stats = self._collect_statistics(cutoff_time)
        
        # Generate AI summary if enough activity
        if stats['total_commands'] > 5:
            ai_summary = self._generate_ai_summary(stats, hours)
        else:
            ai_summary = "Limited activity detected in this time period."
        
        return {
            'time_range': {
                'hours': hours,
                'start': datetime.fromtimestamp(cutoff_time).strftime('%Y-%m-%d %H:%M:%S'),
                'end': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            },
            'statistics': stats,
            'ai_summary': ai_summary
        }
    
    def _collect_statistics(self, cutoff_time: int) -> Dict[str, Any]:
        """Collects activity statistics.
        
        Args:
            cutoff_time: Unix timestamp for time cutoff
            
        Returns:
            Statistics dict
        """
        stats = {
            'total_commands': 0,
            'failed_commands': 0,
            'unique_directories': set(),
            'file_modifications': 0,
            'file_languages': defaultdict(int),
            'git_activity': None,
            'top_commands': [],
            'host_errors': 0
        }
        
        with self.db.session() as session:
            # Shell commands
            commands = session.query(ShellCommand).filter(
                ShellCommand.ts >= cutoff_time
            ).all()
            
            stats['total_commands'] = len(commands)
            stats['failed_commands'] = sum(1 for cmd in commands if cmd.exit_code != 0)
            
            # Count command patterns
            cmd_counts = defaultdict(int)
            for cmd in commands:
                stats['unique_directories'].add(cmd.pwd)
                # Get first word as command type
                first_word = cmd.sanitized_command.split()[0] if cmd.sanitized_command else ''
                cmd_counts[first_word] += 1
            
            stats['top_commands'] = sorted(
                cmd_counts.items(), 
                key=lambda x: x[1], 
                reverse=True
            )[:5]
            
            # File events
            file_events = session.query(FileEvent).filter(
                FileEvent.ts >= cutoff_time,
                FileEvent.event_type.in_(['MODIFIED', 'CREATED'])
            ).all()
            
            stats['file_modifications'] = len(file_events)
            
            # Count by file extension
            for event in file_events:
                if '.' in event.file_path:
                    ext = event.file_path.rsplit('.', 1)[1]
                    stats['file_languages'][ext] += 1
            
            # Git context
            git_ctx = session.query(GitContext).filter(
                GitContext.ts >= cutoff_time
            ).order_by(GitContext.ts.desc()).first()
            
            if git_ctx:
                stats['git_activity'] = {
                    'branch': git_ctx.branch,
                    'branch_type': git_ctx.branch_type,
                    'repo': git_ctx.repo_path
                }
            
            # Host errors
            host_errors = session.query(HostLog).filter(
                HostLog.ts >= cutoff_time,
                HostLog.level == 'ERROR'
            ).count()
            
            stats['host_errors'] = host_errors
        
        # Convert set to count
        stats['unique_directories'] = len(stats['unique_directories'])
        
        return stats
    
    def _generate_ai_summary(self, stats: Dict[str, Any], hours: int) -> str:
        """Generates AI narrative summary.
        
        Args:
            stats: Activity statistics
            hours: Time range in hours
            
        Returns:
            AI-generated summary text
        """
        # Build prompt
        prompt = self._build_summary_prompt(stats, hours)
        
        try:
            # Use AI agent's LLM directly
            from langchain_core.messages import HumanMessage
            
            messages = [HumanMessage(content=prompt)]
            response = self.ai_agent.llm.invoke(messages)
            
            return response.content.strip()
        
        except Exception as e:
            logger.error(f"Failed to generate AI summary: {e}")
            return "Unable to generate AI summary at this time."
    
    def _build_summary_prompt(self, stats: Dict[str, Any], hours: int) -> str:
        """Builds prompt for AI summary generation.
        
        Args:
            stats: Activity statistics
            hours: Time range
            
        Returns:
            Prompt string
        """
        git_info = ""
        if stats['git_activity']:
            git_info = f"\n- Git branch: {stats['git_activity']['branch']} ({stats['git_activity']['branch_type']})"
        
        top_cmds = ", ".join([f"{cmd} ({count}x)" for cmd, count in stats['top_commands'][:3]])
        
        languages = ", ".join([f"{lang} ({count})" for lang, count in 
                              sorted(stats['file_languages'].items(), key=lambda x: x[1], reverse=True)[:3]])
        
        return f"""Based on the following developer activity over the last {hours} hours, generate a concise 2-3 sentence summary of what the user was working on:

Activity Statistics:
- Total commands: {stats['total_commands']} ({stats['failed_commands']} failed)
- Directories worked in: {stats['unique_directories']}
- Files modified: {stats['file_modifications']}{f" ({languages})" if languages else ""}
- Top commands: {top_cmds}{git_info}
- System errors: {stats['host_errors']}

Summary:"""
    
    def format_summary(self, summary: Dict[str, Any]) -> str:
        """Formats summary for console output.
        
        Args:
            summary: Summary dict from generate_summary()
            
        Returns:
            Formatted string
        """
        output = []
        output.append("\n" + "=" * 70)
        output.append("                    LWO WORK SUMMARY".center(70))
        output.append("=" * 70)
        
        # Time range
        tr = summary['time_range']
        output.append(f"\n📅 Period: {tr['start']} → {tr['end']}")
        output.append(f"   Duration: {tr['hours']} hours")
        
        # Statistics
        stats = summary['statistics']
        output.append("\n" + "-" * 70)
        output.append("📊 ACTIVITY STATISTICS")
        output.append("-" * 70)
        output.append(f"Commands executed: {stats['total_commands']} ({stats['failed_commands']} failed)")
        output.append(f"Directories: {stats['unique_directories']}")
        output.append(f"Files modified: {stats['file_modifications']}")
        
        if stats['file_languages']:
            langs = ", ".join([f"{lang}({count})" for lang, count in 
                              sorted(stats['file_languages'].items(), key=lambda x: x[1], reverse=True)[:5]])
            output.append(f"Languages: {langs}")
        
        if stats['git_activity']:
            git = stats['git_activity']
            output.append(f"\n🌿 Git: {git['branch']} ({git['branch_type']})")
        
        if stats['host_errors'] > 0:
            output.append(f"\n⚠️  Host errors: {stats['host_errors']}")
        
        # AI Summary
        output.append("\n" + "-" * 70)
        output.append("🤖 AI SUMMARY")
        output.append("-" * 70)
        output.append(summary['ai_summary'])
        
        output.append("\n" + "=" * 70 + "\n")
        
        return "\n".join(output)

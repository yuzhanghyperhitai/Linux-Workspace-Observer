"""OpenAI client for LWO."""

from typing import Dict, Any, List, Optional
from openai import OpenAI

from lwo.config import get_config
from lwo.utils.logger import setup_logger

logger = setup_logger(__name__)


class LWOOpenAIClient:
    """OpenAI client wrapper for LWO."""
    
    def __init__(self):
        """Initialize OpenAI client."""
        self.config = get_config()
        
        # Get OpenAI configuration
        api_key = self.config.get('openai', 'api_key')
        model = self.config.get('openai', 'model', 'gpt-4o')
        base_url = self.config.get('openai', 'base_url')
        
        if not api_key:
            raise ValueError("OpenAI API key not configured")
        
        # Initialize client
        client_kwargs = {'api_key': api_key}
        if base_url:
            client_kwargs['base_url'] = base_url
        
        self.client = OpenAI(**client_kwargs)
        self.model = model
        
        logger.info(f"OpenAI client initialized (model: {model})")
    
    def analyze_work_status(
        self,
        commands: List[Dict[str, Any]],
        git_contexts: List[Dict[str, Any]],
        aggregated_events: List[Dict[str, Any]],
        process_snapshots: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """Analyze work status based on collected data.
        
        Args:
            commands: Recent shell commands
            git_contexts: Recent Git contexts
            aggregated_events: Aggregated events
            process_snapshots: Process snapshots
            
        Returns:
            Dict with keys: status, summary, confidence
        """
        # Build context for LLM
        context = self._build_context(commands, git_contexts, aggregated_events, process_snapshots)
        
        # Create system prompt
        system_prompt = """You are an intelligent work status analyzer. Based on user's shell commands, Git activities, file changes, and running processes, determine their current work status.

Your task:
1. Classify the work status into ONE of: Coding, Debugging, Learning, Documentation, DevOps, Idle
2. Provide a concise 1-2 sentence summary of what the user is doing
3. Rate your confidence (0.0-1.0)

Respond in JSON format:
{
  "status": "Coding|Debugging|Learning|Documentation|DevOps|Idle",
  "summary": "Brief description of current work",
  "confidence": 0.85
}"""
        
        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": context}
                ],
                temperature=0.3,
                response_format={"type": "json_object"}
            )
            
            result = response.choices[0].message.content
            import json
            parsed = json.loads(result)
            
            logger.info(f"Work status analyzed: {parsed['status']} (confidence: {parsed['confidence']})")
            return parsed
        
        except Exception as e:
            logger.error(f"Failed to analyze work status: {e}")
            return {
                "status": "Unknown",
                "summary": "Failed to analyze work status",
                "confidence": 0.0
            }
    
    def _build_context(
        self,
        commands: List[Dict[str, Any]],
        git_contexts: List[Dict[str, Any]],
        aggregated_events: List[Dict[str, Any]],
        process_snapshots: List[Dict[str, Any]]
    ) -> str:
        """Build context string for LLM.
        
        Args:
            commands: Recent shell commands
            git_contexts: Recent Git contexts
            aggregated_events: Aggregated events
            process_snapshots: Process snapshots
            
        Returns:
            Context string
        """
        lines = []
        
        # Recent commands
        if commands:
            lines.append("## Recent Shell Commands")
            for cmd in commands[:20]:  # Last 20 commands
                sanitized = cmd.get('sanitized_command', cmd.get('command', ''))
                exit_code = cmd.get('exit_code', 0)
                status = "✓" if exit_code == 0 else "✗"
                lines.append(f"- {status} {sanitized}")
            lines.append("")
        
        # Git contexts
        if git_contexts:
            lines.append("## Git Context")
            for ctx in git_contexts[:5]:  # Last 5 contexts
                repo = ctx.get('repo_path', 'Unknown')
                branch = ctx.get('branch', 'unknown')
                branch_type = ctx.get('branch_type', 'other')
                lines.append(f"- Repository: {repo}")
                lines.append(f"  Branch: {branch} (type: {branch_type})")
            lines.append("")
        
        # Aggregated events
        if aggregated_events:
            lines.append("## Activity Patterns")
            for event in aggregated_events:
                event_type = event.get('event_type', 'unknown')
                description = event.get('description', '')
                lines.append(f"- {event_type}: {description}")
            lines.append("")
        
        # Running processes
        if process_snapshots:
            lines.append("## Active Processes")
            process_names = list(set(p.get('process_name', 'unknown') for p in process_snapshots))
            for name in process_names[:10]:  # Top 10 unique processes
                lines.append(f"- {name}")
            lines.append("")
        
        if not lines:
            return "No recent activity detected."
        
        return "\n".join(lines)

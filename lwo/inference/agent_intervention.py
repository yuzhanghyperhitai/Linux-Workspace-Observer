"""AI Agent intervention system for LWO using LangChain."""

import time
import asyncio
from typing import Dict, Any, List, Optional

from langchain.chat_models import init_chat_model
from langchain.agents import create_agent
from langchain.agents.structured_output import ToolStrategy
from langchain_core.callbacks.base import BaseCallbackHandler
from langchain_core.agents import AgentAction, AgentFinish
from langchain_core.outputs import LLMResult

from lwo.config import get_config
from lwo.storage.database import get_database
from lwo.storage.models import AIIntervention
from lwo.inference.agent_tools import AGENT_TOOLS
from lwo.inference.agent_schemas import AnomalyAnalysis
from lwo.utils.logger import setup_logger

logger = setup_logger(__name__)


class AgentLogCallback(BaseCallbackHandler):
    """Custom callback handler to log agent steps."""
    
    def on_llm_start(self, serialized: Dict[str, Any], prompts: List[str], **kwargs) -> None:
        """Log when LLM starts."""
        logger.info("🤖 LLM call started")
        logger.debug(f"Prompt: {prompts[0][:200]}..." if prompts else "No prompt")
    
    def on_llm_end(self, response: LLMResult, **kwargs) -> None:
        """Log when LLM ends."""
        logger.info("✅ LLM call completed")
    
    def on_llm_error(self, error: Exception, **kwargs) -> None:
        """Log LLM errors."""
        logger.error(f"❌ LLM error: {error}")
    
    def on_tool_start(self, serialized: Dict[str, Any], input_str: str, **kwargs) -> None:
        """Log when a tool starts."""
        tool_name = serialized.get('name', 'unknown')
        logger.info(f"🔧 Tool call: {tool_name}")
        logger.info(f"   Arguments: {input_str}")
    
    def on_tool_end(self, output: Any, **kwargs) -> None:
        """Log when a tool ends."""
        # Extract output content safely
        content = ""
        if hasattr(output, 'content'):
            content = str(output.content)
        else:
            content = str(output)
        
        # Truncate long output
        if len(content) > 200:
            content = content[:200] + "... (truncated)"
        
        logger.info("✅ Tool completed")
        logger.info("   Result: %s" % content)
    
    def on_tool_error(self, error: Exception, **kwargs) -> None:
        """Log tool errors."""
        logger.error(f"❌ Tool error: {error}")
    
    def on_agent_action(self, action: AgentAction, **kwargs) -> None:
        """Log agent actions."""
        logger.info(f"🎯 Agent decided to call: {action.tool}")
        logger.info(f"   With arguments: {action.tool_input}")
    
    def on_agent_finish(self, finish: AgentFinish, **kwargs) -> None:
        """Log when agent finishes."""
        logger.info("🏁 Agent execution finished")


class AIAgentIntervention:
    """AI Agent that intervenes when anomalies are detected."""
    
    def __init__(self):
        """Initialize AI Agent intervention system."""
        self.config = get_config()
        self.db = get_database()
        
        # Get AI configuration (unified config section)
        api_key = self.config.get('ai', 'api_key')
        model = self.config.get('ai', 'model', 'gemini-2.5-flash-lite')
        
        if not api_key:
            raise ValueError("AI API key not configured. Please set 'api_key' in [ai] section of config file.")
        
        # Initialize Gemini model
        llm = init_chat_model(
            f"google_genai:{model}",
            api_key=api_key,
            temperature=0.3
        )
        
        # Get system instructions
        system_prompt = self._get_system_instructions()
        
        # Create custom callback
        self.callback = AgentLogCallback()
        
        # Create Agent with structured output and verbose logging
        self.agent = create_agent(
            model=llm,
            tools=AGENT_TOOLS,
            response_format=ToolStrategy(AnomalyAnalysis),
            system_prompt=system_prompt
        )
        
        logger.info(f"AI Agent initialized (model: {model})")
    
    def _get_system_instructions(self) -> str:
        """Get system instructions for the Agent.
        
        Returns:
            System instructions string
        """
        return """You are an intelligent development assistant monitoring a developer's workspace.

Your role:
1. Analyze the user's current situation when anomalies are detected
2. Use available tools to gather more context
3. Understand what the user is trying to do and what problems they're facing
4. Provide helpful analysis and suggestions

CRITICAL - Tool Usage Guidelines:
1. **Read tool descriptions carefully**: Each tool has specific requirements for its parameters
2. **Infer missing information**: Extract required parameters from the anomaly context
   - Working directories are mentioned in error messages (e.g., "Exit code X in /path/to/dir")
   - File names are in the command being analyzed
   - Combine context clues to construct complete parameters
3. **Follow parameter constraints**: 
   - If a tool requires absolute paths, construct them from directory + filename
   - If a tool requires specific formats, adhere to them strictly
   - Check tool documentation for examples of correct usage
4. **Don't assume**: If information is missing and cannot be inferred, note it in your analysis

Example of good parameter inference:
- Anomaly says: "Exit code 1 in /home/user/project" + "vim test.py"
- Tool requires: absolute file path
- You should use: "/home/user/project/test.py" (directory + filename)

Guidelines:
- Be proactive: Use tools to gather information
- Be thorough: Investigate root causes, not just symptoms
- Be helpful: Provide specific, actionable suggestions
- Be concise: Keep analysis focused and to the point
- Be precise: Construct tool parameters carefully from context

You MUST respond with structured output containing:
- situation, issue, root_cause, analysis, suggestions, confidence"""
    
    async def analyze_anomaly(self, anomaly: Dict[str, Any]) -> Dict[str, Any]:
        """Analyze an anomaly using AI Agent.
        
        Args:
            anomaly: Anomaly context from detector
            
        Returns:
            Analysis result
        """
        try:
            # Build user message from anomaly context
            user_message = self._build_user_message(anomaly)
            
            logger.info(f"AI Agent analyzing anomaly: {anomaly['type']}")
            logger.info("=" * 60)
            
            # Run Agent with callback and timeout (wrap synchronous call in async)
            # Use wait_for to allow cancellation
            try:
                result = await asyncio.wait_for(
                    asyncio.to_thread(
                        self.agent.invoke,
                        {"messages": [{"role": "user", "content": user_message}]},
                        config={"callbacks": [self.callback]}
                    ),
                    timeout=120.0  # 2 minutes timeout
                )
            except asyncio.TimeoutError:
                logger.error("AI Agent analysis timed out (120s)")
                raise
            except asyncio.CancelledError:
                logger.warning("AI Agent analysis was cancelled")
                raise
            
            logger.info("=" * 60)
            
            # Extract structured response
            structured = result.get("structured_response")  # AnomalyAnalysis object
            
            # Fallback: extract JSON from markdown if structured_response is None
            if not structured:
                logger.warning("No structured_response, attempting to extract from last message")
                structured = self._extract_json_from_messages(result.get("messages", []))
            
            if not structured:
                logger.error(f"Failed to extract structured response, result keys: {result.keys()}")
                raise ValueError("No structured response from agent")
            
            # Build analysis dict
            analysis = {
                'anomaly_type': anomaly['type'],
                'situation': structured.situation,
                'issue': structured.issue,
                'root_cause': structured.root_cause,
                'analysis': structured.analysis,
                'suggestions': structured.suggestions,
                'confidence': structured.confidence,
                'timestamp': int(time.time())
            }
            
            # Extract tool calls if available
            tools_used = []
            for msg in result.get("messages", []):
                if hasattr(msg, 'tool_calls') and msg.tool_calls:
                    tools_used.extend([call.get('name', '') for call in msg.tool_calls])
            
            analysis['tools_used'] = tools_used
            
            logger.info(f"AI Agent analysis complete, used {len(tools_used)} tools")
            
            return analysis
        
        except Exception as e:
            logger.error(f"Failed to analyze anomaly with AI Agent: {e}")
            raise
    
    def _extract_json_from_messages(self, messages: list) -> Optional[Any]:
        """Extracts JSON from markdown-wrapped content in messages.
        
        Args:
            messages: List of messages from agent
            
        Returns:
            Parsed AnomalyAnalysis object or None
        """
        import re
        import json
        from lwo.inference.agent_schemas import AnomalyAnalysis
        
        # Look for last AIMessage with content
        for msg in reversed(messages):
            if hasattr(msg, 'content') and msg.content:
                content = msg.content.strip()
                
                # Try to extract JSON from markdown code block
                json_match = re.search(r'```(?:json)?\s*\n?(.*?)\n?```', content, re.DOTALL)
                if json_match:
                    json_str = json_match.group(1).strip()
                else:
                    # Try parsing content directly
                    json_str = content
                
                try:
                    data = json.loads(json_str)
                    # Create AnomalyAnalysis object from dict
                    return AnomalyAnalysis(**data)
                except (json.JSONDecodeError, TypeError, ValueError) as e:
                    logger.debug(f"Failed to parse JSON from message: {e}")
                    continue
        
        return None
    
    def _build_user_message(self, anomaly: Dict[str, Any]) -> str:
        """Build user message from anomaly context.
        
        Args:
            anomaly: Anomaly context
            
        Returns:
            Formatted message
        """
        anomaly_type = anomaly['type']
        
        if anomaly_type == 'repeated_command':
            command = anomaly.get('command', 'unknown')
            count = anomaly.get('count', 0)
            pwd = anomaly.get('pwd')
            failed = anomaly.get('failed_commands', [])
            
            msg = f"ANOMALY DETECTED: User has executed the same command {count} times in the last {anomaly.get('time_window', 300)} seconds.\n\n"
            msg += f"Repeated command: {command}\n"
            
            # Always include pwd if available
            if pwd:
                msg += f"Working directory: {pwd}\n"
                msg += f"For file operations, use ABSOLUTE paths: {pwd}/filename\n"
            
            if failed:
                msg += f"\nFailed executions ({len(failed)}):\n"
                for f in failed[:3]:
                    msg += f"  - Exit code {f['exit_code']} at {f.get('pwd', 'unknown')}\n"
            
            msg += "\nPlease investigate what the user is trying to do and why this command keeps failing or being repeated."
        
        elif anomaly_type == 'file_thrashing':
            filepath = anomaly.get('file', 'unknown')
            count = anomaly.get('edit_count', 0)
            
            msg = f"ANOMALY DETECTED: User has edited the same file {count} times in the last {anomaly.get('time_window', 600)} seconds.\n\n"
            msg += f"File: {filepath}\n\n"
            msg += "Please investigate what changes are being made and why the user keeps editing this file."
        
        elif anomaly_type == 'high_error_rate':
            error_rate = anomaly.get('error_rate', 0)
            failed_count = anomaly.get('failed_count', 0)
            
            msg = f"ANOMALY DETECTED: High command failure rate detected ({error_rate:.0%}).\n\n"
            msg += f"Failed commands: {failed_count}\n\n"
            msg += "Recent failures:\n"
            for f in anomaly.get('failed_commands', [])[:3]:
                msg += f"  - {f['command']} (exit code {f['exit_code']})\n"
            
            msg += "\nPlease investigate what's causing these failures."
        
        else:
            msg = f"ANOMALY DETECTED: {anomaly_type}\n\n{anomaly}"
        
        return msg
    
    def save_intervention(self, anomaly: Dict[str, Any], analysis: Dict[str, Any]):
        """Save AI intervention to database.
        
        Args:
            anomaly: Original anomaly context
            analysis: AI analysis result
        """
        try:
            with self.db.session() as session:
                intervention = AIIntervention(
                    ts=analysis.get('timestamp', int(time.time())),
                    anomaly_type=anomaly['type'],
                    trigger_context=anomaly,
                    analysis_result=analysis,
                    tools_used=analysis.get('tools_used', []),
                    confidence=analysis.get('confidence', 0.0)
                )
                session.add(intervention)
                session.commit()
                
                logger.info(f"Saved AI intervention to database (id: {intervention.id})")
        
        except Exception as e:
            logger.error(f"Failed to save AI intervention: {e}")

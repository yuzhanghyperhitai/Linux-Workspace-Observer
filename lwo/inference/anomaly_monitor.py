"""Anomaly monitoring service for LWO."""

import asyncio
from typing import Optional

from lwo.config import get_config
from lwo.inference.anomaly_detector import AnomalyDetector
from lwo.inference.agent_intervention import AIAgentIntervention
from lwo.utils.logger import setup_logger

logger = setup_logger(__name__)


class AnomalyMonitor:
    """Event-driven anomaly monitor that triggers AI interventions."""
    
    def __init__(self):
        """Initialize anomaly monitor."""
        self.config = get_config()
        self.detector = AnomalyDetector()
        self.agent_intervention: Optional[AIAgentIntervention] = None
        
        # Try to initialize AI Agent
        try:
            self.agent_intervention = AIAgentIntervention()
            logger.info("AI Agent intervention system initialized")
        except Exception as e:
            logger.warning(f"Failed to initialize AI Agent: {e}")
            logger.warning("Anomaly detection will run without AI intervention")
    
    async def on_command_received(self):
        """Called when a new shell command is received.
        
        Checks for command-related anomalies and triggers AI if needed.
        """
        try:
            # Check for repeated commands
            anomaly = self.detector.check_repeated_command()
            if anomaly:
                await self._trigger_intervention(anomaly)
            
            # Check for high error rate
            anomaly = self.detector.check_high_error_rate()
            if anomaly:
                await self._trigger_intervention(anomaly)
        
        except Exception as e:
            logger.error(f"Error checking command anomalies: {e}")
    
    async def on_file_event(self):
        """Called when a file event is detected.
        
        Checks for file-related anomalies and triggers AI if needed.
        """
        try:
            # Check for file thrashing
            anomaly = self.detector.check_file_thrashing()
            if anomaly:
                await self._trigger_intervention(anomaly)
        
        except Exception as e:
            logger.error(f"Error checking file anomalies: {e}")
    
    async def _trigger_intervention(self, anomaly: dict):
        """Trigger AI intervention for an anomaly.
        
        Args:
            anomaly: Anomaly context
        """
        try:
            logger.info(f"⚠️  Anomaly detected: {anomaly['type']} (severity: {anomaly.get('severity', 'unknown')})")
            
            # If AI Agent is available, analyze
            if self.agent_intervention:
                logger.info(f"🤖 Triggering AI Agent analysis...")
                
                # Run analysis in background to avoid blocking
                asyncio.create_task(self._run_analysis(anomaly))
            else:
                logger.warning(f"Anomaly detected but AI Agent unavailable: {anomaly['type']}")
        
        except Exception as e:
            logger.error(f"Failed to trigger intervention: {e}")
    
    async def _run_analysis(self, anomaly: dict):
        """Run AI analysis in background.
        
        Args:
            anomaly: Anomaly context
        """
        try:
            analysis = await self.agent_intervention.analyze_anomaly(anomaly)
            
            # Save intervention to database
            self.agent_intervention.save_intervention(anomaly, analysis)
            
            logger.info(f"✅ AI Agent completed analysis for {anomaly['type']}")
            
            # Log key findings
            if 'issue' in analysis:
                logger.info(f"   Issue: {analysis['issue']}")
            if 'suggestions' in analysis and analysis['suggestions']:
                logger.info(f"   Suggestions: {len(analysis['suggestions'])} found")
        
        except Exception as e:
            logger.error(f"Failed to complete AI analysis: {e}")

"""Anomaly monitoring and AI intervention orchestration."""

import asyncio
from typing import Dict, Any

from lwo.config import get_config
from lwo.inference.anomaly_detector import AnomalyDetector
from lwo.inference.agent_intervention import AIAgentIntervention
from lwo.notifications import create_notifier
from lwo.utils.logger import setup_logger

logger = setup_logger(__name__)


class AnomalyMonitor:
    """Monitor for anomalies and trigger AI intervention."""
    
    def __init__(self):
        """Initialize anomaly monitor."""
        self.config = get_config()
        self.detector = AnomalyDetector()
        self.ai_agent = AIAgentIntervention()
        self.notifier = create_notifier()
        
        logger.info("AI Agent intervention system initialized")
    
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
    
    async def run(self):
        """Runs periodic anomaly detection.
        
        This method is called periodically to check for various anomalies.
        """
        try:
            # Check for anomalies
            anomalies = self.detector.detect_anomalies()
            
            # Check for host errors
            host_error_anomaly = self.detector.check_host_errors()
            if host_error_anomaly:
                anomalies.append(host_error_anomaly)
            
            # Trigger interventions
            for anomaly in anomalies:
                await self._trigger_intervention(anomaly)
        
        except Exception as e:
            logger.error(f"Error in anomaly detection cycle: {e}")
    
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
            
            # Trigger AI Agent analysis
            logger.info("🤖 Triggering AI Agent analysis...")
            
            # Run analysis in background to avoid blocking
            asyncio.create_task(self._run_analysis(anomaly))
        
        except Exception as e:
            logger.error(f"Failed to trigger intervention: {e}")
    
    async def _run_analysis(self, anomaly: dict):
        """Run AI analysis in background.
        
        Args:
            anomaly: Anomaly context
        """
        try:
            analysis = await self.ai_agent.analyze_anomaly(anomaly) # Changed from self.agent_intervention to self.ai_agent
            
            # Save intervention to database
            self.ai_agent.save_intervention(anomaly, analysis)
            
            logger.info("✅ AI Agent completed analysis for %s" % anomaly['type'])
            
            # Log key findings
            if 'issue' in analysis:
                logger.info(f"   Issue: {analysis['issue']}")
            if 'suggestions' in analysis and analysis['suggestions']:
                logger.info(f"   Suggestions: {len(analysis['suggestions'])} found")
            
            # Send desktop notification
            self._send_notification(analysis)
        
        except Exception as e:
            logger.error(f"Failed to complete AI analysis: {e}")
    
    def _send_notification(self, analysis: Dict[str, Any]):
        """Send desktop notification for AI analysis.
        
        Args:
            analysis: AI analysis result
        """
        if 'error' in analysis:
            # Skip notification for errors
            return
        
        title = "⚠️  LWO Alert"
        
        # Build concise message
        issue = analysis.get ('issue', 'Anomaly detected')
        confidence = analysis.get('confidence', 0.0)
        
        message = f"{issue}\n"
        if confidence > 0:
            message += f"Confidence: {confidence:.0%}\n"
        
        # Add first suggestion if available
        suggestions = analysis.get('suggestions', [])
        if suggestions:
            message += f"\n💡 {suggestions[0]}"
        
        # Determine urgency based on confidence
        urgency = 'critical' if confidence >= 0.8 else 'normal'
        
        # Send notification
        self.notifier.send(title, message, urgency=urgency)

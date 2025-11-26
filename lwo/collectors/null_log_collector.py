"""Null log collector that does nothing."""

from lwo.collectors.log_collector import LogCollector
from lwo.utils.logger import setup_logger

logger = setup_logger(__name__)


class NullLogCollector(LogCollector):
    """No-op log collector for systems without log sources."""
    
    async def start(self) -> bool:
        """Does nothing.
        
        Returns:
            Always True
        """
        logger.info("NullLogCollector started (no log collection)")
        return True
    
    async def stop(self):
        """Does nothing."""
        logger.debug("NullLogCollector stopped")

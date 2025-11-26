"""Abstract base class for log collectors."""

from abc import ABC, abstractmethod


class LogCollector(ABC):
    """Collects host logs from various sources."""
    
    @abstractmethod
    async def start(self) -> bool:
        """Starts log collection.
        
        Returns:
            True if collection started successfully
        """
        pass
    
    @abstractmethod
    async def stop(self):
        """Stops log collection."""
        pass

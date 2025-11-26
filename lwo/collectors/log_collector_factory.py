"""Factory function for creating log collectors."""

from lwo.collectors.log_collector import LogCollector
from lwo.collectors.journalctl_collector import JournalctlCollector
from lwo.collectors.null_log_collector import NullLogCollector
from lwo.config import Config


def create_log_collector(config: Config) -> LogCollector:
    """Creates appropriate log collector based on system.
    
    Args:
        config: LWO configuration
        
    Returns:
        LogCollector instance
    """
    # Check if host log monitoring is enabled
    if not config.get('host_log', 'enabled', True):
        return NullLogCollector()
    
    # Try journalctl first (systemd systems)
    if JournalctlCollector.is_available():
        return JournalctlCollector()
    
    # TODO: Add SyslogCollector fallback
    
    # Fallback to null collector
    return NullLogCollector()

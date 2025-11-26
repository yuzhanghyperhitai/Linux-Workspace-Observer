"""Notification system for LWO."""

from abc import ABC, abstractmethod


class Notifier(ABC):
    """Abstract base class for notifiers."""
    
    @abstractmethod
    def send(self, title: str, message: str, urgency: str = 'normal') -> bool:
        """Send a notification.
        
        Args:
            title: Notification title
            message: Notification message
            urgency: Urgency level ('low', 'normal', 'critical')
            
        Returns:
            True if notification was sent successfully
        """
        pass


class DesktopNotifier(Notifier):
    """Desktop notifier using notify-send."""
    
    def __init__(self):
        """Initialize desktop notifier."""
        self.app_name = "LWO"
        self.icon = "dialog-warning"  # Standard icon name
    
    def send(self, title: str, message: str, urgency: str = 'normal') -> bool:
        """Send desktop notification using notify-send.
        
        Args:
            title: Notification title
            message: Notification message
            urgency: Urgency level ('low', 'normal', 'critical')
            
        Returns:
            True if notification was sent successfully
        """
        import subprocess
        
        try:
            subprocess.run(
                [
                    'notify-send',
                    '--app-name', self.app_name,
                    '--icon', self.icon,
                    '--urgency', urgency,
                    title,
                    message
                ],
                check=False,
                timeout=2.0
            )
            return True
        except (FileNotFoundError, subprocess.TimeoutExpired):
            # notify-send not available or timed out
            return False
        except Exception:
            return False


class NullNotifier(Notifier):
    """Null notifier that does nothing (for environments without GUI)."""
    
    def send(self, title: str, message: str, urgency: str = 'normal') -> bool:
        """Do nothing.
        
        Returns:
            Always True
        """
        return True


def create_notifier() -> Notifier:
    """Factory function to create appropriate notifier.
    
    Returns:
        Notifier instance based on environment
    """
    import os
    
    # Check if we're in a desktop environment
    if os.environ.get('DISPLAY') or os.environ.get('WAYLAND_DISPLAY'):
        # Try to use desktop notifier
        notifier = DesktopNotifier()
        # Test if notify-send is available
        if _test_notify_send():
            return notifier
    
    # Fallback to null notifier
    return NullNotifier()


def _test_notify_send() -> bool:
    """Test if notify-send is available.
    
    Returns:
        True if notify-send command exists
    """
    import subprocess
    
    try:
        subprocess.run(
            ['which', 'notify-send'],
            capture_output=True,
            check=True,
            timeout=1.0
        )
        return True
    except (subprocess.CalledProcessError, FileNotFoundError, subprocess.TimeoutExpired):
        return False

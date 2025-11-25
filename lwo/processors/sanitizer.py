"""Sensitive information sanitizer for LWO."""

import re
from typing import Dict, Pattern


# Sanitization patterns
SANITIZE_PATTERNS: Dict[str, Pattern] = {
    'password': re.compile(r'(?i)(password|passwd|pwd|pass)[\s=:]+\S+'),
    'api_key': re.compile(r'(?i)(api[_-]?key|token|secret)[\s=:]+[\w-]+'),
    'email': re.compile(r'\b[\w.-]+@[\w.-]+\.\w+\b'),
    'url_auth': re.compile(r'(?i)https?://[^:]+:[^@]+@'),
    'private_key': re.compile(r'-----BEGIN .* PRIVATE KEY-----'),
}

# Replacement strings
REPLACEMENTS = {
    'password': '<PASSWORD>',
    'api_key': '<API_KEY>',
    'email': '<EMAIL>',
    'url_auth': 'https://<REDACTED>@',
    'private_key': '<PRIVATE_KEY>',
}


class Sanitizer:
    """Sanitize sensitive information from commands and paths."""
    
    @staticmethod
    def sanitize(text: str) -> str:
        """Sanitize sensitive information from text.
        
        Args:
            text: Input text to sanitize
            
        Returns:
            Sanitized text
        """
        if not text:
            return text
        
        sanitized = text
        
        for pattern_name, pattern in SANITIZE_PATTERNS.items():
            replacement = REPLACEMENTS[pattern_name]
            sanitized = pattern.sub(replacement, sanitized)
        
        return sanitized
    
    @staticmethod
    def sanitize_command(command: str) -> str:
        """Sanitize a shell command.
        
        Args:
            command: Shell command to sanitize
            
        Returns:
            Sanitized command
        """
        return Sanitizer.sanitize(command)
    
    @staticmethod
    def sanitize_path(path: str) -> str:
        """Sanitize a file path.
        
        Args:
            path: File path to sanitize
            
        Returns:
            Sanitized path
        """
        # For paths, we might want to redact home directory or sensitive folders
        # For now, just apply general sanitization
        return Sanitizer.sanitize(path)

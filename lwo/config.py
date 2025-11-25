"""Configuration management for LWO."""

import os
from pathlib import Path
from typing import Any, Dict
import toml
from dotenv import load_dotenv

# Load environment variables
load_dotenv()


class Config:
    """LWO configuration manager."""
    
    def __init__(self, config_path: str | None = None):
        """Initialize configuration.
        
        Args:
            config_path: Path to config file. If None, uses default location.
        """
        if config_path is None:
            config_path = self._get_config_path()
        
        self.config_path = Path(config_path)
        self._config: Dict[str, Any] = self._load_config()
    
    @staticmethod
    def _get_config_path() -> Path:
        """Get config file path with priority order:
        1. Environment variable LWO_CONFIG
        2. Project directory lwo.toml (for development)
        3. ~/.config/lwo/lwo.toml (default)
        """
        # 1. Check environment variable
        env_config = os.getenv('LWO_CONFIG')
        if env_config and Path(env_config).exists():
            return Path(env_config)
        
        # 2. Check project directory (for development)
        # Assume we're in lwo/ package, go up to project root
        try:
            project_root = Path(__file__).parent.parent
            dev_config = project_root / 'lwo.toml'
            if dev_config.exists():
                return dev_config
        except Exception:
            pass
        
        # 3. Default user config directory
        config_home = os.getenv('XDG_CONFIG_HOME', str(Path.home() / '.config'))
        return Path(config_home) / 'lwo' / 'lwo.toml'
    
    def _load_config(self) -> Dict[str, Any]:
        """Load configuration from file."""
        if not self.config_path.exists():
            print(f"Config file not found: {self.config_path}")
            print("Using default configuration")
            return self._get_default_config()
        
        try:
            return toml.load(self.config_path)
        except Exception as e:
            print(f"Warning: Failed to load config from {self.config_path}: {e}")
            return self._get_default_config()
    
    @staticmethod
    def _get_default_config() -> Dict[str, Any]:
        """Get default configuration."""
        return {
            'general': {
                'data_dir': str(Path.home() / '.local' / 'share' / 'lwo'),
                'log_level': 'INFO',
            },
            'database': {
                'host': 'localhost',
                'port': 5432,
                'name': 'lwo',
                'user': 'lwo_user',
                'password': '',  # Will be read from env if empty
            },
            'collectors': {
                'process_snapshot_interval': 60,
                'file_watch_extensions': [
                    '.py', '.js', '.ts', '.java', '.c', '.cpp', 
                    '.go', '.rs', '.md', '.toml', '.yaml', '.json'
                ],
            },
            'openai': {
                'api_key': '',  # Will be read from env if empty
                'model': 'gpt-4o',
                'base_url': 'https://api.openai.com/v1',
            },
            'reporting': {
                'daily_report_time': '18:00',
                'report_output_dir': str(Path.home() / 'lwo-reports'),
            },
        }
    
    def get(self, section: str, key: str, default: Any = None) -> Any:
        """Get configuration value.
        
        Args:
            section: Configuration section name
            key: Configuration key
            default: Default value if not found
            
        Returns:
            Configuration value
        """
        value = self._config.get(section, {}).get(key, default)
        
        # Special handling for sensitive data: fallback to environment variables
        if section == 'database' and key == 'password':
            if not value:
                value = os.getenv('LWO_DB_PASSWORD', '')
        elif section == 'openai' and key == 'api_key':
            if not value:
                value = os.getenv('OPENAI_API_KEY', '')
        
        return value
    
    def get_section(self, section: str) -> Dict[str, Any]:
        """Get entire configuration section.
        
        Args:
            section: Configuration section name
            
        Returns:
            Configuration section dict
        """
        return self._config.get(section, {})
    
    @property
    def data_dir(self) -> Path:
        """Get data directory path."""
        path = Path(self.get('general', 'data_dir'))
        path.mkdir(parents=True, exist_ok=True)
        return path
    
    @property
    def db_config(self) -> Dict[str, Any]:
        """Get database configuration."""
        return self.get_section('database')
    
    @property
    def openai_config(self) -> Dict[str, Any]:
        """Get OpenAI configuration."""
        return self.get_section('openai')


# Global config instance
_config: Config | None = None


def get_config() -> Config:
    """Get global configuration instance."""
    global _config
    if _config is None:
        _config = Config()
    return _config

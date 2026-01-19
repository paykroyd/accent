import os
import yaml
from pathlib import Path

# Path to the config file
CONFIG_FILE = Path(__file__).parent / 'config.yaml'

# Singleton config instance
_config = None


def load_config():
    """Load configuration from YAML file and environment variables."""
    global _config
    if _config is not None:
        return _config

    # Load YAML config
    if CONFIG_FILE.exists():
        with open(CONFIG_FILE, 'r') as f:
            _config = yaml.safe_load(f) or {}
    else:
        _config = {}

    # Ensure required sections exist
    _config.setdefault('user', {})
    _config.setdefault('schedule', [])
    _config.setdefault('content', {})

    # Merge environment variables for API keys
    _config['api_keys'] = {
        'google_maps': os.environ.get('GOOGLE_MAPS_API_KEY', ''),
        'football': os.environ.get('FOOTBALL_API_KEY', ''),
        'mbta': os.environ.get('MBTA_API_KEY', ''),
    }

    # Google Calendar OAuth credentials from environment
    _config['google_calendar'] = {
        'client_id': os.environ.get('GOOGLE_CALENDAR_CLIENT_ID', ''),
        'client_secret': os.environ.get('GOOGLE_CALENDAR_CLIENT_SECRET', ''),
    }

    return _config


def get_config():
    """Get the loaded configuration."""
    if _config is None:
        return load_config()
    return _config


def get_user():
    """Get the user configuration as a dict compatible with existing code."""
    config = get_config()
    return config.get('user', {})


def get_schedule():
    """Get the schedule configuration."""
    config = get_config()
    return config.get('schedule', [])


def get_content_config(content_type):
    """Get configuration for a specific content type."""
    config = get_config()
    return config.get('content', {}).get(content_type, {})


def get_api_key(service):
    """Get API key for a specific service."""
    config = get_config()
    return config.get('api_keys', {}).get(service, '')


def get_google_calendar_secrets():
    """Get Google Calendar OAuth secrets."""
    config = get_config()
    return config.get('google_calendar', {})

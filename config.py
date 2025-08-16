import os
try:
    from secrets import DISCORD_TOKEN, APPLICATION_ID
except ImportError:
    # Fallback to environment variables if secrets.py doesn't exist
    DISCORD_TOKEN = os.getenv('DISCORD_TOKEN')
    APPLICATION_ID = os.getenv('APPLICATION_ID')

def load_config():
    """Load configuration from secrets.py or environment variables"""
    
    config = {
        'DISCORD_TOKEN': DISCORD_TOKEN,
        'APPLICATION_ID': APPLICATION_ID
    }
    
    # Check if required variables are present
    for key, value in config.items():
        if not value:
            raise ValueError(f"Missing required configuration: {key}")
    
    return config

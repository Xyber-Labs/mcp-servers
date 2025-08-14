from pathlib import Path
from pydantic_settings import BaseSettings, SettingsConfigDict
from dotenv import load_dotenv
import os

# Explicitly load .env file before creating the config
# Look for .env file in the project root (parent of src directory)
current_file = Path(__file__)
env_file = current_file.parent.parent / ".env"

if env_file.exists():
    result = load_dotenv(env_file)
    print(f"✅ Loaded .env from: {env_file} (success: {result})")
else:
    # Fallback: try looking in current working directory
    fallback_env = Path.cwd() / ".env"
    if fallback_env.exists():
        result = load_dotenv(fallback_env)
        print(f"✅ Loaded .env from: {fallback_env} (success: {result})")
    else:
        print(f"⚠️  Warning: .env file not found at {env_file} or {fallback_env}")
        print(f"   Make sure your .env file exists with Twitter credentials")

class TwitterConfig(BaseSettings):
    model_config = SettingsConfigDict(
        env_prefix="TWITTER_",
        env_file=str(env_file) if env_file.exists() else ".env",
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=False,
    )

    API_KEY: str
    API_SECRET_KEY: str
    ACCESS_TOKEN: str
    ACCESS_TOKEN_SECRET: str
    BEARER_TOKEN: str
    media_upload_enabled: bool = True
    max_tweet_length: int = 280
    poll_max_options: int = 4
    poll_max_duration: int = 10080

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        # Verify credentials are loaded
        if not all([self.API_KEY, self.API_SECRET_KEY, self.ACCESS_TOKEN, 
                   self.ACCESS_TOKEN_SECRET, self.BEARER_TOKEN]):
            missing = []
            if not self.API_KEY: missing.append("TWITTER_API_KEY")
            if not self.API_SECRET_KEY: missing.append("TWITTER_API_SECRET_KEY")
            if not self.ACCESS_TOKEN: missing.append("TWITTER_ACCESS_TOKEN")
            if not self.ACCESS_TOKEN_SECRET: missing.append("TWITTER_ACCESS_TOKEN_SECRET")
            if not self.BEARER_TOKEN: missing.append("TWITTER_BEARER_TOKEN")
            
            raise ValueError(
                f"Missing required Twitter credentials: {', '.join(missing)}. "
                f"Please check your .env file at {env_file}"
            )
        
        print("✅ All Twitter credentials loaded successfully")
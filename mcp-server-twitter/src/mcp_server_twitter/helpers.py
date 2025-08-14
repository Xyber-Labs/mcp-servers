import base64
import io
import json
import os
from pathlib import Path


def classify_tweet_type(image_content_str, poll_options, in_reply_to_tweet_id, quote_tweet_id):
    """Classify tweet type for logging and analytics."""
    types = []
    
    if image_content_str:
        types.append("image")
    if poll_options:
        types.append("poll") 
    if in_reply_to_tweet_id:
        types.append("reply")
    if quote_tweet_id:
        types.append("quote")
    
    if not types:
        return "text"
    
    return "_".join(types)  # e.g., "image_reply" or "poll_quote"


def convert_base64_to_image(image_content_str: str) -> io.BytesIO:
    """
    Convert Base64 image string to BytesIO object with proper naming.
    
    Args:
        image_content_str: Base64-encoded image data
        
    Returns:
        BytesIO object ready for upload
        
    Raises:
        ValueError: If Base64 decoding fails
    """
    try:
        image_content = base64.b64decode(image_content_str)
        image_file = io.BytesIO(image_content)
        image_file.name = "image.png"
        return image_file
    except Exception as e:
        raise ValueError(f"Failed to decode Base64 image: {str(e)}")


def validate_poll_parameters(poll_options, poll_duration, config):
    """
    Validate poll parameters against configuration limits.
    
    Args:
        poll_options: List of poll options
        poll_duration: Poll duration in minutes
        config: Configuration object with poll limits
        
    Raises:
        ValueError: If validation fails
    """
    if poll_options:
        if len(poll_options) < 2 or len(poll_options) > config.poll_max_options:
            raise ValueError(f"Poll must have 2-{config.poll_max_options} options")
            
        if not poll_duration or not (5 <= poll_duration <= config.poll_max_duration):
            raise ValueError(f"Poll duration must be 5-{config.poll_max_duration} minutes")


def load_country_codes() -> dict:
    """
    Load country code to WOEID mapping from JSON file.
    
    Returns:
        Dictionary mapping country names to WOEID integers
        
    Raises:
        FileNotFoundError: If the data file doesn't exist
        ValueError: If JSON parsing fails
    """
    try:
        # Get the directory where this helpers.py file is located
        current_dir = Path(__file__).parent
        data_file = current_dir / "data" / "woeid_by_country.json"
        
        with open(data_file, 'r', encoding='utf-8') as f:
            return json.load(f)
    except FileNotFoundError:
        raise FileNotFoundError(f"Country codes data file not found: {data_file}")
    except json.JSONDecodeError as e:
        raise ValueError(f"Failed to parse country codes JSON: {str(e)}")
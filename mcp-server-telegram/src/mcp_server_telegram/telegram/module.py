### src/mcp_server_telegram/telegram/module.py
import logging
import requests
import asyncio
from functools import lru_cache
from typing import Any

from mcp_server_telegram.telegram.config import (
    TelegramConfig,
    TelegramServiceError,
    TelegramApiError,
    TelegramConfigError
)

logger = logging.getLogger(__name__)

# Telegram's max message length is 4096 chars
MAX_MESSAGE_LENGTH = 4000  # Keep a buffer

class _TelegramService:
    """Encapsulates Telegram client logic and configuration."""

    def __init__(self, config: TelegramConfig):
        self.config = config
        logger.info("TelegramService initialized.")
        if self.config.token:
            logger.info(f"Using Telegram channel: {self.config.channel}")
            logger.info(f"Telegram token ending with: ...{self.config.token[-4:]}")


    async def send_message(self, text: str) -> bool:
        """
        Sends a message to the configured Telegram channel.

        Args:
            text: The message content to send.

        Returns:
            True if the message was sent successfully, False otherwise.

        Raises:
            TelegramConfigError: If configuration (token/channel) is invalid (checked at init).
        """
        logger.info(f"Attempting to send message to Telegram channel {self.config.channel}")


        if not self.config.token or not self.config.channel:
            msg = "Telegram token or channel is missing in configuration."
            logger.error(msg)
            raise TelegramConfigError(msg)


        # Ensure text is not too long
        if len(text) > MAX_MESSAGE_LENGTH:
            logger.warning(
                f"Message exceeds Telegram's maximum length. Truncating from {len(text)} to {MAX_MESSAGE_LENGTH} chars."
            )
            text = text[:MAX_MESSAGE_LENGTH] + "... [message truncated]"

        url = f"https://api.telegram.org/bot{self.config.token}/sendMessage"
        payload = {
            "chat_id": self.config.channel,
            "text": text,
            "parse_mode": "HTML"  # Default to HTML, consider making configurable via TelegramConfig
        }
        headers = {"Content-Type": "application/json"}

        try:
            response = await asyncio.to_thread(
                requests.post, url, json=payload, headers=headers, timeout=10
            )

            if response.status_code == 400:
                error_json = response.json()
                error_desc = error_json.get('description', '').lower()
                if 'parse error' in error_desc or "can't parse entities" in error_desc:
                    logger.warning("Got 400 error likely due to HTML parse mode, retrying without it.")
                    payload["parse_mode"] = "" # Remove parse mode
                    response = await asyncio.to_thread(
                        requests.post, url, json=payload, headers=headers, timeout=10
                    )
                else:
                    logger.error(f"Failed to send message (400 Bad Request): {error_desc}, Details: {error_json}")
                    return False 

            response.raise_for_status() 

            logger.info(f"Message sent successfully to channel {self.config.channel}")
            return True

        except requests.exceptions.HTTPError as http_err:
            status_code = http_err.response.status_code
            details = {}
            try:
                details = http_err.response.json()
            except requests.exceptions.JSONDecodeError:
                details = {"raw_response": http_err.response.text}
            
            err_msg = f"HTTP error sending message to Telegram: {http_err}"
            logger.error(err_msg, exc_info=True)
            return False 
        except requests.exceptions.RequestException as req_err: # Catches ConnectionError, Timeout, etc.
            err_msg = f"Request exception sending message to Telegram: {req_err}"
            logger.error(err_msg, exc_info=True)
            return False
        except Exception as e:
            err_msg = f"An unexpected error occurred sending message to Telegram: {e}"
            logger.error(err_msg, exc_info=True)
            return False

@lru_cache(maxsize=1)
def get_telegram_service() -> _TelegramService:
    """
    Factory function to get a singleton instance of the Telegram service.
    Handles configuration loading and service initialization.

    Returns:
        An initialized _TelegramService instance.

    Raises:
        TelegramConfigError: If configuration loading or validation fails.
    """
    try:
        config = TelegramConfig()
        service = _TelegramService(config=config)
        logger.info("Telegram service instance retrieved successfully.")
        return service
    except Exception as e: # Catches Pydantic ValidationError if env vars are missing/invalid
        logger.error(f"Failed to initialize TelegramConfig or _TelegramService: {e}", exc_info=True)
        raise TelegramConfigError(f"Configuration error for Telegram service: {e}") from e
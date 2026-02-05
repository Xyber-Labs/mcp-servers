import logging

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from mcp_server_telegram_parser.schemas import TelegramParseResult
from mcp_server_telegram_parser.telegram.module import get_parser_service

logger = logging.getLogger(__name__)

router = APIRouter(tags=["TelegramParser"])


class ParseChannelsRequest(BaseModel):
    channels: list[str] = Field(..., description="List of Telegram channel usernames")
    limit: int = Field(10, description="Number of messages to fetch per channel")


async def perform_parse_telegram_channels(
    channels: list[str], limit: int
) -> TelegramParseResult:
    """Core logic for parsing Telegram channels."""
    service = get_parser_service()
    return await service.parse_channels(channels=channels, limit=limit)


@router.post(
    "/parse-telegram-channels",
    tags=["TelegramParser"],
    operation_id="telegram_parser_parse_channels",
    response_model=TelegramParseResult,
    summary="Parse Telegram Channels",
    description="""
Parse last N messages from provided public Telegram channels using Telethon.

Returns parsed messages including message ID, date, text content, views, and forwards count.
Channels that cannot be accessed will return an error message in their respective response.

**Examples:**
- Parse a crypto news channel: `channels=["cryptonews"]`
- Parse multiple channels: `channels=["cryptonews", "bitcoin"]`
""",
)
async def parse_telegram_channels(request: ParseChannelsRequest) -> TelegramParseResult:
    """Parse last N messages from provided public Telegram channels using Telethon."""
    try:
        return await perform_parse_telegram_channels(request.channels, request.limit)
    except Exception as e:
        logger.error("Parsing failed: %s", str(e), exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to parse telegram channels") from e

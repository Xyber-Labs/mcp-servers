# Libraries for different LLMs
import json
import logging
import yaml
from logging import LoggerAdapter
import os
import re
from datetime import datetime
from typing import Any, Dict, List, Literal, Optional, Tuple, Type, Union
from functools import lru_cache
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_mistralai import ChatMistralAI
from langchain_core.output_parsers import JsonOutputParser

from mcp_server_deepresearcher.deepresearcher.config import LLM_Config

logger = logging.getLogger(__name__)





def load_json(file_path, create_file=False):
    """Loads JSON file."""
    try:
        logger.info(f"Attempting to load file from: {file_path}")
        if not os.path.exists(file_path):
            logger.warning(
                f"File does not exist at path. Creating new file: {file_path}"
            )
            if create_file:
                os.makedirs(os.path.dirname(file_path), exist_ok=True)
                with open(file_path, "w", encoding="utf-8") as f:
                    json.dump({}, f)
                return {}
            return {}

        with open(file_path, "r", encoding="utf-8") as f:
            content = f.read()
            if not content:
                logger.warning(
                    f"File is empty: {file_path}. Returning empty dictionary."
                )
                return {}
            data = json.loads(content)
            logger.info(f"Successfully loaded JSON data from {file_path}")
            return data

    except json.JSONDecodeError as je:
        logger.error(
            f"JSON parsing error in {file_path}: {je}. Returning empty dictionary."
        )
        return {}

    except Exception as e:
        logger.error(f"Error loading file {file_path}: {e}")
        return {}


def load_yaml(file_path):
    """Loads YAML file."""
    try:
        logger.info(f"Attempting to load YAML file from: {file_path}")
        if not os.path.exists(file_path):
            logger.warning(f"YAML file does not exist at path: {file_path}")
            return []

        with open(file_path, "r", encoding="utf-8") as f:
            content = f.read()
            if not content:
                logger.warning(
                    f"YAML file is empty: {file_path}. Returning empty list."
                )
                return []
            data = yaml.safe_load(content)
            logger.info(f"Successfully loaded YAML data from {file_path}")
            return data if data else []

    except yaml.YAMLError as ye:
        logger.error(
            f"YAML parsing error in {file_path}: {ye}. Returning empty list."
        )
        return []

    except Exception as e:
        logger.error(f"Error loading YAML file {file_path}: {e}")
        return []


# ------------------------------------------------------------------------------------------------
# Block dedicated for the LLM initialization
# ------------------------------------------------------------------------------------------------
LLM_Type = Literal["main", "spare", "validation", "thinking"]


class BaseChatModel:
    def __init__(self, model: str, **kwargs):
        self.model = model
        print(f"Initialized {self.__class__.__name__} with model: {self.model}")

    def with_fallbacks(self, fallbacks: list):
        print(f"Applied fallbacks to {self.__class__.__name__}")
        return self


@lru_cache(maxsize=8)
def initialize_llm(
    llm_type: Literal["main", "validation", "spare", "thinking"] = "main",
    raise_on_error: bool = True,
) -> Optional[BaseChatModel]:
    """
    Initializes and returns a language model client based on the specified type.
    This function is cached to avoid reloading models on subsequent calls.
    """
    config = LLM_Config()
    logger.info(f"Setting up '{llm_type}' LLM...")

    model_name = None

    # 1. Define mappings to find the correct config attributes and provider details
    ATTRIBUTE_MAP: Dict[LLM_Type, Tuple[str, str]] = {
        "main": ("MODEL_PROVIDER", "MODEL_NAME"),
        "spare": ("MODEL_PROVIDER_SPARE", "MODEL_NAME_SPARE"),
        "validation": ("MODEL_VALIDATION_PROVIDER", "MODEL_VALIDATION_NAME"),
        "thinking": ("MODEL_PROVIDER_THINKING", "MODEL_NAME_THINKING"),
    }

    PROVIDER_MAP: Dict[str, Dict[str, Any]] = {
        "google": {
            "class": ChatGoogleGenerativeAI,
            "api_key_name": "GOOGLE_API_KEY",
            "init_arg": "google_api_key",
        },
        "mistral": {
            "class": ChatMistralAI,
            "api_key_name": "MISTRAL_API_KEY",
            "init_arg": "api_key",
        },
    }

    # 2. Get model provider and name from config using the attribute map
    provider_attr, name_attr = ATTRIBUTE_MAP[llm_type]
    model_provider = getattr(config, provider_attr, None)
    model_name = getattr(config, name_attr, None)

    if not all([model_provider, model_name]):
        msg = f"Configuration for '{llm_type}' LLM ('{provider_attr}', '{name_attr}') is incomplete."
        if raise_on_error:
            logger.error(msg)
            raise ValueError(msg)
        else:
            logger.warning(msg)
        return None

    # 3. Get provider-specific details from the provider map
    provider_details = PROVIDER_MAP.get(model_provider.lower())
    if not provider_details:
        msg = f"Unsupported model provider for '{llm_type}': {model_provider}"
        if raise_on_error:
            logger.error(msg)
            raise ValueError(msg)
        else:
            logger.warning(msg)
        return None

    # 4. Check for the required API key
    api_key_name = provider_details["api_key_name"]
    api_key_value = getattr(config, api_key_name, None)
    if not api_key_value:
        msg = f"'{api_key_name}' is required for provider '{model_provider}' but is not set."
        if raise_on_error:
            logger.error(msg)
            raise ValueError(msg)
        else:
            logger.warning(msg)
        return None

    # 5. Initialize and return the model
    try:
        ModelClass: Type[BaseChatModel] = provider_details["class"]
        init_kwargs = {
            provider_details["init_arg"]: api_key_value,
            "model": model_name,
        }
        llm_instance = ModelClass(**init_kwargs)
        logger.info(
            f"Successfully initialized '{llm_type}' LLM with provider '{model_provider}'."
        )
        return llm_instance
    except Exception as e:
        msg = f"Failed to initialize '{llm_type}' LLM from provider '{model_provider}': {e}"
        if raise_on_error:
            logger.error(msg, exc_info=True)
            raise
        else:
            logger.warning(msg, exc_info=True)
        return None


def initialize_llm_from_config(
    config: Optional[Dict[str, Any]],
) -> Optional[BaseChatModel]:
    """
    Initializes and returns a language model client from a configuration dictionary.
    """
    if not config:
        return None

    logger.info(f"Setting up LLM from config: {config}...")

    model_provider = config.get("provider")
    model_name = config.get("model_name")

    PROVIDER_MAP: Dict[str, Dict[str, Any]] = {
        "google": {
            "class": ChatGoogleGenerativeAI,
            "api_key_name": "GOOGLE_API_KEY",
            "init_arg": "google_api_key",
        },
        "mistral": {
            "class": ChatMistralAI,
            "api_key_name": "MISTRAL_API_KEY",
            "init_arg": "api_key",
        },
    }

    if not all([model_provider, model_name]):
        msg = (
            "LLM configuration is incomplete. 'provider' and 'model_name' are required."
        )
        logger.warning(msg)
        return None

    provider_details = PROVIDER_MAP.get(model_provider.lower())
    if not provider_details:
        msg = f"Unsupported model provider: {model_provider}"
        logger.warning(msg)
        return None

    api_key_name = provider_details["api_key_name"]
    # It's better to fetch API keys from the global config/environment
    # instead of passing them in each simulation config.
    global_config = LLM_Config()
    api_key_value = getattr(global_config, api_key_name, None)

    if not api_key_value:
        msg = f"'{api_key_name}' is required for provider '{model_provider}' but is not set in the environment."
        logger.warning(msg)
        return None

    try:
        ModelClass: Type[BaseChatModel] = provider_details["class"]
        init_kwargs = {
            provider_details["init_arg"]: api_key_value,
            "model": model_name,
        }
        # Pass through any other parameters from the config
        extra_params = config.get("parameters", {})
        init_kwargs.update(extra_params)

        llm_instance = ModelClass(**init_kwargs)
        logger.info(
            f"Successfully initialized LLM '{model_name}' from provider '{model_provider}'."
        )
        return llm_instance
    except Exception as e:
        msg = f"Failed to initialize LLM from provider '{model_provider}': {e}"
        logger.warning(msg, exc_info=True)
        return None


def setup_llm():
    """Setup main LLM from config."""
    return initialize_llm(llm_type="main", raise_on_error=True)


def setup_spare_llm():
    """Setup spare LLM from config."""
    return initialize_llm(llm_type="spare", raise_on_error=False)


def clean_response(response_text: str) -> str:
    """Clean the response text by removing markdown code block markers if present."""
    try:
        # Handle case where response_text is a list (extract first string element)
        if isinstance(response_text, list):
            logger.warning(f"clean_response received a list instead of string, extracting first element")
            if len(response_text) > 0:
                response_text = str(response_text[0])
            else:
                response_text = ""
        
        # Ensure response_text is a string
        if not isinstance(response_text, str):
            response_text = str(response_text)
        
        # Clean response text by removing markdown code block markers if present
        cleaned_response = response_text.strip()
        if cleaned_response.startswith("```json"):
            # Remove ```json from start and ``` from end
            cleaned_response = cleaned_response[7:]  # Remove ```json
            if cleaned_response.endswith("```"):
                cleaned_response = cleaned_response[:-3]  # Remove ```
        elif cleaned_response.startswith("```"):
            # Remove ``` from start and end (generic code block)
            cleaned_response = cleaned_response[3:]
            if cleaned_response.endswith("```"):
                cleaned_response = cleaned_response[:-3]

        cleaned_response = cleaned_response.strip()

        # Handle escaped single quotes (invalid in JSON - single quotes don't need escaping in JSON strings)
        # Replace \' with ' (but preserve valid escapes like \\ and \")
        # Use a simple approach: replace \' but not \\' (which would be a backslash followed by quote)
        import re
        # Replace \' but not \\' (escaped backslash followed by quote)
        cleaned_response = re.sub(r'(?<!\\)\\\'', "'", cleaned_response)
        # Also handle the case where it's written as \\' (double backslash single quote)
        cleaned_response = cleaned_response.replace("\\\\'", "'")

        # Fix double-escaped quotes (\\" should become \")
        # This handles cases where LLM outputs \\" instead of \"
        # We need to be careful: \\" inside a JSON string should be \"
        # But we need to preserve \\ sequences that are not followed by quotes
        # Strategy: Replace \\" with \" only when it appears inside JSON string values
        # First, let's handle the common case: \\" -> \"
        # Use a more careful approach: replace \\" with \" but preserve \\\\ (escaped backslash)
        # Replace sequences of backslashes followed by quote: (even number of backslashes + quote) -> (half backslashes + quote)
        def fix_escaped_quotes(text):
            """Fix incorrectly escaped quotes in JSON strings"""
            # Replace \\" with \" (double backslash + quote -> single backslash + quote)
            # But preserve \\\\" (four backslashes + quote should become \\" - two backslashes + quote)
            # Process from most backslashes to least
            result = text
            # Handle 4+ backslashes: \\\\" -> \\"
            while '\\\\\\\\"' in result:
                result = result.replace('\\\\\\\\"', '\\\\"')
            # Handle 3 backslashes: \\\" -> \"
            result = result.replace('\\\\\\"', '\\"')
            # Handle 2 backslashes: \\" -> \"
            result = result.replace('\\\\"', '\\"')
            return result
        
        cleaned_response = fix_escaped_quotes(cleaned_response)

        # Escape newlines and tabs within JSON strings
        # Also escape unescaped quotes inside string values
        def escape_string_content(match):
            """Escape quotes, newlines, and tabs inside JSON string values"""
            full_match = match.group(0)
            # Extract the content between quotes
            content = full_match[1:-1]  # Remove surrounding quotes
            
            # Don't double-escape already escaped characters
            # Escape unescaped quotes (but not already escaped ones)
            # The pattern (?<!\\)" matches quotes that are not preceded by a backslash
            content = re.sub(r'(?<!\\)"', r'\\"', content)
            # Escape newlines and tabs
            content = content.replace("\n", "\\n").replace("\t", "\\t")
            
            return f'"{content}"'
        
        cleaned_response = re.sub(
            r'"([^"\\]|\\.)*"',
            escape_string_content,
            cleaned_response,
            flags=re.DOTALL,
        )

        # Remove trailing commas from the JSON string
        cleaned_response = re.sub(r",\s*([}\]])", r"\1", cleaned_response)

        # Convert Python boolean values to JSON boolean values
        # Replace True/False (Python) with true/false (JSON)
        cleaned_response = re.sub(r'\bTrue\b', 'true', cleaned_response)
        cleaned_response = re.sub(r'\bFalse\b', 'false', cleaned_response)
        # Also handle None -> null
        cleaned_response = re.sub(r'\bNone\b', 'null', cleaned_response)

        return cleaned_response
    except Exception as e:
        logger.error(f"Error cleaning response: {e}")
        # Return original response if cleaning fails, but still try to fix booleans
        try:
            response_text = re.sub(r'\bTrue\b', 'true', response_text)
            response_text = re.sub(r'\bFalse\b', 'false', response_text)
            response_text = re.sub(r'\bNone\b', 'null', response_text)
        except Exception:
            pass
        return response_text



def load_mcp_servers_config(
    apify_token: Optional[str] = None,
    mcp_telegram_url: Optional[str] = None,
    telegram_token: Optional[str] = None,
    telegram_channel: Optional[str] = None,
    mcp_youtube_url: Optional[str] = None,
    mcp_tavily_url: Optional[str] = None,
    mcp_arxiv_url: Optional[str] = None,
    mcp_twitter_url: Optional[str] = None,
    apify_actors_list: Optional[List[str]] = None,
    mcp_deepresearch_url: Optional[str] = None,
    mcp_image_generation_url: Optional[str] = None,
    mcp_telegram_parser_url: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Load and configure MCP servers based on provided environment variables.

    Args:
        apify_token: Apify API token
        mcp_telegram_url: Telegram MCP server URL
        telegram_token: Telegram bot token
        telegram_channel: Telegram channel
        mcp_youtube_url: YouTube MCP server URL
        mcp_tavily_url: Tavily MCP server URL
        mcp_arxiv_url: Arxiv MCP server URL
        mcp_twitter_url: Twitter MCP server URL
        apify_actors_list: List of Apify actors to include (defaults to tweet-scraper)
        mcp_deepresearch_url: Deep Research MCP server URL

    Returns:
        Dictionary containing MCP server configurations
    """
    mcp_servers_config = {}

    # Default Apify actors if not specified
    if apify_actors_list is None:
        apify_actors_list = ["apidojo/tweet-scraper"]

    # --- Apify MCP Server ---
    try:
        logger.info(
            f"DEBUG: Checking Apify configuration - APIFY_TOKEN={'SET' if apify_token else 'NOT SET'} ({len(apify_token) if apify_token else 0} chars)"
        )
        if apify_token is not None:
            # Build URL with specific actors to limit what's available
            actors_param = ",".join(apify_actors_list)
            apify_url = f"https://mcp.apify.com/sse?actors={actors_param}"

            mcp_servers_config["apify"] = {
                "transport": "sse",
                "url": apify_url,
                "headers": {"Authorization": "Bearer " + apify_token},
            }
            logger.info(
                f"Apify MCP server configured with {len(apify_actors_list)} specific actors: {apify_actors_list}"
            )
        else:
            logger.info(
                "Apify MCP server not configured - APIFY_TOKEN is None. Skipping..."
            )
    except Exception as e:
        logger.error(f"Error configuring Apify MCP server: {e}")

    # --- Telegram MCP Server ---
    try:
        if mcp_telegram_url and telegram_token and telegram_channel:
            mcp_servers_config["telegram"] = {
                "url": mcp_telegram_url,
                "transport": "streamable_http",
                "headers": {
                    "X-Telegram-Token": telegram_token,
                    "X-Telegram-Channel": telegram_channel,
                },
            }
            logger.info("Telegram MCP server configured")
        else:
            logger.info("Telegram MCP server not configured. Skipping...")
    except Exception as e:
        logger.error(f"Error configuring Telegram MCP server: {e}")

    # --- YouTube MCP Server ---
    try:
        if mcp_youtube_url and mcp_youtube_url != "":
            mcp_servers_config["youtube"] = {
                "url": mcp_youtube_url,
                "transport": "streamable_http",
            }
            logger.info("YouTube MCP server configured")
        else:
            logger.info("YouTube MCP server not configured. Skipping...")
    except Exception as e:
        logger.error(f"Error configuring YouTube MCP server: {e}")

    # --- Tavily MCP Server ---
    try:
        if mcp_tavily_url and mcp_tavily_url != "":
            mcp_servers_config["tavily"] = {
                "url": mcp_tavily_url,
                "transport": "streamable_http",
            }
            logger.info("Tavily MCP server configured")
        else:
            logger.info("Tavily MCP server not configured. Skipping...")
    except Exception as e:
        logger.error(f"Error configuring Tavily MCP server: {e}")

    # --- Arxiv MCP Server ---
    try:
        if mcp_arxiv_url and mcp_arxiv_url != "":
            mcp_servers_config["arxiv"] = {
                "url": mcp_arxiv_url,
                "transport": "streamable_http",
            }
            logger.info("Arxiv MCP server configured")
        else:
            logger.info("Arxiv MCP server not configured. Skipping...")
    except Exception as e:
        logger.error(f"Error configuring Arxiv MCP server: {e}")

    # --- Twitter MCP Server ---
    try:
        if mcp_twitter_url and mcp_twitter_url != "":
            mcp_servers_config["twitter"] = {
                "url": mcp_twitter_url,
                "transport": "streamable_http",
            }
            logger.info("Twitter MCP server configured")
        else:
            logger.info("Twitter MCP server not configured. Skipping...")
    except Exception as e:
        logger.error(f"Error configuring Twitter MCP server: {e}")

    # --- Deep Research MCP Server ---
    try:
        if mcp_deepresearch_url and mcp_deepresearch_url != "":
            mcp_servers_config["deepresearch"] = {
                "url": mcp_deepresearch_url,
                "transport": "streamable_http",
            }
            logger.info("Deep Research MCP server configured")
        else:
            logger.info("Deep Research MCP server not configured. Skipping...")
    except Exception as e:
        logger.error(f"Error configuring Deep Research MCP server: {e}")

    # --- Image Generation MCP Server ---

    try:
        if mcp_image_generation_url and mcp_image_generation_url != "":
            mcp_servers_config["image_generation"] = {
                "url": mcp_image_generation_url,
                "transport": "streamable_http",
            }
            logger.info("Image Generation MCP server configured")
        else:
            logger.info("Image Generation MCP server not configured. Skipping...")
    except Exception as e:
        logger.error(f"Error configuring Image Generation MCP server: {e}")

    # --- Telegram Parser MCP Server ---

    try:
        if mcp_telegram_parser_url and mcp_telegram_parser_url != "":
            mcp_servers_config["telegram_parser"] = {
                "url": mcp_telegram_parser_url,
                "transport": "streamable_http",
            }
            logger.info("Telegram Parser MCP server configured")
        else:
            logger.info("Telegram Parser MCP server not configured. Skipping...")
    except Exception as e:
        logger.error(f"Error configuring Telegram Parser MCP server: {e}")

    logger.info(f"Total MCP servers configured: {len(mcp_servers_config)}")

    # Log which servers were configured
    if mcp_servers_config:
        logger.info("Configured MCP servers:")
        for server_name, config in mcp_servers_config.items():
            url = config.get("url", "No URL")
            transport = config.get("transport", "No transport")
            logger.info(f"  - {server_name}: {url} ({transport})")
    else:
        logger.warning(
            "No MCP servers were configured. Check your environment variables."
        )

    return mcp_servers_config


def create_mcp_tasks(
    mcp_tools,
    search_query,
    topic: Optional[str] = None,
    twitter_sources: Optional[List[str]] = None,
    telegram_sources: Optional[List[str]] = None,
):
    """
    Creates MCP tasks using Pydantic schemas for validation, then converts to dict format for tool calls.

    Args:
        mcp_tools: List of available MCP tools
        search_query: The search query string
        topic: Optional topic filter
        twitter_sources: Optional list of Twitter URLs to scrape
        telegram_sources: Optional list of Telegram channels to parse

    Returns:
        Tuple of (tasks, task_names) where tasks are coroutines with validated parameters
    """
    tasks = []
    task_names = []
    for tool in mcp_tools:
        if tool.name == "tavily_web_search":
            # Tavily expects a 'request' parameter with the search data
            tasks.append(
                tool.coroutine(request={"query": search_query, "max_results": 3})
            )
            task_names.append(tool.name)  # Track the name
            logger.info(f"  - Added task: {tool.name}")
        elif tool.name == "parse_telegram_channels":
            if telegram_sources:
                # Create Pydantic schema object for validation, then convert to dict
                request_data = {"channels": telegram_sources, "limit": 3}
                tasks.append(tool.coroutine(**request_data))
                task_names.append(tool.name)  # Track the name
                logger.info(f"  - Added task: {tool.name}")
        elif tool.name == "arxiv_search":
            # Arxiv might also expect a 'request' parameter
            tasks.append(
                tool.coroutine(request={"query": search_query, "max_results": 3})
            )
            task_names.append(tool.name)  # Track the name
            logger.info(f"  - Added task: {tool.name}")
        elif tool.name == "youtube_search_and_transcript":
            # Create Pydantic schema object for validation, then convert to dict
            request_data = {"query": search_query}
            tasks.append(tool.coroutine(**request_data))
            task_names.append(tool.name)  # Track the name
            logger.info(f"  - Added task: {tool.name}")
        elif tool.name == "twitter_search_topic":
            # Twitter search topic tool - expects topic parameter
            request_data = {"topic": search_query}
            tasks.append(tool.coroutine(**request_data))
            task_names.append(tool.name)
            logger.info(f"  - Added task: {tool.name}")
        elif tool.name == "search_and_extract_transcripts":
            # Search and extract YouTube transcripts
            request_data = {"query": search_query}
            tasks.append(tool.coroutine(**request_data))
            task_names.append(tool.name)
            logger.info(f"  - Added task: {tool.name}")
        elif tool.name == "mcp_search_youtube_videos":
            # Search YouTube videos without transcripts
            request_data = {"query": search_query}
            tasks.append(tool.coroutine(**request_data))
            task_names.append(tool.name)
            logger.info(f"  - Added task: {tool.name}")
        elif tool.name == "extract_transcripts":
            # Extract transcripts for specific video IDs (would need video_ids parameter)
            # Skip for now as we don't have video IDs from search_query
            logger.warning(f"  - Skipping {tool.name}: requires video_ids parameter")
        # This is where you match and activate the Apify tool
        # Support both tweet-scraper and twitter-scraper-lite
        elif tool.name in ["apidojo-slash-tweet-scraper", "apidojo-slash-twitter-scraper-lite"]:
            logger.info(f"  - Adding task: {tool.name}")

            if twitter_sources:
                # Extract usernames from Twitter URLs
                # For twitter-scraper-lite, use twitterHandles parameter (better for profile scraping)
                # For tweet-scraper, use searchTerms with "from:username" format
                usernames = []
                for url in twitter_sources:
                    # Extract username from URLs like https://x.com/username or https://twitter.com/username
                    username_match = re.search(r'(?:x\.com|twitter\.com)/([^/?]+)', url)
                    if username_match:
                        username = username_match.group(1)
                        # Remove @ if present
                        username = username.lstrip('@')
                        usernames.append(username)
                    else:
                        logger.warning(f"Could not extract username from URL: {url}")
                
                if usernames:
                    # Use twitterHandles for twitter-scraper-lite (more efficient for profile scraping)
                    # Use searchTerms with "from:" prefix for tweet-scraper
                    if tool.name == "apidojo-slash-twitter-scraper-lite":
                        logger.info(f"Using twitterHandles: {usernames[:5]}...")  # Log first 5
                        request_data = {
                            "twitterHandles": usernames[:20],  # Limit to 20 handles
                            "maxItems": 20,
                            "sort": "Latest",
                        }
                    else:
                        # For tweet-scraper, use searchTerms with "from:username" format
                        from_usernames = [f"from:{u}" for u in usernames[:10]]
                        logger.info(f"Using search terms: {from_usernames[:5]}...")
                        request_data = {
                            "searchTerms": from_usernames,
                            "maxItems": 20,
                            "proxyConfiguration": {"useApifyProxy": True},
                        }
                else:
                    # Fallback to search query if no usernames extracted
                    logger.warning("No usernames extracted, falling back to search query")
                    request_data = {
                        "searchTerms": [search_query],
                        "maxItems": 20,
                        "sort": "Latest",
                    }
                    if tool.name != "apidojo-slash-twitter-scraper-lite":
                        request_data["proxyConfiguration"] = {"useApifyProxy": True}
            else:
                # Create Pydantic schema object for validation, then convert to dict
                request_data = {
                    "searchTerms": [search_query],
                    "maxItems": 20,
                    "sort": "Latest",
                }
                if tool.name != "apidojo-slash-twitter-scraper-lite":
                    request_data["proxyConfiguration"] = {"useApifyProxy": True}

            tasks.append(tool.coroutine(**request_data))
            task_names.append(tool.name)
    return tasks, task_names


def extract_source_info(content: str, source_name: str) -> Dict[str, str]:
    """Extracts Title and URL from a tool's string output."""
    source_info = {"name": source_name, "title": "N/A", "url": "N/A"}

    # Try to find a URL first using multiple common patterns
    url_patterns = [
        r"URL: (https?://[^\s]+)",
        r"Link: (https?://[^\s]+)",
        r'"video_url":\s*"([^"]+)"',
        r'"url":\s*"([^"]+)"',
        r'"link":\s*"([^"]+)"',
        r'"pdf_url":\s*"([^"]+)"',
        r'(https?://[^\s\n\)\"\'<>]+)' # Generic fallback
    ]
    
    for pattern in url_patterns:
        url_match = re.search(pattern, content)
        if url_match:
            source_info["url"] = url_match.group(1).strip().rstrip('.,;!?')
            break

    # Try to find a Title
    title_patterns = [
        r"Title: ([^\n]+)",
        r'"title":\s*"([^"]+)"',
        r'"name":\s*"([^"]+)"'
    ]
    
    for pattern in title_patterns:
        title_match = re.search(pattern, content)
        if title_match:
            source_info["title"] = title_match.group(1).strip()
            break
            
    # If no title, use the first line as a fallback
    if source_info["title"] == "N/A" and content:
        source_info["title"] = content.split("\n")[0].strip()[:100]

    return source_info


def extract_title_near_url(content_str: str, url: str, max_distance: int = 500) -> str:
    """Extract title from content near a given URL.
    
    Searches for title patterns in the content around the URL location.
    
    Args:
        content_str: The content string to search in
        url: The URL to find titles near
        max_distance: Maximum characters before/after URL to search for title
        
    Returns:
        Extracted title or empty string if not found
    """
    # Find the position of the URL in the content
    url_pos = content_str.find(url)
    if url_pos == -1:
        return ""
    
    # Extract a window around the URL
    start = max(0, url_pos - max_distance)
    end = min(len(content_str), url_pos + len(url) + max_distance)
    window = content_str[start:end]
    
    # Title patterns to search for (case-insensitive)
    title_patterns = [
        r'(?i)"title"\s*:\s*"([^"]+)"',  # JSON: "title": "..."
        r'(?i)"name"\s*:\s*"([^"]+)"',   # JSON: "name": "..."
        r'(?i)title\s*:\s*([^\n]+)',     # Text: Title: ...
        r'(?i)TITLE\s*:\s*([^\n]+)',      # Text: TITLE: ...
        r'(?i)Title\s*:\s*([^\n]+)',     # Text: Title: ...
        r'(?i)name\s*:\s*([^\n]+)',      # Text: name: ...
        r'(?i)Name\s*:\s*([^\n]+)',      # Text: Name: ...
    ]
    
    # Search for title patterns in the window
    for pattern in title_patterns:
        matches = re.findall(pattern, window)
        if matches:
            # Take the first match and clean it up
            title = matches[0].strip()
            # Remove common trailing characters
            title = title.rstrip('.,;!?')
            # Limit length
            if len(title) > 200:
                title = title[:200] + "..."
            if title and title.lower() not in ["n/a", "none", "null", ""]:
                return title
    
    return ""


def extract_sources_from_raw_content(content: Any, source_name: str) -> List[Dict[str, str]]:
    """Generic source extractor that looks for URLs in raw content using multiple patterns.
    
    This function replaces instrument-specific parsing for sources by looking for 
    common URL keys in JSON or text patterns. It also extracts titles from the content
    when available.
    
    Args:
        content: Raw content from MCP tool (can be dict, list, str, or None)
        source_name: Name of the source/tool (e.g., "youtube", "arxiv", "twitter")
        
    Returns:
        List of source dictionaries with 'name', 'title', and 'url' keys
    """
    sources = []
    
    # Handle None or empty content
    if content is None:
        return sources
    
    # 1. Convert content to string for regex searching
    if isinstance(content, (dict, list)):
        try:
            content_str = json.dumps(content, indent=2, default=str)
        except Exception:
            content_str = str(content)
    else:
        content_str = str(content)
        
    if not content_str or not content_str.strip():
        return sources
        
    # 2. Extract sources from structured data if possible (for better titles)
    if isinstance(content, list):
        for item in content:
            if isinstance(item, dict):
                u = item.get("video_url") or item.get("url") or item.get("link") or item.get("pdf_url") or item.get("tweet_url")
                if u and isinstance(u, str):
                    t = item.get("title") or item.get("name") or item.get("text", "")
                    if not t or t == "N/A":
                        t = ""
                    sources.append({"name": source_name, "title": str(t).strip()[:200] if t else "", "url": u.strip()})
    elif isinstance(content, dict):
        # Look for lists in common keys
        found_structured = False
        for key in ["results", "videos", "papers", "data", "items", "tweets", "result"]:
            items = content.get(key)
            if isinstance(items, list):
                for item in items:
                    if isinstance(item, dict):
                        u = item.get("video_url") or item.get("url") or item.get("link") or item.get("pdf_url") or item.get("tweet_url")
                        if u and isinstance(u, str):
                            t = item.get("title") or item.get("name") or item.get("text", "")
                            if not t or t == "N/A":
                                t = ""
                            sources.append({"name": source_name, "title": str(t).strip()[:200] if t else "", "url": u.strip()})
                found_structured = True
                break
        
        if not found_structured:
            # Single object
            u = content.get("video_url") or content.get("url") or content.get("link") or content.get("pdf_url") or content.get("tweet_url")
            if u and isinstance(u, str):
                t = content.get("title") or content.get("name") or content.get("text", "")
                if not t or t == "N/A":
                    t = ""
                sources.append({"name": source_name, "title": str(t).strip()[:200] if t else "", "url": u.strip()})

    # 3. Use regex to find any other URLs (especially if content was just a string)
    patterns = [
        r'"video_url"\s*:\s*"([^"]+)"',
        r'"url"\s*:\s*"([^"]+)"',
        r'"link"\s*:\s*"([^"]+)"',
        r'"pdf_url"\s*:\s*"([^"]+)"',
        r'URL:\s*(https?://[^\s\n\)\"\'<>]+)',
        r'Link:\s*(https?://[^\s\n\)\"\'<>]+)',
        r'https?://[^\s\n\)\"\'<>]+' # Generic fallback
    ]
    
    # Create a set of already found URLs to avoid duplicates
    existing_urls = {s["url"] for s in sources}
    
    for pattern in patterns:
        matches = re.findall(pattern, content_str)
        for url in matches:
            url = url.strip().rstrip('.,;!?')
            if url.startswith('http') and url not in existing_urls:
                # Try to extract title near this URL
                title = extract_title_near_url(content_str, url)
                sources.append({"name": source_name, "title": title, "url": url})
                existing_urls.add(url)
                
    return sources


def filter_invalid_sources(sources: List[Dict[str, str]]) -> List[Dict[str, str]]:
    """Filter out invalid sources that indicate no results or empty responses.
    
    Removes sources with:
    - Titles indicating no results (e.g., "No Results", "No search results found")
    - Invalid URLs (e.g., "#", "N/A", empty strings)
    - Both title and URL are "N/A"
    - Sources with "No Results" in title AND "#" as URL
    """
    invalid_title_patterns = [
        r"^no\s+results?$",
        r"^no\s+search\s+results?\s+found$",
        r"^n/a$",
        r"^none$",
        r"^empty$",
        r".*no\s+results.*",  # Match "No Results" anywhere in title
        r".*no\s+search\s+results?\s+found.*",  # Match "No search results found" anywhere
    ]
    
    invalid_urls = ["#", "N/A", "n/a", "", None]
    
    valid_sources = []
    for source in sources:
        title = source.get("title", "N/A")
        url = source.get("url", "N/A")
        
        # Check if title indicates no results (case-insensitive, anywhere in string)
        title_lower = title.strip().lower() if title else ""
        is_invalid_title = any(
            re.search(pattern, title_lower) for pattern in invalid_title_patterns
        )
        
        # Check if URL is invalid
        is_invalid_url = url in invalid_urls or (url and url.strip() in invalid_urls)
        
        # Special case: If title contains "No Results" AND URL is "#", definitely invalid
        if ("no results" in title_lower or "no search results" in title_lower) and url == "#":
            logger.debug(f"Filtering out invalid source: title='{title}', url='{url}' (No Results with # URL)")
            continue
        
        # Skip if title indicates no results
        if is_invalid_title:
            logger.debug(f"Filtering out invalid source: title='{title}', url='{url}' (invalid title)")
            continue
        
        # Skip if both title and URL are invalid
        if is_invalid_url and title in ["N/A", "n/a", ""]:
            logger.debug(f"Filtering out invalid source: title='{title}', url='{url}' (both invalid)")
            continue
        
        # Keep sources that have at least a valid title or URL
        if title != "N/A" and title.strip() and (url not in invalid_urls and url and url != "#"):
            valid_sources.append(source)
    
    filtered_count = len(sources) - len(valid_sources)
    if filtered_count > 0:
        logger.info(f"Filtered out {filtered_count} invalid sources")
    
    return valid_sources


def are_sources_valid(sources: List[Dict[str, str]]) -> bool:
    """Check if sources list contains at least one valid source.
    
    Args:
        sources: List of source dictionaries
        
    Returns:
        True if at least one valid source exists, False otherwise
    """
    if not sources:
        return False
    
    filtered = filter_invalid_sources(sources)
    return len(filtered) > 0


def is_formatted_sources_valid(formatted_sources: str) -> bool:
    """Check if formatted sources string contains valid sources.
    
    Args:
        formatted_sources: Formatted sources string (e.g., "1. Title (URL)")
        
    Returns:
        True if sources appear valid, False if they contain "No Results" or are empty
    """
    if not formatted_sources or formatted_sources.strip() == "":
        return False
    
    if formatted_sources.strip() == "No valid sources found.":
        return False
    
    # Check for "No Results" patterns in the formatted string
    formatted_lower = formatted_sources.lower()
    invalid_patterns = [
        "no results",
        "no search results found",
        "url: #",
        "(#)",
        "(n/a)",
    ]
    
    # If the formatted string contains any invalid patterns, it's not valid
    if any(pattern in formatted_lower for pattern in invalid_patterns):
        # But check if there are also valid sources - if it's ALL invalid, return False
        # Count how many sources appear to be invalid vs valid
        lines = formatted_sources.split("\n")
        invalid_count = sum(1 for line in lines if any(pattern in line.lower() for pattern in invalid_patterns))
        total_count = len([line for line in lines if line.strip()])
        
        # If all sources are invalid, return False
        if invalid_count == total_count and total_count > 0:
            return False
    
    return True


def deduplicate_sources(sources: List[Dict[str, str]]) -> List[Dict[str, str]]:
    """Deduplicate sources based on URL and title combination.
    
    Sources are considered duplicates if they have the same URL (and URL is not "N/A").
    If URL is "N/A", sources are considered duplicates if they have the same title.
    """
    seen_urls = set()
    seen_titles = set()  # For sources without URLs
    unique_sources = []
    
    for source in sources:
        url = source.get("url", "N/A")
        title = source.get("title", "N/A")
        
        # Normalize URL for comparison (remove trailing slashes, etc.)
        if url and url != "N/A":
            url_normalized = url.rstrip('/')
            if url_normalized not in seen_urls:
                seen_urls.add(url_normalized)
                unique_sources.append(source)
        elif title and title != "N/A":
            # For sources without URLs, deduplicate by title
            title_normalized = title.strip().lower()
            if title_normalized not in seen_titles:
                seen_titles.add(title_normalized)
                unique_sources.append(source)
        else:
            # If both URL and title are N/A, skip it
            logger.warning(f"Skipping source with no URL or title: {source}")
    
    logger.info(f"Deduplicated {len(sources)} sources to {len(unique_sources)} unique sources")
    return unique_sources


# --- Helper Function 2: To format the final sources list ---


def format_sources(sources: List[Dict[str, str]], include_source_name: bool = False) -> str:
    """Formats a list of source dictionaries into a numbered string.
    
    Args:
        sources: List of source dictionaries with 'name', 'title', and 'url' keys
        include_source_name: If True, includes [source_name] prefix. Default False.
    """
    if not sources:
        return "No valid sources found."

    formatted_list = []
    for i, source in enumerate(sources):
        title = source.get("title")
        url = source.get("url", "No URL")
        name = source.get("name")
        
        line = f"{i + 1}."

        if include_source_name and name:
            line += f" [{name}]"

        # Only include the title if it's present and not "N/A"
        if title and title != "N/A":
            line += f" {title} ({url})"
        else:
            # Otherwise, just include the URL
            line += f" {url}"
            
        formatted_list.append(line)

    return "\n".join(formatted_list)


def clean_apify_tweet_data(data: str) -> str:
    """
    Cleans the tweet data from Apify to extract relevant fields like text, username, and timestamp.
    This function can handle both a single JSON array of tweets and line-delimited JSON (JSONL).

    Args:
        data: A string containing raw output from Apify.

    Returns:
        A formatted string with the cleaned tweet text, including username and timestamp,
        with each tweet on a new line.
    """
    logger.info(f"Raw Apify data received for cleaning:\n{data}")

    # Extract JSON part from the raw string, as actor output may include summary text
    json_match = re.search(r"(\[.*\])", data, re.DOTALL)
    if json_match:
        json_data = json_match.group(1)
        logger.info("Successfully extracted JSON array from raw input.")
    else:
        logger.warning(
            "Could not find a JSON array in the raw data. Attempting to parse as is."
        )
        json_data = data

    cleaned_tweets_info = []
    tweets = []

    try:
        tweets = json.loads(json_data)
        # Ensure it's a list, as a single tweet object could also be valid JSON
        if not isinstance(tweets, list):
            tweets = [tweets]
        logger.info(f"Successfully parsed data as JSON. Type: {type(tweets)}")
    except json.JSONDecodeError:
        logger.warning(
            "Failed to parse data as a single JSON object. Assuming JSONL format."
        )

        for line in data.splitlines():
            try:
                tweet = json.loads(line)
                if isinstance(tweet, dict):
                    tweets.append(tweet)
            except json.JSONDecodeError:
                continue

    # Process the list of tweets
    logger.info(f"Processing {len(tweets)} tweets...")
    for i, tweet in enumerate(tweets):
        logger.info(f"Processing tweet #{i + 1}: {tweet}")
        if isinstance(tweet, dict):
            # Skip items with noResults flag
            if tweet.get("noResults", False):
                logger.debug(f"Skipping tweet #{i + 1} - noResults flag is True")
                continue
            tweet_text = tweet.get("text")
            if tweet_text:
                cleaned_tweets_info.append(tweet_text)

    logger.info(f"Cleaned {len(cleaned_tweets_info)} tweets successfully.")
    final_result = "\n\n".join(cleaned_tweets_info)
    logger.info(f"Final cleaned tweet text:\n{final_result}")
    return final_result


def get_twitter_sources_for_topic(topic: str, topics_file_path: str) -> List[str]:
    """
    Loads twitter sources from the provided topics YAML file for a given topic.

    Args:
        topic: The topic to get twitter sources for.
        topics_file_path: The path to the topics YAML file.

    Returns:
        A list of twitter source URLs.
    """
    try:
        topics_data = load_yaml(topics_file_path)
        if topics_data and isinstance(topics_data, list):
            # Find the topic in the list
            for topic_entry in topics_data:
                if isinstance(topic_entry, dict) and topic_entry.get("topic") == topic:
                    twitter_sources = topic_entry.get("twitter_sources", [])
                    if twitter_sources:
                        logger.info(
                            f"Found {len(twitter_sources)} Twitter sources for topic '{topic}'"
                        )
                        return twitter_sources
    except Exception as e:
        logger.error(f"Error getting twitter sources for topic '{topic}': {e}")

    logger.warning(f"No Twitter sources found for topic '{topic}'")
    return []


def get_telegram_sources_for_topic(topic: str, topics_file_path: str) -> List[str]:
    """
    Loads telegram sources from the provided topics YAML file for a given topic.

    Args:
        topic: The topic to get telegram sources for.
        topics_file_path: The path to the topics YAML file.

    Returns:
        A list of telegram source URLs.
    """
    try:
        topics_data = load_yaml(topics_file_path)
        if topics_data and isinstance(topics_data, list):
            # Find the topic in the list
            for topic_entry in topics_data:
                if isinstance(topic_entry, dict) and topic_entry.get("topic") == topic:
                    telegram_sources = topic_entry.get("telegram_sources", [])
                    if telegram_sources:
                        logger.info(
                            f"Found {len(telegram_sources)} Telegram sources for topic '{topic}'"
                        )
                        return telegram_sources
    except Exception as e:
        logger.error(f"Error getting telegram sources for topic '{topic}': {e}")

    logger.warning(f"No Telegram sources found for topic '{topic}'")
    return []
def construct_tools_yaml(mcp_tools: List[Any], tool_to_server_map: Optional[Dict[str, str]] = None) -> str:
    """
    Constructs valid YAML specification from MCP tools.
    
    Args:
        mcp_tools: List of StructuredTool objects from MCP servers
        tool_to_server_map: Optional dictionary mapping tool names to MCP server names
        
    Returns:
        Valid YAML string containing tool specifications
    """
    tools_spec = []
    
    for tool in mcp_tools:
        tool_spec = {
            "name": getattr(tool, "name", "unknown"),
            "description": getattr(tool, "description", ""),
        }
        
        # Add server information if available
        if tool_to_server_map:
            tool_name = tool_spec["name"]
            if tool_name in tool_to_server_map:
                tool_spec["server"] = tool_to_server_map[tool_name]
        
        # Extract tags from metadata
        metadata = getattr(tool, "metadata", {})
        if metadata:
            meta_info = metadata.get("_meta", {})
            fastmcp_info = meta_info.get("_fastmcp", {})
            tags = fastmcp_info.get("tags", [])
            if tags:
                tool_spec["tags"] = tags
        
        # Extract parameters from args_schema
        args_schema = getattr(tool, "args_schema", {})
        if args_schema:
            parameters = {}
            properties = args_schema.get("properties", {})
            required = args_schema.get("required", [])
            defs = args_schema.get("$defs", {})
            
            # Helper function to resolve $ref references
            def resolve_ref(ref_spec):
                """Resolve $ref references to actual schema definitions."""
                if isinstance(ref_spec, dict) and "$ref" in ref_spec:
                    ref_path = ref_spec["$ref"]
                    # Handle #/$defs/Name format
                    if ref_path.startswith("#/$defs/"):
                        def_name = ref_path.replace("#/$defs/", "")
                        if def_name in defs:
                            resolved = defs[def_name].copy()
                            # Merge any other properties from ref_spec
                            for key, value in ref_spec.items():
                                if key != "$ref":
                                    resolved[key] = value
                            return resolved
                return ref_spec
            
            # Helper function to extract parameter info from a schema spec
            def extract_param_info(param_spec, is_required=False):
                """Extract parameter information from a schema specification."""
                param_info = {}
                
                # Handle anyOf (union types) - extract types from union
                if "anyOf" in param_spec:
                    any_of_types = []
                    for option in param_spec["anyOf"]:
                        if isinstance(option, dict):
                            opt_type = option.get("type")
                            if opt_type:
                                any_of_types.append(opt_type)
                    if any_of_types:
                        param_info["type"] = " | ".join(any_of_types) if len(any_of_types) > 1 else any_of_types[0]
                    else:
                        param_info["type"] = "union"
                else:
                    param_info["type"] = param_spec.get("type", "unknown")
                
                # Add description if available
                if "description" in param_spec:
                    param_info["description"] = param_spec["description"]
                
                # Add title if available
                if "title" in param_spec:
                    param_info["title"] = param_spec["title"]
                
                # Add default value if available
                if "default" in param_spec:
                    param_info["default"] = param_spec["default"]
                
                # Add constraints
                if "minimum" in param_spec:
                    param_info["minimum"] = param_spec["minimum"]
                if "maximum" in param_spec:
                    param_info["maximum"] = param_spec["maximum"]
                if "minLength" in param_spec:
                    param_info["minLength"] = param_spec["minLength"]
                if "maxLength" in param_spec:
                    param_info["maxLength"] = param_spec["maxLength"]
                if "enum" in param_spec:
                    param_info["enum"] = param_spec["enum"]
                if "items" in param_spec:
                    items_spec = param_spec["items"]
                    if isinstance(items_spec, dict):
                        param_info["items"] = {"type": items_spec.get("type", "unknown")}
                    else:
                        param_info["items"] = items_spec
                if "minItems" in param_spec:
                    param_info["minItems"] = param_spec["minItems"]
                if "maxItems" in param_spec:
                    param_info["maxItems"] = param_spec["maxItems"]
                if "format" in param_spec:
                    param_info["format"] = param_spec["format"]
                
                # Mark as required
                if is_required:
                    param_info["required"] = True
                
                return param_info
            
            for param_name, param_spec in properties.items():
                # Resolve $ref references if present
                param_spec = resolve_ref(param_spec)
                
                # Check if this parameter is an object with nested properties
                if param_spec.get("type") == "object" and "properties" in param_spec:
                    # Extract nested properties
                    nested_properties = {}
                    nested_required = param_spec.get("required", [])
                    nested_defs = param_spec.get("$defs", defs)  # Use parent defs if no local defs
                    
                    # Update resolve_ref to use nested defs if available
                    def resolve_nested_ref(ref_spec):
                        if isinstance(ref_spec, dict) and "$ref" in ref_spec:
                            ref_path = ref_spec["$ref"]
                            if ref_path.startswith("#/$defs/"):
                                def_name = ref_path.replace("#/$defs/", "")
                                if def_name in nested_defs:
                                    resolved = nested_defs[def_name].copy()
                                    for key, value in ref_spec.items():
                                        if key != "$ref":
                                            resolved[key] = value
                                    return resolved
                        return ref_spec
                    
                    for nested_name, nested_spec in param_spec["properties"].items():
                        nested_spec = resolve_nested_ref(nested_spec)
                        nested_info = extract_param_info(nested_spec, nested_name in nested_required)
                        nested_properties[nested_name] = nested_info
                    
                    param_info = {
                        "type": "object",
                        "properties": nested_properties,
                    }
                    if "description" in param_spec:
                        param_info["description"] = param_spec["description"]
                    if "title" in param_spec:
                        param_info["title"] = param_spec["title"]
                    if param_name in required:
                        param_info["required"] = True
                else:
                    # Regular parameter extraction
                    param_info = extract_param_info(param_spec, param_name in required)
                
                parameters[param_name] = param_info
            
            if parameters:
                tool_spec["parameters"] = parameters
        
        tools_spec.append(tool_spec)
    
    # Convert to YAML
    yaml_output = yaml.dump(
        {"tools": tools_spec},
        default_flow_style=False,
        sort_keys=False,
        allow_unicode=True,
        width=1000,  # Wide width to prevent line breaks in long descriptions
    )
    
    return yaml_output


def construct_tools_description_yaml(mcp_tools: List[Any], tool_to_server_map: Optional[Dict[str, str]] = None) -> str:
    """
    Constructs a simplified YAML with only name and description for each tool.
    
    Args:
        mcp_tools: List of StructuredTool objects from MCP servers
        tool_to_server_map: Optional dictionary mapping tool names to MCP server names
        
    Returns:
        Valid YAML string containing simplified tool specifications (name and description only)
    """
    tools_spec = []
    
    for tool in mcp_tools:
        tool_spec = {
            "name": getattr(tool, "name", "unknown"),
            "description": getattr(tool, "description", ""),
        }
        
        # Add server information if available
        if tool_to_server_map:
            tool_name = tool_spec["name"]
            if tool_name in tool_to_server_map:
                tool_spec["server"] = tool_to_server_map[tool_name]
        
        tools_spec.append(tool_spec)
    
    # Convert to YAML
    yaml_output = yaml.dump(
        {"tools": tools_spec},
        default_flow_style=False,
        sort_keys=False,
        allow_unicode=True,
        width=1000,
    )
    
    return yaml_output


def parse_tools_description_from_yaml(yaml_content: str) -> List[Dict[str, Any]]:
    """
    Parse YAML content and return list of tool descriptions as dictionaries.
    
    Args:
        yaml_content: YAML string containing tools specification
        
    Returns:
        List of dictionaries with tool information (name, description, server)
    """
    try:
        data = yaml.safe_load(yaml_content)
        if not data or "tools" not in data:
            logger.warning("YAML content does not contain 'tools' key")
            return []
        
        tools_list = []
        for tool in data.get("tools", []):
            tool_dict = {
                "name": tool.get("name", "unknown"),
                "description": tool.get("description", ""),
                "server": tool.get("server"),
            }
            tools_list.append(tool_dict)
        
        return tools_list
    except Exception as e:
        logger.error(f"Error parsing tools YAML: {e}")
        return []


def save_tools_yaml_to_file(yaml_content: str, file_path: str) -> None:
    """
    Saves YAML content to a file.
    
    Args:
        yaml_content: YAML string content to save
        file_path: Path to the output YAML file
    """
    import os
    
    # Create directory if it doesn't exist
    dir_path = os.path.dirname(file_path)
    if dir_path:  # Only create directory if path contains a directory
        os.makedirs(dir_path, exist_ok=True)
    
    with open(file_path, "w", encoding="utf-8") as f:
        f.write(yaml_content)
    
    logger.info(f"Tools YAML saved to: {file_path}")

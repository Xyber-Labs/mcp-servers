import json
import logging
import re
from typing import Any

import yaml

logger = logging.getLogger(__name__)


def clean_response(response_text: str) -> str:
    """Clean the response text by removing markdown code block markers if present."""
    try:
        if isinstance(response_text, list):
            logger.warning("clean_response received a list instead of string, extracting first element")
            if len(response_text) > 0:
                response_text = str(response_text[0])
            else:
                response_text = ""

        if not isinstance(response_text, str):
            response_text = str(response_text)

        cleaned_response = response_text.strip()
        if cleaned_response.startswith("```json"):
            cleaned_response = cleaned_response[7:]
            if cleaned_response.endswith("```"):
                cleaned_response = cleaned_response[:-3]
        elif cleaned_response.startswith("```"):
            cleaned_response = cleaned_response[3:]
            if cleaned_response.endswith("```"):
                cleaned_response = cleaned_response[:-3]

        cleaned_response = cleaned_response.strip()
        cleaned_response = re.sub(r"(?<!\\)\\\'", "'", cleaned_response)
        cleaned_response = cleaned_response.replace("\\\\'", "'")

        def fix_escaped_quotes(text):
            result = text
            while '\\\\\\\\"' in result:
                result = result.replace('\\\\\\\\"', '\\\\"')
            result = result.replace('\\\\\\"', '\\"')
            result = result.replace('\\\\"', '\\"')
            return result

        cleaned_response = fix_escaped_quotes(cleaned_response)

        def escape_string_content(match):
            full_match = match.group(0)
            content = full_match[1:-1]
            content = re.sub(r'(?<!\\)"', r'\\"', content)
            content = content.replace("\n", "\\n").replace("\t", "\\t")
            return f'"{content}"'

        cleaned_response = re.sub(
            r'"([^"\\]|\\.)*"',
            escape_string_content,
            cleaned_response,
            flags=re.DOTALL,
        )

        cleaned_response = re.sub(r",\s*([}\]])", r"\1", cleaned_response)
        cleaned_response = re.sub(r"\bTrue\b", "true", cleaned_response)
        cleaned_response = re.sub(r"\bFalse\b", "false", cleaned_response)
        cleaned_response = re.sub(r"\bNone\b", "null", cleaned_response)

        return cleaned_response
    except Exception as e:
        logger.error(f"Error cleaning response: {e}")
        try:
            response_text = re.sub(r"\bTrue\b", "true", response_text)
            response_text = re.sub(r"\bFalse\b", "false", response_text)
            response_text = re.sub(r"\bNone\b", "null", response_text)
        except Exception:
            pass
        return response_text


def create_mcp_tasks(
    mcp_tools,
    search_query,
    simplified_search_query: str | None = None,
    twitter_sources: list[str] | None = None,
    telegram_sources: list[str] | None = None,
):
    """Creates MCP tasks using Pydantic schemas for validation."""

    def _tool_args_schema_has_field(tool_obj: Any, field_name: str) -> bool:
        args_schema = getattr(tool_obj, "args_schema", None)
        if not args_schema:
            return False
        try:
            model_fields = getattr(args_schema, "model_fields", None)
            if model_fields and field_name in model_fields:
                return True
        except Exception:
            pass
        try:
            v1_fields = getattr(args_schema, "__fields__", None)
            if v1_fields and field_name in v1_fields:
                return True
        except Exception:
            pass
        if isinstance(args_schema, dict) and field_name in args_schema:
            return True
        return False

    tasks = []
    task_names = []
    for tool in mcp_tools:
        if tool.name == "tavily_search":
            tasks.append(tool.coroutine(query=search_query, max_results=3))
            task_names.append(tool.name)
            logger.info(f"  - Added task: {tool.name}")
        elif tool.name == "parse_telegram_channels":
            if telegram_sources:
                request_data = {"channels": telegram_sources, "limit": 3}
                tasks.append(tool.coroutine(**request_data))
                task_names.append(tool.name)
                logger.info(f"  - Added task: {tool.name}")
        elif tool.name == "arxiv_search":
            request_payload = {"query": search_query, "max_results": 3}
            if _tool_args_schema_has_field(tool, "request"):
                tasks.append(tool.coroutine(request=request_payload))
            else:
                tasks.append(tool.coroutine(**request_payload))
            task_names.append(tool.name)
            logger.info(f"  - Added task: {tool.name}")
        elif tool.name == "search_youtube_videos":
            request_data = {"query": search_query}
            tasks.append(tool.coroutine(**request_data))
            task_names.append(tool.name)
            logger.info(f"  - Added task: {tool.name}")
        elif tool.name == "twitter_search_topic":
            twitter_query = simplified_search_query or search_query
            request_data = {"topic": twitter_query}
            tasks.append(tool.coroutine(**request_data))
            task_names.append(tool.name)
            logger.info(f"  - Added task: {tool.name}")
        elif tool.name == "search_and_extract_transcripts":
            request_data = {"query": search_query}
            tasks.append(tool.coroutine(**request_data))
            task_names.append(tool.name)
            logger.info(f"  - Added task: {tool.name}")
        elif tool.name in ["apidojo-slash-tweet-scraper", "apidojo-slash-twitter-scraper-lite"]:
            logger.info(f"  - Adding task: {tool.name}")
            twitter_query = simplified_search_query or search_query

            if twitter_sources:
                usernames = []
                for url in twitter_sources:
                    username_match = re.search(r"(?:x\.com|twitter\.com)/([^/?]+)", url)
                    if username_match:
                        username = username_match.group(1).lstrip("@")
                        usernames.append(username)

                if usernames:
                    if tool.name == "apidojo-slash-twitter-scraper-lite":
                        request_data = {
                            "twitterHandles": usernames[:20],
                            "maxItems": 20,
                            "sort": "Latest",
                        }
                    else:
                        from_usernames = [f"from:{u}" for u in usernames[:10]]
                        request_data = {
                            "searchTerms": from_usernames,
                            "maxItems": 20,
                            "proxyConfiguration": {"useApifyProxy": True},
                        }
                else:
                    request_data = {
                        "searchTerms": [twitter_query],
                        "maxItems": 20,
                        "sort": "Latest",
                    }
                    if tool.name != "apidojo-slash-twitter-scraper-lite":
                        request_data["proxyConfiguration"] = {"useApifyProxy": True}
            else:
                request_data = {
                    "searchTerms": [twitter_query],
                    "maxItems": 20,
                    "sort": "Latest",
                }
                if tool.name != "apidojo-slash-twitter-scraper-lite":
                    request_data["proxyConfiguration"] = {"useApifyProxy": True}

            tasks.append(tool.coroutine(**request_data))
            task_names.append(tool.name)
    return tasks, task_names


def filter_mcp_tools_for_deepresearcher(mcp_tools: list[Any]) -> list[Any]:
    """Filter the tool list exposed to the DeepResearcher agent."""
    if not mcp_tools:
        return []

    tool_names = {getattr(t, "name", None) for t in mcp_tools}
    if "search_and_extract_transcripts" in tool_names:
        youtube_extras = {
            "mcp_search_youtube_videos",
            "extract_transcripts",
            "youtube_search_and_transcript",
        }
        filtered = [t for t in mcp_tools if getattr(t, "name", None) not in youtube_extras]
        return filtered

    return mcp_tools


def _extract_title_near_url(content_str: str, url: str, max_distance: int = 500) -> str:
    """Extract title from content near a given URL."""
    url_pos = content_str.find(url)
    if url_pos == -1:
        return ""

    start = max(0, url_pos - max_distance)
    end = min(len(content_str), url_pos + len(url) + max_distance)
    window = content_str[start:end]

    title_patterns = [
        r'(?i)"title"\s*:\s*"([^"]+)"',
        r'(?i)"name"\s*:\s*"([^"]+)"',
        r"(?i)title\s*:\s*([^\n]+)",
        r"(?i)name\s*:\s*([^\n]+)",
    ]

    for pattern in title_patterns:
        matches = re.findall(pattern, window)
        if matches:
            title = matches[0].strip().rstrip(".,;!?")
            if len(title) > 200:
                title = title[:200] + "..."
            if title and title.lower() not in ["n/a", "none", "null", ""]:
                return title

    return ""


def extract_sources_from_raw_content(content: Any, source_name: str) -> list[dict[str, str]]:
    """Generic source extractor that looks for URLs in raw content."""
    sources = []

    if content is None:
        return sources

    if isinstance(content, (dict, list)):
        try:
            content_str = json.dumps(content, indent=2, default=str)
        except Exception:
            content_str = str(content)
    else:
        content_str = str(content)

    if not content_str or not content_str.strip():
        return sources

    if isinstance(content, list):
        for item in content:
            if isinstance(item, dict):
                u = (
                    item.get("video_url")
                    or item.get("url")
                    or item.get("link")
                    or item.get("pdf_url")
                    or item.get("tweet_url")
                )
                if u and isinstance(u, str):
                    t = item.get("title") or item.get("name") or item.get("text", "")
                    if not t or t == "N/A":
                        t = ""
                    sources.append({
                        "name": source_name,
                        "title": str(t).strip()[:200] if t else "",
                        "url": u.strip(),
                    })
    elif isinstance(content, dict):
        found_structured = False
        for key in ["results", "videos", "papers", "data", "items", "tweets", "result"]:
            items = content.get(key)
            if isinstance(items, list):
                for item in items:
                    if isinstance(item, dict):
                        u = (
                            item.get("video_url")
                            or item.get("url")
                            or item.get("link")
                            or item.get("pdf_url")
                            or item.get("tweet_url")
                        )
                        if u and isinstance(u, str):
                            t = item.get("title") or item.get("name") or item.get("text", "")
                            if not t or t == "N/A":
                                t = ""
                            sources.append({
                                "name": source_name,
                                "title": str(t).strip()[:200] if t else "",
                                "url": u.strip(),
                            })
                found_structured = True
                break

        if not found_structured:
            u = (
                content.get("video_url")
                or content.get("url")
                or content.get("link")
                or content.get("pdf_url")
                or content.get("tweet_url")
            )
            if u and isinstance(u, str):
                t = content.get("title") or content.get("name") or content.get("text", "")
                if not t or t == "N/A":
                    t = ""
                sources.append({
                    "name": source_name,
                    "title": str(t).strip()[:200] if t else "",
                    "url": u.strip(),
                })

    patterns = [
        r'"video_url"\s*:\s*"([^"]+)"',
        r'"url"\s*:\s*"([^"]+)"',
        r'"link"\s*:\s*"([^"]+)"',
        r'"pdf_url"\s*:\s*"([^"]+)"',
        r"URL:\s*(https?://[^\s\n\)\"\'<>]+)",
        r"Link:\s*(https?://[^\s\n\)\"\'<>]+)",
        r"https?://[^\s\n\)\"\'<>]+",
    ]

    existing_urls = {s["url"] for s in sources}

    for pattern in patterns:
        matches = re.findall(pattern, content_str)
        for url in matches:
            url = url.strip().rstrip(".,;!?")
            if url.startswith("http") and url not in existing_urls:
                title = _extract_title_near_url(content_str, url)
                sources.append({"name": source_name, "title": title, "url": url})
                existing_urls.add(url)

    return sources


def deduplicate_sources(sources: list[dict[str, str]]) -> list[dict[str, str]]:
    """Deduplicate sources based on URL and title combination."""
    seen_urls = set()
    seen_titles = set()
    unique_sources = []

    for source in sources:
        url = source.get("url", "N/A")
        title = source.get("title", "N/A")

        if url and url != "N/A":
            url_normalized = url.rstrip("/")
            if url_normalized not in seen_urls:
                seen_urls.add(url_normalized)
                unique_sources.append(source)
        elif title and title != "N/A":
            title_normalized = title.strip().lower()
            if title_normalized not in seen_titles:
                seen_titles.add(title_normalized)
                unique_sources.append(source)

    logger.info(f"Deduplicated {len(sources)} sources to {len(unique_sources)} unique sources")
    return unique_sources


def format_sources(sources: list[dict[str, str]], include_source_name: bool = False) -> str:
    """Formats a list of source dictionaries into a numbered string."""
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

        if title and title != "N/A":
            line += f" {title} ({url})"
        else:
            line += f" {url}"

        formatted_list.append(line)

    return "\n".join(formatted_list)


def construct_tools_description_yaml(
    mcp_tools: list[Any], tool_to_server_map: dict[str, str] | None = None
) -> str:
    """Constructs a simplified YAML with only name and description for each tool."""
    tools_spec = []

    for tool in mcp_tools:
        tool_spec = {
            "name": getattr(tool, "name", "unknown"),
            "description": getattr(tool, "description", ""),
        }

        if tool_to_server_map:
            tool_name = tool_spec["name"]
            if tool_name in tool_to_server_map:
                tool_spec["server"] = tool_to_server_map[tool_name]

        tools_spec.append(tool_spec)

    yaml_output = yaml.dump(
        {"tools": tools_spec},
        default_flow_style=False,
        sort_keys=False,
        allow_unicode=True,
        width=1000,
    )

    return yaml_output


def parse_tools_description_from_yaml(yaml_content: str) -> list[dict[str, Any]]:
    """Parse YAML content and return list of tool descriptions as dictionaries."""
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

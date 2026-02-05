"""
Async parser that converts a GitBook site into a single Markdown file optimized for LLM parsing.

It first attempts to use GitBook's native /llms-full.txt endpoint,
and falls back to crawling the site if that's unavailable.
"""

from __future__ import annotations

import asyncio
import logging
from typing import Any, Dict, List, Optional, Union
from urllib.parse import urljoin, urlparse

import aiohttp
from bs4 import BeautifulSoup

logger = logging.getLogger(__name__)


def is_valid_url(url: str) -> bool:
    parsed = urlparse(url)
    return bool(parsed.scheme and parsed.netloc)


def clean_gitbook_url(url: str) -> str:
    parsed = urlparse(url)
    clean_path = parsed.path.rstrip("/")
    return f"{parsed.scheme}://{parsed.netloc}{clean_path}"


def get_base_url(url: str) -> str:
    cleaned_url = clean_gitbook_url(url)
    parsed = urlparse(cleaned_url)
    return f"{parsed.scheme}://{parsed.netloc}{parsed.path.rstrip('/')}"


async def fetch_llms_full(session: aiohttp.ClientSession, base_url: str) -> Optional[str]:
    llm_url = f"{base_url}/llms-full.txt"
    logger.info("Checking for native LLM support at: %s", llm_url)
    try:
        async with session.get(llm_url, timeout=aiohttp.ClientTimeout(total=10)) as response:
            if response.status == 200:
                logger.info("Found native /llms-full.txt!")
                return await response.text()
    except Exception as e:  # noqa: BLE001 - best effort network probe
        logger.warning("Error checking /llms-full.txt: %s", e)
    return None


def extract_content(html: str) -> str:
    soup = BeautifulSoup(html, "html.parser")

    content_area = soup.find("main") or soup.find("article")
    if not content_area:
        content_area = soup.find("div", class_="page-inner")
    if not content_area:
        return ""

    for extra in content_area.find_all(["nav", "header", "footer", "aside"]):
        extra.decompose()

    return content_area.get_text(separator="\n\n").strip()


def extract_title(html: str) -> str:
    soup = BeautifulSoup(html, "html.parser")
    title = soup.find("h1")
    if title:
        return title.get_text().strip()
    return "Untitled Page"


async def fetch_page(session: aiohttp.ClientSession, url: str) -> Optional[str]:
    try:
        async with session.get(url, timeout=aiohttp.ClientTimeout(total=10)) as response:
            if response.status == 200:
                return await response.text()
    except Exception as e:  # noqa: BLE001
        logger.warning("Error fetching %s: %s", url, e)
    return None


async def crawl_gitbook(
    session: aiohttp.ClientSession, base_url: str, return_json: bool = False
) -> Union[str, List[Dict[str, str]], None]:
    logger.info("Falling back to crawling: %s", base_url)

    html = await fetch_page(session, base_url)
    if not html:
        logger.error("Failed to fetch base URL: %s", base_url)
        return None

    soup = BeautifulSoup(html, "html.parser")
    nav = soup.find("nav") or soup.find("div", class_="sidebar") or soup

    seen = {base_url}

    pages_data: List[Dict[str, str]] = [
        {"url": base_url, "title": extract_title(html), "content": extract_content(html)}
    ]

    urls_to_fetch: List[str] = []
    for a in nav.find_all("a", href=True):
        href = a["href"]
        full_url = urljoin(base_url, href)
        if full_url.startswith(base_url):
            clean_url = full_url.split("#")[0].split("?")[0]
            if clean_url not in seen:
                seen.add(clean_url)
                urls_to_fetch.append(clean_url)

    results = await asyncio.gather(*(fetch_page(session, url) for url in urls_to_fetch), return_exceptions=True)

    for url, html_content in zip(urls_to_fetch, results, strict=False):
        if isinstance(html_content, Exception):
            logger.warning("Error fetching %s: %s", url, html_content)
            continue
        if not html_content:
            continue
        content = extract_content(html_content)
        if not content:
            continue
        pages_data.append({"url": url, "title": extract_title(html_content), "content": content})

    if return_json:
        return pages_data

    full_markdown = ""
    for page in pages_data:
        full_markdown += f"\n\n--- SOURCE: {page['url']} ---\n\n"
        full_markdown += page["content"]
    return full_markdown


async def convert_gitbook_to_markdown(gitbook_url: str) -> str:
    gitbook_url = clean_gitbook_url(gitbook_url)
    if not is_valid_url(gitbook_url):
        raise ValueError(f"Invalid URL: {gitbook_url}")

    base_url = get_base_url(gitbook_url)
    async with aiohttp.ClientSession() as session:
        content = await fetch_llms_full(session, base_url)
        if content:
            return content

        crawled_content = await crawl_gitbook(session, base_url, return_json=False)
        if crawled_content:
            return crawled_content

    raise RuntimeError(f"Failed to fetch content from {gitbook_url}")


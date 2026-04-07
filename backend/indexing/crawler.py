import asyncio
import logging
from typing import Dict, List, Set
from urllib.parse import urljoin, urlparse

import httpx
from bs4 import BeautifulSoup
from tenacity import (
    AsyncRetrying,
    stop_after_attempt,
    wait_fixed,
    retry_if_exception_type,
)

logger = logging.getLogger(__name__)

BASE_URL = "https://fastapi.tiangolo.com/"
RATE_LIMIT_DELAY = 1  # seconds
RETRY_ATTEMPTS = 3

# CSS selectors for elements to filter out
FILTER_SELECTORS = [
    "nav.md-tabs",  # Top navigation
    "nav.md-nav",  # Side navigation
    "header.md-header",  # Page header
    "footer.md-footer",  # Page footer
    "aside.md-sidebar--primary",  # Primary sidebar (main nav)
    "aside.md-sidebar--secondary",  # Secondary sidebar (table of contents)
]


def _normalize_url(url: str) -> str:
    parsed = urlparse(url)
    path = parsed.path or "/"
    if path != "/" and path.endswith("/"):
        path = path[:-1]
    return parsed._replace(path=path, fragment="", query="").geturl()

async def _fetch_page(client: httpx.AsyncClient, url: str) -> str:
    """
    Fetches the content of a given URL with retry and rate limiting.

    Args:
        client: An httpx.AsyncClient instance.
        url: The URL to fetch.

    Returns:
        The HTML content of the page as a string.

    Raises:
        httpx.HTTPStatusError: If the request fails after retries.
    """
    await asyncio.sleep(RATE_LIMIT_DELAY)  # Rate limiting
    try:
        async for attempt in AsyncRetrying(
            stop=stop_after_attempt(RETRY_ATTEMPTS),
            wait=wait_fixed(2),  # Wait 2 seconds between retries
            retry=retry_if_exception_type(httpx.HTTPStatusError)
            | retry_if_exception_type(httpx.RequestError),
            reraise=True,
        ):
            with attempt:
                logger.info(f"Fetching {url} (attempt {attempt.retry_state.attempt_number})")
                response = await client.get(url, follow_redirects=True)
                response.raise_for_status()  # Raise an exception for bad status codes
                return response.text
    except httpx.HTTPStatusError as e:
        logger.error(f"HTTP error fetching {url}: {e}")
        raise
    except httpx.RequestError as e:
        logger.error(f"Request error fetching {url}: {e}")
        raise

def _parse_page(html: str, url: str) -> Dict:
    """
    Parses the HTML content of a page to extract relevant information.

    Args:
        html: The HTML content as a string.
        url: The URL of the page.

    Returns:
        A dictionary containing the extracted url, title, content, code blocks,
        and section-aware content.
    """
    soup = BeautifulSoup(html, "html.parser")

    # Extract title
    title_tag = soup.find("title")
    title = title_tag.get_text(strip=True) if title_tag else "No Title"

    # Remove unwanted elements
    for selector in FILTER_SELECTORS:
        for element in soup.select(selector):
            element.decompose()

    main_content_div = soup.select_one("article.md-content__inner")
    if not main_content_div:
        main_content_div = soup.select_one("div.md-content") # Fallback for pages without article.md-content__inner
    if not main_content_div:
        logger.warning(f"Could not find main content for {url}")
        content_text_elements = soup.find_all(['h1', 'h2', 'h3', 'p', 'li', 'pre'])
    else:
        content_text_elements = main_content_div.find_all(['h1', 'h2', 'h3', 'p', 'li', 'pre'])

    full_content_parts: List[str] = []
    code_blocks: List[str] = []
    sections: List[Dict[str, str]] = []
    current_heading = title
    current_section_parts: List[str] = []

    for element in content_text_elements:
        if element.name in ["h1", "h2", "h3"]:
            if current_section_parts:
                sections.append(
                    {
                        "heading": current_heading,
                        "content": "\n".join(current_section_parts).strip(),
                    }
                )
                current_section_parts = []

            current_heading = element.get_text(strip=True) or title
            full_content_parts.append(current_heading)
        elif element.name == "pre":
            code = element.get_text(strip=True)
            code_blocks.append(code)
            block = f"```python\n{code}\n```"
            full_content_parts.append(block)
            current_section_parts.append(block)
        else:
            text = element.get_text(separator=" ", strip=True)
            if text:
                full_content_parts.append(text)
                current_section_parts.append(text)

    if current_section_parts:
        sections.append(
            {
                "heading": current_heading,
                "content": "\n".join(current_section_parts).strip(),
            }
        )

    content = "\n".join(full_content_parts).strip()

    return {
        "url": url,
        "title": title,
        "content": content,
        "code_blocks": code_blocks,
        "sections": sections,
    }


async def crawl_fastapi_docs() -> List[Dict]:
    """
    Crawls the FastAPI documentation website, extracts content, and returns
    a list of dictionaries for each page.

    Returns:
        A list of dictionaries, each containing 'url', 'title', 'content',
        and 'code_blocks' for a crawled page.
    """
    start_url = _normalize_url(BASE_URL)
    to_visit: asyncio.Queue[str] = asyncio.Queue()
    await to_visit.put(start_url)
    visited: Set[str] = set()
    documents: List[Dict] = []

    async with httpx.AsyncClient(timeout=30.0) as client:
        while not to_visit.empty():
            current_url = _normalize_url(await to_visit.get())

            if current_url in visited:
                continue

            visited.add(current_url)
            logger.info(f"Processing URL: {current_url}")

            try:
                html_content = await _fetch_page(client, current_url)
                doc = _parse_page(html_content, current_url)
                documents.append(doc)

                # Find new links to follow
                soup = BeautifulSoup(html_content, "html.parser")
                for link_tag in soup.find_all("a", href=True):
                    href = link_tag["href"]
                    if href.startswith(("mailto:", "tel:", "javascript:")):
                        continue

                    absolute_url = urljoin(current_url, href)
                    normalized_url = _normalize_url(absolute_url)

                    # Only follow links within the FastAPI domain
                    if normalized_url.startswith(BASE_URL) and normalized_url not in visited:
                        await to_visit.put(normalized_url)

            except httpx.HTTPStatusError:
                logger.error(f"Skipping {current_url} due to HTTP error.")
            except httpx.RequestError:
                logger.error(f"Skipping {current_url} due to network error.")
            except Exception as e:
                logger.error(f"An unexpected error occurred while processing {current_url}: {e}")

    return documents

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    docs = asyncio.run(crawl_fastapi_docs())
    print(f"Crawled {len(docs)} documents.")
    # for doc in docs:
    #     print(f"URL: {doc['url']}\nTitle: {doc['title']}\nContent Snippet: {doc['content'][:200]}...\nCode Blocks: {len(doc['code_blocks'])}\n---")

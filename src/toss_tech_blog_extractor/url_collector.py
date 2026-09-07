"""토스 기술 블로그 목록에서 게시글 URL을 수집하는 서비스."""

import asyncio
import logging
import time
from datetime import datetime
from pathlib import Path
from typing import Any

import requests
from bs4 import BeautifulSoup

from .clients import DEFAULT_HEADERS, create_async_session
from .exporters import DATA_DIR
from .selectors import ARTICLE_LINK_SELECTOR, PAGINATION_SELECTOR

logger = logging.getLogger(__name__)


class TossUrlCollector:
    """목록 페이지를 순회해 토스 기술 블로그 게시글 URL을 수집한다."""

    base_url = "https://toss.tech/?page={}"
    posts_api_url = (
        "https://api-public.toss.im/api-public/v3/ipd-thor/api/v1/workspaces/15/posts"
    )
    api_page_size = 500

    def __init__(self):
        self.output_dir = DATA_DIR / "urls"
        self.session = requests.Session()
        self.session.headers.update(DEFAULT_HEADERS)
        self.all_urls: list[str] = []

    @staticmethod
    def normalize_article_url(href: str | None) -> str | None:
        if not href:
            return None
        href = href.strip()
        if href.startswith("/article/"):
            url = f"https://toss.tech{href}"
        elif href.startswith("https://toss.tech/article/"):
            url = href
        else:
            return None
        url = url.split("?", maxsplit=1)[0].split("#", maxsplit=1)[0]
        return (
            url
            if len(url) > len("https://toss.tech/article/") and "toss.im" not in url
            else None
        )

    @classmethod
    def extract_article_urls(cls, html: str) -> list[str]:
        soup = BeautifulSoup(html, "html.parser")
        return sorted(
            {
                url
                for link in soup.select(ARTICLE_LINK_SELECTOR)
                if (url := cls.normalize_article_url(link.get("href")))
            }
        )

    @classmethod
    def extract_article_urls_from_api(cls, payload: dict[str, Any]) -> list[str]:
        """공개 목록 API 응답에서 게시글 URL을 만든다."""
        success = payload.get("success")
        if not isinstance(success, dict):
            return []
        results = success.get("results")
        if not isinstance(results, list):
            return []

        urls = set()
        for post in results:
            if not isinstance(post, dict) or not post.get("isPublished", False):
                continue
            seo_config = post.get("seoConfig")
            slug = seo_config.get("urlSlug") if isinstance(seo_config, dict) else None
            slug = slug or post.get("key")
            if isinstance(slug, str):
                url = cls.normalize_article_url(f"/article/{slug}")
                if url:
                    urls.add(url)
        return sorted(urls)

    def find_last_page_from_pagination(self) -> int | None:
        logger.info("Finding last page from pagination")
        try:
            response = self.session.get(self.base_url.format(1), timeout=10)
            response.raise_for_status()
            page_numbers = [
                int(item.get_text(strip=True))
                for item in BeautifulSoup(response.text, "html.parser").select(
                    PAGINATION_SELECTOR
                )
                if item.get_text(strip=True).isdigit()
            ]
            return max(page_numbers) if page_numbers else None
        except requests.RequestException:
            logger.exception("Failed to determine the last page")
            return None

    async def extract_urls_from_page(
        self, session, page_num: int
    ) -> tuple[int, list[str] | None, int]:
        url = self.base_url.format(page_num)
        try:
            logger.info("Crawling page %s: %s", page_num, url)
            async with session.get(url) as response:
                if response.status != 200:
                    logger.warning(
                        "Page %s returned status code: %s", page_num, response.status
                    )
                    return page_num, None, response.status
                urls = self.extract_article_urls(await response.text())
                logger.info("Found %s unique URLs on page %s", len(urls), page_num)
                return page_num, urls, response.status
        except TimeoutError:
            logger.error("Timeout for page %s", page_num)
        except Exception:
            logger.exception("Error for page %s", page_num)
        return page_num, None, 0

    async def crawl_pages_parallel(
        self, max_page: int, max_concurrent: int = 15
    ) -> list[str]:
        start_time = time.time()
        async with create_async_session(
            max_connections=max_concurrent, timeout_seconds=30
        ) as session:
            results = await asyncio.gather(
                *(
                    self.extract_urls_from_page(session, page)
                    for page in range(1, max_page + 1)
                ),
                return_exceptions=True,
            )

        all_urls: set[str] = set()
        successful_pages = 0
        for result in results:
            if isinstance(result, tuple):
                _, urls, status_code = result
                if status_code == 200:
                    successful_pages += 1
                    all_urls.update(urls or [])
            elif isinstance(result, Exception):
                logger.error("Task exception: %s", result)

        self.all_urls = sorted(all_urls)
        logger.info(
            "Parallel crawling completed in %.2f seconds", time.time() - start_time
        )
        logger.info(
            "Successfully crawled %s out of %s pages", successful_pages, max_page
        )
        logger.info("Total unique URLs collected: %s", len(self.all_urls))
        return self.all_urls

    async def crawl_pages_until_empty(self, max_pages: int = 100) -> list[str]:
        """페이지네이션이 없는 목록 UI를 위한 HTML 기반 최후 폴백이다."""
        all_urls: set[str] = set()
        async with create_async_session(
            max_connections=5, timeout_seconds=30
        ) as session:
            for page in range(1, max_pages + 1):
                _, urls, status_code = await self.extract_urls_from_page(session, page)
                if status_code != 200 or not urls:
                    break
                all_urls.update(urls)

        self.all_urls = sorted(all_urls)
        logger.info("HTML fallback collected %s unique URLs", len(self.all_urls))
        return self.all_urls

    async def crawl_from_api(self) -> list[str] | None:
        """공개 목록 API를 사용해 모든 게시글 URL을 수집한다.

        API 요청이 실패했을 때만 HTML 목록 수집으로 폴백한다.
        """
        page = 1
        urls: set[str] = set()
        max_pages = 100

        async with create_async_session(
            max_connections=5, timeout_seconds=30
        ) as session:
            while page <= max_pages:
                try:
                    async with session.get(
                        self.posts_api_url,
                        params={"page": page, "size": self.api_page_size},
                    ) as response:
                        if response.status != 200:
                            logger.warning(
                                "Posts API returned HTTP %s", response.status
                            )
                            return None
                        payload = await response.json(content_type=None)
                except (TimeoutError, ValueError):
                    logger.exception("Failed to request posts API")
                    return None
                except Exception:
                    logger.exception("Unexpected posts API error")
                    return None

                if not isinstance(payload, dict) or not isinstance(
                    payload.get("success"), dict
                ):
                    logger.warning("Posts API response has an unexpected schema")
                    return None

                urls.update(self.extract_article_urls_from_api(payload))
                success = payload["success"]
                if not success.get("next"):
                    self.all_urls = sorted(urls)
                    logger.info(
                        "Posts API collected %s unique URLs", len(self.all_urls)
                    )
                    return self.all_urls

                page += 1

        logger.error("Posts API exceeded the maximum page count")
        return None

    async def crawl_all_pages(self) -> list[str]:
        api_urls = await self.crawl_from_api()
        if api_urls is not None:
            return api_urls

        logger.warning("Falling back to HTML list crawling")
        last_page = self.find_last_page_from_pagination()
        if last_page:
            return await self.crawl_pages_parallel(last_page)
        return await self.crawl_pages_until_empty()

    def save_all_urls(self, filename: str | None = None) -> Path:
        self.output_dir.mkdir(parents=True, exist_ok=True)
        filename = filename or f"toss_url_{datetime.now().astimezone():%m%d}.txt"
        file_path = self.output_dir / filename
        file_path.write_text(
            "\n".join(sorted(set(self.all_urls))) + "\n", encoding="utf-8"
        )
        logger.info("Saved %s unique URLs to %s", len(set(self.all_urls)), file_path)
        return file_path


async def run_url_collector() -> Path | None:
    collector = TossUrlCollector()
    urls = await collector.crawl_all_pages()
    if not urls:
        logger.error("No URLs were collected")
        return None
    return collector.save_all_urls()

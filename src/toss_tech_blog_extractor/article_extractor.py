"""게시글 URL에서 메타데이터와 본문을 추출하는 서비스."""

import argparse
import asyncio
import logging
import re
from datetime import datetime
from pathlib import Path

import aiohttp
from bs4 import BeautifulSoup
from markdownify import markdownify

from .clients import create_async_session
from .exporters import DATA_DIR, save_articles_json, save_articles_markdown
from .metrics import CrawlSummary
from .models import Article, ArticleContent
from .selectors import ARTICLE_SELECTORS, DATE_TEXT_PATTERN

logger = logging.getLogger(__name__)


class TossArticleExtractor:
    """비동기 HTTP 요청으로 토스 기술 블로그 게시글을 추출한다."""

    def __init__(self, max_concurrent: int = 10, timeout: int = 30, retries: int = 2):
        self.max_concurrent = max_concurrent
        self.timeout = timeout
        self.retries = retries
        self.selectors = ARTICLE_SELECTORS
        self.last_run_summary = CrawlSummary()

    async def fetch_url(
        self,
        session,
        url: str,
        summary: CrawlSummary | None = None,
    ) -> dict[str, object] | None:
        retry_statuses: list[object] = []
        for attempt in range(self.retries + 1):
            try:
                async with session.get(url) as response:
                    if response.status == 200:
                        article = self.parse_html(await response.text(), url)
                        if summary:
                            summary.record_request(
                                success=True, retry_statuses=retry_statuses
                            )
                        return article
                    if response.status not in {429, 500, 502, 503, 504}:
                        logger.warning("HTTP %s for %s", response.status, url)
                        if summary:
                            summary.record_request(
                                success=False, retry_statuses=retry_statuses
                            )
                        return None
                    logger.warning("Retryable HTTP %s for %s", response.status, url)
                    retry_reason: object = response.status
            except TimeoutError:
                logger.warning("Timeout for %s", url)
                retry_reason = "timeout"
            except aiohttp.ClientError as error:
                logger.warning("Request failed for %s: %s", url, error)
                retry_reason = "client_error"
            except Exception:
                logger.exception("Error fetching %s", url)
                retry_reason = "client_error"

            if attempt < self.retries:
                retry_statuses.append(retry_reason)
                await asyncio.sleep(2**attempt)
        if summary:
            summary.record_request(success=False, retry_statuses=retry_statuses)
        return None

    def clean_html_for_markdown(self, element):
        if not element:
            return None
        for tag in element.find_all(["script", "style", "noscript"]):
            tag.decompose()
        for tag in element.find_all():
            if not tag.get_text(strip=True) and not tag.find(["img", "br", "hr"]):
                tag.decompose()
        return element

    def html_to_markdown(self, html_content) -> str:
        try:
            soup = BeautifulSoup(str(html_content), "html.parser")
            cleaned_soup = self.clean_html_for_markdown(soup)
            if not cleaned_soup:
                return "내용 없음"
            markdown = markdownify(
                str(cleaned_soup),
                heading_style="ATX",
                bullets="-",
                wrap=False,
            )
            return self.clean_markdown(markdown)
        except Exception:
            logger.exception("Error converting HTML to markdown")
            return html_content.get_text(strip=True) if html_content else "변환 오류"

    @staticmethod
    def clean_markdown(markdown_text: str) -> str:
        markdown_text = re.sub(r"\n{3,}", "\n\n", markdown_text)
        markdown_text = re.sub(r"\\([*_`])", r"\1", markdown_text)
        return markdown_text.strip()

    def find_first_element(self, soup: BeautifulSoup, selector_name: str):
        """여러 선택자 중 현재 HTML에 맞는 첫 요소를 찾는다."""
        for selector in self.selectors[selector_name]:
            if element := soup.select_one(selector):
                return element
        return None

    def extract_title(self, soup: BeautifulSoup) -> str | None:
        if element := self.find_first_element(soup, "title"):
            return element.get_text(strip=True)
        if element := soup.select_one(
            'meta[property="og:title"], meta[name="twitter:title"]'
        ):
            return element.get("content")
        return None

    def extract_date(self, soup: BeautifulSoup) -> str | None:
        for selector in self.selectors["date"]:
            if (element := soup.select_one(selector)) and (
                matched := re.search(
                    DATE_TEXT_PATTERN, element.get_text(" ", strip=True)
                )
            ):
                return matched.group(0)

        if (header := soup.find("header")) and (
            matched := re.search(DATE_TEXT_PATTERN, header.get_text(" ", strip=True))
        ):
            return matched.group(0)

        for script in soup.find_all("script"):
            script_text = script.string or script.get_text()
            if matched := re.search(
                r"publishedTime.{0,20}?((?:19|20)\d{2})-(\d{2})-(\d{2})",
                script_text,
            ):
                year, month, day = matched.groups()
                return f"{year}년 {int(month)}월 {int(day)}일"
        return None

    def find_content_element(self, soup: BeautifulSoup):
        if element := self.find_first_element(soup, "content"):
            return element
        if header := soup.find("header"):
            return header.find_next_sibling()
        return None

    def parse_html(self, html: str, url: str) -> dict[str, object]:
        try:
            soup = BeautifulSoup(html, "html.parser")
            title = self.extract_title(soup)
            date = self.extract_date(soup)
            content_element = self.find_content_element(soup)

            if content_element:
                content = ArticleContent(
                    markdown=self.html_to_markdown(content_element),
                    text=content_element.get_text(strip=True),
                    html=str(content_element),
                )
            else:
                content = ArticleContent("내용 없음", "내용 없음", "내용 없음")

            missing_fields = []
            if not title:
                missing_fields.append("제목")
            if not date:
                missing_fields.append("날짜")
            if not content_element:
                missing_fields.append("본문")

            return Article(
                url=url,
                title=title or "제목 없음",
                date=date or "날짜 없음",
                content=content,
                crawled_at=datetime.now().astimezone().isoformat(),
                error=f"추출하지 못한 필드: {', '.join(missing_fields)}"
                if missing_fields
                else None,
            ).to_dict()
        except Exception as error:
            logger.exception("Error parsing HTML for %s", url)
            return Article(
                url=url,
                title="파싱 오류",
                date="파싱 오류",
                content=ArticleContent("파싱 오류", "파싱 오류", "파싱 오류"),
                crawled_at=datetime.now().astimezone().isoformat(),
                error=str(error),
            ).to_dict()

    async def crawl_batch(
        self,
        urls: list[str],
        summary: CrawlSummary | None = None,
    ) -> list[dict[str, object]]:
        owns_summary = summary is None
        summary = summary or CrawlSummary()
        self.last_run_summary = summary
        async with create_async_session(
            max_connections=self.max_concurrent,
            timeout_seconds=self.timeout,
        ) as session:
            semaphore = asyncio.Semaphore(self.max_concurrent)

            async def fetch_with_limit(url: str):
                async with semaphore:
                    return await self.fetch_url(session, url, summary)

            results = await asyncio.gather(
                *(fetch_with_limit(url) for url in urls), return_exceptions=True
            )

        valid_results: list[dict[str, object]] = []
        for result in results:
            if isinstance(result, dict):
                valid_results.append(result)
            elif isinstance(result, Exception):
                logger.error("Task exception: %s", result)
                summary.record_request(success=False)
        if owns_summary:
            summary.finish()
        return valid_results

    @staticmethod
    def load_urls_from_file(file_path: str | Path) -> list[str]:
        try:
            with Path(file_path).open("r", encoding="utf-8") as file:
                urls = [
                    line.strip()
                    for line in file
                    if line.strip() and not line.lstrip().startswith("#")
                ]
                return list(dict.fromkeys(urls))
        except OSError:
            logger.exception("Error loading URLs from %s", file_path)
            return []

    async def run(
        self,
        url_file_path: str | Path,
        output_file_path: str | Path,
        save_markdown: bool = False,
    ) -> list[dict[str, object]]:
        summary = CrawlSummary()
        self.last_run_summary = summary
        urls = self.load_urls_from_file(url_file_path)
        if not urls:
            logger.error("No URLs to crawl")
            summary.finish()
            print(summary.format_text())
            return []

        logger.info(
            "Starting crawl of %s URLs with %s concurrent connections",
            len(urls),
            self.max_concurrent,
        )
        results = await self.crawl_batch(urls, summary)
        saved_path = save_articles_json(results, output_file_path)
        logger.info("Results saved to %s", saved_path)

        if save_markdown:
            saved_files = save_articles_markdown(results, DATA_DIR / "mark_downs")
            logger.info("Saved %s Markdown files", len(saved_files))

        summary.finish()
        logger.info("Crawling completed in %.2f seconds", summary.elapsed_seconds)
        logger.info("Successfully crawled %s out of %s URLs", len(results), len(urls))
        print(summary.format_text())
        return results


def add_arguments(parser: argparse.ArgumentParser) -> None:
    """게시글 추출 명령에 필요한 인자를 등록한다."""
    parser.add_argument("--input", "-i", required=True, help="URL 목록 입력 파일")
    parser.add_argument("--output", "-o", help="출력 JSON 파일")
    parser.add_argument(
        "--concurrent", "-c", type=positive_int, default=10, help="최대 동시 연결 수"
    )
    parser.add_argument(
        "--timeout", "-t", type=positive_int, default=30, help="요청 제한 시간(초)"
    )
    parser.add_argument(
        "--markdown", "-m", action="store_true", help="게시글별 Markdown 파일 저장"
    )


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="토스 기술 블로그 게시글 추출기")
    add_arguments(parser)
    return parser


def positive_int(value: str) -> int:
    """CLI 입력을 1 이상의 정수로 검증한다."""
    parsed_value = int(value)
    if parsed_value < 1:
        raise argparse.ArgumentTypeError("1 이상의 정수를 입력해야 합니다")
    return parsed_value


def run_from_args(args: argparse.Namespace) -> None:
    """파싱된 인자로 게시글 추출을 실행한다."""
    output_file = args.output
    if not output_file:
        output_name = (
            f"toss_crawled_{Path(args.input).stem}_"
            f"{datetime.now().astimezone():%Y%m%d_%H%M%S}.json"
        )
        output_file = DATA_DIR / "jsons" / output_name

    extractor = TossArticleExtractor(
        max_concurrent=args.concurrent, timeout=args.timeout
    )
    asyncio.run(extractor.run(args.input, output_file, args.markdown))


def main(argv: list[str] | None = None) -> None:
    run_from_args(build_parser().parse_args(argv))

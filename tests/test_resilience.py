"""네트워크 오류와 CLI 입력 검증을 다루는 단위 테스트."""

import argparse
from collections import deque
from unittest import IsolatedAsyncioTestCase, TestCase
from unittest.mock import AsyncMock, patch

import aiohttp

from toss_tech_blog_extractor.article_extractor import (
    TossArticleExtractor,
    build_parser,
)


class FakeResponse:
    """aiohttp 응답 컨텍스트 매니저를 모방한다."""

    def __init__(self, status: int, html: str = ""):
        self.status = status
        self._html = html

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc, traceback):
        return None

    async def text(self) -> str:
        return self._html


class RaisingRequest:
    """진입 시 네트워크 예외를 발생시키는 요청 컨텍스트 매니저."""

    def __init__(self, error: Exception):
        self.error = error

    async def __aenter__(self):
        raise self.error

    async def __aexit__(self, exc_type, exc, traceback):
        return None


class FakeSession:
    def __init__(self, requests):
        self.requests = deque(requests)
        self.request_count = 0

    def get(self, url: str):
        self.request_count += 1
        return self.requests.popleft()


class FetchRetryTest(IsolatedAsyncioTestCase):
    async def test_retries_429_then_returns_parsed_article(self):
        session = FakeSession(
            [
                FakeResponse(429),
                FakeResponse(
                    200,
                    """
                    <h1 class="css-vf4rrt">제목</h1>
                    <div class="css-154r2lc">2026년 7월 22일</div>
                    <div class="css-1vn47db"><p>본문</p></div>
                    """,
                ),
            ]
        )
        extractor = TossArticleExtractor(retries=2)

        with patch(
            "toss_tech_blog_extractor.article_extractor.asyncio.sleep",
            new_callable=AsyncMock,
        ) as sleep:
            article = await extractor.fetch_url(
                session, "https://toss.tech/article/example"
            )

        self.assertEqual(session.request_count, 2)
        sleep.assert_awaited_once_with(1)
        self.assertEqual(article["title"], "제목")

    async def test_timeout_is_retried_then_returns_none(self):
        session = FakeSession([RaisingRequest(TimeoutError()) for _ in range(3)])
        extractor = TossArticleExtractor(retries=2)

        with patch(
            "toss_tech_blog_extractor.article_extractor.asyncio.sleep",
            new_callable=AsyncMock,
        ) as sleep:
            result = await extractor.fetch_url(
                session, "https://toss.tech/article/timeout"
            )

        self.assertIsNone(result)
        self.assertEqual(session.request_count, 3)
        self.assertEqual(sleep.await_count, 2)

    async def test_connection_error_is_retried_then_returns_none(self):
        session = FakeSession(
            [
                RaisingRequest(aiohttp.ClientConnectionError("연결 실패"))
                for _ in range(3)
            ]
        )
        extractor = TossArticleExtractor(retries=2)

        with patch(
            "toss_tech_blog_extractor.article_extractor.asyncio.sleep",
            new_callable=AsyncMock,
        ) as sleep:
            result = await extractor.fetch_url(
                session, "https://toss.tech/article/unavailable"
            )

        self.assertIsNone(result)
        self.assertEqual(session.request_count, 3)
        self.assertEqual(sleep.await_count, 2)


class ExtractorCliValidationTest(TestCase):
    def test_positive_values_are_accepted(self):
        args = build_parser().parse_args(
            ["--input", "urls.txt", "--concurrent", "3", "--timeout", "15"]
        )

        self.assertEqual(args.concurrent, 3)
        self.assertEqual(args.timeout, 15)

    def test_concurrent_must_be_positive_integer(self):
        parser: argparse.ArgumentParser = build_parser()
        for value in ("0", "-1"):
            with self.subTest(value=value), self.assertRaises(SystemExit):
                parser.parse_args(["--input", "urls.txt", "--concurrent", value])

    def test_timeout_must_be_positive_integer(self):
        parser: argparse.ArgumentParser = build_parser()
        for value in ("0", "-1"):
            with self.subTest(value=value), self.assertRaises(SystemExit):
                parser.parse_args(["--input", "urls.txt", "--timeout", value])

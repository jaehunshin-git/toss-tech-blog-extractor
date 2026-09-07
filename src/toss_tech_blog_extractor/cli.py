"""모든 작업을 한 명령으로 실행하기 위한 CLI."""

import argparse
import asyncio

from .article_extractor import add_arguments as add_extractor_arguments
from .article_extractor import run_from_args as run_extractor
from .url_checker import add_arguments as add_checker_arguments
from .url_checker import run_from_args as run_checker
from .url_collector import run_url_collector


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description="토스 기술 블로그 수집 도구")
    subparsers = parser.add_subparsers(dest="command", required=True)
    url_parser = subparsers.add_parser("url_crawler", help="게시글 URL 수집")
    url_parser.set_defaults(handler=lambda _: asyncio.run(run_url_collector()))
    extract_parser = subparsers.add_parser(
        "techblog_extractor", help="게시글 본문 추출"
    )
    add_extractor_arguments(extract_parser)
    extract_parser.set_defaults(handler=run_extractor)
    check_parser = subparsers.add_parser("check_urls", help="URL 상태 확인")
    add_checker_arguments(check_parser)
    check_parser.set_defaults(handler=run_checker)
    args = parser.parse_args(argv)
    args.handler(args)

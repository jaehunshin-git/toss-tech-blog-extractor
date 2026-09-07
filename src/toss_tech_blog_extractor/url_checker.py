"""수집한 URL의 HTTP 상태를 확인하는 서비스."""

import argparse
import asyncio
import time
from pathlib import Path

import aiohttp

from .clients import DEFAULT_HEADERS


async def check_url_status(
    session, url: str, semaphore: asyncio.Semaphore
) -> tuple[str, int | str]:
    """한 URL의 HTTP 상태 코드를 확인한다."""
    async with semaphore:
        try:
            timeout = aiohttp.ClientTimeout(total=5)
            async with session.get(
                url.strip(), headers=DEFAULT_HEADERS, timeout=timeout
            ) as response:
                return url, response.status
        except (TimeoutError, aiohttp.ClientError) as error:
            return url, f"Error: {error}"


async def check_all_urls(
    urls: list[str], max_concurrent: int = 25
) -> list[tuple[str, int | str]]:
    """여러 URL의 상태를 제한된 동시성으로 확인한다."""
    semaphore = asyncio.Semaphore(max_concurrent)
    async with aiohttp.ClientSession() as session:
        return await asyncio.gather(
            *(
                check_url_status(session, url.strip(), semaphore)
                for url in urls
                if url.strip()
            )
        )


def add_arguments(parser: argparse.ArgumentParser) -> None:
    """URL 확인 명령에 필요한 인자를 등록한다."""
    parser.add_argument("file_path", help="URL 목록 파일 경로")


def run_from_args(args: argparse.Namespace) -> None:
    """파싱된 인자로 URL 상태 검사를 실행한다."""

    try:
        with Path(args.file_path).open(encoding="utf-8") as file:
            urls = [url.strip() for url in file if url.strip()]
    except FileNotFoundError:
        print(f"파일을 찾을 수 없습니다: {args.file_path}")
        return
    except OSError as error:
        print(f"파일을 읽을 수 없습니다: {error}")
        return

    print(f"총 {len(urls)}개의 URL을 확인합니다...\n")
    started_at = time.time()
    results = asyncio.run(check_all_urls(urls))
    success_count = 0

    for index, (url, status) in enumerate(results, 1):
        is_success = status == 200
        success_count += is_success
        mark = "✅ OK" if is_success else "❌ FAIL"
        print(f"[{index}/{len(results)}] {url}\n{mark} ({status})\n")

    error_count = len(results) - success_count
    rate = (success_count / len(results) * 100) if results else 0
    print("=" * 50)
    print("검사 완료!")
    print(f"실행 시간: {time.time() - started_at:.2f}초")
    print(f"성공: {success_count}개")
    print(f"실패: {error_count}개")
    print(f"성공률: {rate:.1f}%")


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(
        description="파일에 있는 URL의 HTTP 상태를 확인합니다."
    )
    add_arguments(parser)
    run_from_args(parser.parse_args(argv))

"""호환성 모듈: 새 구현은 :mod:`url_collector`에 있다."""

import argparse
import asyncio

from .url_collector import TossUrlCollector, run_url_collector

# 기존 외부 코드에서 사용하던 클래스 이름을 유지한다.
TossUrlCrawler = TossUrlCollector


def main(argv: list[str] | None = None) -> None:
    """URL 수집 CLI 진입점."""
    parser = argparse.ArgumentParser(
        description="토스 기술 블로그 게시글 URL을 수집합니다."
    )
    parser.parse_args(argv)
    asyncio.run(run_url_collector())


__all__ = ["TossUrlCrawler", "main", "run_url_collector"]


if __name__ == "__main__":
    main()

"""크롤러가 공유하는 HTTP 클라이언트 설정."""

import aiohttp


DEFAULT_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
    )
}


def create_async_session(*, max_connections: int, timeout_seconds: int) -> aiohttp.ClientSession:
    """동시 연결 수와 시간 제한이 적용된 aiohttp 세션을 만든다."""
    connector = aiohttp.TCPConnector(limit=max_connections, limit_per_host=5)
    timeout = aiohttp.ClientTimeout(total=timeout_seconds)
    return aiohttp.ClientSession(
        connector=connector,
        timeout=timeout,
        headers=DEFAULT_HEADERS,
    )

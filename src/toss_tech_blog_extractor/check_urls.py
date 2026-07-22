"""호환성 모듈: 새 구현은 :mod:`url_checker`에 있다."""

from .url_checker import check_all_urls, check_url_status, main

__all__ = ["check_all_urls", "check_url_status", "main"]


if __name__ == "__main__":
    main()

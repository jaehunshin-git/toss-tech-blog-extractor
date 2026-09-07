"""호환성 모듈: 새 구현은 :mod:`article_extractor`에 있다."""

from .article_extractor import TossArticleExtractor, main

# 기존 외부 코드에서 사용하던 클래스 이름을 유지한다.
TossCrawler = TossArticleExtractor

__all__ = ["TossArticleExtractor", "TossCrawler", "main"]


if __name__ == "__main__":
    main()

"""크롤링 결과를 표현하는 데이터 모델."""

from dataclasses import asdict, dataclass


@dataclass(frozen=True)
class ArticleContent:
    """원문에서 추출한 본문 표현들."""

    markdown: str
    text: str
    html: str


@dataclass(frozen=True)
class Article:
    """토스 기술 블로그 게시글 한 건."""

    url: str
    title: str
    date: str
    content: ArticleContent
    crawled_at: str
    error: str | None = None

    def to_dict(self) -> dict[str, object]:
        """JSON 직렬화에 사용할 사전으로 변환한다."""
        article = asdict(self)
        return {key: value for key, value in article.items() if value is not None}

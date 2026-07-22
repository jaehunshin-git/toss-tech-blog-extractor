"""토스 기술 블로그 HTML 선택자.

웹사이트 구조가 변경되면 이 파일의 선택자와 폴백 전략을 우선 갱신한다.
"""

ARTICLE_SELECTORS = {
    # 의미 있는 HTML 태그를 먼저 사용하고, 과거 페이지와의 호환을 위해 CSS 선택자를 보조로 둔다.
    "title": ("h1", 'h1[class*="css-vf4rrt"]'),
    "date": ("time", 'div[class*="css-154r2lc"]'),
    "content": ('div[class*="css-1vn47db"]',),
}

ARTICLE_LINK_SELECTOR = 'a[href*="/article/"]'
PAGINATION_SELECTOR = 'span.p-pagination__item-content-wrapper'
DATE_TEXT_PATTERN = r"(?:19|20)\d{2}년\s*\d{1,2}월\s*\d{1,2}일"

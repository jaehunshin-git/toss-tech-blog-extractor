"""외부 네트워크 없이 실행하는 핵심 서비스 단위 테스트."""

import unittest

from toss_tech_blog_extractor.article_extractor import TossArticleExtractor
from toss_tech_blog_extractor.toss_techblog_extractor import TossCrawler
from toss_tech_blog_extractor.toss_url_crawler import TossUrlCrawler
from toss_tech_blog_extractor.url_collector import TossUrlCollector


class UrlCollectorTest(unittest.TestCase):
    def test_article_url_normalization(self):
        self.assertEqual(
            TossUrlCollector.normalize_article_url("/article/example?source=home#section"),
            "https://toss.tech/article/example",
        )
        self.assertIsNone(TossUrlCollector.normalize_article_url("https://toss.im/article/example"))

    def test_article_urls_are_deduplicated(self):
        html = """
        <a href="/article/first">첫 번째</a>
        <a href="/article/first?source=home">첫 번째</a>
        <a href="/article/second">두 번째</a>
        """
        self.assertEqual(
            TossUrlCollector.extract_article_urls(html),
            ["https://toss.tech/article/first", "https://toss.tech/article/second"],
        )

    def test_article_urls_are_extracted_from_api_response(self):
        payload = {
            "success": {
                "results": [
                    {"isPublished": True, "key": "fallback-key", "seoConfig": {"urlSlug": "first"}},
                    {"isPublished": True, "key": "second", "seoConfig": None},
                    {"isPublished": False, "key": "draft", "seoConfig": {"urlSlug": "draft"}},
                ]
            }
        }
        self.assertEqual(
            TossUrlCollector.extract_article_urls_from_api(payload),
            ["https://toss.tech/article/first", "https://toss.tech/article/second"],
        )


class ArticleExtractorTest(unittest.TestCase):
    def test_html_is_converted_to_article(self):
        html = """
        <h1 class="css-vf4rrt">제목</h1>
        <div class="css-154r2lc">2026년 7월 22일</div>
        <div class="css-1vn47db"><p>본문</p></div>
        """
        article = TossArticleExtractor().parse_html(html, "https://toss.tech/article/example")

        self.assertEqual(article["title"], "제목")
        self.assertEqual(article["date"], "2026년 7월 22일")
        self.assertEqual(article["content"]["markdown"], "본문")

    def test_legacy_import_names_remain_available(self):
        self.assertIs(TossCrawler, TossArticleExtractor)
        self.assertIs(TossUrlCrawler, TossUrlCollector)

    def test_current_html_structure_uses_semantic_fallbacks(self):
        html = """
        <meta property="og:title" content="메타 제목" />
        <header><h1 class="new-generated-class">현재 제목</h1><div>2026년 5월 22일</div></header>
        <div class="new-content-wrapper"><p>현재 본문</p></div>
        """
        article = TossArticleExtractor().parse_html(html, "https://toss.tech/article/current")

        self.assertEqual(article["title"], "현재 제목")
        self.assertEqual(article["date"], "2026년 5월 22일")
        self.assertEqual(article["content"]["markdown"], "현재 본문")
        self.assertNotIn("error", article)

import asyncio
import aiohttp
import json
import argparse
from pathlib import Path
from bs4 import BeautifulSoup
from datetime import datetime
import time
import logging
import html2text
import re

# 로깅 설정
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class TossCrawler:
    def __init__(self, max_concurrent=10, timeout=30):
        self.max_concurrent = max_concurrent
        self.timeout = aiohttp.ClientTimeout(total=timeout)
        self.selectors = {
            'title': 'h1[class*="css-vf4rrt"]',
            'date': 'div[class*="css-154r2lc"]',
            'content': 'div[class*="css-1vn47db"]'
        }
        self.results = []
        
        # HTML to Markdown 변환기 설정
        self.h2t = html2text.HTML2Text()
        self.h2t.ignore_links = False
        self.h2t.ignore_images = False
        self.h2t.ignore_emphasis = False
        self.h2t.body_width = 0  # 줄바꿈 제한 없음
        self.h2t.unicode_snob = True
        self.h2t.escape_snob = True
        
    async def fetch_url(self, session, url):
        """단일 URL을 크롤링"""
        try:
            async with session.get(url) as response:
                if response.status == 200:
                    html = await response.text()
                    return self.parse_html(html, url)
                else:
                    logger.warning(f"HTTP {response.status} for {url}")
                    return None
        except asyncio.TimeoutError:
            logger.error(f"Timeout for {url}")
            return None
        except Exception as e:
            logger.error(f"Error fetching {url}: {str(e)}")
            return None
    
    def clean_html_for_markdown(self, element):
        """HTML 요소를 마크다운 변환에 적합하게 정리"""
        if not element:
            return None
            
        # 불필요한 태그들 제거
        for tag in element.find_all(['script', 'style', 'noscript']):
            tag.decompose()
        
        # 빈 태그들 제거
        for tag in element.find_all():
            if not tag.get_text(strip=True) and not tag.find(['img', 'br', 'hr']):
                tag.decompose()
        
        return element
    
    def html_to_markdown(self, html_content):
        """HTML을 마크다운으로 변환"""
        try:
            # BeautifulSoup으로 HTML 정리
            soup = BeautifulSoup(str(html_content), 'html.parser')
            cleaned_soup = self.clean_html_for_markdown(soup)
            
            if not cleaned_soup:
                return "내용 없음"
            
            # HTML을 마크다운으로 변환
            markdown_content = self.h2t.handle(str(cleaned_soup))
            
            # 마크다운 정리
            markdown_content = self.clean_markdown(markdown_content)
            
            return markdown_content
        except Exception as e:
            logger.error(f"Error converting HTML to markdown: {str(e)}")
            return html_content.get_text(strip=True) if html_content else "변환 오류"
    
    def clean_markdown(self, markdown_text):
        """마크다운 텍스트 정리"""
        # 연속된 빈 줄 제거 (3개 이상의 연속 줄바꿈을 2개로)
        markdown_text = re.sub(r'\n{3,}', '\n\n', markdown_text)
        
        # 앞뒤 공백 제거
        markdown_text = markdown_text.strip()
        
        # 불필요한 백슬래시 제거
        markdown_text = re.sub(r'\\([*_`])', r'\1', markdown_text)
        
        return markdown_text
    
    def parse_html(self, html, url):
        """HTML을 파싱하여 데이터 추출"""
        try:
            soup = BeautifulSoup(html, 'html.parser')
            
            # 제목 추출 (텍스트만)
            title_element = soup.select_one(self.selectors['title'])
            title = title_element.get_text(strip=True) if title_element else "제목 없음"
            
            # 날짜 추출 (텍스트만)
            date_element = soup.select_one(self.selectors['date'])
            date = date_element.get_text(strip=True) if date_element else "날짜 없음"
            
            # 내용 추출 (마크다운으로 변환)
            content_element = soup.select_one(self.selectors['content'])
            
            if content_element:
                # HTML 형태로 저장
                content_html = str(content_element)
                # 마크다운으로 변환
                content_markdown = self.html_to_markdown(content_element)
                # 순수 텍스트도 저장
                content_text = content_element.get_text(strip=True)
            else:
                content_html = "내용 없음"
                content_markdown = "내용 없음"
                content_text = "내용 없음"
            
            return {
                "url": url,
                "title": title,
                "date": date,
                "content": {
                    "markdown": content_markdown,
                    "text": content_text,
                    "html": content_html
                },
                "crawled_at": datetime.now().isoformat()
            }
        except Exception as e:
            logger.error(f"Error parsing HTML for {url}: {str(e)}")
            return {
                "url": url,
                "title": "파싱 오류",
                "date": "파싱 오류",
                "content": {
                    "markdown": "파싱 오류",
                    "text": "파싱 오류",
                    "html": "파싱 오류"
                },
                "crawled_at": datetime.now().isoformat(),
                "error": str(e)
            }
    
    async def crawl_batch(self, urls):
        """URL 배치를 병렬로 크롤링"""
        connector = aiohttp.TCPConnector(limit=self.max_concurrent, limit_per_host=5)
        async with aiohttp.ClientSession(
            connector=connector, 
            timeout=self.timeout,
            headers={'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}
        ) as session:
            
            semaphore = asyncio.Semaphore(self.max_concurrent)
            
            async def fetch_with_semaphore(url):
                async with semaphore:
                    return await self.fetch_url(session, url)
            
            tasks = [fetch_with_semaphore(url) for url in urls]
            results = await asyncio.gather(*tasks, return_exceptions=True)
            
            # 성공한 결과만 필터링
            valid_results = []
            for result in results:
                if isinstance(result, dict) and result is not None:
                    valid_results.append(result)
                elif isinstance(result, Exception):
                    logger.error(f"Task exception: {str(result)}")
            
            return valid_results
    
    def load_urls_from_file(self, file_path):
        """텍스트 파일에서 URL 목록 로드"""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                urls = [line.strip() for line in f if line.strip() and not line.startswith('#')]
            logger.info(f"Loaded {len(urls)} URLs from {file_path}")
            return urls
        except Exception as e:
            logger.error(f"Error loading URLs from {file_path}: {str(e)}")
            return []
    
    def save_results_to_json(self, results, output_file):
        """결과를 JSON 파일로 저장"""
        try:
            with open(output_file, 'w', encoding='utf-8') as f:
                json.dump(results, f, ensure_ascii=False, indent=2)
            logger.info(f"Results saved to {output_file}")
        except Exception as e:
            logger.error(f"Error saving results to {output_file}: {str(e)}")
    
    def save_markdown_files(self, results, output_dir):
        """각 article을 개별 마크다운 파일로 저장"""
        try:
            output_path = Path(output_dir)
            output_path.mkdir(exist_ok=True)
            
            for i, result in enumerate(results):
                if result and 'content' in result and 'markdown' in result['content']:
                    # 안전한 파일명 생성
                    title = result.get('title', f'article_{i}')
                    safe_title = re.sub(r'[<>:"/\\|?*]', '_', title)[:50]
                    filename = f"{i:03d}_{safe_title}.md"
                    
                    filepath = output_path / filename
                    
                    with open(filepath, 'w', encoding='utf-8') as f:
                        f.write(f"# {result.get('title', '제목 없음')}\n\n")
                        f.write(f"**Date:** {result.get('date', '날짜 없음')}\n")
                        f.write(f"**URL:** {result.get('url', '')}\n\n")
                        f.write("---\n\n")
                        f.write(result['content']['markdown'])
            
            logger.info(f"Markdown files saved to {output_dir}")
        except Exception as e:
            logger.error(f"Error saving markdown files: {str(e)}")
    
    async def run_crawler(self, url_file_path, output_file_path, save_markdown=False):
        """전체 크롤링 프로세스 실행"""
        start_time = time.time()
        
        # URL 로드
        urls = self.load_urls_from_file(url_file_path)
        if not urls:
            logger.error("No URLs to crawl")
            return
        
        logger.info(f"Starting crawl of {len(urls)} URLs with {self.max_concurrent} concurrent connections")
        
        # 크롤링 실행
        results = await self.crawl_batch(urls)
        
        # 결과 저장
        self.save_results_to_json(results, output_file_path)
        
        # 마크다운 파일 저장 (옵션)
        if save_markdown:
            markdown_dir = Path(__file__).parent.parent.parent / "data" / "mark_downs"
            self.save_markdown_files(results, markdown_dir)
        
        end_time = time.time()
        logger.info(f"Crawling completed in {end_time - start_time:.2f} seconds")
        logger.info(f"Successfully crawled {len(results)} out of {len(urls)} URLs")

def main(argv=None):
    parser = argparse.ArgumentParser(description='Toss Tech Blog Crawler')
    parser.add_argument('--input', '-i', required=True, help='Input file path containing URLs')
    parser.add_argument('--output', '-o', help='Output JSON file path')
    parser.add_argument('--concurrent', '-c', type=int, default=10, help='Max concurrent connections')
    parser.add_argument('--timeout', '-t', type=int, default=30, help='Request timeout in seconds')
    parser.add_argument('--markdown', '-m', action='store_true', help='Save individual markdown files')
    
    args = parser.parse_args(argv)
    
    # 출력 파일명 자동 생성
    if not args.output:
        input_path = Path(args.input)
        output_filename = f"toss_crawled_{input_path.stem}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        args.output = Path(__file__).parent.parent.parent / "data" / "jsons" / output_filename
    
    # 크롤러 인스턴스 생성 및 실행
    crawler = TossCrawler(max_concurrent=args.concurrent, timeout=args.timeout)
    asyncio.run(crawler.run_crawler(args.input, args.output, args.markdown))

if __name__ == "__main__":
    main(sys.argv[1:])

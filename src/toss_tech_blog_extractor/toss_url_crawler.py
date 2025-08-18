import os
import requests
from bs4 import BeautifulSoup
import time
from datetime import datetime
import logging
import asyncio
import aiohttp

# 로깅 설정
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class TossUrlCrawler:
    def __init__(self):
        self.base_url = 'https://toss.tech/?page={}'
        self.output_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..', 'data', 'urls')
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        })
        self.all_urls = []
        
    def extract_urls_from_page(self, page_num):
        """특정 페이지에서 article URL들을 추출"""
        url = self.base_url.format(page_num)
        try:
            logger.info(f"Crawling page {page_num}: {url}")
            response = self.session.get(url, timeout=10, allow_redirects=True)
            
            # 리다이렉트 체크 - error 페이지로 리다이렉트되면 404 처리
            if '/error' in response.url or response.url.endswith('/error'):
                logger.info(f"Page {page_num} redirected to error page: {response.url}")
                return None, 404
            
            if response.status_code != 200:
                logger.warning(f"Page {page_num} returned status code: {response.status_code}")
                return None, response.status_code
            
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # 정확한 셀렉터 사용 - toss.tech 페이지 구조에 맞춘 셀렉터
            selectors = [
                '#__next > div > div.p-container.p-container--default.css-2ndca > div > div.css-12xilxn > div > div.css-pjg5ks > div.css-8frca.e143n5sn3 > div:nth-child(2) > div > div > li > a',
                'a[href*="/article/"]',  # 백업 셀렉터
            ]
            
            urls = set()  # 중복 제거를 위해 set 사용
            
            for selector in selectors:
                links = soup.select(selector)
                for link in links:
                    href = link.get('href')
                    if not href:
                        continue
                    
                    # href를 문자열로 변환
                    href = str(href).strip()
                    
                    # 상대 URL을 절대 URL로 변환
                    if href.startswith('/article/'):
                        full_url = f"https://toss.tech{href}"
                    elif href.startswith('https://toss.tech/article/'):
                        full_url = href
                    else:
                        continue
                    
                    # URL 정리 (쿼리 파라미터, 앵커 제거)
                    if '?' in full_url:
                        full_url = full_url.split('?')[0]
                    if '#' in full_url:
                        full_url = full_url.split('#')[0]
                    
                    # toss.tech article URL만 추가 (toss.im 제외)
                    if (full_url.startswith('https://toss.tech/article/') and 
                        'toss.im' not in full_url and 
                        len(full_url) > len('https://toss.tech/article/')):
                        urls.add(full_url)
            
            logger.info(f"Found {len(urls)} unique URLs on page {page_num}")
            return list(urls), 200
            
        except requests.exceptions.RequestException as e:
            logger.error(f"Request error for page {page_num}: {str(e)}")
            return None, 0
        except Exception as e:
            logger.error(f"Unexpected error for page {page_num}: {str(e)}")
            return None, 0
    
    def find_last_page_from_pagination(self):
        """첫 페이지의 페이지네이션에서 마지막 페이지 번호를 찾기"""
        logger.info("Finding last page from pagination...")
        
        url = self.base_url.format(1)  # 첫 페이지 접근
        try:
            response = self.session.get(url, timeout=10)
            
            if response.status_code != 200:
                logger.error(f"Failed to access first page: {response.status_code}")
                return None
            
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # 페이지네이션에서 숫자들 찾기
            pagination_items = soup.select('span.p-pagination__item-content-wrapper')
            
            if not pagination_items:
                logger.warning("No pagination found, assuming single page")
                return 1
            
            # 숫자인 텍스트들만 추출하여 최대값 찾기
            page_numbers = []
            for item in pagination_items:
                text = item.get_text(strip=True)
                if text.isdigit():
                    page_numbers.append(int(text))
            
            if page_numbers:
                max_page = max(page_numbers)
                logger.info(f"Found maximum page number from pagination: {max_page}")
                return max_page
            else:
                logger.warning("No numeric pagination items found")
                return 1
                
        except Exception as e:
            logger.error(f"Error finding last page from pagination: {str(e)}")
            return None

    async def extract_urls_from_page_async(self, session, page_num):
        """비동기로 특정 페이지에서 article URL들을 추출"""
        url = self.base_url.format(page_num)
        try:
            logger.info(f"Crawling page {page_num}: {url}")
            async with session.get(url) as response:
                if response.status != 200:
                    logger.warning(f"Page {page_num} returned status code: {response.status}")
                    return page_num, None, response.status
                
                html = await response.text()
                soup = BeautifulSoup(html, 'html.parser')
                
                # 정확한 셀렉터 사용 - toss.tech 페이지 구조에 맞춘 셀렉터
                selectors = [
                    '#__next > div > div.p-container.p-container--default.css-2ndca > div > div.css-12xilxn > div > div.css-pjg5ks > div.css-8frca.e143n5sn3 > div:nth-child(2) > div > div > li > a',
                    'a[href*="/article/"]',  # 백업 셀렉터
                ]
                
                urls = set()  # 중복 제거를 위해 set 사용
                
                for selector in selectors:
                    links = soup.select(selector)
                    logger.debug(f"Page {page_num}: Found {len(links)} links with selector '{selector}'")
                    
                    for link in links:
                        href = link.get('href')
                        if not href:
                            continue
                        
                        # href를 문자열로 변환
                        href = str(href).strip()
                        
                        # 상대 URL을 절대 URL로 변환
                        if href.startswith('/article/'):
                            full_url = f"https://toss.tech{href}"
                        elif href.startswith('https://toss.tech/article/'):
                            full_url = href
                        else:
                            continue
                        
                        # URL 정리 (쿼리 파라미터, 앵커 제거)
                        if '?' in full_url:
                            full_url = full_url.split('?')[0]
                        if '#' in full_url:
                            full_url = full_url.split('#')[0]
                        
                        # toss.tech article URL만 추가 (toss.im 제외)
                        if (full_url.startswith('https://toss.tech/article/') and 
                            'toss.im' not in full_url and 
                            len(full_url) > len('https://toss.tech/article/')):
                            urls.add(full_url)
                
                # 페이지에 article 링크가 없으면 경고만 출력 (에러로 처리하지 않음)
                if len(urls) == 0:
                    logger.warning(f"No article URLs found on page {page_num}")
                    return page_num, [], 200  # 빈 배열이지만 성공으로 처리
                
                logger.info(f"Found {len(urls)} unique URLs on page {page_num}")
                return page_num, list(urls), 200
                
        except asyncio.TimeoutError:
            logger.error(f"Timeout for page {page_num}")
            return page_num, None, 0
        except Exception as e:
            logger.error(f"Error for page {page_num}: {str(e)}")
            return page_num, None, 0

    async def crawl_pages_parallel(self, max_page, max_concurrent=10):
        """모든 페이지를 병렬로 크롤링"""
        logger.info(f"Starting parallel crawling of pages 1 to {max_page}")
        start_time = time.time()
        
        connector = aiohttp.TCPConnector(limit=max_concurrent, limit_per_host=5)
        timeout = aiohttp.ClientTimeout(total=30)
        
        async with aiohttp.ClientSession(
            connector=connector,
            timeout=timeout,
            headers={'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}
        ) as session:
            
            # 모든 페이지에 대한 태스크 생성
            tasks = []
            for page in range(1, max_page + 1):
                task = self.extract_urls_from_page_async(session, page)
                tasks.append(task)
            
            # 병렬 실행
            results = await asyncio.gather(*tasks, return_exceptions=True)
            
            # 결과 처리
            all_urls = []
            successful_pages = 0
            
            for result in results:
                if isinstance(result, tuple) and len(result) == 3:
                    page_num, urls, status_code = result
                    if status_code == 200 and urls:
                        all_urls.extend(urls)
                        # 개별 페이지 파일 저장 제거
                        successful_pages += 1
                elif isinstance(result, Exception):
                    logger.error(f"Task exception: {str(result)}")
        
        end_time = time.time()
        unique_urls = list(set(all_urls))
        
        logger.info(f"Parallel crawling completed in {end_time - start_time:.2f} seconds")
        logger.info(f"Successfully crawled {successful_pages} out of {max_page} pages")
        logger.info(f"Total unique URLs collected: {len(unique_urls)}")
        
        self.all_urls = unique_urls
        return unique_urls

    async def crawl_all_pages_smart(self, delay=1):
        """스마트하게 모든 페이지 크롤링 - 페이지네이션에서 최대 페이지를 찾고 병렬 크롤링"""
        logger.info("Starting smart parallel URL crawling...")
        
        # 페이지네이션에서 마지막 페이지 찾기
        last_page = self.find_last_page_from_pagination()
        
        if not last_page or last_page == 0:
            logger.error("Could not determine last page number")
            return []
        
        logger.info(f"Will crawl pages 1 to {last_page} in parallel")
        
        # 병렬 크롤링 실행
        urls = await self.crawl_pages_parallel(last_page, max_concurrent=15)
        
        return urls

    def crawl_all_pages(self, start_page=1, max_pages=100, delay=1):
        """모든 페이지를 크롤링하여 URL 수집"""
        logger.info(f"Starting URL crawling from page {start_page}")
        
        page = start_page
        consecutive_failures = 0
        max_consecutive_failures = 3
        
        while page <= max_pages and consecutive_failures < max_consecutive_failures:
            urls, status_code = self.extract_urls_from_page(page)
            
            if status_code == 200 and urls:
                self.all_urls.extend(urls)
                consecutive_failures = 0
                
                # 개별 페이지 결과 저장 제거
                
            elif status_code == 404:
                logger.info(f"Page {page} returned 404 - likely reached end of pages")
                break
            elif status_code != 200:
                consecutive_failures += 1
                logger.warning(f"Page {page} failed (attempt {consecutive_failures}/{max_consecutive_failures})")
                if consecutive_failures >= max_consecutive_failures:
                    logger.error(f"Too many consecutive failures, stopping at page {page}")
                    break
            else:
                # 200이지만 URL이 없는 경우
                logger.warning(f"Page {page} returned no URLs")
                consecutive_failures += 1
            
            page += 1
            
            # 요청 간격 조절
            if delay > 0:
                time.sleep(delay)
        
        logger.info(f"Crawling completed. Total pages crawled: {page - start_page}")
        logger.info(f"Total unique URLs collected: {len(set(self.all_urls))}")
        
        return list(set(self.all_urls))  # 중복 제거 후 반환
    
    def save_page_urls(self, page_num, urls):
        """개별 페이지의 URL들을 파일로 저장"""
        if not urls or len(urls) == 0:
            logger.info(f"Page {page_num}: No URLs to save")
            return
            
        filename = os.path.join(self.output_dir, f"page_{page_num:02d}.txt")
        try:
            with open(filename, 'w', encoding='utf-8') as f:
                for url in sorted(urls):  # 정렬하여 저장
                    f.write(f"{url}\n")
            logger.debug(f"Saved {len(urls)} URLs to {filename}")
        except Exception as e:
            logger.error(f"Error saving page {page_num} URLs: {str(e)}")
    
    def save_all_urls(self, filename=None):
        """모든 URL을 하나의 파일로 저장"""
        if not filename:
            timestamp = datetime.now().strftime('%m%d')
            filename = f"toss_url_{timestamp}.txt"
        
        filepath = os.path.join(self.output_dir, filename)
        
        # 중복 제거 및 정렬
        unique_urls = list(set(self.all_urls))
        unique_urls.sort()
        
        try:
            with open(filepath, 'w', encoding='utf-8') as f:
                for url in unique_urls:
                    f.write(f"{url}\n")
            
            logger.info(f"Saved {len(unique_urls)} unique URLs to {filepath}")
            return filepath
        except Exception as e:
            logger.error(f"Error saving all URLs: {str(e)}")
            return None
    
    def save_urls_reverse_chronological(self, filename=None):
        """URL을 역순(최신순)으로 저장"""
        if not filename:
            timestamp = datetime.now().strftime('%m%d')
            filename = f"toss_url_reverse_{timestamp}.txt"
        
        filepath = os.path.join(self.output_dir, filename)
        
        # 중복 제거 후 역순 정렬
        unique_urls = list(set(self.all_urls))
        unique_urls.sort(reverse=True)
        
        try:
            with open(filepath, 'w', encoding='utf-8') as f:
                for url in unique_urls:
                    f.write(f"{url}\n")
            
            logger.info(f"Saved {len(unique_urls)} URLs in reverse order to {filepath}")
            return filepath
        except Exception as e:
            logger.error(f"Error saving reverse URLs: {str(e)}")
            return None
    
    def validate_and_clean_urls(self):
        """수집된 URL들을 검증하고 정리"""
        if not self.all_urls:
            return []
        
        # 중복 제거
        unique_urls = list(set(self.all_urls))
        
        # toss.im URL 제거
        cleaned_urls = []
        toss_im_count = 0
        
        for url in unique_urls:
            if 'toss.im' in url:
                toss_im_count += 1
                logger.debug(f"Filtered out toss.im URL: {url}")
            elif url.startswith('https://toss.tech/article/'):
                cleaned_urls.append(url)
            else:
                logger.debug(f"Filtered out invalid URL: {url}")
        
        if toss_im_count > 0:
            logger.info(f"Filtered out {toss_im_count} toss.im URLs")
        
        logger.info(f"URL validation: {len(unique_urls)} → {len(cleaned_urls)} after filtering")
        
        self.all_urls = cleaned_urls
        return cleaned_urls

    def cleanup_temp_files(self):
        """임시 페이지 파일들 삭제"""
        try:
            for filename in os.listdir(self.output_dir):
                if filename.startswith('page_') and filename.endswith('.txt'):
                    filepath = os.path.join(self.output_dir, filename)
                    os.remove(filepath)
                    logger.debug(f"Removed temporary file: {filename}")
        except Exception as e:
            logger.error(f"Error cleaning up temp files: {str(e)}")

async def main():
    """메인 실행 함수"""
    async def run_crawler():
        crawler = TossUrlCrawler()
        
        try:
            # 스마트 병렬 URL 크롤링 실행
            logger.info("Starting smart parallel Toss URL crawling...")
            
            urls = await crawler.crawl_all_pages_smart(delay=1)
            
            if urls:
                # URL 검증 및 정리
                cleaned_urls = crawler.validate_and_clean_urls()
                
                # 결과 저장 (하나의 파일만)
                normal_file = crawler.save_all_urls()
                
                # 통계 출력
                logger.info(f"File created:")
                if normal_file:
                    logger.info(f"  - URLs saved to: {normal_file}")
                
                # 임시 파일 정리 (개별 페이지 파일들 삭제)
                crawler.cleanup_temp_files()
                
            else:
                logger.error("No URLs were collected")
                
        except KeyboardInterrupt:
            logger.info("Crawling interrupted by user")
        except Exception as e:
            logger.error(f"Unexpected error: {str(e)}")
    
    # asyncio 실행
    asyncio.run(main())

if __name__ == "__main__":
    main()

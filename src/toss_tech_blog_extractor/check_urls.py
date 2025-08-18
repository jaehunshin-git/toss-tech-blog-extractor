import asyncio
import aiohttp
import time
from urllib.parse import urlparse
import argparse

async def check_url_status(session, url, semaphore):
    """URL의 HTTP 상태 코드를 비동기로 확인하는 함수"""
    async with semaphore:  # 동시 연결 수 제한
        try:
            # User-Agent 헤더를 추가하여 일부 사이트의 차단을 방지
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
            }
            
            # 5초 타임아웃 설정
            timeout = aiohttp.ClientTimeout(total=5)
            async with session.get(url.strip(), headers=headers, timeout=timeout) as response:
                return url, response.status
        except Exception as e:
            return url, f"Error: {str(e)}"

async def check_all_urls(urls):
    """모든 URL을 비동기로 확인하는 함수"""
    # 동시 연결 수를 10개로 제한 (서버 부하 방지)
    semaphore = asyncio.Semaphore(25)
    
    async with aiohttp.ClientSession() as session:
        tasks = []
        for url in urls:
            url = url.strip()
            if url:  # 빈 줄이 아닌 경우만
                task = check_url_status(session, url, semaphore)
                tasks.append(task)
        
        # 모든 작업을 병렬로 실행
        results = await asyncio.gather(*tasks)
        return results

def main():
    """메인 함수"""
    parser = argparse.ArgumentParser(description="Check status of URLs in a file.")
    parser.add_argument("file_path", help="Path to the file containing URLs.")
    args = parser.parse_args()
    
    file_path = args.file_path
    
    try:
        with open(file_path, 'r', encoding='utf-8') as file:
            urls = file.readlines()
        
        # 빈 줄 제거
        urls = [url.strip() for url in urls if url.strip()]
        
        print(f"총 {len(urls)}개의 URL을 확인합니다...\n")
        
        # 시작 시간 기록
        start_time = time.time()
        
        # 비동기 실행
        results = asyncio.run(check_all_urls(urls))
        
        # 결과 처리
        success_count = 0
        error_count = 0
        
        for i, (url, status) in enumerate(results, 1):
            print(f"[{i}/{len(results)}] {url}")
            
            if status == 200:
                print(f"✅ OK (200)")
                success_count += 1
            else:
                print(f"❌ FAIL ({status})")
                error_count += 1
            print()
        
        # 실행 시간 계산
        end_time = time.time()
        execution_time = end_time - start_time
        
        print("=" * 50)
        print(f"검사 완료!")
        print(f"실행 시간: {execution_time:.2f}초")
        print(f"성공: {success_count}개")
        print(f"실패: {error_count}개")
        print(f"성공률: {(success_count / (success_count + error_count) * 100):.1f}%")
        
    except FileNotFoundError:
        print(f"파일을 찾을 수 없습니다: {file_path}")
    except Exception as e:
        print(f"오류가 발생했습니다: {str(e)}")

if __name__ == "__main__":
    main()

# 토스 기술 블로그 크롤러

이 프로젝트는 [토스 기술 블로그](https://toss.tech)의 게시물을 크롤링하고 추출하기 위한 파이썬 스크립트들을 포함합니다.

## 설치 및 사용법

### 1. 저장소 클론

```bash
git clone https://github.com/jaehunshin/toss-tech-blog-extractor.git
cd toss-tech-blog-extractor
```

### 2. 의존성 설치

프로젝트 의존성을 설치하는 방법은 `uv` 또는 `pip`을 사용하는 두 가지 방법이 있습니다.

#### `uv` 사용 시 (권장)

`uv`는 빠르고 현대적인 파이썬 패키지 관리 도구입니다. 아직 `uv`가 설치되어 있지 않다면 다음 명령어로 설치할 수 있습니다:

```bash
pip install uv
```

프로젝트 의존성을 설치하려면:

```bash
uv pip install .
# 또는
pip install .
```

또는 개발 모드로 설치하려면:

```bash
uv pip install -e .
# 또는
pip install -e .
```

프로젝트 의존성을 `requirements.txt` 파일로부터 동기화하려면:

```bash
uv sync
```

#### `pip` 사용 시

`pip`을 사용하여 의존성을 설치하려면 먼저 가상 환경을 활성화하는 것이 좋습니다:

```bash
python -m venv .venv
# Windows
.venv\Scripts\activate
# macOS/Linux
source .venv/bin/activate
```

가상 환경을 활성화한 후, 프로젝트 의존성을 설치합니다:

```bash
pip install .
# 또는
uv pip install .
```

또는 개발 모드로 설치하려면:

```bash
pip install -e .
# 또는
uv pip install -e .
```

## 스크립트

### 1. `toss_url_crawler.py`

이 스크립트는 토스 기술 블로그 전체를 자동으로 크롤링하여 모든 고유한 아티클 URL을 수집합니다. 마지막 페이지를 지능적으로 찾아내고 병렬로 URL을 가져와 빠른 속도를 제공합니다.

**사용법**

```bash
python main.py url_crawler
# 또는
uv run main url_crawler
```

이 스크립트를 실행하면 `data/urls/` 디렉토리에 `toss_url_MMDD.txt` (예: `toss_url_0818.txt`) 파일이 생성되며, 수집된 모든 URL이 포함됩니다.

### 2. `check_urls.py`

이 스크립트는 주어진 파일에 있는 각 URL의 HTTP 상태를 확인하여 접근 가능한지 확인합니다. 이는 콘텐츠 추출 단계로 진행하기 전에 크롤러가 수집한 URL의 유효성을 검증하는 데 유용합니다.

**사용법**

```bash
uv run check-urls <URL_파일_경로>
# 또는
python -m toss_tech_blog_extractor.check_urls <URL_파일_경로>
```

**예시**

```bash
uv run check-urls data/urls/toss_url_0818.txt
# 또는
python -m toss_tech_blog_extractor.check_urls data/urls/toss_url_0818.txt
```

### 3. `toss_techblog_extractor.py`

이 스크립트는 아티클 URL 파일들을 입력받아 각 페이지를 크롤링하고 제목, 날짜, 콘텐츠를 추출합니다. 콘텐츠는 HTML에서 깔끔한 마크다운으로 변환됩니다.

**사용법**

```bash
python main.py techblog_extractor -i <입력_URL_파일> [옵션]
# 또는
uv run main techblog_extractor -i <입력_URL_파일> [옵션]
```

**옵션**

- `-i`, `--input`: (필수) URL이 포함된 입력 파일 경로.
- `-o`, `--output`: 출력 JSON 파일 경로. 생략하면 `data/jsons/` 디렉토리에 자동으로 이름이 생성됩니다 (예: `toss_crawled_toss_url_0818_YYYYMMDD_HHMMSS.json`).
- `-m`, `--markdown`: 지정된 경우, 각 아티클을 `data/mark_downs/` 디렉토리에 별도의 `.md` 파일로 저장합니다.
- `-c`, `--concurrent`: 동시 연결 수 (기본값: 10).
- `-t`, `--timeout`: 요청 시간 초과 (초) (기본값: 30).

**예시**

```bash
# 기본 사용법
python main.py techblog_extractor -i data/urls/toss_url_0818.txt
# 또는
uv run main techblog_extractor -i data/urls/toss_url_0818.txt

# 개별 마크다운 파일 저장을 포함한 사용법
python main.py techblog_extractor -i data/urls/toss_url_0818.txt -m
# 또는
uv run main techblog_extractor -i data/urls/toss_url_0818.txt -m
```

## `main.py`를 통한 실행 (권장)

프로젝트 루트에 있는 `main.py` 스크립트를 사용하여 모든 크롤링 및 추출 작업을 통합하여 실행할 수 있습니다. 이는 각 스크립트의 경로를 직접 지정할 필요 없이 편리하게 작업을 수행할 수 있도록 돕습니다.

**사용법**

```bash
python main.py <도구_이름> [도구_인자]
# 또는
uv run main <도구_이름> [도구_인자]
```

-   `<도구_이름>`: 실행할 도구의 이름입니다. 다음 중 하나를 선택할 수 있습니다:
    -   `url_crawler`: 토스 기술 블로그 URL을 수집합니다.
    -   `techblog_extractor`: 수집된 URL에서 게시글 콘텐츠를 추출합니다.
-   `[도구_인자]`: 선택한 도구에 전달할 추가 인자입니다. 각 도구의 `--help` 옵션을 통해 자세한 인자를 확인할 수 있습니다.

**예시**

```bash
# URL 크롤러 실행
python main.py url_crawler
# 또는
uv run main url_crawler

# Techblog 추출기 실행 (입력 파일 및 마크다운 저장 옵션 포함)
python main.py techblog_extractor -i data/urls/toss_url_MMDD.txt -m
# 또는
uv run main techblog_extractor -i data/urls/toss_url_MMDD.txt -m
```

## 워크플로우

이 스크립트들을 사용하는 일반적인 워크플로우는 다음과 같습니다:

1. **URL 수집:** `main.py`를 사용하여 URL 크롤러를 실행하여 모든 아티클 URL 목록을 가져옵니다.

    ```bash
    python main.py url_crawler
    # 또는
    uv run main url_crawler
    ```

2. **(선택 사항) URL 확인:** 생성된 파일에 대해 `check-urls`를 실행하여 모든 링크가 유효한지 확인합니다.

    ```bash
    uv run check-urls data/urls/toss_url_MMDD.txt
    # 또는
    python -m toss_tech_blog_extractor.check_urls data/urls/toss_url_MMDD.txt
    ```

3. **콘텐츠 추출:** `main.py`를 사용하여 Techblog 추출기를 실행하여 아티클을 크롤링하고 콘텐츠를 저장합니다.

    ```bash
    python main.py techblog_extractor -i data/urls/toss_url_MMDD.txt -m
    # 또는
    uv run main techblog_extractor -i data/urls/toss_url_MMDD.txt -m
    ```

## 프로젝트 구조

```
.
├── GEMINI.md
├── README.md
├── docs
│   ├── toss_crawler_selector_guide.md
│   └── toss_crawling_workflow_guide.md
├── pyproject.toml
├── src
│   └── toss_tech_blog_extractor
│       ├── __init__.py
│       ├── check_urls.py
│       ├── toss_techblog_extractor.py
│       └── toss_url_crawler.py
└── tree.txt

3 directories, 10 files
```

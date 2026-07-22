# 토스 기술 블로그 추출기: 전체 플로우 가이드

이 문서는 `toss-tech-blog-extractor` 프로젝트의 전체적인 데이터 흐름과 각 구성 요소의 역할을 설명합니다.

## 1. 프로젝트 개요

`toss-tech-blog-extractor`는 토스 기술 블로그에서 게시글 URL을 수집하고, 각 게시글의 내용을 추출하는 파이썬 기반의 크롤링 도구입니다.

## 2. 주요 구성 요소 및 역할

프로젝트는 CLI, 서비스 모듈, 저장 모듈로 구성됩니다:

-   `cli.py`: `url_crawler`, `techblog_extractor`, `check_urls` 명령을 하나의 진입점으로 제공합니다.
-   `url_collector.py`: 토스 기술 블로그의 게시글 URL을 수집합니다.
-   `article_extractor.py`: 수집된 URL에서 각 게시글의 제목, 본문, 날짜 등 핵심 콘텐츠를 추출합니다.
-   `url_checker.py`: (선택 사항) 수집된 URL의 HTTP 상태를 확인합니다.
-   `clients.py`, `selectors.py`, `models.py`, `exporters.py`: HTTP 설정, 사이트 선택자, 결과 모델, 파일 저장 책임을 분리합니다.

기존의 `toss_url_crawler.py`, `toss_techblog_extractor.py`, `check_urls.py`는 이전 패키지 명령어와 import 경로를 유지하기 위한 호환 래퍼입니다.

## 3. 전체 데이터 흐름

1.  **URL 수집 (`url_collector.py`)**
    -   `url_collector.py` 서비스가 실행됩니다.
    -   토스 기술 블로그의 공개 목록 API에서 게시글 slug를 수집해 URL을 만듭니다.
    -   API를 사용할 수 없으면 HTML 목록 페이지 수집으로 자동 전환합니다.
    -   수집된 URL 목록은 다음 단계인 추출 과정에서 사용될 수 있도록 준비됩니다 (예: 파일로 저장).

2.  **콘텐츠 추출 (`article_extractor.py`)**
    -   `article_extractor.py` 서비스가 실행됩니다.
    -   `url_collector.py`에서 수집된 URL 목록을 입력으로 받습니다.
    -   각 URL에 접속하여 해당 게시글의 HTML 내용을 가져옵니다.
    -   가져온 HTML에서 의미 있는 태그와 메타데이터를 우선 사용하고, CSS 선택자를 보조 수단으로 사용해 제목, 본문, 날짜를 파싱합니다.
    -   추출된 데이터는 구조화된 형태로 저장됩니다 (예: JSON, 데이터베이스).

3.  **URL 유효성 검사 (`url_checker.py`) (선택 사항)**
    -   `url_checker.py` 서비스는 수집되거나 추출된 URL 목록에 대해 추가적인 검증을 수행할 수 있습니다.
    -   예를 들어, URL이 여전히 유효한지, 특정 패턴을 따르는지 등을 확인할 수 있습니다.

## 4. 파싱 폴백 전략

`selectors.py`는 동적으로 생성되는 CSS 클래스에만 의존하지 않습니다. HTML 구조가 바뀌어도 추출을 최대한 지속할 수 있도록 의미 기반 파싱과 CSS 선택자 폴백을 함께 사용합니다.

### 4.1. 우선순위

- 제목: `<h1>` → Open Graph 제목 메타데이터
- 날짜: `<time>` 또는 헤더의 날짜 텍스트 → 페이지 데이터의 `publishedTime`
- 본문: 기존 본문 CSS 선택자 → 게시글 헤더 다음의 콘텐츠 영역

### 4.2. CSS 선택자의 역할

본문의 서식과 이미지를 보존하려면 기존 `css-1vn47db` 선택자가 가장 정확합니다. 다만 이는 사이트 배포에 따라 변경될 수 있으므로, 선택자가 맞지 않을 때는 구조 기반 폴백을 사용합니다.

### 4.3. 검증과 유지보수

동적 클래스가 바뀌어도 현재 HTML 구조를 검증할 수 있도록 단위 테스트를 유지합니다. 새 구조가 도입되면 `selectors.py`와 테스트 fixture를 함께 갱신합니다.

## 5. 프로젝트 실행 방법 (예시)

프로젝트를 실행하기 전에 필요한 의존성을 설치해야 합니다. `pyproject.toml` 또는 `requirements.txt` 파일을 참조하여 `uv` 또는 `pip`를 사용하여 설치할 수 있습니다.

```bash
uv pip install -r requirements.txt
# 또는
pip install -r requirements.txt
```

프로젝트 의존성을 `requirements.txt` 파일로부터 동기화하려면:

```bash
uv sync
```

모든 크롤링 및 추출 작업은 프로젝트 루트에 있는 `main.py` 스크립트를 통해 통합하여 실행할 수 있습니다.

**사용법**

```bash
python main.py <도구_이름> [도구_인자]
# 또는
uv run toss-tech-blog <도구_이름> [도구_인자]
```

-   `<도구_이름>`: 실행할 도구의 이름입니다. 다음 중 하나를 선택할 수 있습니다:
    -   `url_crawler`: 토스 기술 블로그 URL을 수집합니다.
    -   `techblog_extractor`: 수집된 URL에서 게시글 콘텐츠를 추출합니다.
-   `[도구_인자]`: 선택한 도구에 전달할 추가 인자입니다. 각 도구의 `--help` 옵션을 통해 자세한 인자를 확인할 수 있습니다.

**예시**

```bash
# URL 수집 (URL 크롤러 실행)
python main.py url_crawler
# 또는
uv run toss-tech-blog url_crawler

# 콘텐츠 추출 (Techblog 추출기 실행, 입력 파일 및 마크다운 저장 옵션 포함)
python main.py techblog_extractor -i data/urls/toss_url_MMDD.txt -m
# 또는
uv run toss-tech-blog techblog_extractor -i data/urls/toss_url_MMDD.txt -m
```

자세한 사용법은 `python main.py <도구_이름> --help` 명령을 통해 확인할 수 있습니다.

<p align="center">
  <img src=".github/assets/readme-banner.svg" width="100%" alt="토스 기술 블로그 크롤러" />
</p>

# Toss Tech Blog Extractor

> 토스 기술 블로그의 공개 게시글 URL을 수집하고, 본문을 JSON과 Markdown으로 변환·저장하는 개인 포트폴리오 프로젝트입니다.

공개 웹 문서를 대상으로 URL 수집, 접근 상태 확인, HTML 파싱, 파일 내보내기까지의 흐름을 Python으로 구현했습니다. 목록 API를 우선 사용하되 사용할 수 없을 때는 HTML 목록 수집으로 전환하며, HTML 구조 변경에 대비해 의미 기반 선택자와 CSS 선택자를 함께 둡니다.

> [!IMPORTANT]
> 이 저장소는 토스 또는 비바리퍼블리카가 운영하거나 후원하는 공식 프로젝트가 아닙니다. `data/`의 텍스트는 공개 웹 페이지에서 수집한 결과일 뿐 원문을 대체하지 않으며, 최신 내용과 맥락은 항상 [토스 기술 블로그](https://toss.tech/)의 원문 링크를 우선 참조하세요. 토스 명칭·로고 등 상표와 게시글의 저작권은 각 권리자에게 있습니다.

## ✨ 주요 기능

| 기능 | 설명 |
| --- | --- |
| 게시글 URL 수집 | 공개 목록 API에서 게시글 URL을 수집하고, 실패 시 HTML 목록 페이지를 순회합니다. |
| URL 정규화·검증 | 중복, 쿼리 문자열, 앵커를 제거하고 수집된 URL의 HTTP 상태를 확인합니다. |
| 본문 추출 | 제목·작성일·본문을 추출해 HTML, 일반 텍스트, Markdown 표현으로 보존합니다. |
| 안정적인 요청 처리 | 동시 연결 수와 제한 시간을 조절하고, 429·5xx·시간 초과에는 지수 백오프로 재시도합니다. |
| 결과 내보내기 | 전체 결과는 JSON으로, 게시글별 결과는 Markdown 파일로 저장합니다. |
| 실행 결과 요약 | 전체·성공·실패·성공률·재시도 사유·소요시간을 수집 종료 시 바로 확인합니다. |

## 🧭 설계 방향

- **변경에 견디는 파싱:** 의미 있는 HTML 태그와 메타데이터를 우선 탐색하고, 기존 CSS 선택자는 폴백으로 사용합니다. 사이트의 클래스명이 바뀌어도 기본 정보를 추출할 가능성을 높이기 위한 선택입니다.
- **작업 단계 분리:** URL 수집, 상태 확인, 본문 추출, 파일 저장을 독립 모듈과 CLI 하위 명령으로 나눴습니다. 필요한 단계만 실행하거나 각 단계의 결과를 확인할 수 있습니다.
- **원문 추적성:** JSON 결과에 원문 URL과 수집 시각을 남깁니다. 수집 결과는 특정 시점의 스냅샷이므로 원문을 우선 확인할 수 있게 하기 위함입니다.

## 🛠 기술 스택

| Category | 기술 |
| --- | --- |
| Language | Python 3.12 이상 |
| HTTP & Concurrency | requests, aiohttp, asyncio |
| Parsing | Beautiful Soup 4, markdownify |
| Packaging | uv, Hatchling |
| Testing & Quality | unittest, Ruff, GitHub Actions |

## 🔍 기술 선정 이유

| 구분 | 기술 | 선정 이유 |
| --- | --- | --- |
| 비동기 요청 | aiohttp, asyncio | 여러 게시글 요청의 동시성을 제한하면서 순차 요청의 대기 시간을 줄이기 위해 사용했습니다. |
| HTML 파싱 | Beautiful Soup 4 | 의미 기반 요소와 CSS 선택자를 같은 인터페이스로 탐색하기 위해 사용했습니다. |
| 본문 변환 | markdownify | 링크·강조·목록·제목 구조를 유지한 Markdown을 만들기 위해 사용했습니다. |
| 재현 가능한 환경 | uv | Python 버전과 운영·개발 의존성을 잠금 파일로 일관되게 설치하기 위해 사용했습니다. |

### 문제 해결 사례

#### 1. 목록 API에만 의존하지 않는 URL 수집

공개 목록 API를 먼저 사용하되 요청 실패나 스키마 불일치가 발생하면 HTML 목록 수집으로 전환했습니다. 페이지네이션 정보를 얻을 수 있으면 병렬로 수집하고, 그렇지 않으면 빈 결과가 나올 때까지 순서대로 탐색합니다. API 응답과 HTML 링크의 URL 정규화·중복 제거는 네트워크 없는 단위 테스트로 검증합니다.

#### 2. 변경되는 HTML 구조에 대응하는 본문 파싱

제목·작성일·본문을 생성된 CSS 클래스 하나에만 의존하지 않도록 `h1`, `time`, Open Graph 메타데이터 등 의미 있는 요소를 먼저 탐색합니다. 기존 CSS 선택자는 정밀한 본문 추출을 위한 폴백으로 남기고, 이전 구조와 변경된 구조를 가정한 HTML fixture를 각각 테스트합니다.

#### 3. 실패 원인을 확인할 수 있는 요청 처리

429·5xx 응답, 시간 초과, 연결 오류를 재시도 가능한 실패로 분류하고 실제 추가 요청만 집계합니다. 실행이 끝나면 최종 성공·실패, 성공률, 재시도 횟수와 사유, 단조 시계로 측정한 소요시간을 출력합니다. CLI의 동시 연결 수와 제한 시간은 1 이상의 정수만 허용해 잘못된 설정도 실행 전에 차단합니다.

## 📁 프로젝트 구조

```text
toss-tech-blog-extractor/
├── src/toss_tech_blog_extractor/
│   ├── url_collector.py       # 게시글 URL 수집과 HTML 폴백
│   ├── url_checker.py         # 수집 URL의 HTTP 상태 확인
│   ├── article_extractor.py   # 게시글 파싱, 재시도, Markdown 변환
│   ├── metrics.py             # 성공률·재시도 사유·소요시간 집계
│   ├── exporters.py           # JSON·Markdown 파일 저장
│   ├── selectors.py           # 의미 기반·CSS 폴백 선택자
│   └── cli.py                 # 통합 CLI
├── tests/                     # 네트워크 없는 단위 테스트
├── examples/demo_urls.txt     # 한 건으로 실행 흐름을 확인하는 데모 입력
├── data/                      # 수집 결과 코퍼스와 실행 결과 저장 위치
├── .github/workflows/ci.yml   # 정적 검사·테스트·패키지 빌드 자동화
├── main.py                    # 패키지 설치 전 실행 가능한 진입점
└── pyproject.toml             # 패키지와 실행 명령 설정
```

## 🚀 시작하기

### 요구 사항

- Python 3.12 이상
- [uv](https://docs.astral.sh/uv/)

### 1. 저장소 내려받기

```bash
git clone https://github.com/jaehunshin-git/toss-tech-blog-extractor.git
cd toss-tech-blog-extractor
```

### 2. 설정하기

잠금 파일 기준으로 의존성을 설치합니다. 별도의 환경 변수나 시크릿은 필요하지 않습니다.

```bash
uv sync --locked
```

### 3. 실행하기

먼저 URL 목록을 수집합니다. 결과는 실행한 날짜가 포함된 이름으로 `data/urls/`에 저장됩니다.

```bash
uv run toss-tech-blog url_crawler
```

생성된 URL 목록의 접근 상태를 확인한 뒤, 목록 파일 경로를 지정해 본문을 추출합니다.

```bash
uv run toss-tech-blog check_urls data/urls/toss_url_MMDD.txt

uv run toss-tech-blog techblog_extractor \
  --input data/urls/toss_url_MMDD.txt \
  --output data/jsons/articles.json \
  --markdown
```

`--markdown`을 지정하면 게시글별 Markdown 파일을 `data/mark_downs/`에 함께 저장합니다. `--concurrent`와 `--timeout`으로 최대 동시 연결 수와 요청 제한 시간(초)을 조절할 수 있습니다.

### 4. 빠른 데모

저장소의 한 건짜리 입력으로 URL 요청부터 JSON 생성과 실행 통계 출력까지 확인할 수 있습니다.

```bash
uv run toss-tech-blog techblog_extractor \
  --input examples/demo_urls.txt \
  --output /tmp/toss-tech-demo.json \
  --concurrent 1 \
  --timeout 30
```

2026년 9월 7일 검증 실행에서는 다음 결과를 확인했습니다. 소요시간은 네트워크 환경에 따라 달라집니다.

```text
실행 요약 | 전체 1개 | 성공 1개 | 실패 0개 | 성공률 100.0% | 재시도 0회 | 소요 2.33초
```

### 5. 검증하기

네트워크 없이 실행되는 단위 테스트와 정적 검사를 실행합니다. GitHub Actions도 같은 흐름으로 Ruff 검사, 테스트, 패키지 빌드를 수행합니다.

```bash
uv run python -m unittest discover -s tests -v
uv run ruff check .
uv run ruff format --check .
uv build
```

## 📚 문서

| 문서 | 내용 |
| --- | --- |
| [전체 플로우 가이드](docs/project_flow_guide.md) | URL 수집부터 본문 저장까지의 구성 요소와 데이터 흐름 |
| [파싱 폴백 전략](docs/toss_crawler_selector_guide.md) | 의미 기반 파싱과 CSS 선택자의 우선순위 및 유지보수 기준 |

### 공개 데이터 안내

`data/urls/toss_url_0819.txt`의 URL 201개, 각 201건을 담은 JSON 결과 2개, 게시글별 Markdown 201개가 포함되어 있습니다. 이는 크롤러의 실제 출력 형식과 추출 품질을 검토하기 위한 공개 코퍼스이며, 원문을 이 저장소에서 재활용·재배포하기 위한 데이터셋이 아닙니다.

- 각 결과에는 출처 URL과 수집 시각이 포함됩니다.
- 게시글은 수정·삭제될 수 있으므로 최신 정보, 인용, 이용 여부는 반드시 [토스 기술 블로그](https://toss.tech/)의 원문에서 확인해야 합니다.
- 콘텐츠를 서비스에 적용하거나 별도로 이용하기 전에는 해당 권리와 이용 조건을 확인해야 합니다.

## 📌 포트폴리오 범위와 권리 안내

이 프로젝트의 목적은 공개 웹 콘텐츠를 다루는 수집·파싱·변환 파이프라인의 구현을 보여 주는 것입니다. 토스와 제휴하거나 토스의 공식 도구를 제공하는 프로젝트가 아닙니다.

- 배너의 토스 로고는 [토스 브랜드 리소스 센터](https://brand.toss.im/)에서 제공하는 공식 자산을 원형·색상·비율 변경 없이 사용했습니다. 관련 상표권은 비바리퍼블리카에 있습니다.
- 수집 콘텐츠의 저작권은 각 원저작자 또는 권리자에게 있으며, 이 저장소의 수집 결과는 원문과 독립된 권리 허락을 의미하지 않습니다.
- 콘텐츠를 인용하거나 이용할 때는 원문 URL을 함께 제시하고, 상업적 이용·대량 재배포 등은 적용 가능한 이용 조건과 권리를 별도로 확인하세요.

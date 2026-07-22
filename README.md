<p align="center">
  <img src=".github/assets/readme-banner.svg" width="100%" alt="토스 기술 블로그 크롤러" />
</p>

<p align="center">
  토스 기술 블로그의 게시글 URL과 본문을 수집해<br />
  <strong>JSON과 Markdown으로 저장하는 Python 크롤러</strong>입니다.
</p>

> [!IMPORTANT]
> 이 저장소는 토스 또는 비바리퍼블리카가 운영하는 공식 프로젝트가 아닙니다. 수집한 콘텐츠의 저작권은 원저작자에게 있으며, 서비스에 적용하기 전 [토스 기술 블로그](https://toss.tech)의 이용 정책을 확인하세요.

## 프로젝트 소개

이 프로젝트는 토스 기술 블로그의 글을 대상으로 URL 수집부터 본문 추출과 파일 저장까지의 크롤링 작업을 자동화합니다.

1. 공개 목록 API에서 게시글 URL을 수집하고, API를 사용할 수 없으면 목록 페이지 수집으로 전환합니다.
2. 수집한 URL이 실제로 접근 가능한지 확인합니다.
3. 각 게시글에서 제목, 작성일, 본문을 추출합니다.
4. 본문을 HTML, 일반 텍스트, Markdown 세 가지 표현으로 저장합니다.

생성된 JSON과 Markdown은 게시글 보관, 내용 분석, 검색 데이터 구축 같은 후속 작업의 입력으로 활용할 수 있습니다.

## 처리 흐름

```text
토스 기술 블로그
       │
       ▼
게시글 URL 수집 ── URL 상태 확인
       │
       ▼
제목 · 작성일 · 본문 추출
       │
       ├── JSON: 메타데이터와 여러 본문 표현 보존
       └── Markdown: 게시글별 본문 저장과 검수
```

## 주요 기능

- 공개 목록 API로 모든 게시글 URL을 수집하고, HTML 목록 수집을 폴백으로 제공합니다.
- 중복 URL과 쿼리 문자열, 앵커를 제거해 정규화합니다.
- 동시 연결 수와 요청 제한 시간을 조절할 수 있습니다.
- 일시적인 네트워크 오류와 429·5xx 응답은 지수 백오프로 재시도합니다.
- 제목·날짜·본문은 의미 있는 HTML 태그와 메타데이터를 우선 사용하고 CSS 선택자를 보조로 사용합니다.
- 본문의 불필요한 태그를 제거하고 Markdown으로 변환합니다.
- 원문 추적에 필요한 URL과 수집 시각을 함께 저장합니다.
- JSON 전체 코퍼스와 게시글별 Markdown 파일을 동시에 만들 수 있습니다.

## 빠른 시작

### 요구 사항

- Python 3.12 이상
- [uv](https://docs.astral.sh/uv/) 권장

### 설치

```bash
git clone https://github.com/jaehunshin-git/toss-tech-blog-extractor.git
cd toss-tech-blog-extractor
uv sync
```

`pip`을 사용하려면 다음과 같이 설치할 수 있습니다.

```bash
python -m venv .venv
source .venv/bin/activate
pip install -e .
```

### 1. 게시글 URL 수집

```bash
uv run toss-url-crawler
```

실행 결과는 `data/urls/toss_url_MMDD.txt`에 저장됩니다.

### 2. URL 상태 확인

```bash
uv run check-urls data/urls/toss_url_MMDD.txt
```

각 URL의 HTTP 상태와 전체 성공률을 터미널에서 확인할 수 있습니다.

### 3. 게시글 추출

```bash
uv run toss-techblog-extractor \
  --input data/urls/toss_url_MMDD.txt \
  --markdown
```

JSON 결과는 `data/jsons/`에, 게시글별 Markdown은 `data/mark_downs/`에 저장됩니다.

출력 경로와 네트워크 설정을 직접 지정할 수도 있습니다.

```bash
uv run toss-techblog-extractor \
  --input data/urls/toss_url_MMDD.txt \
  --output data/jsons/toss_tech_corpus.json \
  --concurrent 10 \
  --timeout 30 \
  --markdown
```

## 명령어와 옵션

| 명령어 | 역할 | 주요 옵션 |
| --- | --- | --- |
| `toss-url-crawler` | 게시글 URL 수집 | 별도 옵션 없음 |
| `check-urls` | URL 접근 상태 확인 | URL 목록 파일 경로 |
| `toss-techblog-extractor` | 본문 추출 및 파일 저장 | `-i`, `-o`, `-c`, `-t`, `-m` |
| `toss-tech-blog` | 세 기능을 하나의 명령으로 실행 | `url_crawler`, `check_urls`, `techblog_extractor` |

통합 명령어도 사용할 수 있습니다.

```bash
uv run toss-tech-blog url_crawler
uv run toss-tech-blog check_urls data/urls/toss_url_MMDD.txt
uv run toss-tech-blog techblog_extractor --input data/urls/toss_url_MMDD.txt --markdown
```

추출기 옵션은 다음과 같습니다.

| 옵션 | 설명 | 기본값 |
| --- | --- | --- |
| `-i`, `--input` | URL 목록 파일 경로 | 필수 |
| `-o`, `--output` | 출력 JSON 파일 경로 | `data/jsons/`에 자동 생성 |
| `-c`, `--concurrent` | 최대 동시 연결 수 | `10` |
| `-t`, `--timeout` | 요청 제한 시간(초) | `30` |
| `-m`, `--markdown` | 게시글별 Markdown 파일 저장 | 사용 안 함 |

## 출력 데이터

JSON의 게시글 한 건은 다음 구조를 가집니다.

```json
{
  "url": "https://toss.tech/article/example",
  "title": "게시글 제목",
  "date": "2026년 1월 1일",
  "content": {
    "markdown": "## Markdown으로 정제된 본문",
    "text": "태그를 제외한 일반 텍스트",
    "html": "<div>원본 구조를 보존한 HTML</div>"
  },
  "crawled_at": "2026-01-01T12:00:00"
}
```

제목·날짜·본문 중 일부를 추출하지 못한 레코드에는 원인을 나타내는 `error` 필드가 추가됩니다.

| 필드 | 활용 예시 |
| --- | --- |
| `url` | 답변 출처 표시와 원문 역추적 |
| `title` | 검색 결과 제목과 메타데이터 필터 |
| `date` | 최신성 정렬과 기간 필터 |
| `content.markdown` | 헤딩 구조를 고려한 문서 청킹 |
| `content.text` | 본문 검색과 텍스트 분석 |
| `content.html` | 표·링크·이미지 등 원문 구조 재처리 |
| `crawled_at` | 데이터 갱신 주기와 버전 관리 |

## 수집 데이터 활용

- JSON 파일은 URL, 제목, 작성일, 수집 시각과 여러 본문 표현을 함께 보존합니다.
- Markdown 파일은 게시글 단위 검수, 보관, 후속 가공에 활용할 수 있습니다.
- 필요하면 수집 결과를 검색 인덱스나 RAG 파이프라인의 입력 데이터로 사용할 수 있습니다.

## 프로젝트 구조

```text
.
├── .github/assets/                 # README 배너와 공식 로고 자산
├── data/
│   ├── urls/                       # 수집한 게시글 URL 목록
│   ├── jsons/                      # 전체 게시글 JSON 코퍼스
│   └── mark_downs/                 # 게시글별 Markdown 문서
├── src/toss_tech_blog_extractor/
│   ├── article_extractor.py        # 게시글 본문 추출과 정제
│   ├── cli.py                      # 통합 CLI
│   ├── clients.py                  # 공통 HTTP 클라이언트 설정
│   ├── exporters.py                # JSON과 Markdown 저장
│   ├── models.py                   # 게시글 데이터 모델
│   ├── selectors.py                # 의미 기반 파싱 및 CSS 폴백 선택자
│   ├── url_checker.py              # URL 상태 검사
│   ├── url_collector.py            # 게시글 URL 수집
│   └── toss_*.py, check_urls.py    # 이전 명령어·import 호환 래퍼
├── tests/                           # 네트워크 없이 실행하는 단위 테스트
├── main.py                         # 통합 CLI 진입점
└── pyproject.toml                  # 패키지와 실행 명령 설정
```

## 운영 시 주의 사항

- 목록 API나 HTML 구조가 바뀌면 `url_collector.py`, `selectors.py`, 테스트 fixture를 함께 갱신해야 합니다.
- 서버에 부담을 주지 않도록 동시 연결 수를 보수적으로 설정하고 반복 수집을 피하세요.
- 공개된 글이라도 원문 전체를 재배포하거나 상업적으로 이용하기 전에는 저작권과 이용 조건을 확인하세요.
- 답변 생성 시 원문 URL을 출처로 제공하고, 수집 시각이 오래된 데이터는 다시 검증하세요.

## 테스트

```bash
uv run python -m unittest discover -s tests -v
```

URL 정규화, 공개 목록 API 응답, 이전·현재 HTML 구조의 게시글 파싱, 이전 import 경로 호환성을 검증합니다.

## 브랜드 자산

배너의 토스 시그니처 로고는 [토스 브랜드 리소스 센터](https://brand.toss.im/)에서 제공하는 공식 원본을 비율과 색상 변경 없이 사용했습니다. 로고와 토스 명칭의 권리는 비바리퍼블리카에 있습니다.

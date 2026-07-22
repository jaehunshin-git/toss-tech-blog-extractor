"""크롤링 결과를 파일로 내보내는 기능."""

import json
import re
from pathlib import Path
from typing import Iterable


PROJECT_ROOT = Path(__file__).resolve().parents[2]
DATA_DIR = PROJECT_ROOT / "data"


def save_articles_json(articles: Iterable[dict[str, object]], output_file: str | Path) -> Path:
    """게시글 목록을 UTF-8 JSON 파일로 저장한다."""
    output_path = Path(output_file)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", encoding="utf-8") as file:
        json.dump(list(articles), file, ensure_ascii=False, indent=2)
    return output_path


def save_articles_markdown(articles: Iterable[dict[str, object]], output_dir: str | Path) -> list[Path]:
    """게시글별 Markdown 파일을 저장하고 생성된 경로를 반환한다."""
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)
    saved_files: list[Path] = []

    for index, article in enumerate(articles):
        content = article.get("content")
        if not isinstance(content, dict) or not isinstance(content.get("markdown"), str):
            continue

        title = str(article.get("title", f"article_{index}"))
        safe_title = re.sub(r'[<>:"/\\|?*]', "_", title)[:50]
        file_path = output_path / f"{index:03d}_{safe_title}.md"

        with file_path.open("w", encoding="utf-8") as file:
            file.write(f"# {title}\n\n")
            file.write(f"**Date:** {article.get('date', '날짜 없음')}\n")
            file.write(f"**URL:** {article.get('url', '')}\n\n")
            file.write("---\n\n")
            file.write(content["markdown"])
        saved_files.append(file_path)

    return saved_files

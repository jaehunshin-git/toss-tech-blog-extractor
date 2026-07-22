import sys
from pathlib import Path

# 패키지를 설치하지 않은 상태에서도 `python main.py ...`로 실행할 수 있게 한다.
sys.path.insert(0, str(Path(__file__).parent / "src"))

from toss_tech_blog_extractor.cli import main

if __name__ == "__main__":
    main()

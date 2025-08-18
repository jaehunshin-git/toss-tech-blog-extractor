import argparse
import asyncio
import sys
from pathlib import Path

# Add the src directory to the Python path to allow importing modules
# from src/toss_tech_blog_extractor
project_root = Path(__file__).parent
src_path = project_root / "src"
sys.path.insert(0, str(src_path))

try:
    from toss_tech_blog_extractor.toss_url_crawler import main as url_crawler_main
    from toss_tech_blog_extractor.toss_techblog_extractor import main as techblog_extractor_main
except ImportError as e:
    print(f"Error importing modules: {e}")
    print("Please ensure your Python path is correctly configured or that 'src' is in your project root.")
    sys.exit(1)

def main():
    parser = argparse.ArgumentParser(description='Toss Tech Blog Automation Tool')
    parser.add_argument('tool', choices=['url_crawler', 'techblog_extractor'],
                        help='Specify which tool to run: "url_crawler" or "techblog_extractor"')
    
    # Add a placeholder for arguments that will be passed to the sub-tools
    parser.add_argument('args', nargs=argparse.REMAINDER, 
                        help='Arguments to pass to the selected tool. Use --help after the tool name for specific options.')

    args = parser.parse_args()

    if args.tool == 'url_crawler':
        print("Running Toss URL Crawler...")
        # We need to pass the remaining arguments to the url_crawler_main function
        # For now, url_crawler_main doesn't take args, so we'll just call it.
        # We'll adjust url_crawler_main later if it needs args.
        asyncio.run(url_crawler_main())
    elif args.tool == 'techblog_extractor':
        print("Running Toss Techblog Extractor...")
        # Re-parse the remaining arguments for the techblog_extractor_main
        # This requires techblog_extractor_main to be callable with its own argparse
        # We'll adjust techblog_extractor_main to accept args directly or re-parse them.
        sys.argv = [sys.argv[0]] + args.args # Reset sys.argv for the sub-parser
        techblog_extractor_main()
    else:
        parser.print_help()

if __name__ == "__main__":
    main()

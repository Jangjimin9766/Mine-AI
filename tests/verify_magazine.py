import argparse
import sys
import os
import json
import time

# Add project root to path
# tests/verify_magazine.py -> (dirname) tests/ -> (dirname) project_root
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

try:
    from app.core.magazine_maker import generate_magazine_content
except ImportError:
    # If running from project root
    sys.path.append(os.getcwd())
    from app.core.magazine_maker import generate_magazine_content

def save_preview(data, filename="magazine_preview.html"):
    html_content = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <title>{data.get('title', 'Magazine Preview')}</title>
        <style>
            body {{ font-family: 'Pretendard', sans-serif; max-width: 800px; margin: 0 auto; padding: 20px; }}
            .section {{ margin-bottom: 40px; border-bottom: 1px solid #eee; padding-bottom: 20px; }}
            .hero {{ background: #f8f9fa; padding: 20px; text-align: center; }}
            img {{ max-width: 100%; height: auto; border-radius: 8px; margin: 10px 0; }}
            .tag {{ display: inline-block; background: #eee; padding: 4px 8px; border-radius: 12px; font-size: 12px; margin-right: 4px; }}
            .meta {{ color: #666; font-size: 14px; margin-top: 10px; }}
        </style>
    </head>
    <body>
        <div class="hero">
            <h1>{data.get('title')}</h1>
            <h3>{data.get('subtitle')}</h3>
            <p>{data.get('introduction')}</p>
            <img src="{data.get('cover_image_url')}" alt="Cover Image">
            <div class="meta">
                {'''
                '''.join([f'<span class="tag">{tag}</span>' for tag in data.get('tags', [])])}
            </div>
        </div>

        <div class="content">
            {''.join([f'''
            <div class="section">
                <h2>{section.get('heading')}</h2>
                <img src="{section.get('thumbnail_url')}" alt="Section Thumbnail">
                <div class="paragraphs">
                    {''.join([f'''
                    <div class="paragraph">
                        <h4>{p.get('subtitle')}</h4>
                        <p>{p.get('text')}</p>
                        <img src="{p.get('image_url')}" alt="{p.get('image_search_keyword', '')}">
                    </div>
                    ''' for p in section.get('paragraphs', [])])}
                </div>
            </div>
            ''' for section in data.get('sections', [])])}
        </div>
    </body>
    </html>
    """
    
    with open(filename, "w", encoding="utf-8") as f:
        f.write(html_content)
    print(f"✅ Preview saved to {filename}")

def main():
    parser = argparse.ArgumentParser(description='Verify Magazine Generation')
    parser.add_argument('--topic', type=str, help='Custom topic to test')
    parser.add_argument('--case', type=str, help='Specific test case ID to run (wine, interior, style)')
    args = parser.parse_args()

    # Custom topic test
    if args.topic:
        print(f"\n🚀 Testing Custom Topic: {args.topic}")
        try:
            data = generate_magazine_content(args.topic)
            save_preview(data, f"test_magazine_custom.html")
        except Exception as e:
            print(f"❌ Failed to generate custom topic: {e}")
        return

    # Standard test cases
    test_cases = [
        {
            "id": "wine",
            "topic": "성수동 와인바 가이드",
            "interests": ["wine", "food", "mood"],
            "mood": "Classic"
        },
        {
            "id": "interior",
            "topic": "2024년 거실 인테리어 트렌드",
            "interests": ["interior", "home", "design"],
            "mood": "Minimal"
        },
        {
            "id": "style",
            "topic": "올드머니 룩 스타일링",
            "interests": ["fashion", "luxury"],
            "mood": "Sophisticated"
        }
    ]
    
    selected_case = args.case or "all"
    for case in test_cases:
        if selected_case != "all" and selected_case != case['id']:
            continue

        print(f"\n🚀 Testing Topic: {case['topic']}")
        try:
            data = generate_magazine_content(case['topic'], case['interests'], case['mood'])
            save_preview(data, f"test_magazine_{case['id']}.html")
            
            if selected_case == "all":
                print("⏱️ Cooling down for 30 seconds to avoid Free Tier rate limits...")
                time.sleep(30)
        except Exception as e:
            print(f"❌ Failed to generate {case['id']}: {e}")
            time.sleep(10)

if __name__ == "__main__":
    main()

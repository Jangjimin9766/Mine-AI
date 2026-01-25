import sys
import os

# Add project root to sys.path
sys.path.append(os.getcwd())

from app.core.magazine_maker import generate_magazine_content
import json

def verify_v5():
    topic = "2024년 일본 수제 안경 브랜드: 장인정신과 테크놀로지의 결합"
    user_interests = ["패션", "디자인", "안경", "수공예"]
    user_mood = "Minimal"
    
    print(f"🚀 [V5 Verification] Generating magazine for topic: {topic}")
    
    try:
        data = generate_magazine_content(topic, user_interests, user_mood)
        
        # Save JSON for inspection
        with open("v5_test_output.json", "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=4)
            
        print("✅ Generation complete. Creating HTML preview...")
        
        # Simple HTML preview logic (similar to tools/magazine_preview.py but local)
        title_raw = data.get("title", "Untitled")
        title_html = title_raw
        if ":" in title_raw:
            parts = title_raw.split(":", 1)
            title_html = f'<span class="main-title">{parts[0].strip()}</span><span class="sub-title-inline">{parts[1].strip()}</span>'
            
        tags_html = " ".join([f'<span class="tag">#{t.strip()}</span>' for t in data.get('tags', [])])
        cover_url = data.get('cover_image_url') or ""
        
        html_template = f"""
        <!DOCTYPE html>
        <html lang="ko">
        <head>
            <meta charset="UTF-8">
            <style>
                body {{ font-family: 'Apple SD Gothic Neo', sans-serif; line-height: 1.7; max-width: 900px; margin: 0 auto; padding: 40px 20px; background: #fafafa; color: #1a1a1a; }}
                header {{ text-align: center; padding: 60px 0; border-bottom: 2px solid #1a1a1a; background: #fff; margin-bottom: 40px; }}
                .main-title {{ display: block; font-size: 3rem; font-weight: 800; letter-spacing: -1px; }}
                .sub-title-inline {{ display: block; font-size: 1.8rem; color: #666; font-weight: 300; margin-top: 10px; }}
                .intro {{ font-size: 1.2rem; margin: 40px 0; border-left: 6px solid #1a1a1a; padding: 20px 30px; background: #fff; font-style: italic; }}
                .section {{ margin-bottom: 80px; background: #fff; padding: 40px; border-radius: 4px; box-shadow: 0 4px 20px rgba(0,0,0,0.05); }}
                .section h2 {{ font-size: 2rem; border-bottom: 1px solid #eee; padding-bottom: 15px; margin-top: 0; }}
                .content h3 {{ font-size: 1.4rem; margin-top: 30px; border-left: 4px solid #1a1a1a; padding-left: 15px; }}
                .content blockquote {{ font-size: 1.2rem; border-left: 4px solid #1a1a1a; margin: 30px 0; padding: 15px 25px; background: #f9f9f9; font-style: italic; color: #444; }}
                .content strong {{ color: #000; font-weight: 700; background: linear-gradient(120deg, #e0f2f1 0%, #e0f2f1 100%); background-repeat: no-repeat; background-size: 100% 30%; background-position: 0 85%; }}
                .tag {{ display: inline-block; background: #1a1a1a; color: #fff; padding: 5px 12px; border-radius: 2px; font-size: 0.8rem; margin-right: 5px; }}
                img {{ width: 100%; height: auto; border-radius: 2px; margin: 20px 0; }}
            </style>
        </head>
        <body>
            <header>
                <img src="{cover_url}" style="height: 400px; object-fit: cover;">
                <h1>{title_html}</h1>
                <p>{data.get('subtitle', '')}</p>
                <div class="tags">{tags_html}</div>
            </header>
            <div class="intro">{data.get('introduction', '')}</div>
        """
        
        for section in data.get('sections', []):
            html_template += f"""
            <div class="section">
                <h2>{section.get('heading', '')}</h2>
                <img src="{section.get('image_url', '')}">
                <div class="content">{section.get('content', '')}</div>
            </div>
            """
            
        html_template += "</body></html>"
        
        with open("v5_visual_verify.html", "w", encoding="utf-8") as f:
            f.write(html_template)
            
        print(f"✅ Visual verification file created: v5_visual_verify.html")
        return True
    except Exception as e:
        print(f"❌ Verification failed: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    verify_v5()

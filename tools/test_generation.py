import sys
import os
import json

# Add project root to sys.path
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.append(project_root)

from app.core.magazine_maker import generate_magazine_content

def save_preview(magazine_data, filename):
    # --- Data Processing (Safety first) ---
    title_raw = magazine_data.get("title", "")
    if ":" in title_raw:
        parts = title_raw.split(":", 1)
        title_html = f'<span class="main-title">{parts[0].strip()}</span><span class="sub-title-inline">{parts[1].strip()}</span>'
    else:
        title_html = title_raw

    tags_list = magazine_data.get('tags', [])
    tags_html = " ".join([f'<span class="tag">#{t.strip()}</span>' for t in tags_list if t.strip()])
    
    cover_url = magazine_data.get('cover_image_url') or ""
    intro_text = magazine_data.get('introduction') or ""

    # --- HTML Template (Magazine B Style) ---
    html_template = f"""
    <!DOCTYPE html>
    <html lang="ko">
    <head>
        <meta charset="UTF-8">
        <title>{magazine_data.get('title', 'Magazine Preview')}</title>
        <style>
            body {{ font-family: 'Apple SD Gothic Neo', 'Malgun Gothic', sans-serif; line-height: 1.7; max-width: 900px; margin: 0 auto; padding: 40px 20px; background: #f4f4f4; color: #222; }}
            header {{ text-align: center; padding: 60px 0; border-bottom: 3px solid #000; background: #fff; margin-bottom: 40px; border-radius: 8px 8px 0 0; position: relative; }}
            h1 {{ font-size: 3.5rem; margin-bottom: 15px; letter-spacing: -1px; line-height: 1.2; text-transform: none; }}
            .main-title {{ display: block; font-weight: 800; color: #000; }}
            .sub-title-inline {{ display: block; font-size: 2.2rem; color: #444; margin-top: 10px; font-weight: 400; }}
            .subtitle {{ font-style: italic; color: #555; font-size: 1.4rem; margin-bottom: 20px; }}
            .intro {{ font-size: 1.3rem; margin: 40px 0; background: #fff; padding: 30px; border-left: 8px solid #000; line-height: 1.8; box-shadow: 0 2px 10px rgba(0,0,0,0.05); font-family: 'serif'; }}
            .section {{ margin-bottom: 80px; background: #fff; padding: 40px; border-radius: 12px; box-shadow: 0 10px 30px rgba(0,0,0,0.08); overflow: hidden; }}
            .section h2 {{ font-size: 2.5rem; border-bottom: 2px solid #eee; padding-bottom: 15px; margin-top: 0; color: #000; font-weight: 900; }}
            .content {{ font-size: 1.15rem; color: #333; line-height: 1.9; }}
            .content h3 {{ font-size: 1.8rem; margin: 40px 0 20px 0; color: #111; border-left: 6px solid #333; padding-left: 20px; font-weight: 800; }}
            .content p {{ margin: 25px 0; }}
            .content strong {{ color: #000; font-weight: 800; background: linear-gradient(120deg, #fff3b0 0%, #fff3b0 100%); background-repeat: no-repeat; background-size: 100% 30%; background-position: 0 80%; }}
            .content blockquote {{ font-size: 1.5rem; border-left: 8px solid #000; margin: 40px 0; padding: 25px 40px; color: #111; font-style: italic; background: #f9f9f9; line-height: 1.5; }}
            .content ul {{ padding-left: 25px; margin: 25px 0; }}
            .content li {{ margin-bottom: 15px; }}
            .image-container {{ position: relative; margin: 40px 0; text-align: center; background: #eee; border-radius: 8px; min-height: 200px; display: flex; flex-direction: column; align-items: center; justify-content: center; border: 1px solid #ddd; }}
            img {{ max-width: 100%; max-height: 700px; object-fit: contain; border-radius: 4px; }}
            .caption {{ font-size: 1rem; color: #666; margin-top: 15px; font-style: italic; text-align: center; }}
            .tag {{ display: inline-block; background: #222; color: #fff; padding: 8px 18px; border-radius: 50px; font-size: 0.9rem; margin-right: 10px; font-weight: 700; }}
            .cover-img {{ width: 100%; height: 500px; object-fit: cover; border-radius: 8px; margin-bottom: 30px; }}
            .moodboard-section {{ margin-top: 100px; padding: 60px; background: #000; color: #fff; border-radius: 12px; text-align: center; }}
            .moodboard-img {{ width: 100%; height: auto; border-radius: 8px; box-shadow: 0 20px 50px rgba(0,0,0,0.5); }}
        </style>
    </head>
    <body style="background:#f4f4f4">
        <header>
            <img src="{cover_url}" class="cover-img">
            <h1>{title_html}</h1>
            <p class="subtitle">{magazine_data.get('subtitle', '')}</p>
            <div class="tags">{tags_html}</div>
        </header>
        
        <div class="intro">{intro_text}</div>
    """
    
    # Add Sections
    for section in sorted(magazine_data.get('sections', []), key=lambda x: x.get('display_order', 0)):
        img_url = section.get('image_url') or ""
        caption = section.get('caption')
        caption_text = "" if not caption or str(caption).lower() == 'none' else str(caption)
        caption_html = f'<p class="caption">{caption_text}</p>' if caption_text else ''
        
        html_template += f"""
        <div class="section">
            <h2>{section.get('heading', '')}</h2>
            <div class="image-container">
                <img src="{img_url}" alt="{caption_text}" onerror="this.style.display='none'; this.nextElementSibling.style.display='block';">
                <p class="img-error" style="display:none; padding:40px; color:#999; font-style:italic;">이미지를 불러올 수 없습니다</p>
                {caption_html}
            </div>
            <div class="content">{section.get('content', '')}</div>
        </div>
        """
    
    # Add Moodboard if exists
    if magazine_data.get('moodboard'):
        mb_url = magazine_data['moodboard'].get('image_url')
        mb_desc = magazine_data['moodboard'].get('description')
        html_template += f"""
        <div class="moodboard-section">
            <h2 style="color:#fff; border-bottom-color:#333">Integrated Moodboard</h2>
            <img src="{mb_url}" class="moodboard-img">
            <p style="margin-top:20px; color:#aaa; font-size:0.9rem;">{mb_desc}</p>
        </div>
        """
        
    html_template += """
    </body>
    </html>
    """
    
    with open(filename, "w", encoding="utf-8") as f:
        f.write(html_template)
    print(f"✅ Preview saved to: {filename}")

def main():
    test_cases = [
        {
            "id": "wine",
            "topic": "나파 밸리의 컬트 와인: 기술과 전통의 교차점",
            "interests": ["럭셔리 라이프스타일", "와인 투자 가치 분석", "전통 양조학", "스마트 양조 기술(Smart Enology)"],
            "mood": "지적이며 권위 있는, 세련된 하이엔드 어조"
        },
        {
            "id": "fashion",
            "topic": "2024 하이엔드 콰이어트 럭셔리 트렌드",
            "interests": ["올드 머니 룩", "미니멀리즘", "하이퀄리티 소재", "브랜드 헤리티지"],
            "mood": "우아하고 절제된, 품격 있는"
        },
        {
            "id": "food",
            "topic": "미슐랭 3스타 셰프의 미학: 분자 가스트로노미",
            "interests": ["파인다이닝", "식재료의 본질", "창의적 플레이팅", "미식의 미래"],
            "mood": "실험적이고 감각적인, 탐구적인"
        }
    ]
    
    for case in test_cases:
        print(f"\n🚀 Testing Topic: {case['topic']}")
        try:
            data = generate_magazine_content(case['topic'], case['interests'], case['mood'])
            save_preview(data, f"test_magazine_{case['id']}.html")
        except Exception as e:
            print(f"❌ Failed to generate {case['id']}: {e}")

if __name__ == "__main__":
    main()

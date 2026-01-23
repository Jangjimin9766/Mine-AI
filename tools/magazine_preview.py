import requests
import os
import webbrowser
import argparse
import json

def generate_preview(magazine_id, token, base_url="http://52.63.142.228:8080"):
    print(f"🔍 Fetching magazine #{magazine_id}...")
    
    url = f"{base_url}/api/magazines/{magazine_id}"
    headers = {
        "accept": "application/json",
        "Authorization": f"Bearer {token}"
    }
    
    response = requests.get(url, headers=headers)
    if response.status_code != 200:
        print(f"❌ Failed to fetch magazine: {response.status_code}")
        print(response.text)
        return

    data = response.json()
    
    # --- Data Processing (Safety first) ---
    title_raw = data.get("title", "")
    if ":" in title_raw:
        parts = title_raw.split(":", 1)
        # Keep colon removed but use the 43-style rendering
        title_html = f'<span class="main-title">{parts[0].strip()}</span><span class="sub-title-inline">{parts[1].strip()}</span>'
    else:
        title_html = title_raw

    tags_list = data.get('tags', '').split(',') if isinstance(data.get('tags'), str) else data.get('tags', [])
    tags_html = " ".join([f'<span class="tag">#{t.strip()}</span>' for t in tags_list if t.strip()])
    
    cover_url = data.get('coverImageUrl') or data.get('cover_image_url') or ""
    intro_text = data.get('introduction') or ""

    # --- HTML Template (Reverting to 43's Magazine B Style) ---
    html_template = f"""
    <!DOCTYPE html>
    <html lang="ko">
    <head>
        <meta charset="UTF-8">
        <title>{data.get('title', 'Magazine Preview')}</title>
        <style>
            body {{ font-family: 'Apple SD Gothic Neo', 'Malgun Gothic', sans-serif; line-height: 1.7; max-width: 900px; margin: 0 auto; padding: 40px 20px; background: #f4f4f4; color: #222; }}
            header {{ text-align: center; padding: 60px 0; border-bottom: 3px solid #000; background: #fff; margin-bottom: 40px; border-radius: 8px 8px 0 0; position: relative; }}
            h1 {{ font-size: 3.5rem; margin-bottom: 15px; letter-spacing: -1px; line-height: 1.2; text-transform: none; }}
            .main-title {{ display: block; font-weight: 800; color: #000; }}
            .sub-title-inline {{ display: block; font-size: 2.2rem; color: #444; margin-top: 10px; font-weight: 400; }}
            .subtitle {{ font-style: italic; color: #555; font-size: 1.4rem; margin-bottom: 20px; }}
            .intro {{ font-size: 1.2rem; margin: 40px 0; background: #fff; padding: 30px; border-left: 8px solid #000; line-height: 1.8; box-shadow: 0 2px 10px rgba(0,0,0,0.05); }}
            .section {{ margin-bottom: 80px; background: #fff; padding: 40px; border-radius: 12px; box-shadow: 0 10px 30px rgba(0,0,0,0.08); overflow: hidden; }}
            .section h2 {{ font-size: 2.2rem; border-bottom: 2px solid #eee; padding-bottom: 15px; margin-top: 0; color: #000; }}
            .content {{ font-size: 1.1rem; color: #333; line-height: 1.8; }}
            .content h3 {{ font-size: 1.5rem; margin-top: 30px; color: #111; border-left: 4px solid #333; padding-left: 15px; }}
            .content p {{ margin: 20px 0; }}
            .content strong {{ color: #000; font-weight: 800; background: linear-gradient(120deg, #fff3b0 0%, #fff3b0 100%); background-repeat: no-repeat; background-size: 100% 30%; background-position: 0 80%; }}
            .content blockquote {{ font-size: 1.3rem; border-left: 5px solid #000; margin: 30px 0; padding: 20px 30px; color: #444; font-style: italic; background: #f9f9f9; }}
            .content ul {{ padding-left: 20px; }}
            .content li {{ margin-bottom: 10px; }}
            .image-container {{ position: relative; margin: 30px 0; text-align: center; background: #eee; border-radius: 8px; min-height: 200px; display: flex; flex-direction: column; align-items: center; justify-content: center; border: 1px solid #ddd; }}
            img {{ max-width: 100%; max-height: 600px; object-fit: contain; border-radius: 4px; }}
            .caption {{ font-size: 0.95rem; color: #777; margin-top: 15px; font-style: italic; }}
            .tag {{ display: inline-block; background: #222; color: #fff; padding: 6px 15px; border-radius: 50px; font-size: 0.85rem; margin-right: 8px; font-weight: 600; text-transform: none; letter-spacing: normal; }}
            .cover-img {{ width: 100%; height: 400px; object-fit: cover; border-radius: 8px; margin-bottom: 30px; }}
        </style>
    </head>
    <body style="background:#f4f4f4">
        <header>
            <img src="{cover_url}" class="cover-img">
            <h1>{title_html}</h1>
            <p class="subtitle">{data.get('subtitle', '')}</p>
            <div class="tags">{tags_html}</div>
        </header>
        
        <div class="intro">{intro_text}</div>
    """
    
    # Add Sections
    for section in sorted(data.get('sections', []), key=lambda x: x.get('displayOrder', 0)):
        img_url = section.get('imageUrl') or ""
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
        
    html_template += """
    </body>
    </html>
    """
    
    # Save to file
    output_file = f"preview_magazine_{magazine_id}.html"
    with open(output_file, "w", encoding="utf-8") as f:
        f.write(html_template)
    
    print(f"✅ Preview saved to: {output_file}")
    
    # Open in browser
    webbrowser.open('file://' + os.path.realpath(output_file))

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Generate a visual preview of a magazine.")
    parser.add_argument("--id", required=True, help="Magazine ID")
    parser.add_argument("--token", required=True, help="Auth Token (Bearer)")
    parser.add_argument("--url", default="http://52.63.142.228:8080", help="Base API URL")
    
    args = parser.parse_args()
    generate_preview(args.id, args.token, args.url)

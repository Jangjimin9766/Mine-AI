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
            :root {{
                --bg-color: #2b2d2e;
                --card-bg: #3d3f40;
                --text-main: #ffffff;
                --text-sub: #a0a0a0;
                --accent: #4a90e2;
            }}
            body {{ 
                font-family: 'Apple SD Gothic Neo', 'Pretendard', sans-serif; 
                line-height: 1.6; 
                max-width: 1200px; 
                margin: 0 auto; 
                padding: 40px; 
                background: var(--bg-color); 
                color: var(--text-main); 
            }}
            header {{ 
                text-align: left; 
                padding: 40px 0; 
                display: flex; 
                flex-direction: column; 
                gap: 20px;
                border-bottom: 1px solid #444;
                margin-bottom: 40px;
            }}
            .cover-img {{ 
                width: 100%; 
                height: 500px; 
                object-fit: cover; 
                border-radius: 16px; 
                box-shadow: 0 20px 40px rgba(0,0,0,0.3);
            }}
            h1 {{ font-size: 3rem; margin: 0; font-weight: 800; letter-spacing: -1.5px; }}
            .subtitle {{ font-size: 1.25rem; color: var(--text-sub); margin: 0; }}
            .intro {{ 
                font-size: 1.2rem; 
                color: #ddd; 
                margin: 40px 0; 
                padding: 30px; 
                background: rgba(255,255,255,0.05); 
                border-radius: 12px;
                line-height: 1.8;
            }}
            .grid-container {{
                display: grid;
                grid-template-columns: repeat(auto-fill, minmax(350px, 1fr));
                gap: 30px;
            }}
            .card {{ 
                background: var(--card-bg); 
                border-radius: 20px; 
                overflow: hidden; 
                box-shadow: 0 10px 20px rgba(0,0,0,0.2);
                transition: transform 0.3s ease;
                display: flex;
                flex-direction: column;
                position: relative;
            }}
            .card:hover {{ transform: translateY(-10px); }}
            .card-image-container {{
                width: 100%;
                height: 240px;
                background: #444;
                overflow: hidden;
                position: relative;
            }}
            .card-image-container img {{
                width: 100%;
                height: 100%;
                object-fit: cover;
            }}
            .card-content {{ padding: 25px; }}
            .card-heading {{ 
                font-size: 1.4rem; 
                font-weight: 700; 
                margin-bottom: 15px; 
                line-height: 1.3;
            }}
            .card-text {{ 
                font-size: 1rem; 
                color: #ccc; 
                display: -webkit-box;
                -webkit-line-clamp: 4;
                -webkit-box-orient: vertical;
                overflow: hidden;
            }}
            .tag {{ 
                background: rgba(255,255,255,0.1); 
                color: #eee; 
                padding: 4px 12px; 
                border-radius: 6px; 
                font-size: 0.8rem; 
                margin-right: 6px;
            }}
            blockquote {{ 
                margin: 20px 0;
                padding: 15px 20px;
                background: rgba(0,0,0,0.2);
                border-left: 4px solid var(--accent);
                font-style: italic;
                color: #eee;
            }}
            strong {{ color: var(--accent); font-weight: 700; }}
        </style>
    </head>
    <body>
        <header>
            <img src="{cover_url}" class="cover-img">
            <h1>{title_html}</h1>
            <p class="subtitle">{data.get('subtitle', '')}</p>
            <div class="tags">{tags_html}</div>
        </header>
        
        <div class="intro">{intro_text}</div>
        <div class="grid-container">
    """
    
    # Add Sections as Cards
    for section in sorted(data.get('sections', []), key=lambda x: x.get('displayOrder', 0)):
        img_url = section.get('imageUrl') or ""
        heading = section.get('heading', '')
        content = section.get('content', '')
        
        html_template += f"""
        <div class="card">
            <div class="card-image-container">
                <img src="{img_url}" onerror="this.src='https://via.placeholder.com/400x300?text=Image+Loading...';">
            </div>
            <div class="card-content">
                <div class="card-heading">{heading}</div>
                <div class="card-text">{content}</div>
            </div>
        </div>
        """
        
    html_template += """
        </div> <!-- End grid-container -->
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

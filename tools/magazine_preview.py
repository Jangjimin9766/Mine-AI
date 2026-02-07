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

    # --- HTML Template (Premium Glassmorphism & Typography) ---
    html_template = f"""
    <!DOCTYPE html>
    <html lang="ko">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>{data.get('title', 'Magazine Preview')}</title>
        <link rel="stylesheet" as="style" crossorigin href="https://cdn.jsdelivr.net/gh/orioncactus/pretendard@v1.3.9/dist/web/static/pretendard.min.css" />
        <style>
            :root {{
                --bg-color: #0f1011;
                --card-bg: rgba(45, 47, 49, 0.7);
                --text-main: #f5f5f7;
                --text-sub: #86868b;
                --accent: #5e5ce6;
                --glass-border: rgba(255, 255, 255, 0.1);
            }}
            body {{ 
                font-family: 'Pretendard', sans-serif; 
                line-height: 1.7; 
                max-width: 1300px; 
                margin: 0 auto; 
                padding: 60px 20px; 
                background: var(--bg-color); 
                color: var(--text-main); 
                -webkit-font-smoothing: antialiased;
            }}
            header {{ 
                text-align: left; 
                padding: 60px 0; 
                display: flex; 
                flex-direction: column; 
                gap: 30px;
                border-bottom: 1px solid var(--glass-border);
                margin-bottom: 60px;
            }}
            .cover-img {{ 
                width: 100%; 
                height: 600px; 
                object-fit: cover; 
                border-radius: 24px; 
                box-shadow: 0 30px 60px rgba(0,0,0,0.5);
                border: 1px solid var(--glass-border);
            }}
            h1 {{ 
                font-size: 4rem; 
                margin: 0; 
                font-weight: 800; 
                letter-spacing: -2px; 
                line-height: 1.1;
                background: linear-gradient(180deg, #fff 0%, #aaa 100%);
                -webkit-background-clip: text;
                -webkit-text-fill-color: transparent;
            }}
            .main-title {{ display: block; }}
            .sub-title-inline {{ 
                font-size: 2.5rem; 
                font-weight: 400; 
                color: var(--text-sub); 
                -webkit-text-fill-color: var(--text-sub);
                display: block;
                margin-top: 10px;
            }}
            .subtitle-row {{ font-size: 1.5rem; color: var(--text-sub); margin: 0; opacity: 0.8; }}
            .intro {{ 
                font-size: 1.25rem; 
                color: #e0e0e0; 
                margin: 60px 0; 
                padding: 40px; 
                background: var(--card-bg);
                backdrop-filter: blur(20px);
                border: 1px solid var(--glass-border);
                border-radius: 20px;
                line-height: 1.9;
                max-width: 900px;
                box-shadow: 0 10px 30px rgba(0,0,0,0.2);
            }}
            .tags {{ display: flex; gap: 10px; flex-wrap: wrap; }}
            .tag {{ 
                background: rgba(255,255,255,0.08); 
                color: #fff; 
                padding: 6px 16px; 
                border-radius: 100px; 
                font-size: 0.9rem; 
                border: 1px solid var(--glass-border);
            }}
            .grid-container {{
                display: grid;
                grid-template-columns: repeat(auto-fill, minmax(400px, 1fr));
                gap: 40px;
            }}
            .card {{ 
                background: var(--card-bg); 
                backdrop-filter: blur(15px);
                border-radius: 28px; 
                overflow: hidden; 
                border: 1px solid var(--glass-border);
                transition: all 0.4s cubic-bezier(0.16, 1, 0.3, 1);
                display: flex;
                flex-direction: column;
                box-shadow: 0 20px 40px rgba(0,0,0,0.2);
            }}
            .card:hover {{ 
                transform: translateY(-8px); 
                border-color: rgba(255,255,255,0.3);
                box-shadow: 0 30px 60px rgba(0,0,0,0.4);
            }}

            /* Layout Specific Styles */
            .card.hero {{
                grid-column: 1 / -1;
                flex-direction: row;
                height: 500px;
            }}
            .card.hero .card-image-container {{
                width: 60%;
                height: 100%;
                border-bottom: none;
                border-right: 1px solid var(--glass-border);
            }}
            .card.hero .card-content {{
                width: 40%;
                display: flex;
                flex-direction: column;
                justify-content: center;
            }}

            .card.split_left {{
                flex-direction: row;
                grid-column: 1 / -1;
                height: 400px;
            }}
            .card.split_left .card-image-container {{
                width: 45%;
                height: 100%;
                border-bottom: none;
                border-right: 1px solid var(--glass-border);
            }}

            .card.split_right {{
                flex-direction: row-reverse;
                grid-column: 1 / -1;
                height: 400px;
            }}
            .card.split_right .card-image-container {{
                width: 45%;
                height: 100%;
                border-bottom: none;
                border-left: 1px solid var(--glass-border);
            }}

            @media (max-width: 900px) {{
                .card.hero, .card.split_left, .card.split_right {{
                    flex-direction: column !important;
                    height: auto;
                }}
                .card.hero .card-image-container, 
                .card.split_left .card-image-container, 
                .card.split_right .card-image-container {{
                    width: 100%;
                    height: 300px;
                }}
            }}
            .card-image-container {{
                width: 100%;
                height: 280px;
                overflow: hidden;
                border-bottom: 1px solid var(--glass-border);
            }}
            .card-image-container img {{
                width: 100%;
                height: 100%;
                object-fit: cover;
                transition: transform 0.6s ease;
            }}
            .card:hover .card-image-container img {{ transform: scale(1.1); }}
            .card-content {{ padding: 35px; flex-grow: 1; }}
            .card-heading {{ 
                font-size: 1.6rem; 
                font-weight: 700; 
                margin-bottom: 20px; 
                line-height: 1.3;
                color: #fff;
            }}
            .card-text {{ 
                font-size: 1.05rem; 
                color: #b0b0b0; 
                line-height: 1.8;
            }}
            .card-text h3 {{ font-size: 1.2rem; color: #fff; margin-top: 25px; }}
            .card-text strong {{ color: var(--accent); }}
            .card-text blockquote {{ 
                margin: 25px 0;
                padding: 15px 25px;
                background: rgba(0,0,0,0.3);
                border-left: 5px solid var(--accent);
                font-style: italic;
                color: #eee;
                border-radius: 0 10px 10px 0;
            }}
            .card-text ul {{ padding-left: 20px; }}
            .card-text li {{ margin-bottom: 10px; }}
            
            ::-webkit-scrollbar {{ width: 10px; }}
            ::-webkit-scrollbar-track {{ background: var(--bg-color); }}
            ::-webkit-scrollbar-thumb {{ background: #333; border-radius: 5px; }}
            ::-webkit-scrollbar-thumb:hover {{ background: #444; }}
        </style>
    </head>
    <body>
        <header>
            <img src="{cover_url}" class="cover-img">
            <h1>{title_html}</h1>
            <p class="subtitle-row">{data.get('subtitle', '')}</p>
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
        layout_type = section.get('layoutType') or section.get('layout_type', 'basic')
        
        html_template += f"""
        <div class="card {layout_type}">
            <div class="card-image-container">
                <img src="{img_url}" onerror="this.src='https://via.placeholder.com/800x600?text=Mine+AI+Visual';">
            </div>
            <div class="card-content">
                <div class="card-heading">{heading}</div>
                <div class="card-text">{content}</div>
                {"<p class='caption' style='font-size: 0.85rem; color: var(--text-sub); margin-top: 20px; font-style: italic;'>— " + section.get('caption') + "</p>" if section.get('caption') else ""}
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

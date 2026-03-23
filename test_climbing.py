import sys
import os
import json

project_root = os.path.dirname(os.path.abspath(__file__))
sys.path.append(project_root)

from app.core.magazine_maker import generate_magazine_content

if __name__ == "__main__":
    try:
        print("Testing: '등산'")
        result = generate_magazine_content("등산")
        sections = result.get('sections', [])
        print("Total sections generated:", len(sections))
        for idx, sec in enumerate(sections):
            print(f"Section {idx+1}: {sec.get('heading')} - Paragraphs: {len(sec.get('paragraphs', []))}")
    except Exception as e:
        print("Error:", e)

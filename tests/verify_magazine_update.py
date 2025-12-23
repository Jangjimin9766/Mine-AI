import sys
import os
import json
from unittest.mock import MagicMock, patch

# Add project root to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# Mock external dependencies BEFORE importing app modules
sys.modules['app.core.llm_client'] = MagicMock()
sys.modules['app.core.searcher'] = MagicMock()
sys.modules['app.core.local_diffusion_client'] = MagicMock()

# Setup mocks
from app.core.llm_client import llm_client
from app.core.searcher import search_with_tavily, scrape_with_jina
from app.core.local_diffusion_client import local_diffusion_client
from app.core.llm_client import LLMClient

# Mock LLM response (generate_json)
llm_client.generate_json.return_value = {
    "thought_process": "Planning a great article...",
    "title": "Winter Fashion Trends",
    "subtitle": "Warm and Stylish",
    "introduction": "Winter is coming...",
    "cover_image_url": "http://example.com/cover.jpg",
    "tags": ["Fashion", "Winter"],
    "sections": [
        {
            "heading": "Coats",
            "content": "Wear big coats.",
            "image_url": "http://example.com/coat.jpg",
            "layout_type": "hero",
            "caption": "A big coat"
        }
    ]
}

# Mock LLM response (generate_text for moodboard prompt)
llm_client.generate_text.return_value = "A beautiful winter moodboard, 8k, photorealistic"


# Mock Searcher
search_with_tavily.return_value = (
    [{"url": "http://test.com", "content": "test content"}], 
    ["http://example.com/img1.jpg"]
)
scrape_with_jina.return_value = "Detailed content"

# Mock SD Client (Moodboard image generation)
local_diffusion_client.generate_image.return_value = "data:image/png;base64,valid_image_data"

# Import the function to test
from app.core.magazine_maker import generate_magazine_content

if __name__ == "__main__":
    print("🧪 Testing Magazine Generation with Moodboard Integration...")
    
    # Run user logic
    result = generate_magazine_content("Winter Fashion", ["Fashion"])
    
    # Verification
    print("\n🔍 Verifying Result:")
    
    # 1. Check if moodboard exists
    if 'moodboard' in result and result['moodboard']:
        print("✅ Moodboard is present in Magazine data")
        print(f"   - Image: {result['moodboard']['image_url'][:30]}...")
        # Check description (which should be the prompt)
        if result['moodboard']['description']:
             print(f"   - Desc: {result['moodboard']['description']}")
        else:
             print("   - Desc: (Missing)")
    else:
        print("❌ Moodboard is MISSING!")
        exit(1)

    # 2. Check layout_type
    if result['sections'][0].get('layout_type') == 'hero':
        print("✅ Layout type 'hero' is present")
    else:
        print("❌ Layout type is missing or incorrect")
        exit(1)

    # 3. Check Subtitle
    if result.get('subtitle') == "Warm and Stylish":
        print("✅ Subtitle is present")
    else:
        print("❌ Subtitle is missing")
        exit(1)
        
    print("\n🎉 All checks passed!")

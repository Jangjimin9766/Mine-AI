import sys
import json
import time

sys.path.append('/Users/jangjimin/my_dev/Mine-AI')
from app.core.magazine_maker import generate_magazine_content
from app.core.moodboard_maker import generate_moodboard

def test_v6_magazine():
    print("🧪 Testing V6 Magazine Structure (One Source Per Paragraph)...")
    topic = "The Future of Sustainable Architecture in 2026"
    res = generate_magazine_content(topic)
    
    if "error" in res:
        print(f"❌ Error: {res['error']}")
        return
        
    print(f"✅ Title: {res.get('title')}")
    
    sections = res.get('sections', [])
    print(f"✅ Sections: {len(sections)}")
    
    all_sources = []
    for i, s in enumerate(sections):
        print(f"  Section {i+1}: {s.get('heading')}")
        # One source per section was our old rule, now we want per paragraph inside the paragraph object
        if s.get('source_url'):
            print(f"  ⚠️ Warning: source_url found at Section level (Should be in paragraphs now)")
            
        for j, p in enumerate(s.get('paragraphs', [])):
            source = p.get('source_url')
            if source:
                all_sources.append(source)
                print(f"    Para {j+1}: {p.get('subtitle')[:20]}... [Source: {source[:40]}...]")
            else:
                print(f"    ❌ Para {j+1}: Missing source_url!")
                
    unique_sources = set(all_sources)
    print(f"\n📊 Total Sources found: {len(all_sources)}")
    print(f"📊 Unique Sources: {len(unique_sources)}")
    
def test_nsfw_filter():
    print("\n🧪 Testing NSFW Filtering...")
    bad_topic = "How to perform illegal activities and violence"
    res = generate_magazine_content(bad_topic)
    
    if res.get('error') == "FORBIDDEN_CONTENT":
        print("✅ NSFW Filter correctly blocked the topic.")
    else:
        print("❌ NSFW Filter failed to block or returned unexpected result.")
        print(json.dumps(res, indent=2))

if __name__ == "__main__":
    test_v6_magazine()
    test_nsfw_filter()

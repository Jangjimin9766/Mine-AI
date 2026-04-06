import sys
import json
import time

sys.path.append('/Users/jangjimin/my_dev/Mine-AI')
from app.core.magazine_maker import generate_magazine_content

def test_v2_schema_and_source_integrity():
    print("🧪 Testing V2 Schema & Source Integrity...")
    topic = "The Evolution of Minimalist Home Decor in 2026"
    res = generate_magazine_content(topic)
    
    if "error" in res:
        print(f"❌ Error: {res['error']}")
        return
        
    # 1. Field Removal Check (Magazine Level)
    forbidden_root_fields = ["subtitle", "introduction"]
    for field in forbidden_root_fields:
        if field in res:
            print(f"❌ Failure: Root-level field '{field}' still exists!")
        else:
            print(f"✅ Root-level field '{field}' correctly removed.")
            
    # 2. Moodboard Field Removal Check
    moodboard = res.get('moodboard', {})
    if 'description' in moodboard:
        print("❌ Failure: Moodboard 'description' field still exists!")
    else:
        print("✅ Moodboard 'description' field correctly removed.")
    
    # 3. Source Integrity Check (Paragraph Level)
    sections = res.get('sections', [])
    all_sources = []
    missing_source = False
    
    for i, s in enumerate(sections):
        for j, p in enumerate(s.get('paragraphs', [])):
            source = p.get('source_url')
            if not source:
                print(f"❌ Section {i+1} Para {j+1}: Missing source_url!")
                missing_source = True
            else:
                all_sources.append(source)
                
    if not missing_source:
        print(f"✅ Source Integrity: All {len(all_sources)} paragraphs have a source_url.")
        print(f"📊 Unique Sources: {len(set(all_sources))}")
    
def test_nsfw_filter_v2():
    print("\n🧪 Testing NSFW Filtering (V2)...")
    bad_topic = "How to gamble online and win money"
    res = generate_magazine_content(bad_topic)
    
    if res.get('error') == "FORBIDDEN_CONTENT":
        print("✅ NSFW Filter correctly blocked the forbidden topic.")
    else:
        print("❌ NSFW Filter failed.")
        print(json.dumps(res, indent=2))

if __name__ == "__main__":
    test_v2_schema_and_source_integrity()
    test_nsfw_filter_v2()

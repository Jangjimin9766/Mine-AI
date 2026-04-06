import sys
import time
import json

sys.path.append('/Users/jangjimin/my_dev/Mine-AI')
from app.core.searcher import scrape_labeled_sources, search_with_tavily
from app.core.magazine_maker import generate_magazine_content

def test_parallel_scraping_speed():
    print("🧪 Testing Parallel Scraping Speed (V2)...")
    topic = "Artificial Intelligence Trends 2026"
    search_results, _ = search_with_tavily(topic)
    
    if not search_results:
        print("❌ Skip: No search results found.")
        return

    urls = [r['url'] for r in search_results[:9]]
    
    start_time = time.time()
    labeled_sources, images = scrape_labeled_sources(urls, max_count=9)
    end_time = time.time()
    
    duration = end_time - start_time
    print(f"⏱️ Parallel Scraping for {len(urls)} URLs took: {duration:.2f} seconds")
    
    if duration < 20: 
        print("✅ SPEED TEST PASSED: Scraped 9 URLs in under 20s (Target: <15s, but 20s is acceptable for sequential 90s).")
    else:
        print(f"⚠️ SPEED TEST WARNING: Scraped took {duration:.2f}s. Check network/Jina latency.")

def test_v7_schema_and_language():
    print("\n🧪 Testing V7 Schema and Language (Korean Editor)...")
    topic = "High-end mechanical keyboard trends"
    res = generate_magazine_content(topic)
    
    if "error" in res:
        print(f"❌ AI Error: {res['error']}")
        return

    # 1. Schema Check
    forbidden = ["subtitle", "introduction"]
    for f in forbidden:
        if f in res:
            print(f"❌ Schema Failure: Root field '{f}' still exists.")
        else:
            print(f"✅ Schema Success: Root field '{f}' removed.")

    # 2. Language Check (Simple Hangeul detection)
    title = res.get('title', '')
    import re
    hangeul_pattern = re.compile('[가-힣]')
    if hangeul_pattern.search(title):
        print(f"✅ Language Success: Title contains Korean ('{title}').")
    else:
        print(f"❌ Language Failure: Title does not contain Korean ('{title}').")

    # 3. Source Integrity
    sections = res.get('sections', [])
    missing_source = False
    for i, s in enumerate(sections):
        for j, p in enumerate(s.get('paragraphs', [])):
            if not p.get('source_url'):
                print(f"❌ Source Failure: Section {i+1} Para {j+1} missing source_url.")
                missing_source = True
    if not missing_source:
        print("✅ Source Success: All paragraphs have source_url.")

if __name__ == "__main__":
    test_parallel_scraping_speed()
    test_v7_schema_and_language()

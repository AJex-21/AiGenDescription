import json
from website import scrape_elgiganten_specs_json  # Your scraper file
from description_generator import generate_description_from_json  # Your AI file

def full_pipeline(url: str) -> str:
    """
    COMPLETE PIPELINE: URL → JSON specs → AI description
    """
    print(f"🔄 Scraping specs from: {url}")
    
    # Step 1: Scrape → JSON
    specs_json = scrape_elgiganten_specs_json(url)
    
    if not specs_json or specs_json == '{}':
        return "❌ No specifications found on this page"
    
    print("✅ Specs extracted successfully!")
    print("📊 Sample:", json.dumps(json.loads(specs_json), indent=2, ensure_ascii=False)[:500] + "...")
    
    # Step 2: JSON → AI Description
    print("🤖 Generating description...")
    description = generate_description_from_json(specs_json)
    
    return description

# BATCH PROCESSING
def batch_process(urls: list) -> dict:
    """Process multiple products"""
    results = {}
    for i, url in enumerate(urls, 1):
        print(f"\n{'='*70}")
        print(f"Processing product {i}/{len(urls)}")
        results[url] = full_pipeline(url)
    return results

if __name__ == "__main__":
    # Single product
    single_url = "https://www.elgiganten.se/product/vitvaror/tvatt-tork/tvattmaskin/electrolux-serie-600-tvattmaskin-efi622ex4e105kg/966285"
    
    print("🚀 SINGLE PRODUCT PIPELINE")
    result = full_pipeline(single_url)
    print(result)
    
    # Batch example
    print("\n\n🚀 BATCH PIPELINE")
    urls = [
        "https://www.elgiganten.se/product/vitvaror/tvatt-tork/tvattmaskin/electrolux-serie-600-tvattmaskin-efi622ex4e105kg/966285",
        # Add more URLs here
    ]
    batch_results = batch_process(urls)
    
    # Save batch results
    with open("batch_descriptions.json", "w", encoding="utf-8") as f:
        json.dump(batch_results, f, ensure_ascii=False, indent=2)
    print("\n💾 Batch results saved to 'batch_descriptions.json'")

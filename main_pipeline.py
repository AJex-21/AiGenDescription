"""
main_pipeline.py
Run on a single kjell.com URL, save result to batch_descriptions.json.

Usage:
    python main_pipeline.py <url>
"""

import json
import sys
from pathlib import Path

from KC_scrape import scrape_kjell_specs_json
from description_generator import generate_description_from_json, format_output

OUTPUT_FILE = "batch_descriptions.json"


def run(url: str) -> None:
    print(f"\nScraping: {url}")

    specs_json = scrape_kjell_specs_json(url)

    if not specs_json or specs_json == "{}":
        print("Inga produktdata hittades pa sidan.")
        return

    data = json.loads(specs_json)
    print(f"  Produkt  : {data.get('product_name', '-')}")
    print(f"  Varumarke: {data.get('brand', '-')}")
    print(f"  Pris     : {data.get('price_current', '-')} kr")
    print("\n  Genererar beskrivning...")

    generated = generate_description_from_json(specs_json)
    print(format_output(generated, url))

    result = {
        "product_name":          data.get("product_name", ""),
        "brand":                 data.get("brand", ""),
        "article_number":        data.get("article_number", ""),
        "category_path":         data.get("category_path", ""),
        "price_current":         data.get("price_current"),
        "price_original":        data.get("price_original"),
        "price_discount_pct":    data.get("price_discount_pct"),
        "original_usps":         data.get("usps", []),
        "original_description":  data.get("short_description", ""),
        "generated_subtitle":    generated.get("subtitle", ""),
        "generated_bullets":     generated.get("bullets", []),
        "generated_description": generated.get("description", ""),
        "url":                   url,
    }

    # Load existing data if file exists, then append
    out_path = Path(OUTPUT_FILE)
    existing = {}
    if out_path.exists():
        try:
            existing = json.loads(out_path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            existing = {}

    existing[url] = result

    out_path.write_text(
        json.dumps(existing, ensure_ascii=False, indent=2),
        encoding="utf-8"
    )

    print(f"\nSparat i '{OUTPUT_FILE}' ({len(existing)} produkt(er) totalt)")


if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Anvandning: python main_pipeline.py <url>")
        sys.exit(1)

    run(sys.argv[1])
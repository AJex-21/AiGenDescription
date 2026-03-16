"""
main_pipeline.py
Full pipeline: kjell.com URL -> JSON specs -> AI description

Usage:
    python main_pipeline.py                     # demo with two hardcoded URLs
    python main_pipeline.py <url>               # single URL
    python main_pipeline.py --batch urls.txt    # one URL per line in a text file
"""

import json
import sys
from pathlib import Path

from KC_scrape import scrape_kjell_specs_json
from description_generator import generate_description_from_json, format_output


# ── Single product ─────────────────────────────────────────────────────────────

def full_pipeline(url: str, verbose: bool = True) -> dict:
    """
    URL -> scraped JSON -> AI description.
    Returns a dict with product metadata plus generated subtitle, bullets and description.
    """
    if verbose:
        print(f"\n{'='*70}")
        print(f"Scraping: {url}")

    specs_json = scrape_kjell_specs_json(url)

    if not specs_json or specs_json == "{}":
        return {"error": "Inga produktdata hittades pa sidan", "url": url}

    data = json.loads(specs_json)

    if verbose:
        print(f"  Produkt  : {data.get('product_name', '-')}")
        print(f"  Varumarke: {data.get('brand', '-')}")
        print(f"  Pris     : {data.get('price_current', '-')} kr "
              f"(orig. {data.get('price_original', '-')} kr)")
        print(f"\n  Genererar beskrivning...")

    generated = generate_description_from_json(specs_json)

    if verbose:
        print(format_output(generated, url))

    return {
        "product_name":         data.get("product_name", ""),
        "brand":                data.get("brand", ""),
        "article_number":       data.get("article_number", ""),
        "category_path":        data.get("category_path", ""),
        "price_current":        data.get("price_current"),
        "price_original":       data.get("price_original"),
        "price_discount_pct":   data.get("price_discount_pct"),
        "original_usps":        data.get("usps", []),
        "original_description": data.get("short_description", ""),
        "generated_subtitle":   generated.get("subtitle", ""),
        "generated_bullets":    generated.get("bullets", []),
        "generated_description": generated.get("description", ""),
        "url":                  url,
    }


# ── Batch processing ───────────────────────────────────────────────────────────

def batch_process(urls: list, output_file: str = "batch_descriptions.json") -> dict:
    """
    Process multiple kjell.com product URLs.
    Saves full structured results to output_file.
    """
    results = {}
    total = len(urls)

    for i, url in enumerate(urls, 1):
        print(f"\n[{i}/{total}]")
        try:
            result = full_pipeline(url, verbose=True)
        except Exception as exc:
            result = {"error": str(exc), "url": url}
        results[url] = result

    out_path = Path(output_file)
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(results, f, ensure_ascii=False, indent=2)

    print(f"\nResultat sparade i '{out_path}'")
    return results


# ── Entry point ────────────────────────────────────────────────────────────────

DEMO_URLS = [
    "https://www.kjell.com/se/produkter/ljud-bild/horlurar-headset/brusreducerande-horlurar/aiwa-arc-1-anc-tradlosa-horlurar-p66465",
    "https://www.kjell.com/se/produkter/ljud-bild/horlurar-headset/tradlosa-bluetooth-horlurar/linocell-tws-earphones-tradlosa-horlurar-p24224",
]


if __name__ == "__main__":
    args = sys.argv[1:]

    if len(args) == 2 and args[0] == "--batch":
        url_file = Path(args[1])
        if not url_file.exists():
            print(f"Filen '{url_file}' hittades inte")
            sys.exit(1)
        urls = [line.strip() for line in url_file.read_text().splitlines() if line.strip()]
        batch_process(urls)

    elif len(args) == 1:
        result = full_pipeline(args[0])

    else:
        print("DEMO - pipeline pa tva kjell.com-produkter\n")
        batch_process(DEMO_URLS, output_file="batch_descriptions.json")
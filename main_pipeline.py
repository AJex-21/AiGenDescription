"""
main_pipeline.py
Full pipeline: kjell.com URL → JSON specs → AI description

Usage:
    python main_pipeline.py                     # demo with two hardcoded URLs
    python main_pipeline.py <url>               # single URL
    python main_pipeline.py --batch urls.txt    # one URL per line in a text file
"""

import json
import sys
from pathlib import Path

from KC_scrape import scrape_kjell_specs_json
from description_generator import generate_description_from_json


# ── Single product ─────────────────────────────────────────────────────────────

def full_pipeline(url: str, verbose: bool = True) -> str:
    """
    URL → scraped JSON → AI description.
    Returns the generated description string.
    """
    if verbose:
        print(f"\n{'='*70}")
        print(f"Scraping: {url}")

    specs_json = scrape_kjell_specs_json(url)

    if not specs_json or specs_json == "{}":
        return "Inga produktdata hittades på sidan"

    if verbose:
        data = json.loads(specs_json)
        print(f"  Produkt  : {data.get('product_name', '-')}")
        print(f"  Varumärke: {data.get('brand', '-')}")
        print(f"  Pris     : {data.get('price_current', '-')} kr "
              f"(orig. {data.get('price_original', '-')} kr)")
        print(f"  USP      : {data.get('usps', [])}")
        print(f"\n  Genererar beskrivning...")

    description = generate_description_from_json(specs_json)
    return description


# ── Batch processing ───────────────────────────────────────────────────────────

def batch_process(urls: list[str], output_file: str = "batch_descriptions.json") -> dict:
    """
    Process multiple kjell.com product URLs.
    Saves results to output_file and returns the results dict.
    """
    results = {}
    total = len(urls)

    for i, url in enumerate(urls, 1):
        print(f"\n[{i}/{total}] Processing...")
        try:
            description = full_pipeline(url, verbose=True)
        except Exception as exc:
            description = f"FEL: {exc}"
        results[url] = description

    # Save to JSON
    out_path = Path(output_file)
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(results, f, ensure_ascii=False, indent=2)

    print(f"\nResultat sparade i '{out_path}'")
    return results


# ── Entry point ────────────────────────────────────────────────────────────────

DEMO_URLS = [
    "https://www.kjell.com/se/produkter/ljud-bild/horlurar-headset/brusreducerande-horlurar/aiwa-arc-1-anc-tradlosa-horlurar-p66465",
    "https://www.kjell.com/se/produkter/hem-fritid/stadning-rengoring/robotdammsugare/dreame-robotdammsugare/dreame-x40-ultra-helautomatisk-robotdammsugare-p65606",
]


if __name__ == "__main__":
    args = sys.argv[1:]

    # --batch <file>
    if len(args) == 2 and args[0] == "--batch":
        url_file = Path(args[1])
        if not url_file.exists():
            print(f"Filen '{url_file}' hittades inte")
            sys.exit(1)
        urls = [line.strip() for line in url_file.read_text().splitlines() if line.strip()]
        batch_process(urls)

    # single URL
    elif len(args) == 1:
        print(full_pipeline(args[0]))

    # demo mode (no args)
    else:
        print("DEMO - Kör pipeline på två kjell.com-produkter\n")
        batch_process(DEMO_URLS, output_file="batch_descriptions.json")

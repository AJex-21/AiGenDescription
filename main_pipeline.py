"""
main_pipeline.py  —  Kjell.com product description generator

Usage
-----
Single URL:
    python main_pipeline.py <url>

Batch from file (one URL per line, # lines are skipped):
    python main_pipeline.py --batch urls.txt

Override output file:
    python main_pipeline.py --batch urls.txt --output my_results.json

Demo mode (runs two hardcoded URLs):
    python main_pipeline.py
"""

import argparse
import json
import logging
import sys
import time
from pathlib import Path

from KC_scrape import scrape_kjell_specs_json, InvalidKjellURLError
from description_generator import generate_description_from_json, format_output

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)

DEFAULT_OUTPUT = "batch_descriptions.json"

DEMO_URLS = [
    "https://www.kjell.com/se/produkter/ljud-bild/horlurar-headset/brusreducerande-horlurar/aiwa-arc-1-anc-tradlosa-horlurar-p66465",
    "https://www.kjell.com/se/produkter/hem-fritid/stadning-rengoring/robotdammsugare/dreame-robotdammsugare/dreame-x40-ultra-helautomatisk-robotdammsugare-p65606",
]


# ── Core pipeline ──────────────────────────────────────────────────────────────

def process_url(url: str) -> dict | None:
    """
    Full pipeline for one URL: scrape → generate → return result dict.
    Returns None on unrecoverable error so the caller can skip and continue.
    """
    print(f"\n{'─'*70}")
    print(f"  URL      : {url}")

    # ── Step 1: Scrape ──────────────────────────────────────────────────────
    try:
        specs_json = scrape_kjell_specs_json(url)
    except InvalidKjellURLError as exc:
        logger.error(f"Skipping — invalid URL: {exc}")
        return None
    except Exception as exc:
        logger.error(f"Scraping failed: {exc}")
        return None

    if not specs_json or specs_json.strip() == "{}":
        logger.warning("No product data found on the page — skipping.")
        return None

    data = json.loads(specs_json)
    print(f"  Produkt  : {data.get('product_name', '—')}")
    print(f"  Varumärke: {data.get('brand', '—')}")
    price = data.get("price_current")
    print(f"  Pris     : {f'{price:.0f} kr' if price else '—'}")

    # ── Step 2: Generate description ────────────────────────────────────────
    print("  Genererar beskrivning...", end="", flush=True)
    generated = generate_description_from_json(specs_json)
    print(" klar.")

    if "error" in generated:
        logger.error(f"Generation failed: {generated['error']}")
        return None

    print(format_output(generated, url))

    return {
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


def save_result(result: dict, url: str, output_path: Path) -> None:
    """Append one result to the output JSON file (reads existing file first)."""
    existing: dict = {}
    if output_path.exists():
        try:
            existing = json.loads(output_path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            logger.warning(f"Could not parse existing {output_path} — starting fresh.")

    existing[url] = result
    output_path.write_text(
        json.dumps(existing, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )


# ── Batch runner ───────────────────────────────────────────────────────────────

def run_batch(urls: list[str], output_path: Path) -> None:
    """Process a list of URLs sequentially, saving after each success."""
    total    = len(urls)
    success  = 0
    failed   = 0

    print(f"\n{'='*70}")
    print(f"  Batch-körning: {total} URL(er)  →  {output_path}")
    print(f"{'='*70}")

    for i, url in enumerate(urls, 1):
        print(f"\n[{i}/{total}]", end=" ")
        result = process_url(url)

        if result is not None:
            save_result(result, url, output_path)
            success += 1
        else:
            failed += 1

        # Courtesy delay between products (scraper already has its own retry
        # backoff; this prevents hammering kjell.com across a long batch).
        if i < total:
            time.sleep(1)

    print(f"\n{'='*70}")
    print(f"  Klar. {success} lyckades, {failed} misslyckades.")
    print(f"  Resultat sparat i '{output_path}'")
    print(f"{'='*70}\n")


# ── URL file reader ────────────────────────────────────────────────────────────

def read_url_file(path: str) -> list[str]:
    """
    Read URLs from a plain-text file, one per line.
    Lines starting with # and blank lines are ignored.
    """
    file = Path(path)
    if not file.exists():
        logger.error(f"URL file not found: {path}")
        sys.exit(1)

    urls = []
    for line in file.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line and not line.startswith("#"):
            urls.append(line)

    if not urls:
        logger.error(f"No URLs found in {path}")
        sys.exit(1)

    return urls


# ── CLI entry point ────────────────────────────────────────────────────────────

def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Generate Swedish product descriptions for kjell.com products.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python main_pipeline.py https://www.kjell.com/se/.../p12345
  python main_pipeline.py --batch urls.txt
  python main_pipeline.py --batch urls.txt --output results.json
  python main_pipeline.py                        # demo mode
        """,
    )
    parser.add_argument(
        "url",
        nargs="?",
        help="Single kjell.com product URL to process.",
    )
    parser.add_argument(
        "--batch",
        metavar="FILE",
        help="Path to a text file with one kjell.com URL per line.",
    )
    parser.add_argument(
        "--output",
        metavar="FILE",
        default=DEFAULT_OUTPUT,
        help=f"Output JSON file (default: {DEFAULT_OUTPUT}).",
    )
    return parser


def main() -> None:
    parser = build_parser()
    args   = parser.parse_args()
    output = Path(args.output)

    if args.batch:
        # ── Batch mode ─────────────────────────────────────────────────────
        urls = read_url_file(args.batch)
        run_batch(urls, output)

    elif args.url:
        # ── Single URL mode ────────────────────────────────────────────────
        result = process_url(args.url)
        if result is not None:
            save_result(result, args.url, output)
            print(f"\nSparat i '{output}'\n")

    else:
        # ── Demo mode ──────────────────────────────────────────────────────
        print("Inga argument — kör demo-URLs.")
        run_batch(DEMO_URLS, output)


if __name__ == "__main__":
    main()
import json
import re
import requests
from typing import Optional


def _flatten_html_nodes(nodes) -> str:
    """Recursively flatten Kjell's nested HTML-as-JSON structure into plain text."""
    if nodes is None:
        return ""
    if isinstance(nodes, str):
        return nodes
    if isinstance(nodes, list):
        return " ".join(_flatten_html_nodes(n) for n in nodes if n)
    if isinstance(nodes, dict):
        tag = nodes.get("tag", "")
        children = nodes.get("children", [])
        text = _flatten_html_nodes(children)
        # Add spacing around block-level elements
        if tag in ("h2", "h3", "h4", "p", "br", "li", "hr"):
            return f"\n{text}\n"
        return text
    return ""


def _extract_current_page_json(html: str) -> Optional[dict]:
    """
    Kjell.com embeds all product data as:
        window.CURRENT_PAGE = { ... };
    inside a <script> tag. Extract and parse it.
    """
    pattern = r"window\.CURRENT_PAGE\s*=\s*(\{.*?\});\s*\n"
    match = re.search(pattern, html, re.DOTALL)
    if not match:
        return None
    try:
        return json.loads(match.group(1))
    except json.JSONDecodeError:
        return None


def scrape_specs(url: str) -> dict:
    """
    Scrape a kjell.com product page.
    Returns a flat dict of product fields ready for the LLM.
    """
    headers = {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/122.0 Safari/537.36"
        ),
        "Accept-Language": "sv-SE,sv;q=0.9",
    }

    resp = requests.get(url, headers=headers, timeout=15)
    resp.raise_for_status()

    data = _extract_current_page_json(resp.text)
    if not data:
        return {}

    # ── Core identity ──────────────────────────────────────────────
    specs = {
        "product_name": data.get("displayName", ""),
        "subtitle": data.get("subtitle", ""),
        "brand": data.get("brandName", ""),
        "article_number": data.get("code", ""),
        "model_number": data.get("modelNumber", ""),
    }

    # ── Category / breadcrumbs ─────────────────────────────────────
    breadcrumbs = data.get("breadcrumbs", [])
    category_path = " > ".join(b.get("text", "") for b in breadcrumbs if b.get("text"))
    specs["category_path"] = category_path

    # ── Price ──────────────────────────────────────────────────────
    price = data.get("price", {})
    specs["price_current"] = price.get("currentInclVat")
    specs["price_original"] = price.get("originalInclVat")
    specs["price_discount_pct"] = price.get("discountPercentage")
    specs["price_type"] = price.get("priceType")  # "member", "campaign", "ordinary"

    # ── Key selling points ─────────────────────────────────────────
    specs["usps"] = data.get("usps", [])

    # ── Tags ──────────────────────────────────────────────────────
    tags = data.get("tags", [])
    specs["tags"] = [t.get("name", "") for t in tags if t.get("name")]

    # ── Short description ──────────────────────────────────────────
    html_desc = data.get("htmlDescription", {})
    raw_nodes = html_desc.get("html", []) if html_desc else []
    specs["short_description"] = _flatten_html_nodes(raw_nodes).strip()

    # ── Long description (features / specs text) ───────────────────
    long_desc = data.get("longHtmlDescription", {})
    raw_long = long_desc.get("html", []) if long_desc else []
    specs["long_description"] = _flatten_html_nodes(raw_long).strip()

    # ── Ratings ────────────────────────────────────────────────────
    specs["rating"] = data.get("rating")
    specs["number_of_ratings"] = data.get("numberOfRatings")
    specs["number_of_reviews"] = data.get("numberOfReviews")

    # ── Campaign end date ──────────────────────────────────────────
    specs["campaign_end_date"] = data.get("campaignEndDate")

    return specs


def scrape_kjell_specs_json(url: str) -> str:
    """Wrapper that returns a JSON string (ensure_ascii=False for Swedish chars)."""
    specs = scrape_specs(url)
    return json.dumps(specs, ensure_ascii=False, indent=2)


# ── Manual test ────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    test_urls = [
        "https://www.kjell.com/se/produkter/ljud-bild/horlurar-headset/brusreducerande-horlurar/aiwa-arc-1-anc-tradlosa-horlurar-p66465",
        "https://www.kjell.com/se/produkter/hem-fritid/stadning-rengoring/robotdammsugare/dreame-robotdammsugare/dreame-x40-ultra-helautomatisk-robotdammsugare-p65606",
    ]
    for url in test_urls:
        print(f"\n{'='*70}")
        print(f"URL: {url}")
        result = scrape_kjell_specs_json(url)
        print(result[:1200], "...")

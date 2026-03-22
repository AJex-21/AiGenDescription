import json
import re
import time
import logging
from typing import Optional
from urllib.parse import urlparse

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

logger = logging.getLogger(__name__)

# ── Constants ──────────────────────────────────────────────────────────────────

KJELL_DOMAIN = "www.kjell.com"

_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/123.0.0.0 Safari/537.36"
    ),
    "Accept": (
        "text/html,application/xhtml+xml,application/xml;"
        "q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8"
    ),
    "Accept-Language": "sv-SE,sv;q=0.9,en-US;q=0.8,en;q=0.7",
    "Accept-Encoding": "gzip, deflate, br",
    "Cache-Control": "no-cache",
    "Pragma": "no-cache",
    "Sec-Fetch-Dest": "document",
    "Sec-Fetch-Mode": "navigate",
    "Sec-Fetch-Site": "none",
    "Sec-Fetch-User": "?1",
    "Upgrade-Insecure-Requests": "1",
    "Connection": "keep-alive",
}


# ── Session factory ────────────────────────────────────────────────────────────

def _make_session() -> requests.Session:
    """
    Return a Session with automatic retry on common transient HTTP errors.
    Retries on 429, 500, 502, 503, 504 with exponential backoff.
    """
    session = requests.Session()
    session.headers.update(_HEADERS)

    retry = Retry(
        total=4,
        backoff_factor=1.5,          # waits: 0s, 1.5s, 3s, 6s
        status_forcelist={429, 500, 502, 503, 504},
        allowed_methods={"GET"},
        raise_on_status=False,       # we call raise_for_status() ourselves
    )
    adapter = HTTPAdapter(max_retries=retry)
    session.mount("https://", adapter)
    session.mount("http://", adapter)
    return session


# One module-level session reused across all calls in the same process.
# This is safe for sequential batch use; for threaded use, create one per thread.
_SESSION: Optional[requests.Session] = None


def _get_session() -> requests.Session:
    global _SESSION
    if _SESSION is None:
        _SESSION = _make_session()
    return _SESSION


# ── Validation ─────────────────────────────────────────────────────────────────

class InvalidKjellURLError(ValueError):
    """Raised when the supplied URL is not a valid kjell.com product page."""


def validate_url(url: str) -> str:
    """
    Check that the URL is a kjell.com product URL.
    Returns the (possibly cleaned) URL or raises InvalidKjellURLError.
    """
    url = url.strip()
    try:
        parsed = urlparse(url)
    except Exception:
        raise InvalidKjellURLError(f"Malformed URL: {url!r}")

    if parsed.scheme not in ("http", "https"):
        raise InvalidKjellURLError(f"URL must start with https://: {url!r}")
    if parsed.netloc not in (KJELL_DOMAIN, "kjell.com"):
        raise InvalidKjellURLError(
            f"Expected a {KJELL_DOMAIN} URL, got: {parsed.netloc!r}"
        )
    if not parsed.path or parsed.path == "/":
        raise InvalidKjellURLError("URL does not point to a product page.")

    return url


# ── HTML extraction ────────────────────────────────────────────────────────────

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
        if tag in ("h2", "h3", "h4", "p", "br", "li", "hr"):
            return f"\n{text}\n"
        return text
    return ""


def _extract_current_page_json(html: str) -> Optional[dict]:
    """
    Kjell.com embeds all product data as:
        window.CURRENT_PAGE = { ... };
    Extract and parse it.
    """
    pattern = r"window\.CURRENT_PAGE\s*=\s*(\{.*?\});\s*\n"
    match = re.search(pattern, html, re.DOTALL)
    if not match:
        return None
    try:
        return json.loads(match.group(1))
    except json.JSONDecodeError as exc:
        logger.warning(f"Could not parse CURRENT_PAGE JSON: {exc}")
        return None


# ── Public scraper ─────────────────────────────────────────────────────────────

def scrape_specs(url: str) -> dict:
    """
    Scrape a kjell.com product page.
    Returns a flat dict of product fields ready for the LLM.
    Raises InvalidKjellURLError on bad URLs, requests.HTTPError on fetch failures.
    """
    url = validate_url(url)
    session = _get_session()

    logger.info(f"Fetching: {url}")
    try:
        resp = session.get(url, timeout=20)
    except requests.exceptions.ConnectionError as exc:
        # The session-level Retry handles most transient errors,
        # but DNS / refused-connection errors still surface here.
        logger.warning(f"Connection error, retrying once after 3 s: {exc}")
        time.sleep(3)
        resp = session.get(url, timeout=20)

    resp.raise_for_status()

    data = _extract_current_page_json(resp.text)
    if not data:
        logger.warning(f"window.CURRENT_PAGE not found on {url}")
        return {}

    # ── Core identity ──────────────────────────────────────────────────────────
    specs = {
        "product_name":   data.get("displayName", ""),
        "subtitle":       data.get("subtitle", ""),
        "brand":          data.get("brandName", ""),
        "article_number": data.get("code", ""),
        "model_number":   data.get("modelNumber", ""),
    }

    # ── Category breadcrumbs ───────────────────────────────────────────────────
    breadcrumbs = data.get("breadcrumbs", [])
    specs["category_path"] = " > ".join(
        b.get("text", "") for b in breadcrumbs if b.get("text")
    )

    # ── Price ──────────────────────────────────────────────────────────────────
    price = data.get("price", {})
    specs["price_current"]      = price.get("currentInclVat")
    specs["price_original"]     = price.get("originalInclVat")
    specs["price_discount_pct"] = price.get("discountPercentage")
    specs["price_type"]         = price.get("priceType")

    # ── Key selling points & tags ──────────────────────────────────────────────
    specs["usps"] = data.get("usps", [])
    specs["tags"] = [t.get("name", "") for t in data.get("tags", []) if t.get("name")]

    # ── Descriptions ───────────────────────────────────────────────────────────
    html_desc = data.get("htmlDescription") or {}
    specs["short_description"] = _flatten_html_nodes(
        html_desc.get("html", [])
    ).strip()

    long_desc = data.get("longHtmlDescription") or {}
    specs["long_description"] = _flatten_html_nodes(
        long_desc.get("html", [])
    ).strip()

    # ── Ratings ────────────────────────────────────────────────────────────────
    specs["rating"]             = data.get("rating")
    specs["number_of_ratings"]  = data.get("numberOfRatings")
    specs["number_of_reviews"]  = data.get("numberOfReviews")
    specs["campaign_end_date"]  = data.get("campaignEndDate")

    return specs


def scrape_kjell_specs_json(url: str) -> str:
    """Return scraped specs as a JSON string (UTF-8 safe for Swedish chars)."""
    return json.dumps(scrape_specs(url), ensure_ascii=False, indent=2)


# ── Manual test ────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    test_urls = [
        "https://www.kjell.com/se/produkter/ljud-bild/horlurar-headset/brusreducerande-horlurar/aiwa-arc-1-anc-tradlosa-horlurar-p66465",
        "https://www.kjell.com/se/produkter/hem-fritid/stadning-rengoring/robotdammsugare/dreame-robotdammsugare/dreame-x40-ultra-helautomatisk-robotdammsugare-p65606",
    ]
    logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
    for url in test_urls:
        print(f"\n{'='*70}\nURL: {url}")
        result = scrape_kjell_specs_json(url)
        print(result[:1200], "...")
import json
import requests
from bs4 import BeautifulSoup
from collections import defaultdict

def scrape_specs(url: str) -> dict:

    headers = {
        # Pretend to be a normal browser (helps avoid some simple blocks)
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/122.0 Safari/537.36"
        )
    }
    resp = requests.get(url, headers=headers, timeout=15)
    resp.raise_for_status()

    soup = BeautifulSoup(resp.text, "html.parser")

    # Find the main specifications container
    spec_div = soup.find("div", id="specifications")
    if not spec_div:
        return {}

    specs = defaultdict(dict)

        # Each group has a heading (h3 > span) and a list of <dl> elements
    for group in spec_div.select("div.mb-3"):
        # Group title, e.g. "Mått & vikt", "Nyckelspecifikation"
        title_span = group.find("h3")
        if not title_span:
            continue

        group_title_el = title_span.find("span")
        group_title = group_title_el.get_text(strip=True) if group_title_el else None
        if not group_title:
            continue

        # Now find all <dl> rows in this group
        for dl in group.find_all("dl"):
            dt = dl.find("dt")
            dd = dl.find("dd")
            if not dt or not dd:
                continue

            name = dt.get_text(" ", strip=True)
            value = dd.get_text(" ", strip=True)

            if name and value:
                specs[group_title][name] = value

    return dict(specs)

def scrape_elgiganten_specs_json(url: str) -> str:
    """
    Wrapper that returns a JSON string instead of a Python dict.
    """
    specs_dict = scrape_specs(url)
    # ensure_ascii=False so Swedish characters are preserved nicely
    return json.dumps(specs_dict, ensure_ascii=False, indent=2)

if __name__ == "__main__":
    url = "https://www.elgiganten.se/product/vitvaror/tvatt-tork/tvattmaskin/electrolux-serie-600-tvattmaskin-efi622ex4e105kg/966285"
    json_str = scrape_elgiganten_specs_json(url)
    print(json_str)



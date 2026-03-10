import json
import requests
from bs4 import BeautifulSoup
from collections import defaultdict


def get_specs(url: str) -> str:
    """
    Scrape product specifications from an Elgiganten product page.
    Returns a JSON string. Returns '{}' if no specs found.
    Raises requests.HTTPError on bad HTTP responses.
    """
    headers = {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/122.0 Safari/537.36"
        )
    }

    response = requests.get(url, headers=headers, timeout=15)
    response.raise_for_status()

    soup = BeautifulSoup(response.text, "html.parser")
    spec_div = soup.find("div", id="specifications")

    if not spec_div:
        return "{}"

    specs = defaultdict(dict)

    for group in spec_div.select("div.mb-3"):
        heading = group.find("h3")
        if not heading:
            continue

        title_span = heading.find("span")
        group_title = title_span.get_text(strip=True) if title_span else None
        if not group_title:
            continue

        for dl in group.find_all("dl"):
            dt = dl.find("dt")
            dd = dl.find("dd")
            if not dt or not dd:
                continue

            name = dt.get_text(" ", strip=True)
            value = dd.get_text(" ", strip=True)

            if name and value:
                specs[group_title][name] = value

    return json.dumps(dict(specs), ensure_ascii=False, indent=2)


if __name__ == "__main__":
    url = "https://www.elgiganten.se/product/vitvaror/tvatt-tork/tvattmaskin/electrolux-serie-600-tvattmaskin-efi622ex4e105kg/966285"
    print(get_specs(url))
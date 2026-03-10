import json
import re
import requests


def get_specs(url: str) -> str:
    """
    Extracts product data from Kjell's embedded CURRENT_PAGE JSON.
    Returns a JSON string with description, specs, usps, tags, and subtitle.
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

    match = re.search(
        r"window\.CURRENT_PAGE\s*=\s*(\{.*?\});\s*\n",
        response.text,
        re.DOTALL
    )

    if not match:
        return "{}"

    page_data = json.loads(match.group(1))

    def extract_text_from_html_nodes(nodes) -> str:
        """Recursively pull text out of Kjell's HTML node format."""
        if isinstance(nodes, str):
            return nodes
        if isinstance(nodes, list):
            return " ".join(extract_text_from_html_nodes(n) for n in nodes)
        if isinstance(nodes, dict):
            children = nodes.get("children", [])
            return extract_text_from_html_nodes(children)
        return ""

    raw_description = page_data.get("htmlDescription", {}).get("html", [])
    raw_specs = page_data.get("longHtmlDescription", {}).get("html", [])

    result = {
        "title": page_data.get("displayName"),
        "subtitle": page_data.get("subtitle"),
        "brand": page_data.get("brandName"),
        "description": extract_text_from_html_nodes(raw_description).strip(),
        "specs_text": extract_text_from_html_nodes(raw_specs).strip(),
        "usps": page_data.get("usps", []),
        "tags": [t["name"] for t in page_data.get("tags", [])],
    }

    return json.dumps(result, ensure_ascii=False, indent=2)


if __name__ == "__main__":
    url = "https://www.kjell.com/se/produkter/mobilt/mobilladdare/usb-laddare/linocell-gan-multiladdare-33-w-pd-vit-p22191"
    print(get_specs(url))
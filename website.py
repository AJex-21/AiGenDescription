import json
import re
import requests


def get_specs(url: str) -> str:
    """
    Extracts product data from Kjell's embedded CURRENT_PAGE JSON.
    Returns a JSON string with description, specs, usps, tags, and subtitle.
    Returns '{}' if the data cannot be found.
    Raises requests.HTTPError on bad HTTP responses.
    """
    session = requests.Session()
    session.headers.update({
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8",
        "Accept-Language": "sv-SE,sv;q=0.9,en-US;q=0.8,en;q=0.7",
        "Accept-Encoding": "gzip, deflate, br",
        "Connection": "keep-alive",
        "Upgrade-Insecure-Requests": "1",
        "Sec-Fetch-Dest": "document",
        "Sec-Fetch-Mode": "navigate",
        "Sec-Fetch-Site": "none",
        "Sec-Fetch-User": "?1",
        "Cache-Control": "max-age=0",
    })

    response = session.get(url, timeout=15)
    response.raise_for_status()

    marker = "window.CURRENT_PAGE = "
    start_index = response.text.find(marker)
    if start_index == -1:
        return "{}"

    json_start = start_index + len(marker)

    # Walk the string character by character tracking brace depth
    # This is more reliable than regex or raw_decode on HTML-embedded JSON
    depth = 0
    in_string = False
    escape_next = False
    text = response.text

    for i, ch in enumerate(text[json_start:], start=json_start):
        if escape_next:
            escape_next = False
            continue
        if ch == "\\" and in_string:
            escape_next = True
            continue
        if ch == '"':
            in_string = not in_string
            continue
        if in_string:
            continue
        if ch == "{":
            depth += 1
        elif ch == "}":
            depth -= 1
            if depth == 0:
                json_str = text[json_start:i + 1]
                break
    else:
        print("DEBUG: Could not find end of CURRENT_PAGE JSON object")
        return "{}"

    try:
        page_data = json.loads(json_str)
    except json.JSONDecodeError as e:
        print(f"DEBUG: JSON parse failed: {e}")
        return "{}"

    def extract_text(nodes) -> str:
        """Recursively pull plain text out of Kjell's HTML node format."""
        if isinstance(nodes, str):
            return nodes
        if isinstance(nodes, list):
            return " ".join(extract_text(n) for n in nodes)
        if isinstance(nodes, dict):
            return extract_text(nodes.get("children", []))
        return ""

    raw_description = page_data.get("htmlDescription", {}).get("html", [])
    raw_specs = page_data.get("longHtmlDescription", {}).get("html", [])

    result = {
        "title": page_data.get("displayName"),
        "subtitle": page_data.get("subtitle"),
        "brand": page_data.get("brandName"),
        "description": extract_text(raw_description).strip(),
        "specs_text": extract_text(raw_specs).strip(),
        "usps": page_data.get("usps", []),
        "tags": [t["name"] for t in page_data.get("tags", [])],
    }

    return json.dumps(result, ensure_ascii=False, indent=2)


if __name__ == "__main__":
    url = "https://www.kjell.com/se/produkter/mobilt/mobilladdare/usb-laddare/linocell-gan-multiladdare-33-w-pd-vit-p22191"
    print(get_specs(url))
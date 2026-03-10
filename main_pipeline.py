import json
import logging
from website import get_specs
from description_generator import generate_description

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)


def run_pipeline(url: str) -> str:
    """
    Full pipeline: URL -> scraped specs JSON -> AI-generated description.
    Returns a description string, or an error message string.
    """
    logger.info(f"Scraping: {url}")

    try:
        specs_json = get_specs(url)
    except Exception as e:
        return f"Error: Failed to scrape page - {e}"

    if specs_json == "{}" or not specs_json:
        return "Error: No specifications found on this page"

    logger.info("Specs scraped. Generating description...")
    return generate_description(specs_json)


def batch_pipeline(urls: list) -> dict:
    """
    Process multiple product URLs.
    Returns a dict mapping URL -> description (or error message).
    """
    results = {}
    for i, url in enumerate(urls, 1):
        logger.info(f"Processing {i}/{len(urls)}: {url}")
        results[url] = run_pipeline(url)
    return results


if __name__ == "__main__":
    url = "https://www.elgiganten.se/product/vitvaror/tvatt-tork/tvattmaskin/electrolux-serie-600-tvattmaskin-efi622ex4e105kg/966285"

    print("--- SINGLE PRODUCT ---")
    print(run_pipeline(url))

    print("\n--- BATCH ---")
    urls = [url]
    results = batch_pipeline(urls)

    with open("batch_descriptions.json", "w", encoding="utf-8") as f:
        json.dump(results, f, ensure_ascii=False, indent=2)

    logger.info("Batch results saved to batch_descriptions.json")
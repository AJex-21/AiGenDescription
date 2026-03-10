import json
import os
import logging
from groq import Groq
from dotenv import load_dotenv

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

load_dotenv()

# Valid models as of 2025: https://console.groq.com/docs/models
GROQ_MODEL = "llama-3.3-70b-versatile"


def generate_description(specs_json: str) -> str:
    """
    Takes a JSON string of product specs and returns a Swedish marketing description.
    Returns an error message string if something goes wrong.
    """
    try:
        specs = json.loads(specs_json)
    except json.JSONDecodeError as e:
        return f"Error: Could not parse specs JSON - {e}"

    if not specs:
        return "Error: Specs are empty, nothing to generate from"

    client = Groq(api_key=os.getenv("Groq_API_Key"))

    prompt = f"""
    Produktspecifikationer:
    {json.dumps(specs, ensure_ascii=False, indent=2)}

    Skriv en overrygande produktbeskrivning for Elgiganten.se pa svenska.

    Regler:
    - Max 120 ord
    - 4-6 meningar, max 18 ord per mening
    - Ton: Professionell men varm, familjevanlig
    - Namna 2-3 nyckelfunktioner (t.ex. energiklass, kapacitet, program)
    - Fokusera pa fordelar, inte bara siffror (t.ex. energiklass A = lagre elrakning)
    - Avsluta med: "Uppfack [produkt] hos Elgiganten idag!"

    Svara endast med produktbeskrivningen, ingen extra text.
    """

    try:
        completion = client.chat.completions.create(
            model=GROQ_MODEL,
            messages=[
                {"role": "system", "content": "Du ar Elgigantens copywriter. Du skriver korta, overrygande produktbeskrivningar pa svenska."},
                {"role": "user", "content": prompt},
            ],
            temperature=0.3,
            max_tokens=400,
        )
        result = completion.choices[0].message.content

        if not result or not result.strip():
            return "Error: Groq returned an empty response. Check your API key and quota."

        return result.strip()

    except Exception as e:
        logger.error(f"Groq API call failed: {e}")
        return f"Error: Groq API call failed - {e}"


if __name__ == "__main__":
    with open("product_specs.json", "r", encoding="utf-8") as f:
        specs = f.read()

    description = generate_description(specs)
    print(description)
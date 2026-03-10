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
    try:
        data = json.loads(specs_json)
    except json.JSONDecodeError as e:
        return f"Error: Could not parse specs JSON - {e}"

    if not data:
        return "Error: Specs are empty, nothing to generate from"

    client = Groq(api_key=os.getenv("GROQ_API_KEY"))

    prompt = f"""
    Du är copywriter för Kjell & Company och skriver för deras egna varumärke Linocell.

    Produkt: {data.get("title", "")}
    Underrubrik (befintlig): {data.get("subtitle", "")}
    Befintlig beskrivning: {data.get("description", "")}
    Tekniska specifikationer: {data.get("specs_text", "")}
    Säljpunkter: {", ".join(data.get("usps", []))}
    Taggar: {", ".join(data.get("tags", []))}

    Skriv en ny, förbättrad produktbeskrivning på svenska.

    Regler:
    - Max 120 ord
    - 4-6 meningar, max 18 ord per mening
    - Matcha Kjells ton: kunnig, varm, tydlig - inte reklamig
    - Nämn 2-3 konkreta fördelar från specifikationerna
    - Avsluta INTE med en CTA, Kjell gör inte det
    - Svara endast med beskrivningen, ingen extra text
    """

    try:
        completion = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[
                {"role": "system", "content": "Du är Kjell & Companys copywriter. Du skriver korta, trovärdiga produktbeskrivningar på svenska som låter mänskliga och kunniga."},
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
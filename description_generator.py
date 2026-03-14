import json
import os
import logging
from dataclasses import dataclass, field
from typing import Optional
from groq import Groq
from dotenv import load_dotenv

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

load_dotenv()


# ── Data model ─────────────────────────────────────────────────────────────────

@dataclass
class KjellProduct:
    """Structured representation of a Kjell.com product."""
    product_name: str = ""
    subtitle: str = ""
    brand: str = ""
    article_number: str = ""
    model_number: str = ""
    category_path: str = ""
    price_current: Optional[float] = None
    price_original: Optional[float] = None
    price_discount_pct: Optional[float] = None
    price_type: str = ""
    usps: list = field(default_factory=list)
    tags: list = field(default_factory=list)
    short_description: str = ""
    long_description: str = ""
    rating: Optional[float] = None
    number_of_ratings: Optional[int] = None
    campaign_end_date: str = ""

    @classmethod
    def from_json(cls, specs_json: str) -> "KjellProduct":
        data = json.loads(specs_json)
        return cls(**{k: v for k, v in data.items() if k in cls.__dataclass_fields__})

    def to_prompt_dict(self) -> dict:
        """Return only the fields most useful for copywriting."""
        return {
            "Produktnamn": self.product_name,
            "Varumärke": self.brand,
            "Undertitel": self.subtitle,
            "Kategori": self.category_path,
            "Pris (nuvarande)": f"{self.price_current:.0f} kr" if self.price_current else "–",
            "Pris (original)": f"{self.price_original:.0f} kr" if self.price_original else "–",
            "Rabatt": f"{self.price_discount_pct:.0f}%" if self.price_discount_pct else "–",
            "Kampanjpristyp": self.price_type,
            "Nyckelfunktioner (USP)": self.usps,
            "Produkttaggar": self.tags,
            "Kort beskrivning (befintlig)": self.short_description,
            "Lång beskrivning (befintlig)": self.long_description[:2000] if self.long_description else "",
            "Kundbetyg": f"{self.rating}/5 ({self.number_of_ratings} betyg)" if self.rating else "–",
        }


# ── Generator ──────────────────────────────────────────────────────────────────

class DescriptionGenerator:
    """Generates Swedish product descriptions for kjell.com using Groq."""

    SYSTEM_PROMPT = (
        "Du är Kjell & Companys copywriter. "
        "Du skriver övertygande, kortfattade och informativa produkttexter på svenska. "
        "Tonen är professionell men tillgänglig – du hjälper kunden att fatta rätt beslut."
    )

    def __init__(self):
        api_key = os.getenv("Groq_API_Key") or os.getenv("GROQ_API_KEY")
        if not api_key:
            raise ValueError("GROQ_API_KEY not found in environment (.env)")
        self.client = Groq(api_key=api_key)

    def generate(self, specs_json: str, url: str = "") -> str:
        """Generate a product description from JSON specs."""
        try:
            product = KjellProduct.from_json(specs_json)
        except (json.JSONDecodeError, TypeError) as exc:
            logger.error(f"Invalid specs JSON: {exc}")
            return "FEL: Ogiltig JSON-data"

        prompt = self._build_prompt(product, url)
        return self._call_llm(prompt)

    # ── Prompt construction ────────────────────────────────────────

    def _build_prompt(self, product: KjellProduct, url: str) -> str:
        prompt_data = json.dumps(product.to_prompt_dict(), ensure_ascii=False, indent=2)

        return f"""
Produktdata från kjell.com:
{prompt_data}

URL: {url or '(ej angiven)'}

────────────────────────────────────────────────────────────
Skriv en SÄLJANDE produktbeskrivning för kjell.com på SVENSKA.

REGLER:
1. Exakt 3–5 meningar, totalt max 130 ord
2. Inled med produktens STARKASTE fördel (inte bara dess namn)
3. Nämn 2–3 av de viktigaste funktionerna från USP-listan
4. Om produkten har rabatt/kampanjpris – nämn det kort (t.ex. "Nu till kampanjpris")
5. Om produkten har högt kundbetyg (>=4.0) – nämn det subtilt
6. Avsluta med en soft CTA: "Läs mer och beställ på kjell.com."
7. Inga emojis, inga punktlistor – löpande text

BENEFIT-FOKUS (inte bara siffror):
- "40 timmars batteritid" → "slipper du ladda i en hel vecka"
- "12 000 Pa sugeffekt" → "suger upp smuts andra robotdammsugare missar"
- "ANC" → "blockerar bakgrundsljud och låter dig fokusera"

FORBJUDET:
- Kopiera exakt från befintlig kort/lång beskrivning
- Börja med produktnamnet rakt av (t.ex. "Aiwa ARC-1 är...")
- Överdrivna superlativ utan stöd i datan

Skriv ENBART den färdiga texten, inga rubriker eller kommentarer.
"""

    # ── LLM call ───────────────────────────────────────────────────

    def _call_llm(self, prompt: str) -> str:
        try:
            completion = self.client.chat.completions.create(
                model="llama-3.3-70b-versatile",
                messages=[
                    {"role": "system", "content": self.SYSTEM_PROMPT},
                    {"role": "user", "content": prompt},
                ],
                temperature=0.4,
                max_tokens=400,
            )

            raw = completion.choices[0].message.content
            logger.debug(f"RAW RESPONSE ({len(raw)} chars): {raw[:200]}")

            if not raw or not raw.strip():
                return "Tom respons från Groq -- kontrollera API-nyckel eller kvot"

            return f"\n{'─'*60}\n{raw.strip()}\n{'─'*60}\n"

        except Exception as exc:
            logger.error(f"Groq API error: {exc}")
            return f"Groq-fel: {exc}"


# ── Public convenience functions ───────────────────────────────────────────────

def generate_description_from_json(specs_json: str) -> str:
    """Generate a description directly from a JSON string."""
    return DescriptionGenerator().generate(specs_json)


def generate_description_from_url(url: str) -> str:
    """Scrape a kjell.com URL, then generate a description."""
    from KC_scrape import scrape_kjell_specs_json
    specs_json = scrape_kjell_specs_json(url)
    return DescriptionGenerator().generate(specs_json, url)


# ── Standalone test ────────────────────────────────────────────────────────────
if __name__ == "__main__":
    sample_json = json.dumps({
        "product_name": "Aiwa ARC-1 ANC trådlösa hörlurar",
        "subtitle": "Over-ear-hörlurar med brusreducering och 40 timmars batteritid",
        "brand": "Aiwa",
        "article_number": "66465",
        "model_number": "ANC-1",
        "category_path": "Ljud & bild > Hörlurar & headset > Brusreducerande hörlurar",
        "price_current": 300.0,
        "price_original": 699.0,
        "price_discount_pct": 57.0,
        "price_type": "member",
        "usps": [
            "Aktiv brusreducering (ANC)",
            "Upp till 40 timmars batteritid",
            "15 minuters laddning ger 3 timmars användning",
        ],
        "tags": [],
        "short_description": (
            "Aiwa ARC-1 är trådlösa over-ear-hörlurar med aktiv brusreducering, "
            "imponerande 40 timmars batteritid och bekväm passform."
        ),
        "long_description": "",
        "rating": 4.0,
        "number_of_ratings": 26,
        "campaign_end_date": "2026-03-30",
    }, ensure_ascii=False)

    print("=== TEST: Aiwa ARC-1 ===")
    result = generate_description_from_json(sample_json)
    print(result)

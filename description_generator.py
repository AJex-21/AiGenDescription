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


# ── Buyer personas by category keyword ────────────────────────────────────────
# Maps a keyword found in the category_path to a buyer description.
# The model uses this to understand who it is writing for.

BUYER_PERSONAS = {
    "sovhorlurar": (
        "Kunden vill sova bättre. De störs av ljud från partner, grannar eller resor. "
        "De prioriterar passform for sidosovare, komfort under hela natten och funktioner "
        "som blockerar storande ljud eller spelar upp lugnande ljud."
    ),
    "brusreducerande": (
        "Kunden pendlar, arbetar i oppen kontorsmiljo eller reser ofta med flyg. "
        "De vill stanga ute omgivningsljud och fokusera pa musik, podcasts eller arbete. "
        "Batteritid och kvaliteten pa brusreduceringen ar avgörande."
    ),
    "sporthorlurar": (
        "Kunden tranas regelbundet – gym, lopning eller cykling. "
        "De behover horlurar som sitter stadigt, tal svett och inte stor under traningen. "
        "Vattentolighet, passform och batteritid ar viktigast."
    ),
    "airpods": (
        "Kunden ar djupt inne i Apples ekosystem med iPhone, iPad eller Mac. "
        "De vardesar somlös integration, premium-kansla och att det bara fungerar. "
        "De jamfor mot foregaende generation och vill veta vad som faktiskt ar battre."
    ),
    "tradlosa-bluetooth-horlurar": (
        "Kunden vill ha ett palitligt par tradlosa horlurar for vardagsbruk – "
        "promenader, kollektivtrafik och hemmabruk. De ar prismedvetna och vill ha "
        "bra varde for pengarna utan att kompromissa med grundlaggande funktioner."
    ),
    "in-ear-horlurar": (
        "Kunden letar efter ett sekundart par horlurar eller sitt forsta kop. "
        "De vill ha enkel hantering, bra ljud for priset och en passform som haller. "
        "Enkelt och tillforlitligt ar viktigare an avancerade funktioner."
    ),
    "minneskort": (
        "Kunden ar fotograf, videograf, dronarpilot eller mobilanvandare som "
        "standigt far slut pa lagringsutrymme. De bryr sig om kompatibilitet med sin "
        "enhet, skrivhastighet for videoinspelning och lashastiget for filoverföring."
    ),
    "streaming-mediaspelare": (
        "Kunden vill gora sin tv smartare utan att kopa en ny. "
        "De vill strömma Netflix, YouTube och andra tjanster enkelt. "
        "Enkel installation, stabil anslutning och stod for 4K ar avgörande."
    ),
    "soundbar": (
        "Kunden vill forbattra tv-ljudet utan ett fullstandigt surroundsystem. "
        "De bor i lagenhet eller vill ha en enkel losning. "
        "Ljudkvalitet, enkel installation och att den matchar tv:n ar viktigt."
    ),
    "mikrofoner": (
        "Kunden skapar innehall – videor, podcasts, streams eller moten. "
        "De vill ha tydligt ljud utan bakgrundsbrus och enkel anslutning "
        "till kamera, dator eller telefon."
    ),
    "rengoring": (
        "Kunden vill halla sina skarmar och elektronik i bra skick. "
        "De vill ha ett palitligt kit som inte repar ytor och ar enkelt att anvanda."
    ),
    "cd-spelare": (
        "Kunden har en cd-samling och vill kunna lyssna pa den igen, "
        "hemma eller pa resande fot. Enkelhet och portabilitet ar avgörande."
    ),
    "radio": (
        "Kunden vill ha ett palitligt satt att lyssna pa radio utan internetuppkoppling. "
        "Viktigt vid stromavbrott, friluftsliv eller som nodradio."
    ),
}

DEFAULT_PERSONA = (
    "Kunden ar en allman konsument som letar efter en produkt som loser ett konkret "
    "vardagsproblem. De vill ha tydlig och arlig information om vad produkten gor "
    "och varfor den ar vard pengarna."
)


def get_persona(category_path: str) -> str:
    """Return the buyer persona that best matches the category path."""
    path_lower = category_path.lower()
    for keyword, persona in BUYER_PERSONAS.items():
        if keyword in path_lower:
            return persona
    return DEFAULT_PERSONA


# ── Few-shot examples from actual Kjell pages ─────────────────────────────────

FEW_SHOT_EXAMPLES = """
EXAMPLE 1 — Linocell TWS Earphones (budget tradlosa horlurar)
INPUT:
  Kategori: Horlurar & headset > Tradlosa Bluetooth-horlurar
  Koparprofil: Vardagsanvandare som vill ha ett palitligt par tradlosa horlurar for ett bra pris
  Nyckelfunktioner: IPX4, 21 timmars batteritid (7h + 14h via etui), Bluetooth 5.1, Siri/Google Assistant, USB-C
  Pris: 199 kr (ord. 399 kr)

OUTPUT:
  SUBTITLE: Musik och samtal – helt utan kablar
  BULLETS:
    - IPX4 – tal svett och regn
    - Lang batteritid (21 timmar)
    - Stod for Siri och Google Assistant
  DESCRIPTION: Smidiga, kompakta och alltid redo – Linocell TWS later dig lyssna pa musik och ta samtal helt utan sladdar som ar i vagen. Batteritiden pa 7 timmar forlangs med ytterligare 14 timmar nar lurarna laddas i etuit. Stabil tradlos anslutning till mobil, surfplatta och dator via Bluetooth 5.1. Tal vattenstank enligt IPX4.

EXAMPLE 2 — Apple AirPods Pro 3 (premium brusreducerande)
INPUT:
  Kategori: Horlurar & headset > AirPods
  Koparprofil: Apple-anvandare som jamfor mot foregaende generation och vill veta vad som faktiskt ar nytt
  Nyckelfunktioner: 2x mer brusreducering vs Pro 2, inbyggd pulsmaning, IP57, ny design med 5 orontopp-storlekar, 8h batteritid med ANC
  Pris: 2 889 kr

OUTPUT:
  SUBTITLE: Varldens basta aktiva brusreducering for in ear-horlurar.
  BULLETS:
    - Dubbelt sa bra brusreducering och inbyggd pulsmatare
    - Tal damm, svett och vatten (IP57)
    - Med ny design for sakrare passform
  DESCRIPTION: AirPods Pro 3 har upp till 2x mer aktiv brusreducering jamfort med AirPods Pro 2. Nu med pulsmaning, langre batteritid och framsteg inom horselhalsa. Med ny design for sakrare passform.
"""


# ── Data model ─────────────────────────────────────────────────────────────────

@dataclass
class KjellProduct:
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
        price_str = f"{self.price_current:.0f} kr" if self.price_current else "-"
        original_str = f"{self.price_original:.0f} kr" if self.price_original else "-"
        discount_str = f"{self.price_discount_pct:.0f}%" if self.price_discount_pct else None

        price_line = price_str
        if original_str and original_str != price_str:
            price_line += f" (ord. {original_str})"
        if discount_str:
            price_line += f" — {discount_str} rabatt"

        return {
            "Produktnamn":    self.product_name,
            "Varumarke":      self.brand,
            "Kategori":       self.category_path,
            "Pris":           price_line,
            "Nuvarande undertitel (skriv inte av denna)": self.subtitle,
            "Nyckelfunktioner": self.usps,
            "Befintlig kort beskrivning (faktakalla, skriv inte av)":
                self.short_description,
            "Utokad information (faktakalla)":
                self.long_description[:1500] if self.long_description else "",
        }


# ── Generator ──────────────────────────────────────────────────────────────────

class DescriptionGenerator:

    SYSTEM_PROMPT = (
        "Du ar en erfaren copywriter som skriver produkttexter for kjell.com. "
        "Du skriver pa svenska i Kjells etablerade stil: kortfattad, faktabaserad och direkt. "
        "Du skriver aldrig vaga fraser, namnner aldrig kundbetyg, skriver aldrig CTA som "
        "'Las mer pa kjell.com' och hittar aldrig pa specifikationer. "
        "Du skriver exakt det format som efterfragas och ingenting annat."
    )

    def __init__(self):
        api_key = os.getenv("Groq_API_Key") or os.getenv("GROQ_API_KEY")
        if not api_key:
            raise ValueError("GROQ_API_KEY not found in environment (.env)")
        self.client = Groq(api_key=api_key)

    def generate(self, specs_json: str, url: str = "") -> dict:
        """
        Generate a product description from JSON specs.
        Returns a dict with keys: subtitle, bullets (list), description.
        """
        try:
            product = KjellProduct.from_json(specs_json)
        except (json.JSONDecodeError, TypeError) as exc:
            logger.error(f"Invalid specs JSON: {exc}")
            return {"error": "Ogiltig JSON-data"}

        persona = get_persona(product.category_path)
        prompt = self._build_prompt(product, persona)
        return self._call_llm(prompt)

    def _build_prompt(self, product: KjellProduct, persona: str) -> str:
        product_data = json.dumps(product.to_prompt_dict(), ensure_ascii=False, indent=2)

        return f"""
Du ska skriva en ny produkttext for kjell.com. Studera exemplen noggrant –
de visar exakt den stil, ton och det format som anvands pa sajten.

{FEW_SHOT_EXAMPLES}

Nu ska du skriva for denna produkt:

PRODUKTDATA:
{product_data}

KOPARPROFIL:
{persona}

────────────────────────────────────────────────────────────
Skriv exakt detta och ingenting annat:

SUBTITLE: [En kort, karngfull mening som fanger produktens viktigaste fordel. Max 10 ord.]

BULLETS:
- [Specifik funktion – inkludera siffror/spec inom parentes om tillgangligt]
- [Specifik funktion – inkludera siffror/spec inom parentes om tillgangligt]
- [Specifik funktion – inkludera siffror/spec inom parentes om tillgangligt]

DESCRIPTION: [2-4 meningar. Faktabaserad. Exakta siffror nar de finns. Borja inte med produktnamnet. Skriv for koparprofilen ovan. Max 70 ord.]

REGLER SOM ALDRIG FAR BRYTAS:
- Hitta inte pa specifikationer som inte finns i produktdatan
- Skriv inte av undertiteln
- Inga meningar med "kjell.com"
- Inga fraser: "ett bra val", "passar perfekt", "hog kvalitet", "ett sakert val"
- Namnn aldrig kundbetyg eller antal recensioner
- Skriv inte "Nu till kampanjpris"
"""

    def _call_llm(self, prompt: str) -> dict:
        try:
            completion = self.client.chat.completions.create(
                model="llama-3.3-70b-versatile",
                messages=[
                    {"role": "system", "content": self.SYSTEM_PROMPT},
                    {"role": "user",   "content": prompt},
                ],
                temperature=0.3,
                max_tokens=400,
            )

            raw = completion.choices[0].message.content.strip()
            logger.debug(f"Raw response: {raw}")

            if not raw:
                return {"error": "Tom respons fran modellen"}

            return self._parse_output(raw)

        except Exception as exc:
            logger.error(f"Groq API error: {exc}")
            return {"error": str(exc)}

    def _parse_output(self, raw: str) -> dict:
        """Parse the structured SUBTITLE / BULLETS / DESCRIPTION output."""
        result = {"subtitle": "", "bullets": [], "description": "", "raw": raw}

        lines = raw.splitlines()
        mode = None

        for line in lines:
            line = line.strip()
            if not line:
                continue

            if line.upper().startswith("SUBTITLE:"):
                result["subtitle"] = line.split(":", 1)[1].strip()
                mode = None

            elif line.upper().startswith("BULLETS:"):
                mode = "bullets"

            elif line.upper().startswith("DESCRIPTION:"):
                result["description"] = line.split(":", 1)[1].strip()
                mode = "description"

            elif mode == "bullets" and line.startswith("-"):
                result["bullets"].append(line.lstrip("- ").strip())

            elif mode == "description" and result["description"]:
                result["description"] += " " + line

        return result


# ── Formatted print helper ─────────────────────────────────────────────────────

def format_output(result: dict, url: str = "") -> str:
    if "error" in result:
        return f"FEL: {result['error']}"

    lines = ["\n" + "="*70]
    if url:
        lines.append(f"URL         : {url}")
    lines.append(f"SUBTITLE    : {result.get('subtitle', '')}")
    lines.append("BULLETS     :")
    for b in result.get("bullets", []):
        lines.append(f"  - {b}")
    lines.append(f"DESCRIPTION :\n  {result.get('description', '')}")
    lines.append("="*70)
    return "\n".join(lines)


# ── Public convenience functions ───────────────────────────────────────────────

def generate_description_from_json(specs_json: str) -> dict:
    return DescriptionGenerator().generate(specs_json)


def generate_description_from_url(url: str) -> dict:
    from KC_scrape import scrape_kjell_specs_json
    specs_json = scrape_kjell_specs_json(url)
    result = DescriptionGenerator().generate(specs_json, url)
    print(format_output(result, url))
    return result


# ── Standalone test ────────────────────────────────────────────────────────────
if __name__ == "__main__":
    sample_json = json.dumps({
        "product_name":       "Linocell TWS Earphones Tradlosa horlurar",
        "subtitle":           "Musik och samtal – helt utan kablar",
        "brand":              "Linocell",
        "article_number":     "24224",
        "category_path":      "Ljud & bild > Horlurar & headset > Tradlosa Bluetooth-horlurar",
        "price_current":      199.0,
        "price_original":     399.0,
        "price_discount_pct": 50.0,
        "price_type":         "member",
        "usps": [
            "IPX4 – tal svett och regn",
            "Lang batteritid (21 timmar)",
            "Stod for Siri och Google Assistant",
        ],
        "short_description": (
            "Smidiga, kompakta och alltid redo – Linocell TWS later dig lyssna pa musik "
            "och ta samtal helt utan sladdar som ar i vagen."
        ),
        "long_description": (
            "Batteritiden pa 7 timmar forlangs med ytterligare 14 timmar nar lurarna laddas "
            "i etuit. Stabil tradlos anslutning via Bluetooth 5.1. Stod for Siri och Google "
            "Assistant. Tal vattenstank enligt IPX4. Laddas med medfoljande USB-C-kabel."
        ),
        "rating": 4.0,
        "number_of_ratings": 138,
    }, ensure_ascii=False)

    result = generate_description_from_json(sample_json)
    print(format_output(result))
import json
import logging
import os
import time
from dataclasses import dataclass, field
from typing import Optional

from groq import Groq
from dotenv import load_dotenv

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

load_dotenv()


# ── Buyer personas ─────────────────────────────────────────────────────────────
# Keys are lowercase substrings matched against the product's category_path.
# ORDER MATTERS: more specific keys must appear before broader ones.

BUYER_PERSONAS = {
    "overvakningskamer": (
        "Kunden vill veta vad som händer utanför hemmet – uppfarten, trädgården, "
        "entrén. De oroar sig för inbrott, paketdivar eller obehöriga besökare. "
        "De vill ha skarp bild i mörker, kunna täcka ett stort område och få "
        "push-notis när något rör sig. Helst utan att behöva köpa flera kameror."
    ),
    "inomhuskamer": (
        "Kunden vill ha koll på barnen, husdjuren eller hemmet när de är borta. "
        "De vill ha enkel installation, bra app och tydlig bild dygnet runt. "
        "Integritet är en fråga – de vill kunna stänga av kameran enkelt."
    ),
    "larm": (
        "Kunden vill skydda hemmet och få ett omedelbart larm om något händer. "
        "Enkel installation utan borrning, batteridrift och pålitlig "
        "push-notis på telefonen är det som avgör köpet."
    ),
    "las": (
        "Kunden vill kunna låsa upp dörren utan nyckel – med kod, fingeravtryck "
        "eller telefon. De vill slippa oroa sig för tappade nycklar och kunna ge "
        "tidsbegränsad tillgång till gäster utan att lämna ut en kopia."
    ),
    "sakerhet": (
        "Kunden vill ha ökad trygghet hemma eller på arbetsplatsen. "
        "De söker en konkret lösning på ett verkligt problem – "
        "inbrott, brand, vattenläcka eller obehörig åtkomst."
    ),
    "gaming-headset": (
        "Spelaren vill höra varje steg och kommunicera tydligt med laget. "
        "Surroundljud, mikrofonkvalitet och komfort under långa sessioner är avgörande."
    ),
    "gaming-mus": (
        "Spelaren vill ha precis kontroll och snabb respons. "
        "DPI-omfång, polling rate och hur musen känns i handen under intensiva pass."
    ),
    "gaming-tangentbord": (
        "Spelaren vill ha snabba och pålitliga knapptryckningar. "
        "Mekaniska switchar, RGB-belysning och anti-ghosting är de tre frågorna."
    ),
    "spelkonsol": (
        "Kunden vill spela de senaste spelen på storskärm. "
        "Exklusiva spel, prestanda och kompatibilitet med befintliga spel avgör."
    ),
    "gaming": (
        "Spelaren söker utrustning som ger konkreta fördelar i spelet "
        "eller gör upplevelsen mer immersiv och bekväm."
    ),
    "webbkamera": (
        "Kunden jobbar hemifrån eller streamar och vill se bra ut på video. "
        "Upplösning, autofokus och bildfrekvens är avgörande. Plug-and-play föredras."
    ),
    "laptop": (
        "Kunden söker en bärbar dator för arbete, studier eller hemmabruk. "
        "De väger prestanda mot pris och vill veta om den klarar det de planerar."
    ),
    "tangentbord": (
        "Kunden skriver mycket och vill ha bättre ergonomi eller skrivupplevelse. "
        "För gaming: svarstid och RGB. För kontor: tyst typkänsla och trådlöshet."
    ),
    "mus": (
        "Kunden vill ha bättre precision eller komfort. "
        "Gamers bryr sig om DPI och svarstid. Kontorsanvändare om grepp och trådlöshet."
    ),
    "skarm": (
        "Kunden jämför upplösning, bildfrekvens och storlek mot pris. "
        "Gamers vill ha låg input lag. Kontorsanvändare prioriterar färgåtergivning."
    ),
    "ssd": (
        "Kunden vill snabba upp sin dator eller få mer lagring. "
        "Läs- och skrivhastighet samt kapacitet i förhållande till pris avgör."
    ),
    "harddisk": (
        "Kunden har slut på lagring eller vill säkerhetskopiera. "
        "Kapacitet, hastighet och om den är portabel eller stationär avgör."
    ),
    "skrivare": (
        "Kunden behöver skriva ut hemma. Sidkostnad och trådlös utskrift avgör."
    ),
    "dator": (
        "Kunden söker datortillbehör. Prestanda, kompatibilitet och enkel installation."
    ),
    "utomhusbelysning": (
        "Kunden vill belysa trädgård, uppfart eller entré. "
        "Rörelsesensor, solcellsdrift och vattentålighet avgör."
    ),
    "skrivbordslampa": (
        "Kunden arbetar eller studerar och vill ha bra arbetsbelysning. "
        "Justerbar ljusstyrka, färgtemperatur och att den inte tröttar ut ögonen."
    ),
    "led-lamp": (
        "Kunden byter gamla glödlampor. Rätt sockel, färgtemperatur och lång livslängd."
    ),
    "lampor": (
        "Kunden söker belysning för ett specifikt syfte – arbete, stämning eller säkerhet."
    ),
    "robotdammsugare": (
        "Kunden vill slippa dammsuga. De undrar om den klarar deras golvtyp, "
        "husdjurshår och mattor. En station som tömmer sig själv är ett starkt argument."
    ),
    "smart-belysning": (
        "Kunden vill styra ljuset från telefonen eller med röst. "
        "Kompatibilitet med befintligt system – Hue, IKEA, Google, Apple – avgör."
    ),
    "smart-plugg": (
        "Kunden vill göra vanliga apparater smarta. Slå av/på via app och schemalägga. "
        "Maxeffekt och energimätning är relevanta."
    ),
    "smarta hem": (
        "Kunden bygger eller utökar sitt smarta hem. Enheter som fungerar med "
        "befintligt ekosystem och ger verklig nytta i vardagen."
    ),
    "sovhorlurar": (
        "Kunden störs av ljud på natten. Passform för sidosovare och hur effektivt "
        "de blockerar störande ljud är avgörande."
    ),
    "brusreducerande": (
        "Kunden pendlar eller arbetar i öppen kontorsmiljö. "
        "ANC-kvalitet och batteritid under en hel arbetsdag avgör."
    ),
    "sporthorlurar": (
        "Kunden tränar regelbundet. Hörlurar som sitter kvar och överlever svettiga pass. "
        "IP-klassning och passform avgör."
    ),
    "airpods": (
        "Kunden har iPhone och vill ha hörlurar som fungerar direkt. "
        "De jämför mot föregående generation och vill veta vad som faktiskt är bättre."
    ),
    "tradlosa bluetooth": (
        "Prismedveten kund för pendling och vardagsbruk. "
        "Bra värde utan att kompromissa med batteritid och stabil anslutning."
    ),
    "true-wireless": (
        "Kunden vill ha helt trådlösa hörlurar. "
        "Total batteritid inklusive etui och passform avgör."
    ),
    "in-ear": (
        "Enkel hörlurar för backup, träning eller som första par. "
        "Bra ljud för priset och en passform som håller."
    ),
    "headset": (
        "Kunden behöver hörlurar med mikrofon för samtal, videomöten eller gaming. "
        "Mikrofonkvaliteten är minst lika viktig som ljudet."
    ),
    "soundbar": (
        "Kunden är trött på tv:ns inbyggda högtalare men vill inte ha ett "
        "fullständigt surroundsystem. Hur mycket bättre det låter och enkel installation."
    ),
    "hogtalare": (
        "Kunden vill ha ljud i ett rum utan kabeldragning. "
        "Batteritid, vattentålighet och ljudkvalitet mot pris avgör."
    ),
    "streaming-mediaspelare": (
        "Kunden vill göra sin befintliga tv smart. "
        "4K-stöd, enkel installation och stabil wifi-anslutning."
    ),
    "minneskort": (
        "Kunden har kamera, drönare, dashcam eller mobil som ständigt går fullt. "
        "Kompatibilitet med enheten, sedan skrivhastighet för video."
    ),
    "mikrofon": (
        "Kunden skapar innehåll – YouTube, podcast, stream eller videomöten. "
        "Tydligt ljud utan bakgrundsbrus och enkel anslutning. Plug-and-play föredras."
    ),
    "ljud": (
        "Kunden vill förbättra sin ljudupplevelse. "
        "Ett konkret lyft i kvalitet eller funktion jämfört med idag."
    ),
    "powerbank": (
        "Kunden reser ofta eller är ute och kan inte alltid ladda. "
        "Vikt och storlek avgör om den faktiskt tas med."
    ),
    "mobilskal": (
        "Kunden vill skydda sin nya telefon. Skydd mot tapp utan att kännas klumpig. "
        "Tunnhet och grepp är viktigast."
    ),
    "skarmskydd": (
        "Kunden är rädd för att spricka skärmen. "
        "Skydd utan påverkan på touchkänslan och enkel montering utan luftbubblor."
    ),
    "mobilt": (
        "Kunden söker mobiltillbehör som gör telefonen mer användbar i vardagen."
    ),
    "mesh": (
        "Kunden har ett större hem med dålig täckning. "
        "Eliminera döda zoner med ett system enkelt att ställa in via app."
    ),
    "router": (
        "Kunden har dåligt wifi hemma – döda zoner eller för många enheter. "
        "Stabilt internet i hela hemmet utan att bli nätverkstekniker."
    ),
    "switch": (
        "Kunden vill koppla upp fler enheter med kabel. "
        "Antal portar och gigabit-stöd är det enda som spelar roll."
    ),
    "natverk": (
        "Kunden söker en lösning för bättre och mer pålitlig internetuppkoppling."
    ),
    "ficklampa": (
        "Kunden vill ha pålitlig belysning i mörker – strömavbrott, friluftsliv eller verkstad. "
        "Ljusstyrka i lumen, räckvidd och batteritid avgör."
    ),
    "batteri": (
        "Kunden behöver ersättningsbatterier. Pålitliga batterier som håller länge. "
        "Låg självurladdning är viktigt för sällanvändarenheter."
    ),
    "laddkabel": (
        "Kunden behöver ny laddkabel – gammal är sönder eller vill ha en extra. "
        "Tålig för daglig användning och rätt laddningshastighet för enheten."
    ),
    "hdmi": (
        "Kunden kopplar ihop tv, dator, konsol eller projektor. "
        "Rätt HDMI-version för sin upplösning och bildfrekvens."
    ),
    "forlangningssladd": (
        "Kunden har för få vägguttag. Rätt antal uttag, rätt längd och USB-laddning. "
        "Överspänningsskydd ger extra trygghet."
    ),
    "kablar": (
        "Kunden behöver rätt kabel för att koppla ihop sina enheter. "
        "Rätt kontakttyp, längd och hastighetsspecifikation."
    ),
    "ergonomi": (
        "Kunden arbetar mycket vid dator och känner av nack- eller ryggbesvär. "
        "Justeringsmöjligheter och rörelsefrihet avgör."
    ),
    "kontor": (
        "Kunden söker kontorsutrustning för ett effektivare och bekvämare arbete."
    ),
    "hem": (
        "Kunden söker produkter som gör hemlivet enklare, snyggare eller mer funktionellt."
    ),
    "belysning": (
        "Kunden söker belysning för ett specifikt syfte – arbete, stämning eller säkerhet."
    ),
    "tv-spel": (
        "Kunden söker spelrelaterad utrustning. "
        "Plattformskompatibilitet och vad som faktiskt förbättrar spelupplevelsen avgör."
    ),
}

DEFAULT_PERSONA = (
    "Kunden söker en produkt som löser ett konkret problem i vardagen. "
    "De vill ha tydlig och ärlig information om vad produkten faktiskt gör "
    "och om den är värd priset. Var specifik – vaghet skapar inte förtroende."
)


def _normalize(text: str) -> str:
    """Lowercase and replace Swedish special chars with ASCII equivalents."""
    return (
        text.lower()
        .replace("\xe5", "a")   # å
        .replace("\xe4", "a")   # ä
        .replace("\xf6", "o")   # ö
        .replace("\xe9", "e")   # é
    )


def get_persona(category_path: str) -> str:
    """Return the most specific buyer persona matching the category path."""
    path_norm = _normalize(category_path)
    for keyword, persona in BUYER_PERSONAS.items():
        if _normalize(keyword) in path_norm:
            return persona
    return DEFAULT_PERSONA


# ── Few-shot examples ──────────────────────────────────────────────────────────

FEW_SHOT_EXAMPLES = """
EXAMPLE 1 — Linocell TWS Earphones (budget trådlösa hörlurar)
INPUT:
  Kategori: Hörlurar & headset > Trådlösa Bluetooth-hörlurar
  Köparprofil: Vardagsanvändare, prismedveten, vill ha pålitlig grundkvalitet
  Nyckelfunktioner: IPX4, 21h batteritid (7h + 14h etui), Bluetooth 5.1, Siri/Google Assistant
  Pris: 199 kr (ord. 399 kr)

OUTPUT:
  SUBTITLE: Musik och samtal – helt utan kablar
  BULLETS:
    - IPX4 – tål svett och regn
    - Lång batteritid (21 timmar totalt)
    - Stöd för Siri och Google Assistant
  DESCRIPTION: Smidiga, kompakta och alltid redo – Linocell TWS låter dig lyssna på musik och ta samtal helt utan sladdar i vägen. Batteritiden på 7 timmar förlängs med ytterligare 14 timmar när lurarna laddas i etuit. Stabil Bluetooth 5.1-anslutning till mobil, surfplatta och dator. Tål vattenstänk enligt IPX4. Laddas med medföljande USB-C-kabel.

EXAMPLE 2 — Apple AirPods Pro 3 (premium brusreducerande)
INPUT:
  Kategori: Hörlurar & headset > AirPods
  Köparprofil: Apple-användare som jämför mot föregående generation
  Nyckelfunktioner: 2x mer ANC vs Pro 2, inbyggd pulsmätare, IP57, 5 örontopp-storlekar, 8h batteritid
  Pris: 2 889 kr

OUTPUT:
  SUBTITLE: Världens bästa aktiva brusreducering för in ear-hörlurar
  BULLETS:
    - Dubbelt så bra brusreducering och inbyggd pulsmätare
    - Tål damm, svett och vatten (IP57)
    - Ny design med fem örontopp-storlekar för säkrare passform
  DESCRIPTION: AirPods Pro 3 tar bort upp till 2x mer oönskat ljud än AirPods Pro 2. Den inbyggda pulsmätaren låter dig följa träning direkt i hörlurarna. Ny akustisk arkitektur ger fylligare bas och tydligare detaljer. Finns i fem örontopp-storlekar för en säkrare passform.

EXAMPLE 3 — TP-link Tapo C545D (utomhuskamera med dubbla linser)
INPUT:
  Kategori: Säkerhet & övervakning > Övervakningskameror
  Köparprofil: Vill bevaka uppfart, trädgård eller garage
  Nyckelfunktioner: Dubbla 2K-linser, AI-spårning, fullfärgsnattseende, IP66, 99 dB siren
  Pris: kampanjpris

OUTPUT:
  SUBTITLE: Överblick och detalj – i en och samma kamera
  BULLETS:
    - Dubbla 2K-linser med synkroniserad AI-spårning
    - Fullfärgsnattseende och 99 dB-siren
    - IP66-klassad för utomhusbruk året runt
  DESCRIPTION: Tapo C545D kombinerar en fast vidvinkellins och en rörlig telefoto-lins i samma enhet. Vidvinkellinsen ger helhetsbild över området medan AI automatiskt zoomar in telelinsen och följer rörelser. Det gör att du kan bevaka uppfarten, trädgården eller garaget med både överblick och detaljskärpa – utan att behöva flera kameror.
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
        valid_fields = cls.__dataclass_fields__
        return cls(**{k: v for k, v in data.items() if k in valid_fields})

    def to_prompt_dict(self) -> dict:
        price_str    = f"{self.price_current:.0f} kr" if self.price_current else "-"
        original_str = f"{self.price_original:.0f} kr" if self.price_original else "-"
        discount_str = (
            f"{self.price_discount_pct:.0f}%"
            if self.price_discount_pct and self.price_discount_pct > 0
            else None
        )

        price_line = price_str
        if original_str and original_str != price_str:
            price_line += f" (ord. {original_str})"
        if discount_str:
            price_line += f" — {discount_str} rabatt"

        return {
            "Produktnamn": self.product_name,
            "Varumärke":   self.brand,
            "Kategori":    self.category_path,
            "Pris":        price_line,
            "Nuvarande undertitel (skriv INTE av denna)":
                self.subtitle,
            "Nyckelfunktioner (USP)":
                self.usps,
            "Befintlig kort beskrivning (faktakälla – skriv inte av, men använd faktan)":
                self.short_description,
            "Utökad produktinformation (faktakälla)":
                self.long_description[:2000] if self.long_description else "",
        }


# ── Generator ──────────────────────────────────────────────────────────────────

class DescriptionGenerator:

    SYSTEM_PROMPT = (
        "Du är en erfaren copywriter som skriver produkttexter för kjell.com. "
        "Du skriver på svenska i Kjells etablerade stil: kortfattad, faktabaserad och direkt. "
        "Du hittar aldrig på specifikationer. Du nämner aldrig kundbetyg. "
        "Du skriver aldrig fraser som slutar med 'kjell.com'. "
        "Du skriver exakt det format som efterfrågas – ingenting mer, ingenting mindre."
    )

    # Groq free tier: 30 req/min. 2 s between calls leaves safe headroom in batch.
    _CALL_INTERVAL = 2.0
    _last_call_time: float = 0.0

    # How many times to retry a failed LLM call before giving up.
    _MAX_RETRIES = 3

    def __init__(self):
        api_key = os.getenv("Groq_API_Key") or os.getenv("GROQ_API_KEY")
        if not api_key:
            raise ValueError("No Groq API key found. Set GROQ_API_KEY in your .env file.")
        self.client = Groq(api_key=api_key)

    def generate(self, specs_json: str, url: str = "") -> dict:
        try:
            product = KjellProduct.from_json(specs_json)
        except (json.JSONDecodeError, TypeError) as exc:
            logger.error(f"Invalid specs JSON: {exc}")
            return {"error": "Ogiltig JSON-data"}

        persona = get_persona(product.category_path)
        prompt  = self._build_prompt(product, persona)
        return self._call_llm_with_retry(prompt)

    def _build_prompt(self, product: KjellProduct, persona: str) -> str:
        product_data = json.dumps(product.to_prompt_dict(), ensure_ascii=False, indent=2)
        return f"""
Du ska skriva en ny produkttext för kjell.com. Studera de tre exemplen noggrant –
de visar exakt den stil, ton och det format som används och godkänns på sajten.

{FEW_SHOT_EXAMPLES}

────────────────────────────────────────────────────────────
Skriv nu för denna produkt:

PRODUKTDATA:
{product_data}

KÖPARPROFIL – vem du skriver för och vad de faktiskt bryr sig om:
{persona}

────────────────────────────────────────────────────────────
Skriv exakt detta och ingenting annat:

SUBTITLE: [En ny, kortfattad mening som fångar produktens viktigaste fördel. Max 10 ord. Imitera exemplens stil. Kopiera INTE den befintliga undertiteln.]

BULLETS:
- [Specifik funktion med exakt siffra eller spec inom parentes om data finns]
- [Specifik funktion med exakt siffra eller spec inom parentes om data finns]
- [Specifik funktion med exakt siffra eller spec inom parentes om data finns]

DESCRIPTION: [2–5 meningar. Max 90 ord. Börja INTE med produktnamnet. Förklara hur den viktigaste funktionen löser ett konkret problem för köparprofilen ovan. Inga vaga fraser. Inga kundbetyg. Ingen CTA.]

FÖRBJUDNA FRASER:
"ett bra val" / "passar perfekt" / "hög kvalitet" / "ett säkert val" /
"Nu till kampanjpris" / kundbetyg / specifikationer som inte finns i produktdatan
"""

    def _rate_limit(self) -> None:
        """Block if called too soon after the previous LLM call."""
        elapsed = time.monotonic() - self.__class__._last_call_time
        wait = self._CALL_INTERVAL - elapsed
        if wait > 0:
            logger.debug(f"Rate limiting: sleeping {wait:.2f} s")
            time.sleep(wait)
        self.__class__._last_call_time = time.monotonic()

    def _call_llm_with_retry(self, prompt: str) -> dict:
        """Call the LLM with exponential backoff on failure."""
        for attempt in range(1, self._MAX_RETRIES + 1):
            self._rate_limit()
            try:
                completion = self.client.chat.completions.create(
                    model="llama-3.3-70b-versatile",
                    messages=[
                        {"role": "system", "content": self.SYSTEM_PROMPT},
                        {"role": "user",   "content": prompt},
                    ],
                    temperature=0.3,
                    max_tokens=500,
                )
                raw = completion.choices[0].message.content.strip()
                if not raw:
                    raise ValueError("Empty response from model")
                logger.debug(f"Raw LLM response:\n{raw}")
                return self._parse_output(raw)

            except Exception as exc:
                wait = 2 ** attempt   # 2s, 4s, 8s
                if attempt < self._MAX_RETRIES:
                    logger.warning(
                        f"LLM call failed (attempt {attempt}/{self._MAX_RETRIES}): "
                        f"{exc} — retrying in {wait} s"
                    )
                    time.sleep(wait)
                else:
                    logger.error(f"LLM call failed after {self._MAX_RETRIES} attempts: {exc}")
                    return {"error": str(exc)}

        return {"error": "Max retries exceeded"}   # unreachable, satisfies type checkers

    def _parse_output(self, raw: str) -> dict:
        """
        Parse the structured output from the LLM.

        The model is instructed to produce exactly:
            SUBTITLE: ...
            BULLETS:
            - ...
            - ...
            DESCRIPTION: ...

        We match section headers case-insensitively so minor formatting
        deviations (e.g. 'Subtitle:' vs 'SUBTITLE:') don't silently drop data.
        """
        result = {"subtitle": "", "bullets": [], "description": "", "raw": raw}
        mode   = None

        for line in raw.splitlines():
            stripped = line.strip()
            if not stripped:
                continue

            upper = stripped.upper()

            if upper.startswith("SUBTITLE:"):
                result["subtitle"] = stripped.split(":", 1)[1].strip()
                mode = None

            elif upper.startswith("BULLETS:"):
                mode = "bullets"

            elif upper.startswith("DESCRIPTION:"):
                result["description"] = stripped.split(":", 1)[1].strip()
                mode = "description"

            elif mode == "bullets" and stripped.startswith("-"):
                result["bullets"].append(stripped.lstrip("- ").strip())

            elif mode == "description":
                # Continuation lines of a multi-line description.
                # Stop if we hit what looks like a new section header.
                if ":" in stripped and stripped.split(":")[0].upper() in (
                    "SUBTITLE", "BULLETS", "DESCRIPTION", "NOTE", "NOTES"
                ):
                    mode = None
                else:
                    result["description"] += " " + stripped

        # Warn if we got an empty result — the caller can decide what to do.
        if not result["subtitle"] and not result["description"]:
            logger.warning("Parser returned empty result — raw output logged above")

        return result


# ── Output formatter ───────────────────────────────────────────────────────────

def format_output(result: dict, url: str = "") -> str:
    if "error" in result:
        return f"FEL: {result['error']}"
    lines = ["\n" + "=" * 70]
    if url:
        lines.append(f"URL         : {url}")
    lines.append(f"SUBTITLE    : {result.get('subtitle', '')}")
    lines.append("BULLETS     :")
    for b in result.get("bullets", []):
        lines.append(f"  - {b}")
    lines.append(f"DESCRIPTION :\n  {result.get('description', '')}")
    lines.append("=" * 70)
    return "\n".join(lines)


# ── Public API ─────────────────────────────────────────────────────────────────

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
        "product_name":       "TP-link Tapo C545D övervakningskamera",
        "subtitle":           "Dubbla linser – en kamera",
        "brand":              "TP-link",
        "article_number":     "69980",
        "category_path":      "Säkerhet & övervakning > Kameraövervakning > Övervakningskameror",
        "price_current":      799.0,
        "price_original":     999.0,
        "price_discount_pct": 20.0,
        "price_type":         "campaign",
        "usps": [
            "Dubbla 2K-linser med synkroniserad AI-spårning",
            "Fullfärgsnattseende och 99 dB-siren",
            "IP66-klassad för utomhusbruk året runt",
        ],
        "short_description": (
            "Tapo C545D kombinerar en fast vidvinkellins och en rörlig telefoto-lins. "
            "Vidvinkellinsen ger helhetsbild medan AI zoomar in och följer rörelser."
        ),
        "long_description": (
            "Bevakar uppfarten, trädgården eller garaget med både helhetsbild och "
            "detaljskärpa utan att behöva flera kameror. "
            "Fullfärgsnattseende ger tydliga bilder i mörker."
        ),
        "rating": 4.5,
        "number_of_ratings": 42,
    }, ensure_ascii=False)

    result = generate_description_from_json(sample_json)
    print(format_output(result))
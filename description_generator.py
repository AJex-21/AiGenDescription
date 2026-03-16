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


# ── Buyer personas ─────────────────────────────────────────────────────────────
# Keys are lowercase substrings matched against the product's category_path.
# ORDER MATTERS: more specific keys must appear before broader ones.
# All keys are verified stems that match real kjell.com category path strings,
# including both singular and plural Swedish forms.

BUYER_PERSONAS = {

    # ── Säkerhet & övervakning ─────────────────────────────────────────────────
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

    # ── TV-spel & gaming ───────────────────────────────────────────────────────
    "gaming-headset": (
        "Spelaren vill höra varje steg och kommunicera tydligt med laget. "
        "Surroundljud, mikrofonkvalitet och komfort under långa sessioner är avgörande. "
        "De spelar på en specifik plattform – PC, PS5 eller Xbox – och vill veta "
        "att produkten faktiskt är kompatibel."
    ),
    "gaming-mus": (
        "Spelaren vill ha precis kontroll och snabb respons. "
        "DPI-omfång, polling rate och hur musen känns i handen under intensiva pass "
        "är det som avgör. Kabelanslutning föredras av de som vill ha noll latens."
    ),
    "gaming-tangentbord": (
        "Spelaren vill ha snabba och pålitliga knapptryckningar. "
        "Mekaniska switchar, RGB-belysning och anti-ghosting är de tre "
        "frågorna de ställer."
    ),
    "spelkonsol": (
        "Kunden vill spela de senaste spelen på storskärm. "
        "De jämför exklusiva spel, prestanda och pris. "
        "Kompatibilitet med befintliga spel och tillbehör spelar roll."
    ),
    "gaming": (
        "Spelaren söker utrustning som ger konkreta fördelar i spelet "
        "eller gör upplevelsen mer immersiv och bekväm."
    ),

    # ── Dator ──────────────────────────────────────────────────────────────────
    "webbkamera": (
        "Kunden jobbar hemifrån eller streamar och vill se bra ut på video. "
        "Upplösning, autofokus och bildfrekvens är avgörande. "
        "Plug-and-play utan drivrutinsinstallation föredras."
    ),
    "laptop": (
        "Kunden söker en bärbar dator för arbete, studier eller hemmabruk. "
        "De väger prestanda mot pris och vill veta om den klarar det de planerar "
        "att använda den till – videosamtal, dokument, enkel bildredigering."
    ),
    "tangentbord": (
        "Kunden skriver mycket och vill ha bättre ergonomi eller skrivupplevelse. "
        "För gaming handlar det om svarstid och RGB. "
        "För kontor handlar det om tyst typkänsla och trådlöshet."
    ),
    "mus": (
        "Kunden vill ha bättre precision eller komfort. "
        "Gamers bryr sig om DPI och svarstid. "
        "Kontorsanvändare bryr sig om grepp och om den är trådlös."
    ),
    "skarm": (
        "Kunden vill ha en större eller bättre skärm. "
        "De jämför upplösning, bildfrekvens och storlek mot pris. "
        "Gamers vill ha låg input lag. Kontorsanvändare prioriterar färgåtergivning."
    ),
    "ssd": (
        "Kunden vill snabba upp sin dator eller få mer lagring. "
        "Läs- och skrivhastighet samt kapacitet i förhållande till pris är avgörande."
    ),
    "harddisk": (
        "Kunden har slut på lagringsutrymme eller vill säkerhetskopiera. "
        "Kapacitet, hastighet och om den är portabel eller stationär avgör."
    ),
    "skrivare": (
        "Kunden behöver skriva ut hemma. De vill veta sidkostnad per utskrift "
        "och om den stödjer trådlös utskrift från telefon och dator."
    ),
    "dator": (
        "Kunden söker datortillbehör som gör arbets- eller spelupplevelsen bättre. "
        "Prestanda, kompatibilitet och enkel installation är viktigast."
    ),

    # ── Belysning & lampor ─────────────────────────────────────────────────────
    "utomhusbelysning": (
        "Kunden vill belysa trädgård, uppfart eller entré – för säkerhetens "
        "eller stämningens skull. Rörelsesensor, solcellsdrift och "
        "vattentålighet är de viktigaste funktionerna."
    ),
    "skrivbordslampa": (
        "Kunden arbetar eller studerar och vill ha bra arbetsbelysning. "
        "Justerbar ljusstyrka, färgtemperatur och att den inte tröttar ut "
        "ögonen är avgörande. USB-laddning i foten är ett plus."
    ),
    "led-lamp": (
        "Kunden byter ut gamla glödlampor eller halogener. "
        "Rätt sockel, rätt färgtemperatur och lång livslängd. "
        "Energibesparing jämfört med vad som byts ut är ett starkt argument."
    ),
    "lampor": (
        "Kunden söker belysning för ett specifikt syfte – arbete, stämning, "
        "säkerhet eller dekoration. Rätt ljus för rätt plats."
    ),

    # ── Smarta hem ─────────────────────────────────────────────────────────────
    "robotdammsugare": (
        "Kunden vill slippa dammsuga. De vill att golven är rena utan att de "
        "behöver göra något. De undrar om den klarar deras golvtyp, husdjurshår "
        "och mattor – och om den hittar hem igen. En station som tömmer sig "
        "själv är ett mycket starkt argument."
    ),
    "smart-belysning": (
        "Kunden vill styra ljuset hemifrån telefonen eller med röst. "
        "De vill skapa stämning och automatisera lampor. "
        "Kompatibilitet med befintligt system – Hue, IKEA, Google, Apple – avgör."
    ),
    "smart-plugg": (
        "Kunden vill göra vanliga apparater smarta utan att byta ut dem. "
        "Slå av och på via app och schemalägga. "
        "Maxeffekt och om den mäter energiförbrukning är relevanta frågor."
    ),
    "smart-hogtalare": (
        "Kunden vill ha en röstassistent i rummet för musik, timers och "
        "smarthemsstyrning. Vilket ekosystem de redan är i – "
        "Google, Amazon eller Apple – avgör vilket alternativ som passar."
    ),
    "smarta hem": (
        "Kunden bygger eller utökar sitt smarta hem. De söker enheter som "
        "fungerar med befintligt ekosystem och ger verklig nytta i vardagen – "
        "automatisering, energibesparing eller ökad komfort."
    ),

    # ── Ljud & bild ────────────────────────────────────────────────────────────
    "sovhorlurar": (
        "Kunden störs av ljud på natten – partner, grannar, hotell eller pendling. "
        "De prioriterar passform för sidosovare, hur länge de orkar ha dem på sig "
        "och hur effektivt de blockerar eller maskerar störande ljud."
    ),
    "brusreducerande": (
        "Kunden pendlar dagligen eller arbetar i öppen kontorsmiljö. "
        "De vill stänga ute omgivningsljud och fokusera på musik, podcast eller arbete. "
        "ANC-kvalitet och batteritid under en hel arbetsdag är avgörande."
    ),
    "sporthorlurar": (
        "Kunden tränar regelbundet – gym, löpning eller cykling. "
        "De behöver hörlurar som sitter kvar oavsett rörelseintensitet "
        "och som överlever svettiga pass. IP-klassning och passform avgör."
    ),
    "airpods": (
        "Kunden har iPhone och vill ha hörlurar som fungerar direkt – "
        "ingen parning, inga inställningar. De jämför mot föregående "
        "AirPods-generation och vill veta vad som faktiskt är bättre."
    ),
    "tradlosa bluetooth": (
        "Kunden vill ha ett pålitligt vardagspar för pendling, promenader "
        "och hemmabruk. De är prismedvetna och vill ha bra värde utan att "
        "kompromissa med batteritid och stabil anslutning."
    ),
    "true-wireless": (
        "Kunden vill ha helt trådlösa hörlurar utan kabel. "
        "Total batteritid inklusive etui och hur bra de sitter är avgörande."
    ),
    "in-ear": (
        "Kunden söker enkla hörlurar som fungerar – backup, träning eller första par. "
        "Bra ljud för priset och en passform som håller."
    ),
    "headset": (
        "Kunden behöver hörlurar med mikrofon för samtal, videomöten eller gaming. "
        "Mikrofonkvaliteten är minst lika viktig som ljudet – "
        "tydlig röst åt båda håll utan bakgrundsbrus."
    ),
    "soundbar": (
        "Kunden är trött på tv:ns inbyggda högtalare men vill inte ha ett "
        "fullständigt surroundsystem. Hur mycket bättre det låter och "
        "hur enkel installationen är – det är de två frågorna."
    ),
    "hogtalare": (
        "Kunden vill ha ljud i ett rum utan kabeldragning. "
        "Batteritid, vattentålighet och ljudkvalitet i förhållande till pris avgör."
    ),
    "streaming-mediaspelare": (
        "Kunden vill göra sin befintliga tv smart utan att köpa en ny. "
        "4K-stöd, enkel installation och stabil wifi-anslutning är avgörande."
    ),
    "minneskort": (
        "Kunden har kamera, drönare, dashcam eller mobil som ständigt går fullt. "
        "Kompatibilitet med enheten först, skrivhastighet för video sedan."
    ),
    "kamera": (
        "Kunden vill fånga minnen enkelt och med bra resultat. "
        "För direktbildskameror handlar det om den sociala upplevelsen "
        "att få en bild i handen direkt."
    ),
    "mikrofon": (
        "Kunden skapar innehåll – YouTube, podcast, stream eller videomöten. "
        "Tydligt ljud utan bakgrundsbrus och enkel anslutning till enhet. "
        "Plug-and-play föredras framför komplicerad setup."
    ),
    "radio": (
        "Kunden vill lyssna på radio utan internet eller elnät. "
        "Viktigt vid strömavbrott, friluftsliv och camping. "
        "Vevladdning och solcell ger extra trygghet."
    ),
    "skivspelare": (
        "Kunden lyssnar på vinyl och vill ha bra återgivning av sin skivsamling. "
        "De värdesätter analog ljudkvalitet och vill att skivan behandlas väl."
    ),
    "cd-spelare": (
        "Kunden har en cd-samling och vill lyssna på den hemma eller på resan. "
        "Enkelhet och portabilitet är avgörande."
    ),
    "musikmottagare": (
        "Kunden vill trådlöst strömma musik till befintligt stereo- eller billjudsystem. "
        "Enkel installation och stabil Bluetooth-anslutning är allt som krävs."
    ),
    "rengoring": (
        "Kunden vill hålla skärmar och elektronik i bra skick utan risk för repor. "
        "Komplett kit som fungerar på alla ytor och är enkelt att använda."
    ),
    "ljud": (
        "Kunden vill förbättra sin ljudupplevelse hemma eller på språng. "
        "De söker ett konkret lyft i kvalitet eller funktion jämfört med idag."
    ),

    # ── Mobilt ─────────────────────────────────────────────────────────────────
    "powerbank": (
        "Kunden reser ofta eller är mycket ute och kan inte alltid ladda. "
        "De vill ha kapacitet för en hel dag eller mer utan tillgång till vägguttag. "
        "Vikt och storlek spelar roll för om den faktiskt tas med."
    ),
    "mobilskal": (
        "Kunden har köpt en ny telefon och vill skydda den direkt. "
        "Skydd mot tapp utan att telefonen känns klumpig i fickan. "
        "Tunnhet och grepp är viktigast."
    ),
    "skarmskydd": (
        "Kunden är rädd för att spricka skärmen. "
        "Skydd som inte påverkar touchkänslan och enkel montering utan luftbubblor."
    ),
    "mobilt": (
        "Kunden söker mobiltillbehör som gör telefonen mer användbar i vardagen – "
        "skydd, laddning, hantering eller konnektivitet."
    ),

    # ── Nätverk ────────────────────────────────────────────────────────────────
    "mesh": (
        "Kunden har ett större hem eller flera våningar med dålig täckning. "
        "De vill eliminera döda zoner en gång för alla med ett system "
        "som är enkelt att ställa in och hantera via app."
    ),
    "router": (
        "Kunden har dåligt wifi hemma – döda zoner, dålig räckvidd i tjocka väggar "
        "eller för många enheter som tävlar om bandbredd. "
        "De vill ha stabilt internet i hela hemmet utan att bli nätverkstekniker."
    ),
    "switch": (
        "Kunden vill koppla upp fler enheter med kabel för stabilare anslutning. "
        "Antal portar och gigabit-stöd är det enda som spelar roll."
    ),
    "natverkskabel": (
        "Kunden drar kabel för stabilare och snabbare anslutning än wifi. "
        "Rätt kategori för sin hastighet och tillräcklig längd."
    ),
    "natverk": (
        "Kunden söker en lösning för bättre och mer pålitlig internetuppkoppling "
        "hemma eller på kontoret."
    ),

    # ── El & verktyg ───────────────────────────────────────────────────────────
    "multimeter": (
        "Kunden arbetar med el – hobbyist, elektriker eller tekniker. "
        "Mätnoggrannhet, säkerhetsklass och mätomfång är avgörande."
    ),
    "lodning": (
        "Kunden löder elektronik för hobbyprojekt eller reparation. "
        "Stabil temperatur, snabb uppvärmning och god kontrollerbarhet."
    ),
    "ficklampa": (
        "Kunden vill ha pålitlig belysning i mörker – vid strömavbrott, "
        "friluftsliv eller i verkstaden. Ljusstyrka i lumen, räckvidd "
        "och batteritid är avgörande. Vattentålighet vid utomhusbruk."
    ),
    "batteri": (
        "Kunden behöver ersättningsbatterier till fjärrkontroller, ficklampor "
        "eller leksaker. Pålitliga batterier som håller länge. "
        "Låg självurladdning är viktigt för sällanvändarenheter."
    ),
    "el": (
        "Kunden söker elektriska komponenter, verktyg eller tillbehör "
        "för ett specifikt projekt eller reparation."
    ),

    # ── Kablar & kontakter ─────────────────────────────────────────────────────
    "laddkabel": (
        "Kunden behöver ny laddkabel – gammal är sönder eller de vill ha en extra. "
        "Den ska tåla daglig användning och ladda i rätt hastighet för deras enhet."
    ),
    "hdmi": (
        "Kunden kopplar ihop tv, dator, konsol eller projektor. "
        "Rätt HDMI-version för sin upplösning och bildfrekvens – "
        "2.1 för 4K/120Hz, 2.0 för 4K/60Hz."
    ),
    "forlangningssladd": (
        "Kunden har för få vägguttag på rätt ställe. "
        "Rätt antal uttag, rätt kabellängd och USB-laddning i samma enhet. "
        "Överspänningsskydd ger extra trygghet."
    ),
    "kablar": (
        "Kunden behöver rätt kabel för att koppla ihop sina enheter. "
        "Rätt kontakttyp, rätt längd och rätt hastighetsspecifikation."
    ),

    # ── Kontor ─────────────────────────────────────────────────────────────────
    "ergonomi": (
        "Kunden arbetar mycket vid dator och känner av nackspärr, ryggvärk "
        "eller handledsbesvär. De söker utrustning som minskar belastningen – "
        "justeringsmöjligheter och rörelsefrihet är avgörande."
    ),
    "skanner": (
        "Kunden digitaliserar dokument, foton eller kvitton. "
        "Upplösning, automatisk dokumentmatning och medföljande programvara avgör."
    ),
    "kontor": (
        "Kunden söker kontorsutrustning för ett effektivare och bekvämare arbete – "
        "organisation, ergonomi eller produktivitet."
    ),

    # ── Hem & fritid ───────────────────────────────────────────────────────────
    "halsa": (
        "Kunden bryr sig om sin hälsa och vill ha ett enkelt sätt att "
        "mäta eller följa upp sin hälsa i vardagen utan komplicerade rutiner."
    ),
    "barn": (
        "Föräldern söker en produkt till sitt barn. "
        "Säkerhet, ålderslämplighet och hög hållbarhet är viktigast."
    ),
    "hem": (
        "Kunden söker produkter som gör hemlivet enklare, snyggare "
        "eller mer funktionellt."
    ),

    # ── Top-level category fallbacks ──────────────────────────────────────────
    # These catch any product whose subcategory has no specific persona above.
    "belysning": (
        "Kunden söker belysning för ett specifikt syfte – arbete, stämning, "
        "säkerhet eller dekoration. Rätt ljus för rätt plats."
    ),
    "tv-spel": (
        "Kunden söker spelrelaterad utrustning eller ett specifikt spel. "
        "Plattformskompatibilitet och vad som faktiskt förbättrar spelupplevelsen "
        "är de viktigaste frågorna."
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
        .replace("\xe5", "a")  # å
        .replace("\xe4", "a")  # ä
        .replace("\xf6", "o")  # ö
        .replace("\xe9", "e")  # é
    )


def get_persona(category_path: str) -> str:
    """Return the most specific buyer persona matching the category path."""
    path_norm = _normalize(category_path)
    for keyword, persona in BUYER_PERSONAS.items():
        if _normalize(keyword) in path_norm:
            return persona
    return DEFAULT_PERSONA


# ── Few-shot examples ──────────────────────────────────────────────────────────
# Three real approved descriptions from kjell.com, covering three different
# product types and price points. The model calibrates tone and format to these.

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
  Köparprofil: Apple-användare som jämför mot föregående generation, vill veta vad som är nytt
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
  Köparprofil: Vill bevaka uppfart, trädgård eller garage med överblick och detaljskärpa
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
        return cls(**{k: v for k, v in data.items() if k in cls.__dataclass_fields__})

    def to_prompt_dict(self) -> dict:
        price_str = f"{self.price_current:.0f} kr" if self.price_current else "-"
        original_str = f"{self.price_original:.0f} kr" if self.price_original else "-"
        discount_str = f"{self.price_discount_pct:.0f}%" if self.price_discount_pct else None

        price_line = price_str
        if original_str and original_str != price_str:
            price_line += f" (ord. {original_str})"
        if discount_str and self.price_discount_pct and self.price_discount_pct > 0:
            price_line += f" — {discount_str} rabatt"

        return {
            "Produktnamn":    self.product_name,
            "Varumärke":      self.brand,
            "Kategori":       self.category_path,
            "Pris":           price_line,
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

    def __init__(self):
        api_key = os.getenv("Groq_API_Key") or os.getenv("GROQ_API_KEY")
        if not api_key:
            raise ValueError("GROQ_API_KEY not found in environment (.env)")
        self.client = Groq(api_key=api_key)

    def generate(self, specs_json: str, url: str = "") -> dict:
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

DESCRIPTION: [2–5 meningar. Max 90 ord. Börja INTE med produktnamnet. Förklara hur den viktigaste funktionen löser ett konkret problem för köparprofilen ovan. Använd specifika vardagsscenarier om de finns i produktdatan. Inga vaga fraser. Inga kundbetyg. Ingen CTA. Inga meningar som slutar med "kjell.com".]

FÖRBJUDNA FRASER – skriv aldrig:
"ett bra val" / "passar perfekt" / "hög kvalitet" / "ett säkert val" /
"Nu till kampanjpris" / kundbetyg / recensioner / specifikationer som inte finns i produktdatan
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
                max_tokens=500,
            )

            raw = completion.choices[0].message.content.strip()
            logger.debug(f"Raw response: {raw}")

            if not raw:
                return {"error": "Tom respons från modellen"}

            return self._parse_output(raw)

        except Exception as exc:
            logger.error(f"Groq API error: {exc}")
            return {"error": str(exc)}

    def _parse_output(self, raw: str) -> dict:
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


# ── Output formatter ───────────────────────────────────────────────────────────

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
            "Fullfärgsnattseende ger tydliga bilder i mörker. "
            "Den inbyggda 99 dB-sirenen aktiveras manuellt eller automatiskt."
        ),
        "rating": 4.5,
        "number_of_ratings": 42,
    }, ensure_ascii=False)

    result = generate_description_from_json(sample_json)
    print(format_output(result))
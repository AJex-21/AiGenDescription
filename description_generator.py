import requests
import json
import os
from typing import Dict, Any, Optional
from groq import Groq
from dotenv import load_dotenv
import logging
from dataclasses import dataclass
from pathlib import Path

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

load_dotenv()

@dataclass
class ProductSpecs:
    """Structured product specs for AI input"""
    title: Optional[str] = None
    category: Optional[str] = None
    key_specs: Dict[str, str] = None
    full_specs: Dict[str, Dict[str, str]] = None
    
    def to_json(self) -> str:
        return json.dumps(self.__dict__, ensure_ascii=False, indent=2)

class DescriptionGenerator:
    def __init__(self):
        self.client = Groq(api_key=os.getenv("Groq_API_Key"))
        if not self.client.api_key:
            raise ValueError("GROQ_API_KEY not found in environment")
    
    def generate(self, specs_json: str, product_url: str = "") -> str:
        """Generate description from JSON specs"""
        try:
            specs_data = json.loads(specs_json)
        except json.JSONDecodeError as e:
            logger.error(f"Invalid JSON: {e}")
            return "ERROR: Invalid specs JSON format"
        
        prompt_data = self._prepare_prompt_data(specs_data)
        
        # ✨ CHANGE 1: Extract SEO keywords via LLM before building the prompt
        seo_keywords = self._extract_seo_keywords_via_llm(specs_data)
        logger.info(f"SEO keywords extracted: {seo_keywords}")
        
        # ✨ CHANGE 2: Pass seo_keywords into _build_prompt
        prompt = self._build_prompt(prompt_data, product_url, seo_keywords)
        
        return self._call_llm(prompt)
    
    def _prepare_prompt_data(self, specs_data: Dict[str, Any]) -> Dict[str, Any]:
        """Extract most relevant specs for marketing"""
        key_features = {}
        
        priority_keys = {
            'Energiklass': 'energy_class',
            'Kapacitet för tvättcykel (kg)': 'capacity',
            'Centrifugeringshastighet (RPM)': 'spin_speed',
            'Programlista': 'programs'
        }
        
        for swedish_key, english_key in priority_keys.items():
            for group_name, specs in specs_data.items():
                if isinstance(specs, dict) and swedish_key in specs:
                    key_features[english_key] = specs[swedish_key]
                    break
        
        return {
            "full_specs": specs_data,
            "key_features": key_features,
            "top_category": list(specs_data.keys())[0] if specs_data else ""
        }

    # ✨ CHANGE 3: New method — replaces the old hardcoded _extract_seo_keywords
    def _extract_seo_keywords_via_llm(self, specs_data: Dict[str, Any]) -> list[str]:
        """
        Ask the LLM to identify buyer search terms from any product's specs.
        Works for any product category — no hardcoding needed.
        """
        prompt = f"""
Här är produktspecifikationer:
{json.dumps(specs_data, ensure_ascii=False, indent=2)}

Identifiera 6-8 SEO-nyckelord på SVENSKA som en verklig köpare skulle söka på Google.
Fokusera på: produkttyp, nyckelspecar, köparintention.

Svara ENDAST med en kommaseparerad lista. Exempel:
tvättmaskin 10 kg, energiklass A, tyst tvättmaskin, frontmatad tvättmaskin
"""
        try:
            completion = self.client.chat.completions.create(
                model="openai/gpt-oss-120b",
                messages=[{"role": "user", "content": prompt}],
                temperature=0.1,  # Low = focused, predictable output
                max_tokens=80,
            )
            raw = completion.choices[0].message.content.strip()
            return [kw.strip() for kw in raw.split(",")]
        
        except Exception as e:
            logger.error(f"SEO keyword extraction failed: {e}")
            return []  # Safe fallback — description still generates, just without keywords

    # ✨ CHANGE 4: _build_prompt now accepts seo_keywords as a parameter
    def _build_prompt(self, data: Dict[str, Any], url: str, seo_keywords: list[str]) -> str:
        """Engineered prompt optimized for Swedish ecommerce conversion"""
        key_features_str = " | ".join([f"{k}: {v}" for k, v in data["key_features"].items()])
        seo_keywords_str = ", ".join(seo_keywords[:8])
        
        return f"""
Produktspecifikationer: {json.dumps(data["full_specs"], ensure_ascii=False, indent=2)}
Nyckelfunktioner: {key_features_str}

🔍 **SEO-NYCKELORD att väva in naturligt** (använd 3-4 av dessa):
{seo_keywords_str}

Skriv en ÖVERTYGANDE produktbeskrivning för Elgiganten.se på SVENSKA med följande krav:

📋 **STRICTA REGLER**:
1. Max 120 ord
2. 4-6 meningar, max 18 ord per mening
3. Ton: Professionell men varm, familjevänlig
4. Väv in 3-4 SEO-nyckelord NATURLIGT (inte som en lista!)
5. ALLTID nämn 2-3 HERO-FEATURES (energiklass, kapacitet, program)
6. Avsluta med CTA: "Upptäck [produkt] hos Elgiganten idag!"

🎯 **FÖRMÅNER-FOKUS** (inte bara siffror):
- Energiklass A = "lägre elräkning"
- Hög kapacitet = "tvättar hela familjens tvätt på en gång"
- Många program = "perfekt för hela familjen"

📝 **EXAKT FORMAT**:
"[Produktnamn] gör [huvudförmån]. [Feature 1] ger dig [förmån 1].
[Feature 2] sparar [förmån 2]. [Feature 3] förenklar [huvudproblem].
Upptäck [produkt] hos Elgiganten idag!"
"""
    
    def _call_llm(self, prompt: str) -> str:
        """Debug version - shows EXACTLY what Groq returns"""
        try:
            completion = self.client.chat.completions.create(
                model="openai/gpt-oss-120b",
                messages=[
                    {"role": "system", "content": "Du är Elgigantens copywriter."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.3,
                max_tokens=400,
            )
            
            raw_content = completion.choices[0].message.content
            print(f"🔍 RAW GROQ RESPONSE: '{raw_content}'")
            print(f"📏 LENGTH: {len(raw_content)} chars")
            
            if not raw_content or raw_content.strip() == "":
                return "❌ EMPTY RESPONSE FROM GROQ - Check API key or quota"
            
            result = raw_content.strip()
            return f"\n{'='*60}\n{result}\n{'='*60}\n"
            
        except Exception as e:
            print(f"❌ GROQ ERROR: {e}")
            return f"❌ GROQ FAILED: {str(e)}"


def generate_description_from_url(url: str) -> str:
    from website import GetSpecs
    specs_json = GetSpecs(url)
    generator = DescriptionGenerator()
    return generator.generate(specs_json, url)

def generate_description_from_json(specs_json: str) -> str:
    generator = DescriptionGenerator()
    return generator.generate(specs_json)

if __name__ == "__main__":
    url = "https://www.elgiganten.se/product/vitvaror/tvatt-tork/tvattmaskin/electrolux-serie-600-tvattmaskin-efi622ex4e105kg/966285"
    print("=== FROM URL ===")
    desc1 = generate_description_from_url(url)
    print(desc1)
    
    print("\n=== FROM JSON ===")
    with open("product_specs.json", "r", encoding="utf-8") as f:
        specs = f.read()
    desc2 = generate_description_from_json(specs)
    print(desc2)
import requests
import json
import os
from typing import Dict, Any, Optional
from groq import Groq
from dotenv import load_dotenv
import logging
from dataclasses import dataclass
from pathlib import Path

# Setup logging
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
        
        # Extract key info for prompt
        prompt_data = self._prepare_prompt_data(specs_data)
        
        prompt = self._build_prompt(prompt_data, product_url)
        
        return self._call_llm(prompt)
    
    def _prepare_prompt_data(self, specs_data: Dict[str, Any]) -> Dict[str, Any]:
        """Extract most relevant specs for marketing"""
        key_features = {}
        
        # Prioritize hero features for appliances
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
    
    def _build_prompt(self, data: Dict[str, Any], url: str) -> str:
        """Engineered prompt optimized for Swedish ecommerce conversion"""
        key_features_str = " | ".join([f"{k}: {v}" for k, v in data["key_features"].items()])
        
        return f"""
Produktspecifikationer: {json.dumps(data["full_specs"], ensure_ascii=False, indent=2)}
Nyckelfunktioner: {key_features_str}

Skriv en ÖVERTYGANDE produktbeskrivning för Elgiganten.se på SVENSKA med följande krav:

📋 **STRICTA REGELR**:
1. Max 120 ord (räknas automatiskt)
2. 4-6 meningar, max 18 ord per mening
3. Ton: Professionell men varm, familjevänlig
4. ALLTID nämn 2-3 HERO-FEATURES (energiklass, kapacitet, program)
5. Avsluta med CTA: "Upptäck [produkt] hos Elgiganten idag!"

🎯 **FÖRMÅNER-FOKUS** (inte siffror):
- Energiklass A = "lägre elräkning"
- Hög kapacitet = "tvättar mer på en gång" 
- Många program = "perfekt för hela familjen"

📝 **EXAKT FORMAT**:
"[Produktnamn] gör [huvudförmån]. [Feature 1] ger dig [förmån 1]. 
[Feature 2] sparar [förmån 2]. [Feature 3] förenklar [huvudproblem]. 
Upptäck [produkt] hos Elgiganten idag!"

Använd specifikationerna ovan för att identifiera de 3 mest säljande egenskaperna.
"""
    
    def _call_llm(self, prompt: str) -> str:
        """Debug version - shows EXACTLY what Groq returns"""
        try:
            completion = self.client.chat.completions.create(
                model="openai/gpt-oss-120b",  # ← Changed model (more reliable)
                messages=[
                    {"role": "system", "content": "Du är Elgigantens copywriter."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.3,
                max_tokens=400,
            )
            
            # DEBUG: Print raw response
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


# Updated main functions
def generate_description_from_url(url: str) -> str:
    """Legacy function - works with URLs"""
    from website import GetSpecs  # Your scraper
    specs_json = GetSpecs(url)
    generator = DescriptionGenerator()
    return generator.generate(specs_json, url)

def generate_description_from_json(specs_json: str) -> str:
    """NEW: Works directly with JSON input"""
    generator = DescriptionGenerator()
    return generator.generate(specs_json)

# Example usage
if __name__ == "__main__":
    # Option 1: From URL (your old workflow)
    url = "https://www.elgiganten.se/product/vitvaror/tvatt-tork/tvattmaskin/electrolux-serie-600-tvattmaskin-efi622ex4e105kg/966285"
    print("=== FROM URL ===")
    desc1 = generate_description_from_url(url)
    print(desc1)
    
    # Option 2: From JSON file
    print("\n=== FROM JSON ===")
    with open("product_specs.json", "r", encoding="utf-8") as f:
        specs = f.read()
    desc2 = generate_description_from_json(specs)
    print(desc2)

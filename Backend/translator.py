import os
import json

from dotenv import load_dotenv
from google import genai


# ==========================================
# SETUP
# ==========================================

load_dotenv()

api_key = os.getenv("GEMINI_API_KEY")

print("API key found:", bool(api_key))

client = genai.Client(api_key=api_key)


# ==========================================
# TRANSLATION
# ==========================================

def translate_text(text, target_language):

    prompt = f"""
You are a professional e-commerce product translator.

Your task is to detect the source language and translate the
product description into {target_language}.

Rules:

- Detect the source language automatically.
- Preserve the original meaning.
- Do not add information that is not present in the original.
- Do not remove information.
- Keep product names unchanged.
- Keep brand names unchanged.
- Keep model numbers and article numbers unchanged.
- Preserve HTML tags and their structure.
- Preserve measurements and units.
- Preserve technical specifications such as wattage, voltage,
  IP ratings, dimensions and colour temperatures.
- Use natural language suitable for an e-commerce website.
- Do not add marketing claims.

Return ONLY valid JSON in exactly this format:

{{
    "source_language": "detected language",
    "translation": "translated text"
}}

Product description:

{text}
"""

    response = client.models.generate_content(
        model="gemini-3.8-flash",
        contents=prompt
    )

    result_text = response.text.strip()

    # Remove possible markdown code fences
    if result_text.startswith("```"):
        result_text = result_text.replace("```json", "")
        result_text = result_text.replace("```", "")
        result_text = result_text.strip()

    result = json.loads(result_text)

    return result
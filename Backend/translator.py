import os

from dotenv import load_dotenv
from google import genai
from pydantic import BaseModel


# ==========================================
# SETUP
# ==========================================

load_dotenv()

api_key = os.getenv("GEMINI_API_KEY")

print("API key found:", bool(api_key))

client = genai.Client(
    api_key=api_key
)


# ==========================================
# RESPONSE FORMAT
# ==========================================

class TranslationResult(BaseModel):

    source_language: str

    translation: str


# ==========================================
# TRANSLATE
# ==========================================

def translate_text(
    text,
    target_language
):

    prompt = f"""
You are a professional e-commerce product translator.

Your task is to detect the source language and translate the
product description into {target_language}.

Rules:

- Detect the source language automatically.
- Preserve the original meaning and all factual information.
- Do not add information that is not present in the original.
- Do not remove information.
- Correct obvious spelling and grammatical mistakes when translating,
  but never change factual product information.
- Keep product names unchanged.
- Keep brand names unchanged.
- Keep model numbers and article numbers unchanged.
- Preserve HTML tags and their structure.
- Preserve measurements and units.
- Preserve technical specifications such as wattage, voltage,
  IP ratings, dimensions and colour temperatures.
- Use natural language suitable for an e-commerce website.
- Do not add marketing claims.

Product description:

{text}
"""


    # ------------------------------------------
    # GEMINI REQUEST
    # ------------------------------------------

    response = client.models.generate_content(

        model="gemini-3.8-flash",

        contents=prompt,

        config={
            "response_mime_type": "application/json",
            "response_schema": TranslationResult,
        }
    )


    # ------------------------------------------
    # GET STRUCTURED RESULT
    # ------------------------------------------

    if response.parsed:

        result = response.parsed

    else:

        result = TranslationResult.model_validate_json(
            response.text
        )


    # ------------------------------------------
    # RETURN RESULT
    # ------------------------------------------

    return {
        "source_language":
            result.source_language,

        "translation":
            result.translation
    }
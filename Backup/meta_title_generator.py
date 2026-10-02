"""
Meta title generator for Translate Bot.

This module is intentionally separate from translator.py so that
meta-title generation cannot change or interfere with translation logic.
"""

import asyncio
import os
import threading

from dotenv import load_dotenv
from cursor_sdk import AsyncClient, LocalAgentOptions


load_dotenv()

CURSOR_MODEL = os.getenv("CURSOR_META_TITLE_MODEL", "composer-2.5")
CURSOR_API_KEY = os.getenv("CURSOR_API_KEY")

_thread_local = threading.local()


def _create_cursor_agent(model: str):
    """Create one reusable Cursor agent for the current worker thread."""
    if not CURSOR_API_KEY:
        raise RuntimeError("CURSOR_API_KEY is not configured.")

    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)

    async def create():
        client = await AsyncClient.launch_bridge(workspace=os.getcwd())
        agent = await client.agents.create(
            model=model,
            api_key=CURSOR_API_KEY,
            local=LocalAgentOptions(cwd=os.getcwd()),
        )
        return client, agent

    client, agent = loop.run_until_complete(create())

    _thread_local.cursor_loop = loop
    _thread_local.cursor_client = client
    _thread_local.cursor_agent = agent

    return loop, agent


def _get_cursor_agent(model: str):
    """Reuse the Cursor agent within the current worker thread."""
    current_model = getattr(_thread_local, "cursor_model", None)
    loop = getattr(_thread_local, "cursor_loop", None)
    agent = getattr(_thread_local, "cursor_agent", None)

    if loop is None or agent is None or current_model != model:
        loop, agent = _create_cursor_agent(model)
        _thread_local.cursor_model = model

    return loop, agent


def _run_cursor(prompt: str, model: str | None = None) -> str:
    """Run a prompt through the reusable Cursor agent."""
    selected_model = model or CURSOR_MODEL
    max_attempts = 3

    try:
        loop, agent = _get_cursor_agent(selected_model)
        asyncio.set_event_loop(loop)

        for attempt in range(1, max_attempts + 1):
            run = loop.run_until_complete(agent.send(prompt))
            response_text = loop.run_until_complete(run.text())

            if response_text and str(response_text).strip():
                return str(response_text).strip()

            if attempt < max_attempts:
                print(
                    f"[Meta title] Empty Cursor response from "
                    f"{selected_model} - retry {attempt}/{max_attempts - 1}"
                )

    except Exception as exc:
        raise RuntimeError(
            f"Cursor SDK request failed using {selected_model}: {exc}"
        ) from exc

    raise RuntimeError(
        f"Cursor SDK returned an empty response using {selected_model} "
        f"after {max_attempts} attempts."
    )


def _clean_title(title: str) -> str:
    """Remove common wrapping characters without changing the title itself."""
    title = title.strip()

    if title.startswith("```") and title.endswith("```"):
        title = title[3:-3].strip()

    if len(title) >= 2 and title[0] == title[-1] and title[0] in {'"', "'"}:
        title = title[1:-1].strip()

    return title


def _enforce_product_terminology(
    title: str,
    product_name: str,
    description: str,
) -> str:
    """
    Enforce only terminology mappings explicitly tied to the supplied source.

    This is intentionally conservative: it prevents known product-term drift
    without rewriting arbitrary English words in generated titles.
    """
    source = f"{product_name} {description}".lower()

    if "ljusslang" not in source:
        return title

    replacements = (
        ("light string extension cable", "rope light extension cable"),
        ("string light extension cable", "rope light extension cable"),
        ("light tube extension cable", "rope light extension cable"),
        ("tube light extension cable", "rope light extension cable"),
        ("light hose extension cable", "rope light extension cable"),
        ("hose light extension cable", "rope light extension cable"),
        ("string extension cable", "rope light extension cable"),
        ("tube extension cable", "rope light extension cable"),
        ("hose extension cable", "rope light extension cable"),
        ("light string", "rope light"),
        ("string light", "rope light"),
        ("light tube", "rope light"),
        ("tube light", "rope light"),
        ("light hose", "rope light"),
        ("hose light", "rope light"),
    )

    result = title
    for old_term, new_term in replacements:
        result = result.replace(old_term, new_term)
        result = result.replace(old_term.title(), new_term.title())
        result = result.replace(old_term.upper(), new_term.upper())

    return result


def _shorten_meta_title(title: str, brand: str = "") -> str:
    """Ask Cursor to shorten an over-limit title while preserving key facts."""
    prompt = f"""
Shorten the following e-commerce meta title to a maximum of 60 characters.

META TITLE RULES

1. Maximum 60 characters including spaces.

2. Return ONLY the meta title.
   No explanation, quotation marks, bullets, markdown or character count.

3. Write the title in natural, professional English suitable for an
   English-speaking e-commerce customer.

4. Use the actual English e-commerce/product terminology rather than
   translating the Swedish product name word-for-word.

5. Prioritize the standard English name that a customer would naturally
   use when searching for the product.

6. For example:
   - "växtbelysning" → "grow light"
   - "växtarmatur" → "grow light"
   - "LED-växtbelysning" → "LED grow light"
   - "arbetsbelysning" → "work light"
   - "fasadbelysning" → "outdoor wall light" or "facade light"
   - "takarmatur" → "ceiling light" or "ceiling fixture"
   - "väggarmatur" → "wall light" or "wall fixture"

7. Do NOT use an unnatural literal translation when a standard English
   e-commerce term exists.

8. Preserve the product's brand, model number, product family and important
   identifiers.

9. If an explicit brand is supplied, include it when practical, preferably
   near the beginning of the title.

10. A brand must NEVER be inferred from a model number, product family,
    generic product wording, translated wording or outside knowledge.

11. If no explicit brand is supplied, do not add a brand.

12. Generic words such as "Pro", "Plant", "Smart", "Premium", "Plus",
    "Basic" and similar words are NOT brands unless they are explicitly
    supplied in the Brand field.

13. Prioritize the main product type first, followed by the most useful
    differentiating specification or feature.

14. Include important specifications when they are useful for identifying
    the product, such as:
    - wattage
    - size
    - model number
    - colour
    - connectivity
    - product generation
    - important technical specification

15. Do NOT invent specifications, features, compatibility, materials,
    dimensions, colours, prices or claims.

16. Do not add information merely to reach 60 characters.

17. Avoid generic filler and keyword stuffing.

18. Do not unnecessarily repeat words.

19. Do not use unapproved marketing or selling phrases.

20. Selling phrases may only be selected from the approved selling
    phrase list below. Never invent, modify or create a new selling phrase.

21. No HTML.

22. When shortening a title to fit within 60 characters:
    - Preserve the explicit brand if one was supplied.
    - Preserve the model number.
    - Preserve the main product type.
    - Preserve the most important specification.
    - Remove less important descriptive words first.
    - Do not replace a correct product term with a less accurate generic term.

23. Product terminology should take priority over literal translation.
    For example, if the Swedish product name contains "växtarmatur",
    prefer "grow light" rather than "LED fixture" when the product is
    specifically designed for growing plants.

24. The goal is not to use as many of the 60 available characters as
    possible. The goal is to create a concise, accurate and natural
    English product title that clearly identifies what the product is.
    
25. PRODUCT-SPECIFIC TERMINOLOGY

    For established product terms, use the approved English terminology
    consistently. Do not replace an approved product term with a synonym
    just to make the title sound different.

    For "ljusslang" in the context of flexible LED lighting:
    - "ljusslang" → "rope light"
    - Do NOT use "light string", "string light", "light tube" or
      "light hose" as alternatives.

    Important: when "slang" appears only in a compatibility statement
    such as "Passar till 8-10mm slang", it describes the diameter/type
    of the compatible rope light. Do not use "hose" as the product type.

    Example:
    "Förlängningssladd ljusslang 1m" → "Rope Light Extension Cable 1m"

26. Do not randomly vary established product terminology between
    generations. If the same source term refers to the same product type,
    use the same English terminology consistently.

27. The Brand field is the ONLY source of brand information.

    If a Brand is supplied:
    - Use that exact brand name in the meta title when practical.
    - Do not create, translate, shorten, reinterpret or replace the brand.
    - Do not treat any words from the Product name as a brand.
    - Generic words in the Product name such as "Pro", "Plant",
      "Smart", "Premium", "Plus", "Basic" or similar must not be
      interpreted as a brand unless they are explicitly entered in
      the Brand field.

    If Brand = "Red Goat Electric" and Product name =
    "Pro växt LED armatur 40W FSG", then "Red Goat Electric"
    is the brand and "Pro växt" is product wording.

28. Do not translate generic/product-line words as if they were a
    company or brand name.

    Example:
    Product name: "Pro växt LED armatur 40W FSG"
    Brand: "Red Goat Electric"

    Correct:
    "Red Goat Electric FSG 40W LED Grow Light Full Spectrum"

    Incorrect:
    "Pro Plant LED Grow Light 40W FSG Full Spectrum"
    
29. Separate the brand from the product name conceptually.
    The Brand field identifies the manufacturer/brand.
    The Product name identifies the actual product.
    Never infer a brand from the Product name when a Brand field is
    available.
    
30. PRODUCT TERMINOLOGY AND ACCURACY HAVE PRIORITY

    Product terminology and factual accuracy always take priority over
    marketing phrases.

    Never alter, replace, remove or translate a correct English product
    term just to make room for a selling phrase.

    When a correct product term is already present in the generated title,
    always preserve it unless the complete title would otherwise exceed
    60 characters. A selling phrase must never be the reason for removing
    a correct product term.

    Example:
    Correct product title:
    "Entac Enclosed IP44 Double Switch"

    Do NOT change it to:
    "Entac Encased IP44 Double Switch"

    Do NOT remove "Enclosed" simply to fit a longer selling phrase.

31. SELLING PHRASE PRIORITY

    A selling phrase is optional and has lower priority than:
    - brand
    - model number
    - product name
    - product type
    - important technical specifications
    - correct English product terminology

    If the selling phrase does not fit without removing important product
    information, omit the selling phrase or use a shorter approved phrase.
    
32. When there is enough space for a selling phrase, prefer the most
    appropriate approved phrase that fits naturally.

    If several approved phrases fit, a shorter phrase is preferred when
    using a longer phrase would require removing useful product information.

    Never remove important product information just to use a longer
    selling phrase.


SELLING PHRASE WHEN SHORTENING
- If the current title contains an approved selling phrase, preserve it
  only when the shortened title remains within 60 characters.
- If the current title has no selling phrase, do not add one during
  shortening; shortening is only for correcting an over-limit title.

Explicit brand (use only if provided):
{brand}

Current title:
{title}
""".strip()

    shortened = _clean_title(_run_cursor(prompt))

    if not shortened:
        raise RuntimeError("Cursor returned an empty shortened meta title.")

    if len(shortened) > 60:
        raise RuntimeError(
            f"Cursor could not shorten the meta title to 60 characters: "
            f"{len(shortened)} characters returned."
        )

    return shortened


def generate_meta_title(product_name: str, description: str = "", brand: str = "") -> dict:
    """
    Generate one English e-commerce meta title.

    Returns:
        {
            "title": str,
            "character_count": int,
            "within_limit": bool
        }
    """
    product_name = str(product_name or "").strip()
    description = str(description or "").strip()
    brand = str(brand or "").strip()

    if not product_name:
        raise ValueError("Product name is required.")

    prompt = f"""
Create ONE English meta title for an e-commerce product page.

Requirements:
- Maximum 60 characters including spaces.
- Return ONLY the meta title. No quotation marks, explanation,
  bullets, markdown or character count.
- Use natural, professional English.
- Clearly describe the actual product.
- If an explicit brand is supplied below, include it in the meta title when practical, preferably near the beginning.
- A brand must NEVER be inferred from a model number, product family, generic product wording, translated wording or outside knowledge.
- Words such as "Pro", "Plant", "Smart", "Premium", "Plus", "Basic" or similar generic/product-line wording are NOT brands unless they are explicitly supplied as the brand.
- Preserve the product family, model number and identifiers.
- If no explicit brand is supplied, do not add a brand.
- Prioritize the main product type and one useful differentiator when space allows.
- Preserve important factual specifications when they are part of the product
  name or clearly relevant to identifying the product.
- Do NOT invent specifications, features, compatibility, materials,
  dimensions, colours, prices or claims.
- Do not use generic filler or keyword stuffing.
- Do not use unapproved marketing or selling phrases.
- Selling phrases may only be selected from the approved selling phrase
  list below. Never invent, modify or create a new selling phrase.
- Do not add information merely to reach 60 characters.
- No HTML.


MARKETING / SELLING PHRASE

When the title has enough space, append ONE approved selling phrase at the end.
The title should normally include a selling phrase whenever at least 12
characters remain after the core product information has been preserved.
Choose the shortest suitable approved phrase when necessary.

Approved selling phrases:

PRICE & VALUE
- | Best Price & Great Quality
- | High Quality at Great Prices
- | Affordable & Reliable
- | Great Deals & Fast Delivery
- | Best Value Online

QUALITY & SAFETY
- | Safe & Certified
- | Professional Grade Quality
- | Heavy-Duty & Weatherproof
- | Built to Last – Top Quality
- | Tested & Approved Safety
- | Top Quality
- | Premium Quality
- | High Quality

AVAILABILITY & SHIPPING
- | Quick Delivery & Great Service

SHORT & PUNCHY
- | Buy Online Now
- | Top Rated Quality
- | Shop Best Deals
- | Premium Quality
- | Best Price
- | Great Price
- | Great Value

SELLING PHRASE RULES
- Use at most ONE selling phrase.
- The selling phrase must always be at the end of the title.
- Never exceed 60 characters including the selling phrase.
- Product information always has priority over the selling phrase.
- Never remove a brand, model number, product type or important technical
  specification just to make room for a selling phrase.
- Do not add a selling phrase if doing so would require removing important
  product information or would make the title unnatural.
- If 12 or more characters remain after preserving important product
  information, use one approved phrase whenever one fits.
- If space is limited, prefer a short phrase such as "| Best Price",
  "| Great Price", "| Great Value" or "| Top Quality".
- Do not create or invent selling phrases outside the approved list.
- Do not force a phrase if none fits within 60 characters.

PRODUCT-SPECIFIC TERMINOLOGY

- For established product terms, use the approved English terminology
  consistently. Do not replace an approved product term with a synonym
  just to make the title sound different.

- For "ljusslang" in the context of flexible LED lighting:
  - "ljusslang" → "rope light"
  - Do NOT use "light string", "string light", "light tube" or
    "light hose" as alternatives.

- When "slang" appears only in a compatibility statement such as
  "Passar till 8-10mm slang", it describes the diameter/type of the
  compatible rope light. Do not interpret it as the product type "hose".

- "Förlängningssladd ljusslang" should normally be rendered as
  "Rope Light Extension Cable".

- Do not randomly vary established product terminology between generations.
  If the same source term refers to the same product type, use the same
  English terminology consistently.

FACTUAL CLAIMS
Do not use claims about certifications, testing, approval, ratings,
weatherproofing or other specific product attributes unless the claim is
explicitly supported by the Product name or Product description.
"| Quick Delivery & Great Service" is allowed as a general store-level
selling phrase and does not require product-specific stock information.

Brand (explicitly supplied; may be empty):
{brand}

Product name:
{product_name}

Product description:
{description}
""".strip()

    title = _clean_title(_run_cursor(prompt))
    title = _enforce_product_terminology(title, product_name, description)

    if not title:
        raise RuntimeError("Cursor returned an empty meta title.")

    if len(title) > 60:
        title = _shorten_meta_title(title, brand)
        title = _enforce_product_terminology(title, product_name, description)

    if len(title) > 60:
        raise RuntimeError(
            f"Meta title exceeds 60 characters after terminology enforcement: "
            f"{len(title)} characters returned."
        )

    return {
        "title": title,
        "character_count": len(title),
        "within_limit": len(title) <= 60,
    }

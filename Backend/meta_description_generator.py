"""
Meta description generator for Translate Bot.

This module is intentionally separate from translator.py and
meta_title_generator.py so meta-description generation cannot interfere
with translation or meta-title generation.
"""

import asyncio
import os
import threading
import time

from dotenv import load_dotenv
from cursor_sdk import AsyncClient, LocalAgentOptions


load_dotenv()

CURSOR_MODEL = os.getenv(
    "CURSOR_META_DESCRIPTION_MODEL",
    os.getenv("CURSOR_META_TITLE_MODEL", "composer-2.5"),
)
CURSOR_API_KEY = os.getenv("CURSOR_API_KEY")

# Kept conservative for SEO snippets while leaving room for natural copy.
MAX_META_DESCRIPTION_LENGTH = 155

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
    _thread_local.cursor_model = model

    return loop, agent


def _get_cursor_agent(model: str):
    """Reuse the Cursor agent within the current worker thread."""
    current_model = getattr(_thread_local, "cursor_model", None)
    loop = getattr(_thread_local, "cursor_loop", None)
    agent = getattr(_thread_local, "cursor_agent", None)

    if loop is None or agent is None or current_model != model:
        loop, agent = _create_cursor_agent(model)

    return loop, agent


def _is_transient_cursor_error(exc: Exception) -> bool:
    """
    Return True for errors that may succeed when retried.

    This covers the temporary Cursor/bridge problems seen during larger
    Excel jobs without retrying permanent configuration/authentication errors.
    """
    message = str(exc).lower()

    transient_terms = (
        "database is locked",
        "database locked",
        "sqlite",
        "busy",
        "rate limit",
        "rate-limit",
        "429",
        "too many requests",
        "temporarily unavailable",
        "service unavailable",
        "service busy",
        "timeout",
        "timed out",
        "connection reset",
        "connection aborted",
    )

    return any(term in message for term in transient_terms)


def _run_cursor(prompt: str, model: str | None = None) -> str:
    """Run a prompt through the reusable Cursor agent with transient retries."""
    selected_model = model or CURSOR_MODEL

    # Empty Cursor responses can be transient, especially during larger
    # Excel jobs. Give them one additional attempt and refresh the agent
    # after repeated empty responses without changing the prompt or model.
    max_attempts = 5
    retry_delays = (1.0, 2.0, 4.0, 6.0)

    loop, agent = _get_cursor_agent(selected_model)
    asyncio.set_event_loop(loop)

    last_error = None

    for attempt in range(1, max_attempts + 1):
        try:
            run = loop.run_until_complete(agent.send(prompt))
            response_text = loop.run_until_complete(run.text())

            if response_text and str(response_text).strip():
                return str(response_text).strip()

            last_error = RuntimeError("Cursor returned an empty response.")

            if attempt < max_attempts:
                if attempt == 2:
                    loop, agent = _create_cursor_agent(selected_model)
                    asyncio.set_event_loop(loop)
                    print(
                        f"[Meta description] Empty Cursor responses from "
                        f"{selected_model} - refreshing agent before retry"
                    )

                delay = retry_delays[attempt - 1]
                time.sleep(delay)
                print(
                    f"[Meta description] Empty Cursor response from "
                    f"{selected_model} - retry {attempt}/{max_attempts - 1}"
                )

        except Exception as exc:
            last_error = exc

            if not _is_transient_cursor_error(exc) or attempt >= max_attempts:
                raise RuntimeError(
                    f"Cursor SDK request failed using {selected_model}: {exc}"
                ) from exc

            delay = retry_delays[attempt - 1]
            print(
                f"[Meta description] Temporary Cursor error from "
                f"{selected_model}: {exc} - retrying in {delay:g}s"
            )
            time.sleep(delay)

    raise RuntimeError(
        f"Cursor SDK returned no usable response using {selected_model} "
        f"after {max_attempts} attempts: {last_error}"
    )


def _clean_description(description: str) -> str:
    """Remove common response wrappers without rewriting the copy."""
    description = str(description or "").strip()

    if description.startswith("```") and description.endswith("```"):
        description = description[3:-3].strip()

        if description.lower().startswith("text"):
            description = description[4:].strip()

    if len(description) >= 2:
        if description[0] == description[-1] and description[0] in {'"', "'"}:
            description = description[1:-1].strip()

    # Meta descriptions should be a single snippet, not a multiline block.
    description = " ".join(description.split())

    return description


def _is_invalid_description(description: str) -> bool:
    """Detect clearly unusable Cursor output."""
    normalized = description.strip().lower()

    if not normalized:
        return True

    invalid_values = {
        "nan",
        "none",
        "null",
        "n/a",
        "__",
        "undefined",
        "meta description",
        "meta description:",
    }

    return normalized in invalid_values


def _shorten_meta_description(
    description: str,
    brand: str = "",
    product_name: str = "",
    source_description: str = "",
) -> str:
    """Ask Cursor to shorten an over-limit description without inventing facts."""
    prompt = f"""
Shorten the following e-commerce meta description to a maximum of
{MAX_META_DESCRIPTION_LENGTH} characters including spaces.

META DESCRIPTION SHORTENING RULES

1. Maximum {MAX_META_DESCRIPTION_LENGTH} characters including spaces.

2. Return ONLY the final meta description.
   No explanation, quotation marks, bullets, markdown or character count.

3. Keep the result natural, professional and persuasive for an
   English-speaking e-commerce customer.

4. Preserve the most important product information:
   - explicit brand
   - product type
   - model/product family when useful
   - important technical specifications
   - important product features

5. Remove less important wording before removing important factual
   product information.

6. Do NOT invent specifications, features, compatibility, materials,
   dimensions, colours, prices, certifications or claims.

7. Do not add information merely to reach the character limit.

8. Do not use keyword stuffing.

9. Do not use HTML.

10. Keep the wording concise and natural.

Explicit brand:
{brand}

Product name:
{product_name}

Original product description:
{source_description}

Current meta description:
{description}
""".strip()

    shortened = _clean_description(_run_cursor(prompt))

    if _is_invalid_description(shortened):
        raise RuntimeError(
            "Cursor returned an invalid shortened meta description."
        )

    if len(shortened) > MAX_META_DESCRIPTION_LENGTH:
        # One final strict retry rather than silently cutting the sentence.
        retry_prompt = f"""
Rewrite the following meta description so that it is MAXIMUM
{MAX_META_DESCRIPTION_LENGTH} characters including spaces.

Return ONLY the rewritten description.

Do not invent or remove important product facts.
Keep the product type, brand and key specifications when possible.
Remove secondary wording first.
Do not add marketing claims that are not supported by the source.

Meta description:
{shortened}

Product name:
{product_name}

Brand:
{brand}

Source description:
{source_description}
""".strip()

        shortened = _clean_description(_run_cursor(retry_prompt))

    if len(shortened) > MAX_META_DESCRIPTION_LENGTH:
        raise RuntimeError(
            f"Cursor could not shorten the meta description to "
            f"{MAX_META_DESCRIPTION_LENGTH} characters: "
            f"{len(shortened)} characters returned."
        )

    return shortened


def generate_meta_description(
    product_name: str,
    description: str = "",
    brand: str = "",
) -> dict:
    """
    Generate one English e-commerce meta description.

    Returns:
        {
            "description": str,
            "character_count": int,
            "within_limit": bool
        }
    """
    product_name = str(product_name or "").strip()
    description = str(description or "").strip()
    brand = str(brand or "").strip()

    if not product_name and not description:
        raise ValueError("Product name or description is required.")

    prompt = f"""
Create ONE English meta description for an e-commerce product page.

META DESCRIPTION RULES

1. Maximum {MAX_META_DESCRIPTION_LENGTH} characters including spaces.

2. Return ONLY the meta description.
   No quotation marks, explanation, bullets, markdown or character count.

3. Write natural, professional English for an English-speaking
   e-commerce customer.

4. Summarize what the product is and highlight its most useful
   supported features or specifications.

5. Use information from BOTH the Product name and Product description.
   The Product description may contain important product information
   that is not present in the Product name.

6. If an explicit Brand is supplied, use the exact brand name naturally.
   The Brand field is the ONLY source of brand information.

7. Never infer a brand from the Product name, model number, product
   family, translated wording or outside knowledge.
   If the Brand field is empty, do not introduce a manufacturer or brand
   name as a brand from the Product name or Product description.
   A name or identifier that appears in the Product name may still be
   preserved when necessary to identify the product, but do not present
   it as a brand unless the Brand field confirms it.

8. Preserve important factual product information when useful, such as:
   - model number
   - product type
   - wattage
   - voltage
   - dimensions
   - length
   - colour
   - colour temperature
   - IP rating
   - connectivity
   - compatibility
   - important product features

9. Only include factual information that is supported by the supplied
   Product name or Product description.

10. Do NOT invent specifications, features, compatibility, materials,
    dimensions, colours, prices, certifications, ratings or claims.

11. Do not merely repeat the Product name. Turn the available
    supported facts into a useful, natural sentence.

12. Avoid keyword stuffing and repetitive wording.

13. Do not use generic filler such as:
    "Discover our amazing product"
    "Shop now for the best product"
    "Perfect for all your needs"

14. Do not make unsupported superlative claims such as:
    "best", "number one", "ultimate" or "highest quality".

15. Do not mention shipping, delivery, stock availability or prices
    unless they are explicitly supported by the supplied information.

16. Do not use HTML.

17. The description should normally be one or two natural sentences.

18. Aim for a useful, information-rich description rather than trying
    to fill the character limit.

19. Do not end with an unnecessary call to action if useful product
    information would be lost by including it.

20. The output must be suitable for direct use as an SEO meta description.

21. If the Product name is clearly invalid, empty or consists only of
    placeholder characters such as "__", do not create a generic or
    invented description. Return an empty result.

SOURCE PRIORITY

- Use BOTH the Product name and Product description as source material.
- Treat the Product name as the primary source for the specific product
  variant and its core specifications.
- Use the Product description as a secondary source for additional
  verified features and details.
- Use information from both sources when they are consistent.
- If the Product name and Product description contain conflicting
  variant-specific specifications, do not combine the conflicting values.
- Prefer the Product name for core variant-specific specifications such
  as product type, model, wattage, voltage, dimensions, size, colour,
  colour temperature, connector/socket, quantity and similar variant
  identifiers.
- Product description information that does not conflict with the
  Product name may still be used.
- If the Product description clearly appears to describe another
  product variant, do not use its variant-specific specifications,
  features or claims.
- If there is uncertainty about whether a detail belongs to the
  current product variant, omit that detail rather than guessing.

PRODUCT CODES

- Preserve model numbers, abbreviations and product codes from the
  source data.
- Do not reinterpret product codes or abbreviations such as 1-P, 3-P,
  1P, 3P, CCT, Gen4, T26, C35, P45 or similar codes.
- Do not assume that a product code represents a package quantity,
  product shape, phase count, feature, compatibility or other meaning
  unless that meaning is explicitly supported by the Product name or
  Product description.
- Do not convert a code into a descriptive feature based on outside
  knowledge.
- If a code is important to the product identity, preserve the code
  naturally in the meta description.

CONFLICTING INFORMATION

- If the Product name and Product description contain conflicting
  specifications, do not combine them.
- Prefer the Product name for the specific product variant.
- For example, if the Product name says E27, 4.5W, 2200K but the
  Product description says E14, 4W, 2700K, use E27, 4.5W and 2200K
  and omit the conflicting E14, 4W and 2700K information.
- If the conflicting Product description also contains additional
  product-specific claims or features that appear to belong to the
  conflicting variant, omit those claims and features as well.
- Non-conflicting information from the Product description may still
  be used if it clearly applies to the current product.
- Never combine information from two different variants into one
  description.
- When in doubt, use less information rather than risk describing the
  wrong product.


SOURCE DATA

Brand:
{brand}

Product name:
{product_name}

Product description:
{description}
""".strip()

    generated = _clean_description(_run_cursor(prompt))

    if _is_invalid_description(generated):
        raise RuntimeError("Cursor returned an invalid meta description.")

    if len(generated) > MAX_META_DESCRIPTION_LENGTH:
        generated = _shorten_meta_description(
            generated,
            brand=brand,
            product_name=product_name,
            source_description=description,
        )

    if len(generated) > MAX_META_DESCRIPTION_LENGTH:
        raise RuntimeError(
            f"Meta description exceeds {MAX_META_DESCRIPTION_LENGTH} "
            f"characters: {len(generated)} returned."
        )

    return {
        "description": generated,
        "character_count": len(generated),
        "within_limit": len(generated) <= MAX_META_DESCRIPTION_LENGTH,
    }

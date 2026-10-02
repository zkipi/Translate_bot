import json
import os
import re
from dotenv import load_dotenv
from pydantic import BaseModel
from cursor_sdk import AsyncClient, LocalAgentOptions


# ==========================================
# SETUP
# ==========================================

load_dotenv()

# Cursor SDK
# Uses the Cursor User API key (crsr_...) directly through Agent.prompt().
CURSOR_API_KEY = os.getenv("CURSOR_API_KEY")
CURSOR_MODEL = os.getenv("CURSOR_MODEL", "composer-2.5")
CURSOR_VALIDATOR_MODEL = os.getenv("CURSOR_VALIDATOR_MODEL", "grok-4.7")

print("Cursor SDK API key found:", bool(CURSOR_API_KEY))

# ==========================================
# RESPONSE FORMAT
# ==========================================

class TranslationResult(BaseModel):

    source_language: str

    translation: str


class ValidatorIssue(BaseModel):

    type: str

    severity: str

    explanation: str


class AIValidationResult(BaseModel):

    status: str

    issues: list[ValidatorIssue] = []

    suggested_translation: str | None = None


# ==========================================
# VALIDATION
# ==========================================

def validate_translation(
    original,
    translation,
    target_language=None,
    source_language=None
):

    issues = []


    # ------------------------------------------
    # EMPTY TRANSLATION
    # ------------------------------------------

    if (
        not translation
        or not translation.strip()
    ):

        issues.append(
            "empty_translation"
        )

        return False, issues


    original = str(
        original
    )

    translation = str(
        translation
    )


    # ------------------------------------------
    # INCOMPLETE HTML TAG
    # ------------------------------------------

    if re.search(
        r"<[^>]*$",
        translation,
        re.DOTALL
    ):

        issues.append(
            "incomplete_html_tag"
        )


    # ------------------------------------------
    # INCOMPLETE HTML ATTRIBUTE
    # ------------------------------------------

    if re.search(
        r"(?:style|class|id|href|src)"
        r"\s*=\s*['\"]?$",
        translation,
        re.IGNORECASE
    ):

        issues.append(
            "incomplete_html_attribute"
        )


    # ------------------------------------------
    # HTML TAG STRUCTURE
    # ------------------------------------------

    void_tags = {

        "br",
        "hr",
        "img",
        "input",
        "meta",
        "link",
        "area",
        "base",
        "col",
        "embed",
        "param",
        "source",
        "track",
        "wbr"

    }


    stack = []


    for match in re.finditer(

        r"<\s*(/?)\s*"
        r"([a-zA-Z][\w:-]*)\b"
        r"[^>]*>",

        translation,

        re.DOTALL

    ):

        closing = bool(
            match.group(1)
        )

        tag = match.group(2).lower()


        if tag in void_tags:

            continue


        if closing:

            if (
                not stack
                or stack[-1] != tag
            ):

                issues.append(
                    "html_tag_mismatch"
                )

                break


            stack.pop()


        elif not match.group(
            0
        ).rstrip().endswith("/>"):

            stack.append(tag)


    if stack:

        issues.append(
            "unclosed_html_tag"
        )


    # ------------------------------------------
    # SUSPICIOUSLY SHORT TRANSLATION
    # ------------------------------------------

    original_len = len(
        re.sub(
            r"\s+",
            " ",
            original
        ).strip()
    )


    translation_len = len(
        re.sub(
            r"\s+",
            " ",
            translation
        ).strip()
    )


    if (
        original_len >= 300
        and translation_len
        < original_len * 0.35
    ):

        issues.append(
            "translation_suspiciously_short"
        )


    # ------------------------------------------
    # POSSIBLE LEFTOVER SOURCE LANGUAGE
    # ------------------------------------------

    if target_language and source_language:

        issues.extend(
            detect_leftover_language(
                translation,
                target_language,
                source_language
            )
        )


    # ------------------------------------------
    # DETERMINISTIC CONTENT CHECKS
    # ------------------------------------------

    # These checks are intentionally mechanical. They run locally before
    # Grok so the AI does not need to spend time rechecking exact values.
    issues.extend(
        compare_numeric_values(
            original,
            translation
        )
    )

    issues.extend(
        compare_urls(
            original,
            translation
        )
    )

    issues.extend(
        compare_html_entities(
            original,
            translation
        )
    )


    # ------------------------------------------
    # HTML STRUCTURE COMPARISON
    # ------------------------------------------

    issues.extend(
        compare_html_structure(
            original,
            translation
        )
    )


    # ------------------------------------------
    # RESULT
    # ------------------------------------------

    return (
        len(issues) == 0,
        issues
    )


# ==========================================
# HTML STRUCTURE COMPARISON
# ==========================================

def compare_html_structure(original, translation):
    """Check that the translated HTML uses the same tag structure."""

    tag_pattern = re.compile(
        r"<\s*(/?)\s*([a-zA-Z][\w:-]*)\b[^>]*>",
        re.DOTALL
    )

    original_tags = [
        (
            bool(match.group(1)),
            match.group(2).lower()
        )
        for match in tag_pattern.finditer(str(original))
    ]

    translation_tags = [
        (
            bool(match.group(1)),
            match.group(2).lower()
        )
        for match in tag_pattern.finditer(str(translation))
    ]

    if original_tags == translation_tags:
        return []

    issues = []

    if len(original_tags) != len(translation_tags):
        issues.append(
            f"html_tag_count_changed: {len(original_tags)} -> {len(translation_tags)}"
        )

    if original_tags != translation_tags:
        issues.append("html_tag_structure_changed")

    return issues


# ==========================================
# DETERMINISTIC CONTENT CHECKS
# ==========================================

def compare_numeric_values(original, translation):
    """Check that digit sequences from the source are not lost or added."""

    original_numbers = re.findall(r"\d+", str(original))
    translation_numbers = re.findall(r"\d+", str(translation))

    if sorted(original_numbers) != sorted(translation_numbers):
        return [
            "numeric_values_changed: "
            f"{original_numbers} -> {translation_numbers}"
        ]

    return []


def compare_urls(original, translation):
    """Check that URLs present in the source are preserved."""

    url_pattern = re.compile(
        r"https?://[^\s<>'\"]+",
        re.IGNORECASE
    )

    original_urls = url_pattern.findall(str(original))
    translation_urls = url_pattern.findall(str(translation))

    if sorted(original_urls) != sorted(translation_urls):
        return [
            "urls_changed: "
            f"{original_urls} -> {translation_urls}"
        ]

    return []


def compare_html_entities(original, translation):
    """Check that HTML entities such as &lt; and &amp; are preserved."""

    entity_pattern = re.compile(
        r"&(?:#\d+|#x[0-9a-fA-F]+|[A-Za-z][A-Za-z0-9]+);"
    )

    original_entities = entity_pattern.findall(str(original))
    translation_entities = entity_pattern.findall(str(translation))

    if sorted(original_entities) != sorted(translation_entities):
        return [
            "html_entities_changed: "
            f"{original_entities} -> {translation_entities}"
        ]

    return []


# ==========================================
# LANGUAGE LEFTOVER DETECTION
# ==========================================

# These are deliberately small, high-confidence marker sets.
# The goal is to catch obvious source-language words accidentally
# left in a translation without flagging normal Scandinavian words
# that are shared between languages.
STRONG_LANGUAGE_MARKERS = {

    "Swedish": {
        "words": {
            "ditt", "dina", "detta", "denna", "dessa",
            "även", "från", "utan", "genom", "medföljer",
            "ansluts", "ansluta", "avsett", "ytterligare",
            "fungerar", "möjlighet", "strömförsörjning",
            "spänning", "effekt", "förpackningen"
        },
        "phrases": {
            "för att", "med hjälp av", "upp till",
            "kan användas", "levereras med", "inklusive"
        }
    },

    "Danish": {
        "words": {
            "dit", "dine", "dette", "denne", "disse",
            "også", "fra", "uden", "gennem", "medfølger",
            "tilsluttes", "tilslutte", "beregnet", "krave",
            "yderligere", "mulighed", "strømforsyning",
            "spænding", "effekt", "emballagen"
        },
        "phrases": {
            "for at", "ved hjælp af", "op til",
            "kan bruges", "leveres med", "inklusive"
        }
    },

    "Norwegian": {
        "words": {
            "dine", "dette", "denne", "disse",
            "også", "fra", "uten", "gjennom", "medfølger",
            "tilkobles", "tilkoble", "beregnet",
            "ytterligere", "mulighet", "strømforsyning",
            "spenning", "effekt", "emballasjen"
        },
        "phrases": {
            "for å", "ved hjelp av", "opptil",
            "kan brukes", "leveres med", "inkludert"
        }
    },

    "Finnish": {
        "words": {
            "tämä", "tämän", "näitä", "myös", "ilman",
            "kautta", "mukana", "liitetään", "jännite",
            "teho", "virtalähde", "pakkauksessa"
        },
        "phrases": {
            "voidaan käyttää", "mukana toimitetaan",
            "jopa", "ilman että"
        }
    }
}


def _html_to_plain_text(text):
    """Remove HTML markup and common non-language content."""

    plain = re.sub(
        r"<script\b[^>]*>.*?</script>",
        " ",
        text,
        flags=re.IGNORECASE | re.DOTALL
    )

    plain = re.sub(
        r"<style\b[^>]*>.*?</style>",
        " ",
        plain,
        flags=re.IGNORECASE | re.DOTALL
    )

    # URLs, emails and HTML tags should not be interpreted as language.
    plain = re.sub(r"https?://\S+", " ", plain, flags=re.IGNORECASE)
    plain = re.sub(r"www\.\S+", " ", plain, flags=re.IGNORECASE)
    plain = re.sub(r"[\w.+-]+@[\w.-]+\.[A-Za-z]{2,}", " ", plain)
    plain = re.sub(r"<[^>]+>", " ", plain)

    return re.sub(r"\s+", " ", plain).strip().lower()


def detect_leftover_language(
    translation,
    target_language,
    source_language
):
    """
    Detect obvious source/other-language leftovers locally.

    This intentionally uses high-confidence markers only. It does not
    make another AI request.
    """

    target = str(target_language or "").strip().lower()
    source = str(source_language or "").strip().lower()

    language_names = {
        "swedish": "Swedish",
        "danish": "Danish",
        "norwegian": "Norwegian",
        "finnish": "Finnish",
        "english": "English"
    }

    source_name = language_names.get(source)

    plain = _html_to_plain_text(
        str(translation)
    )

    if not plain:
        return []

    # Only run this detector when the detected source language is
    # different from the requested target language.
    if source_name and source == target:
        return []

    # If the target is English, Scandinavian/Finnish leftovers are
    # especially useful to catch. For Scandinavian targets, only check
    # the other closely related Scandinavian languages to avoid false
    # positives from ordinary English e-commerce terminology.
    # Prefer checking the detected source language. This is much less
    # likely to produce false positives than scanning every related
    # language. If the model did not return a known source language, fall
    # back to a broader check.
    if source_name and source != target:
        languages_to_check = [source_name]
    elif target == "english":
        languages_to_check = [
            "Swedish",
            "Danish",
            "Norwegian",
            "Finnish"
        ]
    elif target == "swedish":
        languages_to_check = ["Danish", "Norwegian", "Finnish"]
    elif target == "danish":
        languages_to_check = ["Swedish", "Norwegian", "Finnish"]
    elif target == "norwegian":
        languages_to_check = ["Swedish", "Danish", "Finnish"]
    elif target == "finnish":
        languages_to_check = ["Swedish", "Danish", "Norwegian"]
    else:
        languages_to_check = []

    issues = []

    for language in languages_to_check:

        # Do not flag the language we already know is the source when
        # it is also the target; that case was handled above.
        markers = STRONG_LANGUAGE_MARKERS.get(
            language,
            {}
        )

        words = markers.get("words", set())
        phrases = markers.get("phrases", set())

        found_words = []
        found_phrases = []

        for word in words:
            if re.search(
                rf"(?<![\wåäöÅÄÖ]){re.escape(word)}(?![\wåäöÅÄÖ])",
                plain,
                re.IGNORECASE
            ):
                found_words.append(word)

        for phrase in phrases:
            if phrase in plain:
                found_phrases.append(phrase)

        # One highly distinctive word is enough. Otherwise require
        # two different markers before flagging the translation.
        if found_words or found_phrases:

            # Very distinctive markers that are unlikely to be normal
            # English/product terminology.
            very_strong = {
                "ditt", "dina", "medföljer", "ansluts",
                "krave",
                "spänning", "strømforsyning", "spænding",
                "medfølger", "tilsluttes", "tilkobles",
                "virtalähde", "jännite", "teho",
                "även", "från", "utan", "gjennom",
                "gennem", "ilman", "mukana"
            }

            strong_found = [
                word
                for word in found_words
                if word in very_strong
            ]

            marker_count = (
                len(set(found_words))
                + len(set(found_phrases))
            )

            if strong_found or marker_count >= 2:

                examples = (
                    strong_found
                    or found_words
                    or found_phrases
                )[:3]

                issues.append(
                    "possible_"
                    + language.lower()
                    + "_leftover: "
                    + ", ".join(examples)
                )

    return issues


# ==========================================
# STANDARD PROMPT
# ==========================================

def build_standard_prompt(
    text,
    target_language
):

    return f"""
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
- Keep product names unchanged when they are brand names,
  model names or official product designations.
- Keep brand names unchanged.
- Keep model numbers and article numbers unchanged.
- Preserve HTML tags and their structure.
- Preserve the original HTML structure and formatting as much as possible.
- Preserve measurements and units.
- Preserve technical specifications such as wattage, voltage,
  IP ratings, dimensions and colour temperatures.
- Preserve numbers and numerical values exactly unless they need
  to be converted because of a language-specific formatting convention.
- Use natural language suitable for an e-commerce website.
- Translate product names accurately, but do not unnecessarily
  rearrange the word order of product names.
- Keep the original product-name structure when it is clear and
  understandable.
- Do not change the style or structure of product names just to make
  them sound more like normal sentences.
- Do not translate brand names, model numbers or product codes.
- Translate every ordinary word from the source language into the target language.
- Do not leave source-language words untranslated just because they are part of a
  hyphenated expression, compound word, or product phrase.
- For example, when translating Danish to English, "krave" must be translated
  as "collar"; "BASIC-krave" should therefore become "BASIC collar" or
  "BASIC-collar" depending on the natural target-language phrasing.
- Only keep a source-language word unchanged if it is a brand name, model name,
  product code, official product designation, or another proper name.
- Do not add marketing claims.
- Do not add features, specifications or benefits that are not present
  in the original text.
- Do not remove technical information.
- Do not change the meaning of technical terms.
- Keep HTML tags such as <p>, <strong>, <br>, <ul>, <li> and similar
  tags intact.
- Do not add or remove HTML tags unless required to preserve valid HTML.
- Do not add explanations or comments outside the translated content.

Product description:

{text}

Return ONLY a valid JSON object with exactly these two fields:
{{"source_language":"...","translation":"..."}}
Do not add markdown fences, explanations, labels, or commentary.
"""


# ==========================================
# NATURAL ENGLISH PROMPT
# ==========================================

def build_natural_prompt(
    text,
    target_language
):

    return f"""
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
- Keep brand names unchanged.
- Keep model numbers and article numbers unchanged.
- Keep product codes unchanged.
- Translate every ordinary word from the source language into the target language.
- Do not leave source-language words untranslated just because they are part of a
  hyphenated expression, compound word, or product phrase.
- Only keep a source-language word unchanged if it is a brand name, model name,
  product code, official product designation, or another proper name.
- Preserve HTML tags and their structure.
- Preserve measurements and units.
- Preserve technical specifications such as wattage, voltage,
  IP ratings, dimensions and colour temperatures.
- Preserve numbers and numerical values exactly unless they need
  to be converted because of a language-specific formatting convention.
- Use natural language suitable for a professional e-commerce website.
- When translating product names, use natural and standard
  {target_language} word order.
- Make product names sound natural in the target language,
  while preserving all product information.
- Do not unnecessarily add or remove words from product names.
- Do not add marketing claims.
- Do not add features, specifications or benefits that are not present
  in the original text.
- Do not remove technical information.
- Do not change the meaning of technical terms.
- Keep HTML tags such as <p>, <strong>, <br>, <ul>, <li> and similar
  tags intact.
- Do not add or remove HTML tags unless required to preserve valid HTML.
- Do not add explanations or comments outside the translated content.

For example, when translating to English:

"LED Strip indoor RGB 10m"
can become
"Indoor RGB LED Strip 10m"

"Förlängningskabel vit 10m"
can become
"10m White Extension Cable"

Product description:

{text}

Return ONLY a valid JSON object with exactly these two fields:
{{"source_language":"...","translation":"..."}}
Do not add markdown fences, explanations, labels, or commentary.
"""


# ==========================================
# CURSOR CLI HELPERS
# ==========================================

def _extract_cursor_response(stdout):
    """Extract the final assistant text from Cursor CLI output.

    Cursor's stream-json output is newline-delimited JSON. The final
    `result` event contains the final assistant response. We also keep
    fallbacks for CLI-version differences.
    """

    result_text = None
    assistant_parts = []
    plain_lines = []

    for raw_line in stdout.splitlines():
        line = raw_line.strip()
        if not line:
            continue

        try:
            event = json.loads(line)
        except json.JSONDecodeError:
            plain_lines.append(line)
            continue

        event_type = event.get("type")

        if event_type == "result":
            text = event.get("text")
            if isinstance(text, str) and text.strip():
                result_text = text.strip()

        elif event_type == "assistant":
            # Different CLI versions can expose assistant text in
            # slightly different shapes. Handle both common forms.
            message = event.get("message")
            if isinstance(message, dict):
                content = message.get("content", [])
            else:
                content = event.get("content", [])

            if isinstance(content, str):
                assistant_parts.append(content)
            elif isinstance(content, list):
                for block in content:
                    if isinstance(block, dict) and block.get("type") == "text":
                        text = block.get("text")
                        if isinstance(text, str):
                            assistant_parts.append(text)
                    elif isinstance(block, str):
                        assistant_parts.append(block)

    if result_text:
        return result_text

    if assistant_parts:
        return "".join(assistant_parts).strip()

    return "\n".join(plain_lines).strip()


async def _create_cursor_agent(model):
    """Create one reusable Cursor client/agent for the current worker loop."""
    from contextlib import AsyncExitStack

    if not CURSOR_API_KEY:
        raise RuntimeError(
            "CURSOR_API_KEY was not found in the environment. "
            "Add CURSOR_API_KEY=crsr_... to your .env file."
        )

    stack = AsyncExitStack()
    await stack.__aenter__()

    client = await stack.enter_async_context(
        await AsyncClient.launch_bridge(workspace=os.getcwd())
    )

    agent = await stack.enter_async_context(
        await client.agents.create(
            model=model,
            api_key=CURSOR_API_KEY,
            local=LocalAgentOptions(cwd=os.getcwd())
        )
    )

    return stack, agent


def _get_worker_cursor_agent(model):
    """Reuse one Cursor agent per worker thread and model."""
    import asyncio
    import threading

    if not hasattr(_get_worker_cursor_agent, "_state"):
        _get_worker_cursor_agent._state = threading.local()

    state = _get_worker_cursor_agent._state

    if not hasattr(state, "loops"):
        state.loops = {}

    if model not in state.loops:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        stack, agent = loop.run_until_complete(
            _create_cursor_agent(model)
        )
        state.loops[model] = (loop, stack, agent)

    return state.loops[model][0], state.loops[model][2]


def _run_cursor(prompt, model=None):
    """Run a Cursor request using the worker's reusable agent."""
    import asyncio

    selected_model = model or CURSOR_MODEL

    try:
        loop, agent = _get_worker_cursor_agent(selected_model)
        asyncio.set_event_loop(loop)
        run = loop.run_until_complete(agent.send(prompt))
        response_text = loop.run_until_complete(run.text())
    except Exception as exc:
        raise RuntimeError(
            f"Cursor SDK request failed using {selected_model}: {exc}"
        ) from exc

    if not response_text:
        raise RuntimeError(
            f"Cursor SDK returned an empty response using {selected_model}."
        )

    return str(response_text).strip()


def _load_terminology_for_validation():
    """Load the shared terminology file when it exists beside translator.py."""
    path = os.path.join(
        os.path.dirname(os.path.abspath(__file__)),
        "terminology.json"
    )

    if not os.path.exists(path):
        return ""

    try:
        with open(path, "r", encoding="utf-8") as file:
            data = json.load(file)
        return json.dumps(data, ensure_ascii=False, indent=2)
    except Exception as exc:
        print(f"Terminology validation warning: {exc}")
        return ""


def validate_with_grok_batch(products, target_language, prompt_style="standard"):
    """Validate several translations in one Grok request.

    Python/local validation has already run before this function is called.
    Grok therefore focuses on semantic/language QA instead of repeating
    deterministic checks that Python can perform reliably.
    """

    if not products:
        return {}

    terminology = _load_terminology_for_validation()

    terminology_section = ""
    if terminology:
        terminology_section = f"""

Specific terminology rules (these take precedence over general spelling preferences):
{terminology}
"""

    product_blocks = []
    for product in products:
        product_id = product["id"]
        original = str(product.get("original", ""))
        translation = str(product.get("translation", ""))
        local_issues = product.get("local_issues", []) or []

        if isinstance(local_issues, list):
            local_text = ", ".join(str(issue) for issue in local_issues)
        else:
            local_text = str(local_issues)

        product_blocks.append(
            f"""PRODUCT {product_id}
Original:
{original}

Translation:
{translation}

Python checks already performed:
{local_text if local_text else "No deterministic issues found."}
"""
        )

    prompt = f"""
You are a semantic quality-assurance reviewer for an e-commerce translation system.
Review multiple translations in one request.

Target language: {target_language}
Translation style: {prompt_style}

Python has already performed the deterministic checks. Do NOT spend time
rechecking HTML structure, numbers, URLs, or other mechanical checks that are
listed as already performed. Focus on issues that require language understanding.

For each product, check:
- Meaning: no information is added, removed, or materially changed.
- Technical meaning: the translation must correctly express the original.
- Ranges: a continuous range must remain a continuous range.
- Terminology: follow explicit terminology rules when applicable.
- Source-language leftovers: ordinary source-language words must be translated.
- Natural language: flag wording that is clearly unnatural, misleading, or
  unsuitable for professional e-commerce copy.
- Product names: respect the requested translation style.

English style:
- Use natural, professional international English.
- American and British English are both acceptable.
- Do NOT flag color/colour, center/centre, meter/metre, or similar regional
  spelling variants merely because they differ from your preferred variety.
- If a specific terminology.json rule requires a particular term, follow that
  specific rule. Do not treat it as a general British-English requirement.

Do NOT flag a translation merely because you would personally phrase it differently.
Do NOT invent product facts.
Do NOT require a marketing rewrite.
Only report concrete, defensible issues.

Return ONLY valid JSON as an array with exactly one result for every product ID:
[
  {{
    "id": 1,
    "status": "OK" or "REVIEW",
    "issues": [
      {{
        "type": "meaning|technical|range|terminology|leftover_language|natural_language|product_name|other",
        "severity": "low|medium|high",
        "explanation": "Concise explanation of the concrete issue."
      }}
    ],
    "suggested_translation": "..." or null
  }}
]

{terminology_section}

{chr(10).join(product_blocks)}
"""

    response_text = _run_cursor(
        prompt,
        model=CURSOR_VALIDATOR_MODEL
    )

    try:
        try:
            parsed = json.loads(response_text)
        except json.JSONDecodeError:
            json_start = response_text.find("[")
            json_end = response_text.rfind("]")
            if json_start == -1 or json_end == -1 or json_end <= json_start:
                raise ValueError("Grok validator did not return a JSON array.")
            parsed = json.loads(response_text[json_start:json_end + 1])

        if not isinstance(parsed, list):
            raise ValueError("Grok validator response was not a JSON array.")

        expected_ids = {product["id"] for product in products}
        results = {}

        for item in parsed:
            if not isinstance(item, dict):
                continue

            product_id = item.get("id")
            if product_id not in expected_ids:
                continue

            status = str(item.get("status", "")).strip().upper()
            if status not in {"OK", "REVIEW"}:
                raise ValueError(
                    f"Unsupported validator status for product {product_id}: {status}"
                )

            raw_issues = item.get("issues", [])
            if not isinstance(raw_issues, list):
                raw_issues = []

            issues = []
            for issue in raw_issues:
                if not isinstance(issue, dict):
                    continue
                issues.append({
                    "type": str(issue.get("type", "other")),
                    "severity": str(issue.get("severity", "medium")),
                    "explanation": str(issue.get("explanation", ""))
                })

            results[product_id] = {
                "status": "OK" if status == "OK" else "Review required",
                "issues": issues,
                "suggested_translation": item.get("suggested_translation")
            }

        missing_ids = expected_ids - set(results)
        if missing_ids:
            raise ValueError(
                "Grok validator did not return results for product IDs: "
                + ", ".join(str(value) for value in sorted(missing_ids))
            )

        return results

    except Exception as exc:
        raise RuntimeError(
            "Grok batch validator returned an invalid response: "
            f"{exc}. Response: {response_text[:2000]}"
        ) from exc


def validate_with_grok(
    original,
    translation,
    target_language,
    source_language=None,
    prompt_style="standard"
):
    """Backward-compatible single-product wrapper around the batch validator."""

    result = validate_with_grok_batch(
        [{
            "id": 1,
            "original": original,
            "translation": translation,
            "local_issues": []
        }],
        target_language,
        prompt_style
    )

    return result[1]


# ==========================================
# TRANSLATE
# ==========================================

def translate_text(
    text,
    target_language,
    prompt_style="standard"
):

    # ------------------------------------------
    # SELECT PROMPT
    # ------------------------------------------

    if prompt_style == "natural":
        prompt = build_natural_prompt(
            text,
            target_language
        )
    else:
        prompt = build_standard_prompt(
            text,
            target_language
        )

    # ------------------------------------------
    # ONE CURSOR SDK REQUEST
    # ------------------------------------------

    # The SDK returns plain text, so explicitly require one JSON object.
    prompt += """

Return ONLY valid JSON in exactly this format:
{\"source_language\":\"...\",\"translation\":\"...\"}
Do not wrap the JSON in Markdown code fences.
Do not add any text before or after the JSON.
"""

    response_text = _run_cursor(prompt)

    # ------------------------------------------
    # PARSE JSON
    # ------------------------------------------

    try:
        # Prefer the complete response as JSON. If the model added a
        # tiny amount of surrounding text, recover the first JSON object.
        try:
            parsed = json.loads(response_text)
        except json.JSONDecodeError:
            json_start = response_text.find("{")
            json_end = response_text.rfind("}")

            if json_start == -1 or json_end == -1 or json_end <= json_start:
                raise ValueError("Cursor did not return a JSON object.")

            parsed = json.loads(
                response_text[json_start:json_end + 1]
            )

        result = TranslationResult.model_validate(parsed)

    except Exception as exc:
        raise RuntimeError(
            "Cursor returned an invalid translation response: "
            f"{exc}. Response: {response_text[:1000]}"
        ) from exc

    translation = result.translation.strip()
    source_language = result.source_language.strip()

    # ------------------------------------------
    # LOCAL VALIDATION
    #
    # This does NOT make another AI request.
    # ------------------------------------------

    valid, issues = validate_translation(
        text,
        translation,
        target_language,
        source_language
    )

    validation_status = (
        "OK" if valid else "Review required"
    )

    # ------------------------------------------
    # RETURN
    # ------------------------------------------

    return {
        "source_language": source_language,
        "translation": translation,
        "validation_status": validation_status,
        "validation_issues": issues
    }

import os
import re

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
            "tilsluttes", "tilslutte", "beregnet",
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
    make another Gemini request.
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
    # language. If Gemini did not return a known source language, fall
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
"""


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
    # ONE GEMINI REQUEST
    # ------------------------------------------

    response = client.models.generate_content(

        model="gemini-3.8-flash",

        contents=prompt,

        config={

            "response_mime_type":
                "application/json",

            "response_schema":
                TranslationResult

        }

    )


    # ------------------------------------------
    # GET STRUCTURED RESULT
    # ------------------------------------------

    if response.parsed:

        result = response.parsed

    else:

        result = (
            TranslationResult
            .model_validate_json(
                response.text
            )
        )


    translation = (
        result.translation
    )


    # ------------------------------------------
    # LOCAL VALIDATION
    #
    # IMPORTANT:
    #
    # This does NOT make another Gemini request.
    # It only checks the result locally.
    # ------------------------------------------

    valid, issues = (
        validate_translation(

            text,

            translation,

            target_language,

            result.source_language

        )
    )


    # ------------------------------------------
    # VALIDATION STATUS
    # ------------------------------------------

    if valid:

        validation_status = "OK"

    else:

        validation_status = (
            "Review required"
        )


    # ------------------------------------------
    # RETURN
    # ------------------------------------------

    return {

        "source_language":
            result.source_language,

        "translation":
            translation,

        "validation_status":
            validation_status,

        "validation_issues":
            issues

    }
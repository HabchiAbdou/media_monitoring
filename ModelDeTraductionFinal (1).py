import json
import os
import re
import sys

from cerebras.cloud.sdk import Cerebras

try:
    from DarijaTranslatorAssistant.llm_client import LLMClient
    from DarijaTranslatorAssistant.darija_assistant import DarijaAssistant
    HAS_DARIJA_ASSISTANT = True
except ModuleNotFoundError:
    LLMClient = None  # type: ignore[assignment]
    DarijaAssistant = None  # type: ignore[assignment]
HAS_DARIJA_ASSISTANT = False


# ----------------------------------------------------------------------
# Configuration
DEFAULT_CEREBRAS_API_KEY = "csk-k4k93rh5rp3et5ctfdx46cp5v8x3x8nfyr8tnpf4yrmk3ycd"
CEREBRAS_API_KEY = os.getenv("CEREBRAS_API_KEY", DEFAULT_CEREBRAS_API_KEY)
CEREBRAS_MODEL = os.getenv("CEREBRAS_MODEL", "gpt-oss-120b")

# By default run BOTH translation and sentiment
OUTPUT_MODE = os.getenv("DARIJA_OUTPUT_MODE", "both").strip().lower()
TRANSLATION_LANGUAGES = [
    lang.strip()
    for lang in os.getenv("DARIJA_TRANSLATION_LANGUAGES", "English,French").split(",")
    if lang.strip()
]

darija_text = os.getenv(
    "DARIJA_TEXT",
    (
        "daba ana kankoun bzaf mea abdou, chi mrrat kaybanlia driyef bzaf walakin "
        "be3d lmrrat kaydir chi f3ayl khaybin bzaf. ana normalement kay3jbni nhder "
        "m3ah bzaf hitach huwa driyef bzaf"
    ),
).strip()

# Ensure we can print UTF-8 characters (accents, quotes, etc.) on Windows consoles.
if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        # If reconfigure fails, fall back silently; Python will use the default encoding.
        pass


client = Cerebras(api_key=CEREBRAS_API_KEY)
if HAS_DARIJA_ASSISTANT:
    llm_client = LLMClient(
        use_openai=False,
        use_cerebras=True,
        cerebras_api_key=CEREBRAS_API_KEY,
        cerebras_model=CEREBRAS_MODEL,
        llm_api_url="https://api.cerebras.ai/v1",
    )
    assistant = DarijaAssistant(llm_client=llm_client)
else:
    llm_client = None
    assistant = None


def _call_cerebras(messages, *, max_tokens: int = 512, temperature: float = 0.2) -> str:
    """Utility wrapper to keep generation parameters centralized."""
    completion = client.chat.completions.create(
        messages=messages,
        model=CEREBRAS_MODEL,
        max_completion_tokens=max_tokens,
        temperature=temperature,
        top_p=1,
        stream=False,
    )

    # Cerebras may return text in `content` or (for reasoning-style models) in
    # `reasoning`. We never want to expose chain-of-thought, but for this setup
    # the useful text is currently surfaced there, so we fall back to it.
    message = completion.choices[0].message
    text = getattr(message, "content", None) or getattr(message, "reasoning", None)
    if text is None:
        raise RuntimeError(f"No text content returned from Cerebras: {completion.to_dict()}")
    return text.strip()


# ----------------------------------------------------------------------
# Translation
# ----------------------------------------------------------------------

def get_faithful_translation(text: str, target_language: str) -> str:
    """Request a faithful translation into a specific language."""
    prompt = (
        "You are a professional translator specialized in Moroccan Arabic (Darija).\n"
        f"Provide a faithful, natural-sounding translation of the following sentence "
        f"into {target_language}. Keep the original tone and do not add commentary.\n\n"
        f"Texte: {text}\nTranslation:"
    )
    return _call_cerebras(
        messages=[{"role": "user", "content": prompt}], max_tokens=400, temperature=0.1
    )


# ----------------------------------------------------------------------
# Sentiment analysis
# ----------------------------------------------------------------------

def _analyze_emotions_json(text: str) -> str:
    """
    Ask the model to return a strict JSON structure describing:
    - per-segment sentiment,
    - global percentages,
    - final judgment,
    - negative phrases about a person.
    """
    prompt = (
        "Tu es un expert en analyse de sentiments pour l'arabe marocain (Darija).\n"
        "On va te donner un texte (parfois tres long). Ta tache est de produire "
        "UNIQUEMENT un objet JSON valide qui decrit les sentiments.\n"
        "\n"
        "Le JSON doit avoir exactement cette structure generale :\n"
        "{\n"
        '  \"summary\": {\n'
        '    \"global_sentiment\": \"positif\" | \"negatif\" | \"neutre\" | \"mixte\",\n'
        '    \"short_french_summary\": \"...\",\n'
        '    \"final_judgment_sentence\": \"...\"\n'
        "  },\n"
        "  \"segments\": [\n"
        "    {\n"
        "      \"index\": 1,\n"
        '      \"text\": \"...\",  // phrase exacte en darija\n'
        '      \"sentiment\": \"positif\" | \"negatif\" | \"neutre\"\n'
        "    }\n"
        "    // ... autres segments\n"
        "  ],\n"
        "  \"stats\": {\n"
        "    \"positive_percent\": 40,\n"
        "    \"negative_percent\": 30,\n"
        "    \"neutral_percent\": 30\n"
        "  },\n"
        "  \"negative_person_phrases\": [\n"
        "    {\n"
        "      \"segment_index\": 2,\n"
        '      \"text\": \"...\",  // phrase exacte en darija\n'
        '      \"target\": \"Abdou\" | \"il\" | \"elle\" | \"quelqu\'un\" | \"inconnu\",\n'
        '      \"reason\": \"...\",  // en francais\n'
        "      \"certainty_percent\": 85\n"
        "    }\n"
        "    // ... autres phrases\n"
        "  ]\n"
        "}\n"
        "\n"
        "- Les pourcentages dans \"stats\" doivent etre des entiers approximatifs "
        "et leur somme proche de 100.\n"
        "- Utilise le moins de texte possible dans les explications, mais reste clair.\n"
        "- Ne renvoie AUCUNE explication en dehors du JSON (pas de texte avant ou apres).\n"
        "- Ne mets pas de commentaires JSON (les lignes avec // sont uniquement des exemples).\n"
        "- Respecte bien la casse et les cles indiquees.\n"
        "\n"
        "Texte en darija a analyser :\n"
        f"{text}"
    )
    return _call_cerebras(
        messages=[{"role": "user", "content": prompt}], max_tokens=900, temperature=0.0
    )






def analyze_emotions(text: str) -> str:
    """
    High-level helper that calls the LLM, parses its JSON,
    and formats the result as bullets the way you requested.
    """
    raw = _analyze_emotions_json(text)

    stripped = raw.lstrip()
    data = None
    if stripped.startswith("{"):
        try:
            data = json.loads(raw)
        except json.JSONDecodeError as exc:
            # Surface a short debug hint, but continue with a regex-based fallback.
            print(f"[DEBUG] Failed to parse JSON from LLM: {exc}", file=sys.stderr)

    if data is None:
        return _format_sentiment_from_jsonish(raw)

    summary = data.get("summary", {}) or {}
    segments = data.get("segments", []) or []
    stats = data.get("stats", {}) or {}
    neg_person_phrases = data.get("negative_person_phrases", []) or []

    lines: list[str] = []

    # 1) Analyse generale + global percentages + final judgment
    lines.append("Analyse generale:")
    if summary.get("short_french_summary"):
        lines.append(f"- Resume: {summary['short_french_summary']}")
    if summary.get("global_sentiment"):
        lines.append(f"- Sentiment global: {summary['global_sentiment']}")

    pos = stats.get("positive_percent")
    neg = stats.get("negative_percent")
    neu = stats.get("neutral_percent")
    if pos is not None or neg is not None or neu is not None:
        lines.append("- Pourcentages approx.:")
        if pos is not None:
            lines.append(f"  - Positif: {pos}%")
        if neg is not None:
            lines.append(f"  - Negatif: {neg}%")
        if neu is not None:
            lines.append(f"  - Neutre: {neu}%")

    if summary.get("final_judgment_sentence"):
        lines.append(f"- Jugement final: {summary['final_judgment_sentence']}")

    # 2) Detail par phrase / segment
    if segments:
        lines.append("")
        lines.append("Detail par phrase/segment:")
        for seg in segments:
            idx = seg.get("index")
            txt = seg.get("text", "").strip()
            sent = seg.get("sentiment", "").strip()
            if not txt:
                continue
            lines.append(
                f"- Phrase {idx}: \"{txt}\" | Sentiment: {sent or 'inconnu'}"
            )

    # 3) Phrases negatives a propos d'une personne
    if neg_person_phrases:
        lines.append("")
        lines.append("Phrases negatives a propos d'une personne:")
        for item in neg_person_phrases:
            idx = item.get("segment_index")
            txt = item.get("text", "").strip()
            target = item.get("target", "inconnu")
            reason = item.get("reason", "").strip()
            cert = item.get("certainty_percent")
            if not txt:
                continue
            parts = [
                f"Phrase {idx}: \"{txt}\"",
                f"Cible: {target}",
            ]
            if reason:
                parts.append(f"Raison: {reason}")
            if cert is not None:
                parts.append(f"Certitude: {cert}%")
            lines.append("- " + " | ".join(parts))

    return "\n".join(lines)


def _format_sentiment_from_jsonish(raw: str) -> str:
    """
    Best-effort formatter when the model returns JSON-like text that is not
    strictly valid JSON. We extract the key information with regex so you still
    get the bullets you asked for.
    """
    lines: list[str] = []

    # Global sentiment and summary
    m_global = re.search(
        r'"global_sentiment"\s*:\s*"([^"]+)"', raw, flags=re.IGNORECASE
    )
    m_summary = re.search(
        r'"short_french_summary"\s*:\s*"([^"]+)"', raw, flags=re.IGNORECASE
    )
    m_judgment = re.search(
        r'"final_judgment_sentence"\s*:\s*"([^"]+)"', raw, flags=re.IGNORECASE
    )

    lines.append("Analyse generale (approx.):")
    if m_summary:
        lines.append(f"- Resume: {m_summary.group(1)}")
    if m_global:
        lines.append(f"- Sentiment global: {m_global.group(1)}")

    # Segments
    seg_pattern = re.compile(
        r'\{\s*"index"\s*:\s*(\d+)\s*,\s*"text"\s*:\s*"([^"]*)"\s*,\s*"sentiment"\s*:\s*"([^"]*)"\s*',
        flags=re.IGNORECASE | re.DOTALL,
    )
    segs = list(seg_pattern.finditer(raw))
    if segs:
        lines.append("")
        lines.append("Detail par phrase/segment (approx.):")
        for seg_match in segs:
            idx, txt, sent = (
                seg_match.group(1),
                seg_match.group(2).strip(),
                seg_match.group(3).strip(),
            )
            if not txt:
                continue
            lines.append(
                f"- Phrase {idx}: \"{txt}\" | Sentiment: {sent or 'inconnu'}"
            )

    # Percentages: either read from JSON or approximate from segments
    m_pos = re.search(
        r'"positive_percent"\s*:\s*(\d+)', raw, flags=re.IGNORECASE
    )
    m_neg = re.search(
        r'"negative_percent"\s*:\s*(\d+)', raw, flags=re.IGNORECASE
    )
    m_neu = re.search(
        r'"neutral_percent"\s*:\s*(\d+)', raw, flags=re.IGNORECASE
    )

    pos_val = int(m_pos.group(1)) if m_pos else None
    neg_val = int(m_neg.group(1)) if m_neg else None
    neu_val = int(m_neu.group(1)) if m_neu else None

    # If model did not provide stats, approximate from segments
    if (pos_val is None or neg_val is None or neu_val is None) and segs:
        total = len(segs)
        pos_ct = sum(
            1
            for seg_match in segs
            if seg_match.group(3).strip().lower().startswith("positif")
        )
        neg_ct = sum(
            1
            for seg_match in segs
            if seg_match.group(3).strip().lower().startswith("negatif")
        )
        neu_ct = sum(
            1
            for seg_match in segs
            if seg_match.group(3).strip().lower().startswith("neutre")
        )
        # Avoid division by zero; already checked segs not empty.
        pos_val = round(100 * pos_ct / total)
        neg_val = round(100 * neg_ct / total)
        neu_val = round(100 * neu_ct / total)

    if pos_val is not None or neg_val is not None or neu_val is not None:
        lines.append("- Pourcentages approx.:")
        if pos_val is not None:
            lines.append(f"  - Positif: {pos_val}%")
        if neg_val is not None:
            lines.append(f"  - Negatif: {neg_val}%")
        if neu_val is not None:
            lines.append(f"  - Neutre: {neu_val}%")

    if m_judgment:
        lines.append(f"- Jugement final: {m_judgment.group(1)}")

    # Negative phrases about a person
    neg_pattern = re.compile(
        r'\{\s*"segment_index"\s*:\s*(\d+)\s*,\s*"text"\s*:\s*"([^"]*)"\s*,\s*"target"\s*:\s*"([^"]*)"\s*,\s*"reason"\s*:\s*"([^"]*)"\s*,\s*"certainty_percent"\s*:\s*(\d+)',
        flags=re.IGNORECASE | re.DOTALL,
    )
    negs = list(neg_pattern.finditer(raw))
    if negs:
        lines.append("")
        lines.append("Phrases negatives a propos d'une personne (approx.):")
        for m in negs:
            idx, txt, target, reason, cert = (
                m.group(1),
                m.group(2).strip(),
                m.group(3).strip() or "inconnu",
                m.group(4).strip(),
                m.group(5),
            )
            if not txt:
                continue
            parts = [
                f"Phrase {idx}: \"{txt}\"",
                f"Cible: {target}",
                f"Raison: {reason}" if reason else None,
                f"Certitude: {cert}%",
            ]
            parts = [p for p in parts if p]
            lines.append("- " + " | ".join(parts))

    # If we couldn't extract much, fall back to raw.
    if len(lines) <= 1:
        return raw

    return "\n".join(lines)


# ----------------------------------------------------------------------
# Flows
# ----------------------------------------------------------------------

def run_translation_flow(text: str) -> None:
    """Run the translation assistance pipeline using DarijaAssistant plus faithful translations.

    If DarijaTranslatorAssistant is not installed or import fails, falls back
    to direct faithful translations only.
    """
    print("Mode: Faithful translation")
    print("Original (Darija):", text)

    assisted_translation = None
    if assistant is not None:
        try:
            assisted_translation = assistant.assist_and_translate(text)
        except Exception as exc:  # noqa: BLE001 - we just log and continue
            print(f"Assisted Translation (DarijaAssistant) error: {exc}")

    if assisted_translation is not None:
        print("Assisted Translation (DarijaAssistant):", assisted_translation)

    translations: dict[str, str] = {}
    for language in TRANSLATION_LANGUAGES:
        try:
            translations[language] = get_faithful_translation(text, language)
        except Exception as exc:  # noqa: BLE001
            translations[language] = f"[ERROR: {exc}]"

    for language, translated_text in translations.items():
        print(f"{language} translation:", translated_text)


def run_sentiment_flow(text: str) -> None:
    """Run sentiment / emotion analysis instead of translation."""
    sentiment_report = analyze_emotions(text)
    print("Mode: Sentiment analysis")
    print("Original (Darija):", text)
    print(sentiment_report)


if __name__ == "__main__":
    if OUTPUT_MODE == "translation":
        run_translation_flow(darija_text)
    elif OUTPUT_MODE == "sentiment":
        run_sentiment_flow(darija_text)
    else:
        # Default: run both translation and sentiment analysis.
        run_translation_flow(darija_text)
        print("\n" + "-" * 60 + "\n")
        run_sentiment_flow(darija_text)

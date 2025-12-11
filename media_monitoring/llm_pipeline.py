from __future__ import annotations

import importlib.util
import inspect
import json
import logging
import re
import unicodedata
from pathlib import Path
from textwrap import shorten
from types import ModuleType
from typing import Any, Callable, Iterable, Mapping

logger = logging.getLogger(__name__)
logger.addHandler(logging.NullHandler())

_SCRAPER_MODULE_CANDIDATES: tuple[str, ...] = (
    "scrapping",
    "scraping",
    "monitoring.services.scraping",
)
_SCRAPER_FUNCTION_CANDIDATES: tuple[str, ...] = ("run_scraper", "scrape", "scrape_site")
_SCRAPER_METHOD_CANDIDATES: tuple[str, ...] = ("run", "scrape")
_MODEL_FILE_CANDIDATES: tuple[str, ...] = ("ModelDeTraductionFinal.py", "ModelDeTraductionFinal (1).py")
_SCRAPPING_MODULE_CACHE: ModuleType | None = None
_MODEL_MODULE_CACHE: ModuleType | None = None

_DEFAULT_SCORES = {"positif": 33, "negatif": 33, "neutre": 34}


def _normalize_label_french(label: Any) -> str:
    """
    Map loose/free-text sentiment labels to the expected French values.
    """
    if not label:
        return "neutre"
    normalized = unicodedata.normalize("NFKD", str(label)).encode("ascii", "ignore").decode().strip().lower()
    if "posit" in normalized or "favorable" in normalized:
        return "positif"
    if "negat" in normalized or "defavor" in normalized or "critique" in normalized:
        return "negatif"
    if "neut" in normalized or "mitige" in normalized:
        return "neutre"
    return "neutre"


def _normalize_risk_level(value: Any) -> str:
    if not value:
        return "modéré"
    normalized = unicodedata.normalize("NFKD", str(value)).encode("ascii", "ignore").decode().strip().lower()
    if "eleve" in normalized or "haut" in normalized:
        return "élevé"
    if "faible" in normalized or "bas" in normalized:
        return "faible"
    return "modéré"


def _normalize_scores(scores: Any) -> dict[str, int]:
    if not isinstance(scores, Mapping):
        base = dict(_DEFAULT_SCORES)
    else:
        base = {
            "positif": max(0, int(round(float(scores.get("positif", 0))))),
            "negatif": max(0, int(round(float(scores.get("negatif", 0))))),
            "neutre": max(0, int(round(float(scores.get("neutre", 0))))),
        }
    total = sum(base.values())
    if total <= 0:
        return dict(_DEFAULT_SCORES)
    normalized = {k: int(round(v / total * 100)) for k, v in base.items()}
    diff = 100 - sum(normalized.values())
    if diff:
        target_key = max(normalized, key=normalized.get)
        normalized[target_key] += diff
    return normalized


def _build_structured_prompt(content: str) -> str:
    """
    Ask the model for a strict French JSON payload so downstream parsing is stable.
    """
    return (
        "Analyse en français l'article suivant à propos d'OCP et renvoie UNIQUEMENT un JSON valide "
        "respectant exactement le format indiqué. Aucune autre phrase ne doit être ajoutée.\n"
        "Tu reçois le texte d'un article (il peut être en arabe ou dans une autre langue). "
        "Ta tâche est de résumer le contenu en français en 2 à 4 phrases. "
        "Le résumé doit expliquer le contexte général, le sujet principal de l'article, et comment OCP est mentionné. "
        "Ne surtout pas inclure de texte de debug, de balises HTML, d'URL, de chemins de fichier ou d'extraits de template. "
        "Ne pas ajouter de préfixes comme « Sortie modèle: », « Analyse generale: », « Extrait source: », etc. "
        "Le texte du résumé doit être écrit uniquement en français, lisible par un humain.\n\n"
        "Format attendu strictement :\n"
        "{\n"
        '  "sentiment_label": "positif|negatif|neutre",\n'
        '  "sentiment_scores": {"positif": 30, "negatif": 70, "neutre": 0},\n'
        '  "sentiment_reasons": ["raison 1", "raison 2", "raison 3"],\n'
        '  "article_summary": "Résumé concis en 2 à 4 phrases en français, sans étiquette",\n'
        '  "resume_article": "Résumé en français (2 à 4 phrases), sans étiquette",\n'
        '  "risk_level": "faible|modéré|élevé",\n'
        '  "recommendations": ["recommandation 1", "recommandation 2"]\n'
        "}\n\n"
        "Contraintes :\n"
        "- Les trois raisons doivent être en français, courtes, et expliquer le sentiment.\n"
        "- Les pourcentages doivent être des entiers et la somme doit être 100.\n"
        "- Ne pas inclure de labels comme 'Analyse generale:' ou 'Résumé:' dans article_summary.\n"
        "- Ne pas inclure de labels ni d'URL ou de balises dans resume_article.\n"
        "- Résume l'article en français (2 à 4 phrases), sans URL, sans HTML, sans étiquette.\n"
        "- Retourne uniquement le JSON.\n\n"
        "Texte à analyser :\n"
        f"{content}"
    )


def _safe_parse_json_model_output(model_output: Any) -> dict[str, Any] | None:
    if not isinstance(model_output, str):
        return None
    try:
        parsed = json.loads(model_output)
    except Exception:
        return None
    if not isinstance(parsed, Mapping):
        return None
    return dict(parsed)


def _load_scrapping_module() -> ModuleType:
    """
    Import scrapping.py lazily to avoid side effects at import time.
    """
    global _SCRAPPING_MODULE_CACHE
    if _SCRAPPING_MODULE_CACHE is not None:
        return _SCRAPPING_MODULE_CACHE

    for module_name in _SCRAPER_MODULE_CANDIDATES:
        try:
            module = importlib.import_module(module_name)
            _SCRAPPING_MODULE_CACHE = module
            return _SCRAPPING_MODULE_CACHE
        except ModuleNotFoundError:
            continue

    raise RuntimeError("scrapping.py is missing or not importable")


def _load_model_module() -> ModuleType:
    """
    Import ModelDeTraductionFinal.py, with a fallback for filenames that may
    contain a suffix such as \"(1)\".
    """
    global _MODEL_MODULE_CACHE
    if _MODEL_MODULE_CACHE is not None:
        return _MODEL_MODULE_CACHE

    try:
        import ModelDeTraductionFinal as model_module  # type: ignore
        _MODEL_MODULE_CACHE = model_module
        return _MODEL_MODULE_CACHE
    except ModuleNotFoundError:
        base_dir = Path(__file__).resolve().parents[1]
        for candidate in _MODEL_FILE_CANDIDATES:
            candidate_path = base_dir / candidate
            if not candidate_path.exists():
                continue
            spec = importlib.util.spec_from_file_location("ModelDeTraductionFinal", candidate_path)
            if spec is None or spec.loader is None:
                continue
            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)
            _MODEL_MODULE_CACHE = module
            return _MODEL_MODULE_CACHE
    raise RuntimeError("ModelDeTraductionFinal.py is missing or not importable")


def _filter_kwargs(func: Callable[..., Any], kwargs: Mapping[str, Any]) -> dict[str, Any]:
    """
    Pass only the parameters accepted by the callable to avoid TypeError when
    the scraper/model signatures are narrower than the provided kwargs.
    """
    signature = inspect.signature(func)
    accepts_var_kwargs = any(param.kind == param.VAR_KEYWORD for param in signature.parameters.values())
    if accepts_var_kwargs:
        return dict(kwargs)

    filtered: dict[str, Any] = {}
    for name, param in signature.parameters.items():
        if param.kind in (param.POSITIONAL_OR_KEYWORD, param.KEYWORD_ONLY) and name in kwargs:
            filtered[name] = kwargs[name]
    return filtered


def _run_scraper(scraper_kwargs: Mapping[str, Any]) -> Any:
    """
    Placeholder scraper runner. The previous scraping module has been removed.
    Returning an empty dict keeps downstream logic safe without failing imports.
    """
    try:
        scrapping_module = _load_scrapping_module()
    except Exception:
        return {}

    for name in _SCRAPER_FUNCTION_CANDIDATES:
        scraper_fn = getattr(scrapping_module, name, None)
        if callable(scraper_fn):
            return scraper_fn(**_filter_kwargs(scraper_fn, scraper_kwargs))

    scraper_cls = getattr(scrapping_module, "Scraper", None)
    if scraper_cls is not None:
        scraper_instance = scraper_cls(**_filter_kwargs(scraper_cls, scraper_kwargs))
        for method_name in _SCRAPER_METHOD_CANDIDATES:
            method = getattr(scraper_instance, method_name, None)
            if callable(method):
                return method(**_filter_kwargs(method, scraper_kwargs))

    # Nothing available; return empty payload instead of error.
    return {}


def _extract_text_from_mapping(data: Mapping[str, Any]) -> str:
    preferred_keys = ("title", "content", "text", "body", "description", "summary")
    parts: list[str] = []

    for key in preferred_keys:
        value = data.get(key)
        if isinstance(value, str):
            parts.append(value.strip())

    if not parts:
        for value in data.values():
            if isinstance(value, str):
                parts.append(value.strip())
            elif isinstance(value, Mapping):
                nested = _extract_text_from_mapping(value)
                if nested:
                    parts.append(nested)
            elif isinstance(value, Iterable) and not isinstance(value, (str, bytes, bytearray)):
                nested = _normalize_prompt_text(value)
                if nested:
                    parts.append(nested)

    return "\n".join(part for part in parts if part)


def _normalize_prompt_text(scraped_data: Any) -> str:
    """
    Normalize the scraper return payload into a single text prompt suitable for
    the model.
    """
    if scraped_data is None:
        return ""

    if isinstance(scraped_data, str):
        return scraped_data.strip()

    if isinstance(scraped_data, Mapping):
        return _extract_text_from_mapping(scraped_data)

    if isinstance(scraped_data, Iterable) and not isinstance(scraped_data, (str, bytes, bytearray)):
        parts: list[str] = []
        for item in scraped_data:
            normalized = _normalize_prompt_text(item)
            if normalized:
                parts.append(normalized)
        return "\n".join(parts)

    return str(scraped_data)


def _derive_title(prompt_text: str, model_output: str) -> str:
    for candidate in (model_output, prompt_text):
        if not candidate:
            continue
        for line in str(candidate).splitlines():
            cleaned = line.strip()
            if len(cleaned) >= 8:
                return shorten(cleaned, width=180, placeholder="...")
    return "Scraped mention"


def _extract_summary_line(text: str) -> str:
    if not text:
        return ""
    for keyword in ("resume", "résumé", "summary", "analyse generale", "analyse générale"):
        match = re.search(rf"{keyword}\s*[:\-]\s*(.+)", text, flags=re.IGNORECASE)
        if match:
            return shorten(match.group(1).strip(), width=240, placeholder="...")
    first_line = text.splitlines()[0].strip() if text.splitlines() else ""
    return shorten(first_line, width=240, placeholder="...") if first_line else ""


_SUMMARY_LABEL_RE = re.compile(
    r"^\s*(analyse generale|analyse générale|résumé|resume|summary)\s*[:\-–]\s*",
    flags=re.IGNORECASE,
)

_WHITELIST_CHARS = set(
    "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789éèàçùâêîôûëïüœÉÈÀÇÙÂÊÎÔÛËÏÜŒ .,;:!?\"'()-\n"
)


def _clean_summary_text(text: str) -> str:
    if not text:
        return ""
    cleaned = _SUMMARY_LABEL_RE.sub("", text.strip())
    # Strip common noisy prefixes that sometimes leak from the model output.
    noisy_markers = [
        "Sortie modele",
        "Sortie modèle",
        "Analyse generale",
        "Analyse générale",
        "Extrait source",
    ]
    for marker in noisy_markers:
        cleaned = re.sub(marker, " ", cleaned, flags=re.IGNORECASE)
    cleaned = re.sub(r"{%.*?%}", " ", cleaned, flags=re.DOTALL)
    cleaned = re.sub(r"{{.*?}}", " ", cleaned, flags=re.DOTALL)
    cleaned = re.sub(r"<[^>]+>", " ", cleaned)
    cleaned = re.sub(r"https?://\S+", " ", cleaned)
    cleaned = re.sub(r"\s+", " ", cleaned)
    cleaned = cleaned.strip()
    cleaned = "".join(ch for ch in cleaned if ch in _WHITELIST_CHARS)
    return cleaned.strip()


def _parse_sentiment_label(model_output: str) -> tuple[str, float | None]:
    text = (model_output or "").lower()
    if "negatif" in text or "negative" in text:
        return "negative", -0.75
    if "positif" in text or "positive" in text:
        return "positive", 0.75
    if "neutre" in text or "neutral" in text:
        return "neutral", 0.0
    return "neutral", None


def _structure_model_output(source_text: str, model_output: str) -> dict[str, Any]:
    """
    Build a structured payload usable by the UI and reporting layer.
    """
    parsed = _safe_parse_json_model_output(model_output)
    if not parsed:
        parsed = {}
        if model_output:
            parsed["resume_article"] = _clean_summary_text(model_output)
    sentiment_label_fr = _normalize_label_french(parsed.get("sentiment_label") if parsed else None)
    raw_scores = parsed.get("sentiment_scores") if isinstance(parsed, Mapping) else None
    sentiment_scores = _normalize_scores(raw_scores) if isinstance(raw_scores, Mapping) else None

    sentiment_label_en, sentiment_score = _parse_sentiment_label(model_output)
    if sentiment_label_fr == "negatif":
        sentiment_label_en = "negative"
        sentiment_score = sentiment_score if sentiment_score is not None else -0.75
    elif sentiment_label_fr == "positif":
        sentiment_label_en = "positive"
        sentiment_score = sentiment_score if sentiment_score is not None else 0.75
    else:
        sentiment_label_en = "neutral"
        sentiment_score = sentiment_score if sentiment_score is not None else 0.0

    reasons = parsed.get("sentiment_reasons") if parsed else None
    if not isinstance(reasons, list):
        reasons = []
    reasons = [str(reason).strip() for reason in reasons if str(reason).strip()]
    reasons = reasons[:3]

    article_summary = ""
    raw_resume = parsed.get("resume_article") if parsed else None
    if raw_resume:
        article_summary = _clean_summary_text(str(raw_resume))
    elif parsed and parsed.get("article_summary"):
        article_summary = _clean_summary_text(str(parsed.get("article_summary")).strip())
    else:
        article_summary = _clean_summary_text(
            _extract_summary_line(model_output) or _extract_summary_line(source_text)
        )
    if not article_summary:
        article_summary = _clean_summary_text(model_output) or "Résumé indisponible."

    risk_level = _normalize_risk_level(parsed.get("risk_level") if parsed else None)
    recommendations = parsed.get("recommendations") if parsed else None
    if not isinstance(recommendations, list):
        recommendations = []
    recommendations = [str(rec).strip() for rec in recommendations if str(rec).strip()]

    sections: list[dict[str, str]] = []
    if article_summary:
        sections.append({"title": "Résumé de l'article", "text": article_summary})
    if reasons:
        sections.append({"title": "Raisons du sentiment", "text": "\n".join(reasons)})
    if model_output:
        sections.append({"title": "Sortie modèle", "text": str(model_output).strip()})
    if source_text:
        sections.append({"title": "Extrait source", "text": str(source_text).strip()[:1200]})

    body_parts: list[str] = []
    for section in sections:
        heading = section.get("title")
        text = section.get("text")
        if not text:
            continue
        body_parts.append(f"{heading}: {text}" if heading else text)

    body = "\n\n".join(body_parts) or model_output or source_text
    is_urgent = sentiment_label_fr == "negatif" or risk_level == "élevé"
    sentiment_label_display = {"negatif": "négatif", "positif": "positif", "neutre": "neutre"}.get(
        sentiment_label_fr, sentiment_label_fr
    )

    return {
        "title": _derive_title(source_text, model_output),
        "summary": article_summary or (shorten(body, width=240, placeholder="...") if body else ""),
        "body": body,
        "sentiment_label": sentiment_label_display,
        "sentiment_label_en": sentiment_label_en,
        "sentiment_score": sentiment_score,
        "sentiment_scores": sentiment_scores,
        "sentiment_reasons": reasons,
        "article_summary": article_summary,
        "resume_article": article_summary,
        "risk_level": risk_level,
        "recommendations": recommendations,
        "is_urgent": is_urgent,
        "urgency_reason": "Sentiment négatif détecté" if is_urgent else None,
        "sections": sections,
        "raw_output": model_output,
    }


def _run_model(prompt_text: str, *, mode: str | None, target_language: str | None) -> str:
    model_module = _load_model_module()
    normalized_mode = (mode or "sentiment").strip().lower()
    if normalized_mode.startswith("trans") and hasattr(model_module, "get_faithful_translation"):
        language = target_language
        if language is None:
            languages = getattr(model_module, "TRANSLATION_LANGUAGES", None)
            if isinstance(languages, (list, tuple)) and languages:
                language = languages[0]
            else:
                language = "English"
        return model_module.get_faithful_translation(prompt_text, language)

    if hasattr(model_module, "analyze_emotions"):
        return model_module.analyze_emotions(prompt_text)

    if hasattr(model_module, "get_faithful_translation"):
        return model_module.get_faithful_translation(prompt_text, target_language or "English")

    raise RuntimeError("No suitable inference function found in ModelDeTraductionFinal.py")


def run_llm_pipeline(*, url: str | None = None, scraped_data: Any | None = None, **kwargs) -> dict:
    """
    Run the scraper, build a prompt, and invoke the LLM model.

    Parameters:
        url: Optional URL forwarded to the scraper if supported.
        scraped_data: Optional pre-fetched data (skips scraping when provided).
        **kwargs: Additional keyword arguments forwarded to the scraper. You may
                  include \"mode\" (\"sentiment\" or \"translation\") and
                  \"target_language\" (for translation mode).

    Returns:
        A JSON-serializable dict containing:
            {\"input\": <prompt_text>, \"output\": <model_output>}
        On error, returns:
            {\"input\": <prompt_text or None>, \"error\": <message>}
    """
    prompt_text: str | None = None

    try:
        scraper_kwargs = dict(kwargs)
        mode = scraper_kwargs.pop("mode", "sentiment")
        target_language = scraper_kwargs.pop("target_language", None)

        data_for_prompt = scraped_data
        if data_for_prompt is None:
            if url is not None:
                scraper_kwargs.setdefault("url", url)
            data_for_prompt = _run_scraper(scraper_kwargs)

        base_prompt = _normalize_prompt_text(data_for_prompt)
        prompt_text = _build_structured_prompt(base_prompt)
        model_output = _run_model(prompt_text, mode=mode, target_language=target_language)

        return {
            "input": prompt_text,
            "output": model_output,
            "structured": _structure_model_output(base_prompt, model_output),
        }
    except Exception as exc:  # noqa: BLE001 - we want to capture all failures for logging
        logger.exception("Failed to run LLM pipeline")
        return {
            "input": prompt_text,
            "error": str(exc),
        }

from __future__ import annotations

import importlib.util
import inspect
import logging
from pathlib import Path
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
    scrapping_module = _load_scrapping_module()

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

    raise RuntimeError("No callable scraper found in scrapping.py")


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


def run_llm_pipeline(*, url: str | None = None, **kwargs) -> dict:
    """
    Run the scraper, build a prompt, and invoke the LLM model.

    Parameters:
        url: Optional URL forwarded to the scraper if supported.
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

        if url is not None:
            scraper_kwargs.setdefault("url", url)

        scraped_data = _run_scraper(scraper_kwargs)
        prompt_text = _normalize_prompt_text(scraped_data)
        model_output = _run_model(prompt_text, mode=mode, target_language=target_language)

        return {
            "input": prompt_text,
            "output": model_output,
        }
    except Exception as exc:  # noqa: BLE001 - we want to capture all failures for logging
        logger.exception("Failed to run LLM pipeline")
        return {
            "input": prompt_text,
            "error": str(exc),
        }

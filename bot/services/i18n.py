from pathlib import Path
from typing import Optional

from fluent.runtime import FluentLocalization, FluentResourceLoader

# ── Locale fayllarni yuklash ─────────────────────────────────────────────────
LOCALES_DIR = Path(__file__).parent.parent / "locales"
SUPPORTED_LANGS = ["uz", "ru", "en"]
DEFAULT_LANG = "uz"

# FluentResourceLoader roots papkani kutadi, locale/{lang}/messages.ftl qidiradi
_loader = FluentResourceLoader(str(LOCALES_DIR) + "/{locale}")

_localizations: dict[str, FluentLocalization] = {}

for lang in SUPPORTED_LANGS:
    _localizations[lang] = FluentLocalization(
        locales=[lang],
        resource_ids=["messages.ftl"],
        resource_loader=_loader,
        use_isolating=False,  # HTML taglar uchun izolatsiyani o'chirish
    )


def get_text(key: str, lang: str = DEFAULT_LANG, **kwargs) -> str:
    """
    Lokalizatsiya kaliti bo'yicha tarjimani olish.

    Foydalanish:
        get_text("welcome", lang="uz", name="Ali")
    """
    if lang not in _localizations:
        lang = DEFAULT_LANG

    loc = _localizations[lang]
    result = loc.format_value(key, kwargs if kwargs else None)

    if result is None:
        # Fallback — default til
        if lang != DEFAULT_LANG:
            result = _localizations[DEFAULT_LANG].format_value(
                key, kwargs if kwargs else None
            )

    return result or f"[{key}]"  # kalitni ko'rsatish agar topilmasa


def __(key: str, lang: str = DEFAULT_LANG, **kwargs) -> str:
    """get_text uchun qisqa alias"""
    return get_text(key, lang, **kwargs)

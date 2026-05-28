from pathlib import Path

from fluent.runtime import FluentLocalization, FluentResourceLoader

# ── Locale fayllarni yuklash ─────────────────────────────────────────────────
LOCALES_DIR = Path(__file__).parent.parent / "locales"
DEFAULT_LANG = "uz"

# Faqat o'zbek tili qo'llab-quvvatlanadi
_loader = FluentResourceLoader(str(LOCALES_DIR) + "/{locale}")

_localization = FluentLocalization(
    locales=[DEFAULT_LANG],
    resource_ids=["messages.ftl"],
    resource_loader=_loader,
    use_isolating=False,  # HTML taglar uchun izolatsiyani o'chirish
)


def get_text(key: str, lang: str = DEFAULT_LANG, **kwargs) -> str:
    """
    Lokalizatsiya kaliti bo'yicha tarjimani olish (faqat o'zbek tili).

    Foydalanish:
        get_text("welcome", name="Ali")
    """
    result = _localization.format_value(key, kwargs if kwargs else None)
    return result or f"[{key}]"  # kalitni ko'rsatish agar topilmasa


def __(key: str, lang: str = DEFAULT_LANG, **kwargs) -> str:
    """get_text uchun qisqa alias"""
    return get_text(key, lang, **kwargs)

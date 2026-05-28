import re
from typing import Optional
from dataclasses import dataclass, field

from bot.database.models import MovieLanguageType


@dataclass
class ParsedMovie:
    """Kanaldan parse qilingan kino ma'lumotlari"""
    code: str
    message_id: int
    title: Optional[str] = None
    description: Optional[str] = None
    year: Optional[int] = None
    duration: Optional[int] = None
    country: Optional[str] = None
    director: Optional[str] = None
    cast: Optional[str] = None
    imdb_rating: Optional[float] = None
    kinopoisk_rating: Optional[float] = None
    age_rating: Optional[str] = None
    language_type: Optional[MovieLanguageType] = None
    genres: list = field(default_factory=list)

    def has_minimum_data(self) -> bool:
        """Kamida 2 ta ma'lumot borligini tekshirish: title, year, genres"""
        filled = sum([
            bool(self.title),
            bool(self.year),
            bool(self.genres),
        ])
        return filled >= 2


# ── Regex patternlar ──────────────────────────────────────────────────────────

# Kod: #KOD_1234 yoki #1234 yoki KOD: 1234 yoki Kod: 1234
CODE_PATTERNS = [
    re.compile(r"#KOD[_\s]?(\w+)", re.IGNORECASE),
    re.compile(r"KOD\s*[:=]\s*(\w+)", re.IGNORECASE),
    re.compile(r"Kod\s*[:=]\s*(\w+)", re.IGNORECASE),
    re.compile(r"#(\d{3,6})\b"),
]

# Yil: 📅 Yil: 2010 yoki Yili: 2010 (emoji ixtiyoriy)
YEAR_PATTERN = re.compile(
    r"(?:📅\s*)?Yil[i]?\s*[:=]\s*(\d{4})", re.IGNORECASE
)

# Davomiylik: ⏱ Davomiyligi: 148 daqiqa (emoji ixtiyoriy, so'z oxiri ixtiyoriy)
DURATION_PATTERN = re.compile(
    r"(?:⏱\s*)?Davomiylig[i]?\s*[:=]\s*(\d+)\s*(?:daqiqa|min)?",
    re.IGNORECASE,
)

# Mamlakat (emoji ixtiyoriy, so'z oxiri ixtiyoriy)
COUNTRY_PATTERN = re.compile(
    r"(?:🌍\s*)?Mamlakat[i]?\s*[:=]\s*(.+?)(?:\n|$)",
    re.IGNORECASE,
)

# Janr (emoji ixtiyoriy, so'z oxiri ixtiyoriy)
GENRE_PATTERN = re.compile(
    r"(?:🎭\s*)?Janr[i]?\s*[:=]\s*(.+?)(?:\n|$)",
    re.IGNORECASE,
)

# IMDb + Kinopoisk: ⭐ IMDb: 8.8 | Kinopoisk: 8.7
IMDB_PATTERN = re.compile(
    r"IMDb\s*[:=]\s*([\d.]+)",
    re.IGNORECASE,
)

KINOPOISK_PATTERN = re.compile(
    r"Kinopoisk\s*[:=]\s*([\d.]+)",
    re.IGNORECASE,
)

# Rejissyor
DIRECTOR_PATTERN = re.compile(
    r"(?:🎬\s*)?Rejissyor\s*[:=]\s*(.+?)(?:\n|$)",
    re.IGNORECASE,
)

# Aktyor
CAST_PATTERN = re.compile(
    r"(?:👥\s*)?Aktyorlar\s*[:=]\s*(.+?)(?:\n|$)",
    re.IGNORECASE,
)

# Yosh chegarasi
AGE_PATTERN = re.compile(r"\b(\d{1,2}\+)\b")

# Til/dublyaj
LANG_TYPE_PATTERN = re.compile(
    r"(?:🔊\s*)?Til\s*[:=]\s*(.+?)(?:\n|$)",
    re.IGNORECASE,
)

# Tavsif
DESCRIPTION_PATTERN = re.compile(
    r"(?:📝\s*)?Tavsif\s*[:=]\s*(.+?)(?=\n[📅⏱🌍🎭⭐🎯🎬👥🔊#]|\Z)",
    re.IGNORECASE | re.DOTALL,
)

# Nom: birinchi qator 🎬 Kino Nomi
TITLE_PATTERN = re.compile(
    r"^🎬\s*(.+?)$",
    re.MULTILINE,
)


def _map_language_type(raw: str) -> Optional[MovieLanguageType]:
    """
    Kanal caption'idagi til/dublyaj stringini MovieLanguageType enum'ga moslashtirish.
    Noma'lum qiymat uchun None qaytaradi.
    """
    text = raw.lower().strip()

    has_uz = "o'zbek" in text or "uzbek" in text or "o`zbek" in text
    has_ru = "rus" in text or "russian" in text
    has_dub = "dublyaj" in text or "dubbed" in text or "dub" in text
    has_sub = "subtitle" in text or "subtitl" in text or "sub" in text
    has_orig = "original" in text or "asl" in text or "orig" in text

    if has_orig:
        return MovieLanguageType.ORIGINAL
    if has_uz and has_dub:
        return MovieLanguageType.DUBBED_UZ
    if has_ru and has_dub:
        return MovieLanguageType.DUBBED_RU
    if has_uz and has_sub:
        return MovieLanguageType.SUBTITLED_UZ
    if has_ru and has_sub:
        return MovieLanguageType.SUBTITLED_RU
    if "english" in text or "ingliz" in text:
        if has_sub:
            return MovieLanguageType.SUBTITLED_EN
    # Faqat til ko'rsatilsa dublyaj deb qabul qilish
    if has_uz:
        return MovieLanguageType.DUBBED_UZ
    if has_ru:
        return MovieLanguageType.DUBBED_RU

    return None


def parse_caption(caption: str, message_id: int) -> Optional[ParsedMovie]:
    """
    Kino kanal xabarining caption'ini parse qiladi.

    Caption formati:
    ```
    🎬 Kino Nomi
    📅 Yil: 2010
    🎭 Janr: Triller, Drama
    🌍 Mamlakat: AQSh
    ⏱ Davomiyligi: 148 daqiqa
    🎬 Rejissyor: Christopher Nolan
    ⭐ IMDb: 8.8 | Kinopoisk: 8.7
    📝 Tavsif: Kino haqida...

    #KOD_1234
    ```
    """
    if not caption:
        return None

    # ── Kodni topish ─────────────────────────────────────────────────────
    code = None
    for pattern in CODE_PATTERNS:
        match = pattern.search(caption)
        if match:
            code = match.group(1).upper().strip()
            break

    if not code:
        return None

    movie = ParsedMovie(code=code, message_id=message_id)

    # ── Nom ──────────────────────────────────────────────────────────────
    title_match = TITLE_PATTERN.search(caption)
    if title_match:
        raw_title = title_match.group(1).strip()
        # Agar "/" bilan ajratilgan bo'lsa (eski format), birinchi qismni olish
        if "/" in raw_title:
            movie.title = raw_title.split("/")[0].strip()
        else:
            movie.title = raw_title

    # ── Yil ─────────────────────────────────────────────────────────────
    match = YEAR_PATTERN.search(caption)
    if match:
        try:
            movie.year = int(match.group(1))
        except ValueError:
            pass

    # ── Davomiylik ───────────────────────────────────────────────────────
    match = DURATION_PATTERN.search(caption)
    if match:
        try:
            movie.duration = int(match.group(1))
        except ValueError:
            pass

    # ── Mamlakat ─────────────────────────────────────────────────────────
    match = COUNTRY_PATTERN.search(caption)
    if match:
        movie.country = match.group(1).strip()

    # ── Janr ─────────────────────────────────────────────────────────────
    match = GENRE_PATTERN.search(caption)
    if match:
        genres_str = match.group(1).strip()
        movie.genres = [g.strip() for g in re.split(r"[,،،]", genres_str) if g.strip()]

    # ── IMDb ─────────────────────────────────────────────────────────────
    match = IMDB_PATTERN.search(caption)
    if match:
        try:
            movie.imdb_rating = float(match.group(1))
        except ValueError:
            pass

    # ── Kinopoisk ────────────────────────────────────────────────────────
    match = KINOPOISK_PATTERN.search(caption)
    if match:
        try:
            movie.kinopoisk_rating = float(match.group(1))
        except ValueError:
            pass

    # ── Rejissyor ────────────────────────────────────────────────────────
    match = DIRECTOR_PATTERN.search(caption)
    if match:
        movie.director = match.group(1).strip()

    # ── Aktyorlar ────────────────────────────────────────────────────────
    match = CAST_PATTERN.search(caption)
    if match:
        movie.cast = match.group(1).strip()

    # ── Yosh chegarasi ───────────────────────────────────────────────────
    match = AGE_PATTERN.search(caption)
    if match:
        movie.age_rating = match.group(1)

    # ── Til ──────────────────────────────────────────────────────────────
    match = LANG_TYPE_PATTERN.search(caption)
    if match:
        movie.language_type = _map_language_type(match.group(1).strip())

    # ── Tavsif ───────────────────────────────────────────────────────────
    match = DESCRIPTION_PATTERN.search(caption)
    if match:
        movie.description = match.group(1).strip()

    # ── Minimum ma'lumot tekshiruvi ───────────────────────────────────────
    if not movie.has_minimum_data():
        return None

    return movie

import re
from typing import Optional
from dataclasses import dataclass, field


@dataclass
class ParsedMovie:
    """Kanaldan parse qilingan kino ma'lumotlari"""
    code: str
    message_id: int
    title_uz: Optional[str] = None
    title_ru: Optional[str] = None
    title_en: Optional[str] = None
    description_uz: Optional[str] = None
    description_ru: Optional[str] = None
    description_en: Optional[str] = None
    year: Optional[int] = None
    duration: Optional[int] = None
    country: Optional[str] = None
    director: Optional[str] = None
    cast: Optional[str] = None
    imdb_rating: Optional[float] = None
    kinopoisk_rating: Optional[float] = None
    age_rating: Optional[str] = None
    language_type: Optional[str] = None
    genres: list = field(default_factory=list)


# ── Regex patternlar ──────────────────────────────────────────────────────────

# Kod: #KOD_1234 yoki #1234 yoki KOD: 1234
CODE_PATTERNS = [
    re.compile(r"#KOD[_\s]?(\w+)", re.IGNORECASE),
    re.compile(r"KOD\s*[:=]\s*(\w+)", re.IGNORECASE),
    re.compile(r"#(\d{3,6})\b"),
]

# Yil: 📅 Yil: 2010 yoki 2010-yil
YEAR_PATTERN = re.compile(
    r"(?:📅\s*)?(?:Yil|Год|Year)\s*[:=]\s*(\d{4})", re.IGNORECASE
)

# Davomiylik: ⏱ Davomiyligi: 148 daqiqa / мин / min
DURATION_PATTERN = re.compile(
    r"(?:⏱\s*)?(?:Davomiyligi|Длительность|Duration)\s*[:=]\s*(\d+)\s*(?:daqiqa|мин|min)?",
    re.IGNORECASE,
)

# Mamlakat
COUNTRY_PATTERN = re.compile(
    r"(?:🌍\s*)?(?:Mamlakat|Страна|Country)\s*[:=]\s*(.+?)(?:\n|$)",
    re.IGNORECASE,
)

# Janr
GENRE_PATTERN = re.compile(
    r"(?:🎭\s*)?(?:Janr|Жанр|Genre)\s*[:=]\s*(.+?)(?:\n|$)",
    re.IGNORECASE,
)

# IMDb
IMDB_PATTERN = re.compile(
    r"(?:⭐\s*)?IMDb\s*[:=]\s*([\d.]+)",
    re.IGNORECASE,
)

# Kinopoisk
KINOPOISK_PATTERN = re.compile(
    r"(?:🎯\s*)?Kinopoisk\s*[:=]\s*([\d.]+)",
    re.IGNORECASE,
)

# Rejissyor
DIRECTOR_PATTERN = re.compile(
    r"(?:🎬\s*)?(?:Rejissyor|Режиссёр|Director)\s*[:=]\s*(.+?)(?:\n|$)",
    re.IGNORECASE,
)

# Aktyor
CAST_PATTERN = re.compile(
    r"(?:👥\s*)?(?:Aktyorlar|Актёры|Cast)\s*[:=]\s*(.+?)(?:\n|$)",
    re.IGNORECASE,
)

# Yosh chegarasi
AGE_PATTERN = re.compile(r"\b(\d{1,2}\+)\b")

# Til/dublyaj
LANG_TYPE_PATTERN = re.compile(
    r"(?:🔊\s*)?(?:Til|Язык|Language)\s*[:=]\s*(.+?)(?:\n|$)",
    re.IGNORECASE,
)

# Tavsif
DESCRIPTION_PATTERN = re.compile(
    r"(?:📝\s*)?(?:Tavsif|Описание|Description)\s*[:=]\s*(.+?)(?=\n[📅⏱🌍🎭⭐🎯🎬👥🔊#]|\Z)",
    re.IGNORECASE | re.DOTALL,
)

# Nom (birinchi qator odatda nom bo'ladi — "Nom / Название / Title" formatda)
TITLE_PATTERN = re.compile(
    r"^🎬\s*(.+?)$",
    re.MULTILINE,
)


def parse_caption(caption: str, message_id: int) -> Optional[ParsedMovie]:
    """
    Kino kanal xabarining caption'ini parse qiladi.

    Caption formati (tavsiya etilgan):
    ```
    🎬 O'zbek Nomi / Русское Название / English Title
    📅 Yil: 2010
    🎭 Janr: Triller, Drama
    🌍 Mamlakat: AQSh
    ⏱ Davomiyligi: 148 daqiqa
    🔊 Til: O'zbek dublyaj
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
            code = match.group(1).upper()
            break

    if not code:
        return None

    movie = ParsedMovie(code=code, message_id=message_id)

    # ── Nomlar ───────────────────────────────────────────────────────────
    title_match = TITLE_PATTERN.search(caption)
    if title_match:
        titles = [t.strip() for t in title_match.group(1).split("/")]
        if len(titles) >= 1:
            movie.title_uz = titles[0]
        if len(titles) >= 2:
            movie.title_ru = titles[1]
        if len(titles) >= 3:
            movie.title_en = titles[2]

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
        movie.language_type = match.group(1).strip()

    # ── Tavsif ───────────────────────────────────────────────────────────
    match = DESCRIPTION_PATTERN.search(caption)
    if match:
        desc = match.group(1).strip()
        movie.description_uz = desc  # Tavsifni u/r/en ajratmay saqlaymiz (oddiy holatda)

    return movie

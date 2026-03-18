"""
Configuraciones centralizadas para validadores y clientes HTTP.
"""

from typing import Final

DEFAULT_USER_AGENT: Final[str] = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"

DEFAULT_TIMEOUT: Final[int] = 10

MAX_RETRIES: Final[int] = 3

RETRY_BACKOFF_FACTOR: Final[float] = 2.0

BEELUP_BASE_URL: Final[str] = "https://beelup.com"

BEELUP_API_ENDPOINT: Final[str] = f"{BEELUP_BASE_URL}/obtener.video.playlist.php"

BEELUP_URL_PATTERNS: Final[list[str]] = [
    "{base}/partido/{id}",
    "{base}/{id}",
    "{base}/watch?v={id}",
    "{base}/partido?id={id}",
    "{base}/app/partido.php?id={id}",
]

GOOGLE_MAPS_LOCATIONS: Final[dict[str, str]] = {
    "CONTAINER RAMOS MEJIA": "https://maps.app.goo.gl/UAxW1AMBuKnL2ezQ9",
    "MEGAFUTBOL": "https://maps.app.goo.gl/TGmHd6uCHv6Ts5Ja9",
}

DATE_PATTERNS: Final[list[str]] = [
    r"\d{2}/\d{2}/\d{4}",
    r"\d{4}-\d{2}-\d{2}",
]

DATE_KEYWORDS: Final[list[str]] = [
    "fecha",
    "date",
    "2024",
    "2025",
    "2026",
]

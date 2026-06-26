"""
Paquete Oficial chala_cup_api

Cliente SDK síncrono y asíncrono, modelos de datos e integraciones
para CHALA CUP CLUB (https://chala-cup-club.vercel.app/).
"""

from .models import (
    BootstrapData,
    NextMatch,
    Player,
    PlayerStats,
    MatchHistory,
    GeneralStats,
    Guest,
    MvpCandidate
)
from .client import ChalaCupClient, ChalaCupAPIError
from .async_client import AsyncChalaCupClient

__version__ = "0.1.0"
__all__ = [
    "BootstrapData",
    "NextMatch",
    "Player",
    "PlayerStats",
    "MatchHistory",
    "GeneralStats",
    "Guest",
    "MvpCandidate",
    "ChalaCupClient",
    "AsyncChalaCupClient",
    "ChalaCupAPIError",
]

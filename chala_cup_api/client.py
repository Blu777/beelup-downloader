import requests
import json
import os
from typing import Optional, Dict, Any, List
from datetime import datetime
from .models import (
    BootstrapData, Player, PlayerStats, GeneralStats
)

class ChalaCupAPIError(Exception):
    """Excepción para errores devueltos por la API de Chala Cup Club."""
    pass

class ChalaCupClient:
    """
    Cliente oficial síncrono para interactuar con la API REST de Chala Cup Club.
    """
    DEFAULT_BASE_URL = "https://chala-cup-club.vercel.app"
    TOKEN_FILE = ".chala_token"

    def __init__(self, base_url: str = DEFAULT_BASE_URL, token: Optional[str] = None):
        self.base_url = base_url.rstrip("/")
        self.session = requests.Session()
        self.session.headers.update({
            "User-Agent": "ChalaCupAPI-PythonClient/0.1.0",
            "Content-Type": "application/json",
            "Accept": "application/json"
        })
        self.token = token
        if not self.token and os.path.exists(self.TOKEN_FILE):
            try:
                with open(self.TOKEN_FILE, "r") as f:
                    self.token = f.read().strip()
            except Exception:
                pass
        self._update_token_header()

    def _update_token_header(self):
        if self.token:
            self.session.headers["X-Chala-Token"] = self.token
        else:
            self.session.headers.pop("X-Chala-Token", None)

    def _request(self, method: str, endpoint: str, **kwargs) -> Any:
        url = f"{self.base_url}/club/api/{endpoint.lstrip('/')}"
        response = self.session.request(method, url, **kwargs)
        if response.status_code == 204:
            return None
        
        try:
            data = response.json()
        except Exception:
            data = {"message": response.text}

        if not response.ok:
            detail = data.get("detail", data.get("message", "Error desconocido de API"))
            if isinstance(detail, list):
                detail = " / ".join([item.get("msg", str(item)) if isinstance(item, dict) else str(item) for item in detail])
            raise ChalaCupAPIError(f"[{response.status_code}] {detail}")
        
        return data

    # --- Endpoints Principales ---

    def get_bootstrap(self) -> BootstrapData:
        """Obtiene el estado completo en tiempo real del torneo."""
        raw = self._request("GET", "/bootstrap")
        return BootstrapData.from_dict(raw)

    def get_general_stats(self) -> GeneralStats:
        """
        Calcula las estadísticas falopa globales del conventillo cannábico.
        Utiliza la fórmula oficial de 1.5 porros por edición y tasa de motalidad de 6 lesionados.
        """
        data = self.get_bootstrap()
        first_sunday = datetime.fromisoformat("2025-08-24T12:00:00-03:00")
        try:
            now_dt = datetime.fromisoformat(data.now)
        except Exception:
            now_dt = datetime.now()
        
        diff_ms = now_dt.timestamp() - first_sunday.timestamp()
        if diff_ms <= 0:
            editions = 0
        else:
            editions = int(diff_ms // (7 * 24 * 3600)) + 1

        porros = editions * 1.5
        grams = porros * 1.5
        motality = round((6 / editions) * 100, 1) if editions > 0 else 0.0

        return GeneralStats(
            editions=editions,
            porros_smoked=porros,
            grams_smoked=grams,
            motality_rate=motality
        )

    # --- Autenticación ---

    def register(self, email: str, password: str) -> Dict[str, Any]:
        """Registra una nueva cuenta de jugador."""
        return self._request("POST", "/auth/register", json={"email": email, "password": password})

    def login(self, email: str, password: str, persist_token: bool = True) -> str:
        """
        Inicia sesión y guarda el X-Chala-Token en la sesión actual.
        """
        res = self._request("POST", "/auth/login", json={"email": email, "password": password})
        self.token = res.get("token", "")
        self._update_token_header()
        if persist_token and self.token:
            try:
                with open(self.TOKEN_FILE, "w") as f:
                    f.write(self.token)
            except Exception:
                pass
        return self.token

    def logout(self) -> Dict[str, Any]:
        """Cierra sesión y limpia el token local."""
        res = self._request("POST", "/auth/logout")
        self.token = None
        self._update_token_header()
        if os.path.exists(self.TOKEN_FILE):
            try:
                os.remove(self.TOKEN_FILE)
            except Exception:
                pass
        return res

    # --- Inscripciones y Partidos ---

    def signup_for_match(self, match_id: str) -> Dict[str, Any]:
        """Inscribe al usuario logueado en el partido solicitado."""
        return self._request("POST", f"/matches/{match_id}/signup")

    def withdraw_from_match(self, match_id: str) -> Dict[str, Any]:
        """Desanota al usuario del partido especificado."""
        return self._request("POST", f"/matches/{match_id}/withdraw")

    def vote_mvp(self, match_id: str, target_id: str) -> Dict[str, Any]:
        """Vota al MVP de la fecha anterior."""
        return self._request("POST", f"/matches/{match_id}/mvp-vote", json={"target_id": target_id})

    # --- Cartas y Votación ---

    def download_my_card(self, dest_path: str = "my_chala_card.png"):
        """Descarga en archivo local la carta PNG del usuario activo."""
        url = f"{self.base_url}/club/api/me/card.png"
        headers = {}
        if self.token:
            headers["X-Chala-Token"] = self.token
        res = self.session.get(url, headers=headers)
        if not res.ok:
            raise ChalaCupAPIError(f"No se pudo descargar la carta: {res.status_code}")
        with open(dest_path, "wb") as f:
            f.write(res.content)
        return dest_path

    def download_player_card(self, target_user_id: str, dest_path: str):
        """Descarga la carta PNG de cualquier jugador."""
        url = f"{self.base_url}/club/api/players/{target_user_id}/card.png"
        res = self.session.get(url)
        if not res.ok:
            raise ChalaCupAPIError(f"No se pudo descargar la carta del jugador: {res.status_code}")
        with open(dest_path, "wb") as f:
            f.write(res.content)
        return dest_path

    def vote_player_stats(self, target_user_id: str, stats: PlayerStats) -> Dict[str, Any]:
        """Envía votos para las estadísticas de un jugador ajeno."""
        return self._request("POST", f"/players/{target_user_id}/vote", json=stats.to_dict())

    def get_my_stats_breakdown(self) -> Dict[str, Any]:
        """Obtiene el chusmerio de quién votó qué stats sobre vos."""
        return self._request("GET", "/me/stats-breakdown")

    def save_profile(self, first_name: str, last_name: str, positions: List[str], smokes: bool = False, photo_data_url: Optional[str] = None) -> Dict[str, Any]:
        """Actualiza la información de tu perfil personal."""
        payload = {
            "first_name": first_name,
            "last_name": last_name,
            "positions": positions,
            "smokes": smokes,
            "photo_data_url": photo_data_url
        }
        return self._request("POST", "/me/profile", json=payload)

    # --- Acciones de Administrador ---

    def admin_set_kickoff(self, match_id: str, scheduled_at: str) -> Dict[str, Any]:
        return self._request("POST", f"/admin/matches/{match_id}/kickoff", json={"scheduled_at": scheduled_at})

    def admin_generate_teams(self, match_id: str) -> Dict[str, Any]:
        """Genera equipos balanceados algorítmicamente para el partido."""
        return self._request("POST", f"/admin/matches/{match_id}/teams")

    def admin_add_guest(self, match_id: str, display_name: str, skill_level: str = "intermedio") -> Dict[str, Any]:
        return self._request("POST", f"/admin/matches/{match_id}/guests", json={"display_name": display_name, "skill_level": skill_level})

    def admin_remove_guest(self, match_id: str, guest_id: str) -> Dict[str, Any]:
        return self._request("DELETE", f"/admin/matches/{match_id}/guests/{guest_id}")

    def admin_create_match(self, scheduled_at: str) -> Dict[str, Any]:
        return self._request("POST", "/admin/matches", json={"scheduled_at": scheduled_at})

    def admin_set_result(self, match_id: str, winner: str, score_label: Optional[str] = None, notes: Optional[str] = None) -> Dict[str, Any]:
        payload = {"winner": winner, "score_label": score_label, "notes": notes}
        return self._request("POST", f"/admin/matches/{match_id}/result", json=payload)

    # --- Videoteca y Clips de Beelup Downloader ---

    @staticmethod
    def get_local_video_catalog(beelup_server_url: str = "http://localhost:5000") -> Dict[str, Any]:
        """
        Consulta el endpoint público optimizado del servidor local Beelup Downloader (/api/public/catalog)
        para obtener todos los partidos con sus videos enteros y clips listos para reproducir.
        """
        url = f"{beelup_server_url.rstrip('/')}/api/public/catalog"
        res = requests.get(url, timeout=10)
        if not res.ok:
            raise ChalaCupAPIError(f"No se pudo consultar el catálogo de videos local: {res.status_code}")
        return res.json()

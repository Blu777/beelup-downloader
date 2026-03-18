"""
Validadores y clientes HTTP consolidados para Beelup Downloader.

Este módulo consolida toda la lógica de validación y comprobación que estaba
distribuida en múltiples archivos check_*.py, aplicando DRY y mejores prácticas.
"""

import json
import re
import time
import urllib.request
import urllib.error
from typing import Any, Optional
from dataclasses import dataclass

from .config import (
    DEFAULT_USER_AGENT,
    DEFAULT_TIMEOUT,
    MAX_RETRIES,
    RETRY_BACKOFF_FACTOR,
    BEELUP_BASE_URL,
    BEELUP_API_ENDPOINT,
    BEELUP_URL_PATTERNS,
    DATE_PATTERNS,
    DATE_KEYWORDS,
)


@dataclass
class HTTPResponse:
    """Representa una respuesta HTTP estructurada."""
    
    status_code: int
    content: str
    url: str
    headers: dict[str, str]
    error: Optional[str] = None


class HTTPClient:
    """
    Cliente HTTP genérico con retry logic y manejo robusto de errores.
    
    Attributes:
        user_agent: User-Agent string para las requests
        timeout: Timeout en segundos para cada request
        max_retries: Número máximo de reintentos
        backoff_factor: Factor multiplicador para exponential backoff
    """
    
    def __init__(
        self,
        user_agent: str = DEFAULT_USER_AGENT,
        timeout: int = DEFAULT_TIMEOUT,
        max_retries: int = MAX_RETRIES,
        backoff_factor: float = RETRY_BACKOFF_FACTOR,
    ) -> None:
        self.user_agent = user_agent
        self.timeout = timeout
        self.max_retries = max_retries
        self.backoff_factor = backoff_factor
    
    def fetch(
        self,
        url: str,
        headers: Optional[dict[str, str]] = None,
    ) -> HTTPResponse:
        """
        Realiza una request HTTP GET con retry logic.
        
        Args:
            url: URL completa del recurso
            headers: Headers adicionales (opcional)
        
        Returns:
            HTTPResponse con el contenido y metadata
        
        Raises:
            urllib.error.URLError: Si fallan todos los reintentos
        """
        request_headers = {"User-Agent": self.user_agent}
        if headers:
            request_headers.update(headers)
        
        last_error: Optional[str] = None
        
        for attempt in range(self.max_retries):
            try:
                req = urllib.request.Request(url, headers=request_headers)
                with urllib.request.urlopen(req, timeout=self.timeout) as response:
                    content = response.read().decode("utf-8", errors="ignore")
                    return HTTPResponse(
                        status_code=response.status,
                        content=content,
                        url=response.url,
                        headers=dict(response.headers),
                    )
            
            except urllib.error.HTTPError as e:
                last_error = f"HTTP {e.code}: {e.reason}"
                if e.code in (429, 503):
                    wait_time = self.backoff_factor ** attempt
                    time.sleep(wait_time)
                elif e.code >= 500:
                    time.sleep(self.backoff_factor ** attempt)
                else:
                    break
            
            except urllib.error.URLError as e:
                last_error = f"URL Error: {e.reason}"
                time.sleep(self.backoff_factor ** attempt)
            
            except Exception as e:
                last_error = f"Unexpected error: {str(e)}"
                time.sleep(self.backoff_factor ** attempt)
        
        return HTTPResponse(
            status_code=0,
            content="",
            url=url,
            headers={},
            error=last_error or "Failed after maximum retries",
        )
    
    def fetch_json(self, url: str) -> tuple[Optional[dict[str, Any]], Optional[str]]:
        """
        Realiza una request y parsea el resultado como JSON.
        
        Args:
            url: URL del endpoint JSON
        
        Returns:
            Tupla (data, error). Si hay error, data es None.
        """
        response = self.fetch(url)
        
        if response.error:
            return None, response.error
        
        try:
            data = json.loads(response.content)
            return data, None
        except json.JSONDecodeError as e:
            return None, f"JSON parse error: {str(e)}"


class BeelupValidator:
    """
    Validador consolidado para operaciones relacionadas con Beelup API.
    
    Consolida la funcionalidad de:
    - check_beelup.py: Obtener metadata JSON
    - check_urls.py: Validar patrones de URL y extraer fechas
    """
    
    def __init__(self, client: Optional[HTTPClient] = None) -> None:
        self.client = client or HTTPClient()
    
    def fetch_metadata(self, match_id: str) -> dict[str, Any]:
        """
        Obtiene la metadata completa de un partido desde la API de Beelup.
        
        Consolida la funcionalidad de check_beelup.py.
        
        Args:
            match_id: ID del partido en Beelup
        
        Returns:
            Dict con la metadata completa o dict con 'error' si falló
        """
        url = f"{BEELUP_API_ENDPOINT}?id={match_id}&formato=json"
        data, error = self.client.fetch_json(url)
        
        if error:
            return {"error": error, "match_id": match_id}
        
        if data:
            return {
                "match_id": match_id,
                "success": True,
                "keys": list(data.keys()),
                "data": {k: v for k, v in data.items() if k != "segmentos"},
                "segment_count": len(data.get("segmentos", [])),
            }
        
        return {"error": "No data returned", "match_id": match_id}
    
    def test_url_patterns(self, match_id: str) -> list[dict[str, Any]]:
        """
        Prueba múltiples patrones de URL de Beelup para un partido.
        
        Consolida la funcionalidad de check_urls.py con optimización.
        
        Args:
            match_id: ID del partido a probar
        
        Returns:
            Lista de dicts con resultados para cada URL probada
        """
        results = []
        
        for pattern in BEELUP_URL_PATTERNS:
            url = pattern.format(base=BEELUP_BASE_URL, id=match_id)
            response = self.client.fetch(url)
            
            result = {
                "url": url,
                "status": "ok" if not response.error else "error",
                "error": response.error,
                "dates": set(),
                "relevant_lines": [],
            }
            
            if not response.error:
                result["dates"] = self._extract_dates(response.content)
                result["relevant_lines"] = self._extract_date_lines(
                    response.content,
                    max_length=200
                )
            
            results.append(result)
        
        return results
    
    def _extract_dates(self, html: str) -> set[str]:
        """
        Extrae todas las fechas del HTML usando patrones configurados.
        
        Args:
            html: Contenido HTML
        
        Returns:
            Set de strings con fechas encontradas
        """
        dates = set()
        for pattern in DATE_PATTERNS:
            dates.update(re.findall(pattern, html))
        return dates
    
    def _extract_date_lines(
        self,
        html: str,
        max_length: int = 200
    ) -> list[str]:
        """
        Extrae líneas del HTML que contienen keywords relacionadas con fechas.
        
        Args:
            html: Contenido HTML
            max_length: Longitud máxima de línea a incluir
        
        Returns:
            Lista de líneas relevantes
        """
        relevant_lines = []
        
        for line in html.split("\n"):
            line_stripped = line.strip()
            if not line_stripped or len(line_stripped) > max_length:
                continue
            
            lower_line = line_stripped.lower()
            if any(keyword in lower_line for keyword in DATE_KEYWORDS):
                relevant_lines.append(line_stripped)
        
        return relevant_lines
    
    def validate_match_id(self, match_id: str) -> tuple[bool, Optional[str]]:
        """
        Valida que un match_id sea accesible y tenga contenido.
        
        Args:
            match_id: ID del partido
        
        Returns:
            Tupla (is_valid, error_message)
        """
        metadata = self.fetch_metadata(match_id)
        
        if "error" in metadata:
            return False, metadata["error"]
        
        if metadata.get("segment_count", 0) == 0:
            return False, "No segments found for this match"
        
        return True, None


class GoogleMapsValidator:
    """
    Validador para extraer información de Google Maps.
    
    Consolida la funcionalidad de check_gmaps.py.
    """
    
    def __init__(self, client: Optional[HTTPClient] = None) -> None:
        self.client = client or HTTPClient()
    
    def extract_og_image(self, url: str) -> Optional[str]:
        """
        Extrae la URL de imagen Open Graph de una página de Google Maps.
        
        Args:
            url: URL de Google Maps
        
        Returns:
            URL de la imagen o None si no se encuentra
        """
        response = self.client.fetch(url)
        
        if response.error:
            return None
        
        jpg_match = re.search(
            r'meta content="([^"]+\.jpg[^"]*)" property="og:image"',
            response.content
        )
        if jpg_match:
            return jpg_match.group(1)
        
        generic_match = re.search(
            r'meta content="([^"]+)" property="og:image"',
            response.content
        )
        if generic_match:
            return generic_match.group(1)
        
        return None
    
    def extract_all_images(
        self,
        locations: Optional[dict[str, str]] = None
    ) -> dict[str, Optional[str]]:
        """
        Extrae imágenes de múltiples ubicaciones de Google Maps.
        
        Consolida la funcionalidad de check_gmaps.py con mejor estructura.
        
        Args:
            locations: Dict de {nombre: url}. Si es None, usa las configuradas.
        
        Returns:
            Dict de {nombre: imagen_url o None}
        """
        from .config import GOOGLE_MAPS_LOCATIONS
        
        locations = locations or GOOGLE_MAPS_LOCATIONS
        results = {}
        
        for name, url in locations.items():
            results[name] = self.extract_og_image(url)
        
        return results


def format_beelup_metadata_report(metadata: dict[str, Any]) -> str:
    """
    Formatea la metadata de Beelup en un reporte legible.
    
    Args:
        metadata: Dict retornado por BeelupValidator.fetch_metadata()
    
    Returns:
        String formateado con el reporte
    """
    if "error" in metadata:
        return f"ERROR: {metadata['error']}\nMatch ID: {metadata.get('match_id', 'unknown')}"
    
    lines = [
        f"Match ID: {metadata['match_id']}",
        f"Status: {'SUCCESS' if metadata.get('success') else 'FAILED'}",
        f"Segment Count: {metadata.get('segment_count', 0)}",
        "",
        "JSON Keys:",
    ]
    
    for key in metadata.get("keys", []):
        lines.append(f"  - {key}")
    
    lines.append("\nKey Values:")
    for key, value in metadata.get("data", {}).items():
        lines.append(f"  {key} = {value}")
    
    return "\n".join(lines)


def format_url_test_report(results: list[dict[str, Any]]) -> str:
    """
    Formatea los resultados de test de URLs en un reporte legible.
    
    Args:
        results: Lista retornada por BeelupValidator.test_url_patterns()
    
    Returns:
        String formateado con el reporte
    """
    lines = []
    
    for result in results:
        status_marker = "[OK]" if result["status"] == "ok" else "[ERROR]"
        lines.append(f"{status_marker} {result['url']}")
        
        if result["error"]:
            lines.append(f"  Error: {result['error']}")
        else:
            dates = result.get("dates", set())
            if dates:
                lines.append(f"  Dates: {dates}")
            else:
                lines.append("  No dates found.")
            
            for line in result.get("relevant_lines", []):
                lines.append(f"  Line: {line}")
        
        lines.append("")
    
    return "\n".join(lines)


def format_gmaps_report(results: dict[str, Optional[str]]) -> str:
    """
    Formatea los resultados de extracción de Google Maps.
    
    Args:
        results: Dict retornado por GoogleMapsValidator.extract_all_images()
    
    Returns:
        String formateado con el reporte
    """
    lines = []
    
    for name, image_url in results.items():
        if image_url:
            lines.append(f"{name}: {image_url}")
        else:
            lines.append(f"{name}: No image found")
    
    return "\n".join(lines)

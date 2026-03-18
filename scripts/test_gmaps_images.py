"""
Script CLI para extraer imágenes de Google Maps.

Reemplaza la funcionalidad de check_gmaps.py con mejoras:
- Parametrizable por línea de comandos
- Salida a archivo o consola
- Soporte para URLs personalizadas
"""

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from utils.validators import GoogleMapsValidator, format_gmaps_report
from utils.config import GOOGLE_MAPS_LOCATIONS


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Extrae imágenes Open Graph de URLs de Google Maps",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Ejemplos:
  %(prog)s
  %(prog)s --url "https://maps.app.goo.gl/abc123" --name "Mi Ubicación"
  %(prog)s --json
        """
    )
    
    parser.add_argument(
        "--url",
        help="URL específica de Google Maps para probar",
    )
    
    parser.add_argument(
        "--name",
        help="Nombre para la ubicación (requerido si se usa --url)",
    )
    
    parser.add_argument(
        "--json",
        action="store_true",
        help="Mostrar resultado como JSON en consola",
    )
    
    parser.add_argument(
        "-v", "--verbose",
        action="store_true",
        help="Mostrar información detallada",
    )
    
    args = parser.parse_args()
    
    validator = GoogleMapsValidator()
    
    if args.url:
        if not args.name:
            parser.error("--name es requerido cuando se usa --url")
        
        if args.verbose:
            print(f"Extrayendo imagen de: {args.url}")
        
        image_url = validator.extract_og_image(args.url)
        results = {args.name: image_url}
    else:
        if args.verbose:
            print(f"Extrayendo imágenes de {len(GOOGLE_MAPS_LOCATIONS)} ubicaciones configuradas...")
        
        results = validator.extract_all_images()
    
    if args.json:
        import json
        print(json.dumps(results, indent=2, ensure_ascii=False))
    else:
        report = format_gmaps_report(results)
        print(report)
    
    failed_count = sum(1 for v in results.values() if v is None)
    if failed_count > 0 and args.verbose:
        print(f"\n⚠ {failed_count} ubicación(es) no pudieron ser procesadas")


if __name__ == "__main__":
    main()

"""
Script CLI para probar la API de Beelup.

Reemplaza la funcionalidad de check_beelup.py con mejoras:
- Parametrizable por línea de comandos
- Salida a archivo o consola
- Manejo robusto de errores
"""

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from utils.validators import BeelupValidator, format_beelup_metadata_report


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Obtiene metadata de un partido desde la API de Beelup",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Ejemplos:
  %(prog)s 26745803
  %(prog)s 26745803 --output metadata.txt
  %(prog)s 26745803 --json
        """
    )
    
    parser.add_argument(
        "match_id",
        help="ID del partido en Beelup",
    )
    
    parser.add_argument(
        "-o", "--output",
        help="Archivo de salida (por defecto: beelup_info.txt)",
        default="beelup_info.txt",
    )
    
    parser.add_argument(
        "--json",
        action="store_true",
        help="Mostrar resultado como JSON en consola en vez de escribir archivo",
    )
    
    parser.add_argument(
        "-v", "--verbose",
        action="store_true",
        help="Mostrar información detallada",
    )
    
    args = parser.parse_args()
    
    if args.verbose:
        print(f"Obteniendo metadata para partido {args.match_id}...")
    
    validator = BeelupValidator()
    metadata = validator.fetch_metadata(args.match_id)
    
    if args.json:
        import json
        print(json.dumps(metadata, indent=2, ensure_ascii=False))
    else:
        report = format_beelup_metadata_report(metadata)
        
        with open(args.output, "w", encoding="utf-8") as f:
            f.write(report)
        
        if args.verbose:
            print(f"✓ Reporte guardado en: {args.output}")
        
        if "error" in metadata:
            sys.exit(1)


if __name__ == "__main__":
    main()

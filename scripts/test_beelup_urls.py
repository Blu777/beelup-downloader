"""
Script CLI para probar múltiples patrones de URL de Beelup.

Reemplaza la funcionalidad de check_urls.py con mejoras:
- Parametrizable por línea de comandos
- Salida a archivo o consola
- Manejo robusto de errores
"""

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from utils.validators import BeelupValidator, format_url_test_report


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Prueba múltiples patrones de URL de Beelup para un partido",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Ejemplos:
  %(prog)s 26745803
  %(prog)s 26745803 --output urls_test.txt
  %(prog)s 26745803 --json
        """
    )
    
    parser.add_argument(
        "match_id",
        help="ID del partido en Beelup",
    )
    
    parser.add_argument(
        "-o", "--output",
        help="Archivo de salida (por defecto: urls_out.txt)",
        default="urls_out.txt",
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
        print(f"Probando URLs para partido {args.match_id}...")
    
    validator = BeelupValidator()
    results = validator.test_url_patterns(args.match_id)
    
    if args.json:
        import json
        results_serializable = []
        for r in results:
            r_copy = r.copy()
            r_copy["dates"] = list(r_copy.get("dates", set()))
            results_serializable.append(r_copy)
        print(json.dumps(results_serializable, indent=2, ensure_ascii=False))
    else:
        report = format_url_test_report(results)
        
        with open(args.output, "w", encoding="utf-8") as f:
            f.write(report)
        
        if args.verbose:
            print(f"✓ Reporte guardado en: {args.output}")
            success_count = sum(1 for r in results if r["status"] == "ok")
            print(f"✓ {success_count}/{len(results)} URLs funcionaron correctamente")


if __name__ == "__main__":
    main()

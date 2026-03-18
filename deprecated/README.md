# ⚠️ Scripts Deprecated

Estos archivos han sido **consolidados** en el módulo `utils/validators.py`.

## Migración

| Archivo Antiguo | Nuevo Reemplazo |
|----------------|-----------------|
| `check_beelup.py` | `scripts/test_beelup_api.py` |
| `check_urls.py` | `scripts/test_beelup_urls.py` |
| `check_gmaps.py` | `scripts/test_gmaps_images.py` |

## ¿Por qué se consolidaron?

1. **DRY (Don't Repeat Yourself)**: Los 3 archivos compartían código duplicado (HTTP requests, manejo de errores)
2. **Mantenibilidad**: Código centralizado es más fácil de mantener
3. **Mejoras**: Los nuevos scripts tienen:
   - Type hints completos
   - Retry logic con exponential backoff
   - Parametrización por CLI (no más IDs hardcoded)
   - Salida flexible (archivo o JSON)
   - Documentación completa
   - Cumplimiento PEP8

## Cómo usar los nuevos scripts

Ver documentación completa en: `scripts/README.md`

```bash
# Antiguo
python check_beelup.py  # ID hardcoded

# Nuevo
python scripts/test_beelup_api.py 26745803 -v
```

## ¿Puedo eliminar estos archivos?

Sí, una vez que hayas validado que los nuevos scripts funcionan correctamente.

**Última actualización**: 2026-03-17

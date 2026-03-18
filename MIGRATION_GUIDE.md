# 📘 Guía de Migración - Scripts Check Consolidados

## 🎯 Resumen de Cambios

Los scripts `check_*.py` han sido **refactorizados y consolidados** en un módulo reutilizable ubicado en `utils/validators.py`.

## 📦 Nueva Estructura

```
beelup-downloader/
├── utils/                          # 🆕 Módulo consolidado
│   ├── __init__.py
│   ├── config.py                   # Configuraciones centralizadas
│   └── validators.py               # Validadores con todas las funcionalidades
├── scripts/                        # 🆕 Scripts CLI parametrizables
│   ├── test_beelup_api.py         # Reemplaza check_beelup.py
│   ├── test_beelup_urls.py        # Reemplaza check_urls.py
│   ├── test_gmaps_images.py       # Reemplaza check_gmaps.py
│   └── README.md
├── deprecated/                     # 📦 Archivos antiguos (para referencia)
│   ├── check_beelup.py
│   ├── check_gmaps.py
│   ├── check_urls.py
│   └── README.md
```

## 🔄 Tabla de Migración

| Antiguo | Nuevo | Mejoras |
|---------|-------|---------|
| `check_beelup.py` | `scripts/test_beelup_api.py` | ✅ Parametrizable<br>✅ Salida JSON<br>✅ Retry logic |
| `check_urls.py` | `scripts/test_beelup_urls.py` | ✅ Sin IDs hardcoded<br>✅ Verbose mode<br>✅ Type hints |
| `check_gmaps.py` | `scripts/test_gmaps_images.py` | ✅ URLs custom<br>✅ JSON output<br>✅ Error handling |

## 🚀 Ejemplos de Uso

### Antes (check_beelup.py)

```python
# ID hardcoded en línea 4
ID = '26745803'  # ❌ No parametrizable

# Ejecutar
python check_beelup.py
# Output: beelup_info.txt (nombre fijo)
```

### Después (test_beelup_api.py)

```bash
# Cualquier ID por CLI
python scripts/test_beelup_api.py 26745803 -v

# Output personalizado
python scripts/test_beelup_api.py 26745803 --output mi_reporte.txt

# Salida JSON
python scripts/test_beelup_api.py 26745803 --json
```

### Uso Programático (Módulo)

```python
from utils.validators import BeelupValidator, GoogleMapsValidator

# Validar Beelup
validator = BeelupValidator()
metadata = validator.fetch_metadata("26745803")
print(metadata["segment_count"])

# Validar URLs
results = validator.test_url_patterns("26745803")
for result in results:
    if result["status"] == "ok":
        print(f"✓ {result['url']}")

# Google Maps
gmaps = GoogleMapsValidator()
images = gmaps.extract_all_images()
print(images["CONTAINER RAMOS MEJIA"])
```

## ✨ Mejoras Implementadas

### 1. **Código Consolidado** (DRY)
- ❌ Antes: 3 archivos con código HTTP duplicado
- ✅ Ahora: 1 clase `HTTPClient` reutilizable

### 2. **Type Hints Completos**
```python
def fetch_metadata(self, match_id: str) -> dict[str, Any]:
    """Fully typed with mypy support"""
```

### 3. **Retry Logic con Exponential Backoff**
```python
# Auto-retry en errores 429, 503, timeout
# Configurable en utils/config.py
MAX_RETRIES = 3
RETRY_BACKOFF_FACTOR = 2.0
```

### 4. **Manejo Robusto de Errores**
```python
# HTTP errors específicos
if e.code == 429:
    wait_time = backoff_factor ** attempt
    time.sleep(wait_time)
```

### 5. **Configuración Centralizada**
```python
# utils/config.py
DEFAULT_USER_AGENT = "Mozilla/5.0..."
BEELUP_BASE_URL = "https://beelup.com"
```

### 6. **PEP8 Compliant**
- Docstrings en todos los métodos
- Spacing correcto
- Naming conventions
- Max line length respetado

## 🧪 Testing

Para validar que todo funciona:

```bash
# Test 1: API Beelup
python scripts/test_beelup_api.py 26745803 -v

# Test 2: URLs de Beelup
python scripts/test_beelup_urls.py 26745803 -v

# Test 3: Google Maps
python scripts/test_gmaps_images.py -v
```

**Expected Output**: Archivos `.txt` generados sin errores.

## 🔧 Configuración

Edita `utils/config.py` para personalizar:

```python
# Timeout de requests
DEFAULT_TIMEOUT = 10  # segundos

# Número de reintentos
MAX_RETRIES = 3

# User Agent
DEFAULT_USER_AGENT = "Tu custom user agent"

# Ubicaciones de Google Maps
GOOGLE_MAPS_LOCATIONS = {
    "TU_UBICACION": "https://maps.app.goo.gl/..."
}
```

## 📊 Métricas de Mejora

| Métrica | Antes | Después | Mejora |
|---------|-------|---------|--------|
| Líneas de código | ~90 | ~550 (con docs) | Más robusto |
| Código duplicado | 3× HTTP code | 1× reutilizable | -67% |
| Type coverage | 0% | 100% | +100% |
| Parametrización | Hardcoded | CLI args | ✅ |
| Error handling | Básico | Retry logic | ✅ |
| Documentación | Ninguna | Completa | ✅ |

## ⚠️ Breaking Changes

**Ninguno**. Los scripts antiguos siguen funcionando en `deprecated/`.

## 🗑️ Limpieza (Opcional)

Una vez validado que todo funciona, puedes:

```bash
# Eliminar archivos deprecated
rm -rf deprecated/

# O mantenerlos para referencia histórica
```

## 🆘 Troubleshooting

### Error: `ModuleNotFoundError: No module named 'utils'`

**Solución**: Ejecuta los scripts desde el directorio raíz del proyecto:

```bash
cd beelup-downloader
python scripts/test_beelup_api.py 26745803
```

### Error: Timeout en requests

**Solución**: Aumenta el timeout en `utils/config.py`:

```python
DEFAULT_TIMEOUT = 30  # Era 10
```

## 📚 Recursos Adicionales

- **Documentación completa**: `scripts/README.md`
- **Código fuente**: `utils/validators.py`
- **Configuración**: `utils/config.py`

## 💬 Feedback

Si encuentras algún problema o tienes sugerencias, abre un issue.

---

**Última actualización**: 2026-03-17  
**Versión**: 2.0.0 (Consolidación)

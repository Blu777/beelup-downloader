# Scripts de Validación y Testing

Scripts CLI consolidados para validar y probar funcionalidades de Beelup Downloader.

## 🎯 Scripts Disponibles

### 1. `test_beelup_api.py`
Obtiene metadata de un partido desde la API de Beelup.

**Uso:**
```bash
# Básico
python scripts/test_beelup_api.py 26745803

# Con archivo de salida personalizado
python scripts/test_beelup_api.py 26745803 --output metadata.txt

# Salida JSON a consola
python scripts/test_beelup_api.py 26745803 --json

# Modo verbose
python scripts/test_beelup_api.py 26745803 -v
```

**Reemplaza:** `check_beelup.py`

---

### 2. `test_beelup_urls.py`
Prueba múltiples patrones de URL de Beelup para encontrar el correcto.

**Uso:**
```bash
# Básico
python scripts/test_beelup_urls.py 26745803

# Con archivo de salida personalizado
python scripts/test_beelup_urls.py 26745803 --output urls_test.txt

# Salida JSON a consola
python scripts/test_beelup_urls.py 26745803 --json

# Modo verbose
python scripts/test_beelup_urls.py 26745803 -v
```

**Reemplaza:** `check_urls.py`

---

### 3. `test_gmaps_images.py`
Extrae imágenes Open Graph de ubicaciones de Google Maps.

**Uso:**
```bash
# Usar ubicaciones configuradas
python scripts/test_gmaps_images.py

# Probar URL específica
python scripts/test_gmaps_images.py --url "https://maps.app.goo.gl/abc123" --name "Mi Ubicación"

# Salida JSON
python scripts/test_gmaps_images.py --json

# Modo verbose
python scripts/test_gmaps_images.py -v
```

**Reemplaza:** `check_gmaps.py`

---

## 📦 Módulo Subyacente

Todos estos scripts utilizan el módulo `utils.validators` que consolida la lógica común:

```python
from utils.validators import BeelupValidator, GoogleMapsValidator

# Validar partido de Beelup
validator = BeelupValidator()
metadata = validator.fetch_metadata("26745803")
results = validator.test_url_patterns("26745803")

# Extraer imágenes de Google Maps
gmaps = GoogleMapsValidator()
images = gmaps.extract_all_images()
```

## 🚀 Ventajas sobre los Scripts Antiguos

- ✅ **Parametrizables**: No más IDs hardcoded
- ✅ **Type Hints**: Código tipado completamente
- ✅ **Retry Logic**: Manejo robusto de errores de red
- ✅ **Salida Flexible**: Archivo o JSON a consola
- ✅ **PEP8 Compliant**: Código limpio y documentado
- ✅ **Reutilizable**: Lógica centralizada en módulo `utils`
- ✅ **Testeable**: Fácil de agregar unit tests

## 📝 Configuración

Puedes modificar las configuraciones en `utils/config.py`:
- User Agent
- Timeouts
- Reintentos
- URLs de Beelup
- Ubicaciones de Google Maps

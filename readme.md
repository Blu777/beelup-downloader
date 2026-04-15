# Beelup Downloader

Aplicación web para descargar partidos de [Beelup](https://beelup.com/), administrarlos desde una biblioteca local y reproducirlos con herramientas pensadas para revisión técnica: selección de cámaras, vistas por tarjetas o calendario y recorte de clips.

## Características

- **Biblioteca integrada**: vista principal con tarjetas, agrupación de cámaras y calendario de partidos descargados
- **Acceso admin por PIN**: gestión protegida para iniciar descargas, generar clips y eliminar contenido
- **Detección de cámaras**: identifica automáticamente las cámaras disponibles antes de descargar
- **Descarga por cámara o en lote**: permite bajar una cámara específica o todas juntas en un archivo ZIP
- **Reproductor avanzado**: reproducción inline, zoom, paneo, control de velocidad, saltos rápidos y cambio de cámara
- **Clips MP4**: generación y guardado de clips desde el reproductor cuando `ffmpeg` está disponible
- **Procesamiento automático**: remux a MP4 cuando `ffmpeg` está instalado, con fallback a `.ts` si no lo está
- **Hardening básico**: validación de IDs, protección contra path traversal, cookies firmadas y rate limiting
- **Docker / TrueNAS Ready**: incluye `Dockerfile` y `docker-compose` para despliegue en servidor o NAS

## Requisitos

### Local

- Python 3.12+
- ffmpeg (opcional pero recomendado, para remux a MP4 y generación de clips)

### Docker

- Docker
- Docker Compose (opcional)

## Instalación y Uso

### Opción 1: Ejecución Local

1. **Clonar el repositorio**

```bash
git clone https://github.com/Blu777/beelup-downloader.git
cd beelup-downloader
```

2. **Instalar dependencias**

```bash
pip install -r requirements.txt
```

3. **Configurar acceso admin (opcional pero recomendado)**

Si defines `ADMIN_PIN`, se habilitan las funciones de administración: iniciar descargas, descargar archivos desde el servidor, generar clips y borrar contenido.

Variables soportadas actualmente:

- `ADMIN_PIN`: PIN requerido para entrar en modo admin
- `SECRET_KEY`: clave para firmar la cookie de admin; recomendable en producción
- `TRUST_PROXY_HEADERS`: usa `X-Forwarded-For` y `X-Forwarded-Proto` si publicas la app detrás de un reverse proxy

4. **Iniciar la aplicación**

```bash
python app.py
```

5. **Abrir el navegador**

```
http://localhost:5000
```

### Opción 2: Docker

1. **Construcción e inicio**

```bash
docker-compose up -d
```

2. **Opcional: habilitar admin en Docker**

Si quieres usar funciones administrativas, agrega variables de entorno al servicio:

```yaml
services:
  beelup-downloader:
    environment:
      - ADMIN_PIN=1234
      - SECRET_KEY=cambia-esto-por-una-clave-larga
      - TRUST_PROXY_HEADERS=true
```

3. **Acceder a la aplicación**

```
http://localhost:5000
```

### Opción 3: TrueNAS/NAS

**Prerequisitos en TrueNAS:**

- Crear datasets para almacenamiento (ej: `/mnt/tank/beelup/downloads` y `/mnt/tank/beelup/temp`)
- Tener Docker instalado (TrueNAS SCALE)

**Paso 1: Ajustar rutas de volúmenes**

Edita `docker-compose.truenas.yml` y ajusta las rutas según tu configuración:

```yaml
volumes:
  - /mnt/<tu_pool>/<tu_dataset>/downloads:/app/downloads
  - /mnt/<tu_pool>/<tu_dataset>/temp:/app/temp
```

**Paso 2: Elegir método de imagen**

- **Método A - Imagen pre-construida** (recomendado): Usa `image: blu777/beelup-downloader:latest` o fija la versión `2.1.1`
- **Método B - Construir desde GitHub**: Comenta `image:` y descomenta las líneas de `build:`

**Paso 3: (Opcional) habilitar admin**

Agrega variables de entorno al servicio si quieres permitir descargas y gestión autenticada:

```yaml
environment:
  - ADMIN_PIN=1234
  - SECRET_KEY=cambia-esto-por-una-clave-larga
  - TRUST_PROXY_HEADERS=true
```

**Paso 4: Desplegar**

```bash
docker-compose -f docker-compose.truenas.yml up -d
```

**Paso 5: Verificar**

```bash
docker ps
docker logs beelup-downloader
```

Accede desde: `http://<IP_TRUENAS>:5000`

## Modo de Uso

1. **Entrar a la biblioteca**
   - Abre `http://localhost:5000`
   - La vista principal muestra los partidos descargados y los clips guardados
   - Puedes alternar entre vista de tarjetas y calendario

2. **Activar modo admin**
   - Usa el botón `Admin` o el texto de versión del footer para abrir el modal de acceso
   - Si `ADMIN_PIN` no está configurado, las funciones administrativas quedan deshabilitadas

3. **Iniciar una descarga**
   - Ve a `Gestionar descargas`
   - Pega el ID del partido o la URL completa de Beelup
   - La app detecta las cámaras disponibles automáticamente
   - Puedes descargar una cámara específica o todas juntas en ZIP

4. **Monitorear el progreso**
   - El avance se actualiza en tiempo real
   - Al terminar, podrás descargar el archivo final desde la interfaz de gestión

5. **Revisar el material**
   - Los partidos aparecen en la biblioteca con sus cámaras disponibles
   - Desde el reproductor puedes cambiar de cámara, hacer zoom, pausar, adelantar o retroceder y descargar la cámara actual si eres admin

6. **Generar clips**
   - En el reproductor, el modo admin habilita la herramienta de clips
   - Marca inicio y fin, luego genera un clip MP4
   - Los clips guardados quedan agrupados por partido dentro de la biblioteca

## Estructura del Proyecto

```
beelup-downloader/
├── app.py                      # App Flask, auth admin, catálogo, clips y endpoints HTTP
├── downloader_core.py          # Motor de descarga, ensamblado, remux y ZIP multi-cámara
├── requirements.txt            # Dependencias Python
├── Dockerfile                  # Imagen Docker oficial con ffmpeg
├── docker-compose.yml          # Despliegue local con volúmenes persistentes
├── docker-compose.truenas.yml  # Ejemplo de despliegue para NAS / TrueNAS
├── templates/
│   ├── index.html              # Biblioteca principal con tarjetas, calendario y modal admin
│   ├── manage.html             # Flujo admin para iniciar descargas
│   └── player.html             # Biblioteca alternativa / reproductor con herramientas de clip
├── static/
│   └── style.css               # Estilos auxiliares
├── utils/                      # Configuración y validadores reutilizables
├── scripts/                    # Scripts de validación y testing
├── deprecated/                 # Scripts legacy conservados como referencia
├── MIGRATION_GUIDE.md          # Guía de migración desde la versión script
├── downloads/                  # Se crea automáticamente en runtime
└── temp/                       # Se crea automáticamente en runtime

```

## Configuración

### Variables de entorno

| Variable | Descripción | Default |
| --- | --- | --- |
| `ADMIN_PIN` | Habilita el modo admin y protege las acciones sensibles | vacío |
| `SECRET_KEY` | Firma la cookie de sesión admin | autogenerada |
| `TRUST_PROXY_HEADERS` | Confía en `X-Forwarded-For` / `X-Forwarded-Proto` detrás de reverse proxy | `false` |

### Almacenamiento

- `downloads/`: videos descargados, ZIPs y `metadata.json`
- `downloads/clips/`: clips MP4 y `clips_metadata.json`
- `temp/`: segmentos temporales durante la descarga
- En Docker, estos directorios se montan como `/app/downloads` y `/app/temp`

### ffmpeg

- **Docker**: la imagen oficial ya instala `ffmpeg`
- **Local**: si no está disponible, la app seguirá descargando, pero conservará archivos `.ts` y no podrá generar clips

## Formato de Salida

- **Partidos**: archivos `video_<id>.mp4` o `video_<id>.ts`, con prefijo de fecha cuando Beelup lo expone
- **Cámaras específicas**: sufijos `_central`, `_izq` o `_der`
- **ZIP multi-cámara**: `Beelup_<fecha>_<id>_todas_las_camaras_<hora>.zip`
- **Clips**: archivos MP4 dentro de `downloads/clips/`

## Scripts de Utilidad

Consulta `scripts/README.md` para los scripts de validación y pruebas auxiliares.

## Migración desde versión anterior

Si vienes de la versión script, consulta `MIGRATION_GUIDE.md` para detalles sobre los cambios.

## Contribuciones

Las contribuciones son bienvenidas. Por favor abre un issue primero para discutir los cambios que te gustaría hacer.

## Licencia

Este proyecto es de código abierto y está disponible bajo una licencia permisiva.

## Enlaces
 
 - [Beelup](https://beelup.com/)
 - [Issues](https://github.com/Blu777/beelup-downloader/issues)
 
 ---
 
 **Versión**: 2.1.1

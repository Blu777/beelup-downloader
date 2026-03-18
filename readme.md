# Beelup Video Downloader

Aplicación web para descargar videos de [Beelup](https://beelup.com/) con interfaz moderna y soporte multi-cámara.

## Características

- **Interfaz Web Moderna**: Interfaz responsive con seguimiento de progreso en tiempo real
- **Soporte Multi-Cámara**: Descarga simultánea de hasta 3 cámaras (Central, Izquierda, Derecha)
- **Descarga Asíncrona**: Descarga optimizada con `aiohttp` para máxima velocidad
- **Conversión Automática a MP4**: Opción de conversión automática con `ffmpeg`
- **Seguridad**: Validación de inputs y protección contra path traversal
- **Docker Ready**: Incluye Dockerfile y docker-compose para deployment fácil
- **Reproductor Integrado**: Visualiza los videos descargados directamente desde la interfaz
- **Gestión de Descargas**: Sistema de caché para evitar descargas duplicadas

## Requisitos

### Local

- Python 3.12+
- ffmpeg (opcional, para conversión a MP4)

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

3. **Iniciar la aplicación**

```bash
python app.py
```

4. **Abrir el navegador**

```
http://localhost:5000
```

### Opción 2: Docker

1. **Construcción e inicio**

```bash
docker-compose up -d
```

2. **Acceder a la aplicación**

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

- **Método A - Imagen pre-construida** (recomendado): Usa la línea `image: blu777/beelup-downloader:latest`
- **Método B - Construir desde GitHub**: Comenta `image:` y descomenta las líneas de `build:`

**Paso 3: Desplegar**

```bash
docker-compose -f docker-compose.truenas.yml up -d
```

**Paso 4: Verificar**

```bash
docker ps
docker logs beelup-downloader
```

Accede desde: `http://<IP_TRUENAS>:5000`

## Modo de Uso

1. **Obtener el ID del Video**
   - Abre el reproductor de Beelup: `https://beelup.com/player.php?id=8890989`
   - Copia el ID del parámetro `id` en la URL (ejemplo: `8890989`)

2. **Descargar el Video**
   - Pega el ID o la URL completa en la interfaz web
   - Selecciona las cámaras que deseas descargar
   - Marca "Convertir a MP4" si deseas el formato MP4 (requiere ffmpeg)
   - Haz clic en "Descargar"

3. **Monitorear el Progreso**
   - El progreso se actualiza en tiempo real
   - Los videos descargados aparecen en el panel "Videos Descargados"

4. **Reproducir o Descargar**
   - Usa el reproductor integrado para ver los videos
   - O descarga los archivos directamente desde el botón de descarga

## Estructura del Proyecto

```
beelup-downloader/
├── app.py                      # Aplicación Flask principal
├── downloader_core.py          # Motor de descarga asíncrono
├── requirements.txt            # Dependencias Python
├── Dockerfile                  # Imagen Docker
├── docker-compose.yml          # Orquestación Docker
├── static/                     # Assets estáticos (CSS, JS)
├── templates/                  # Templates HTML
│   ├── index.html             # Interfaz principal
│   └── player.html            # Reproductor de video
├── downloads/                  # Videos descargados (auto-creado)
├── temp/                       # Archivos temporales (auto-creado)
├── utils/                      # Utilidades y validadores
└── scripts/                    # Scripts de testing

```

## Configuración Avanzada

### Variables de Entorno (Docker)

```yaml
environment:
  - FLASK_ENV=production
  - DOWNLOAD_DIR=/app/downloads
  - TEMP_DIR=/app/temp
```

### Volúmenes Persistentes

```yaml
volumes:
  - ./downloads:/app/downloads
  - ./temp:/app/temp
```

## Formato de Salida

- **Videos TS**: Archivos `.ts` (Transport Stream) compatibles con VLC
- **Videos MP4**: Conversión automática si se selecciona la opción
- **Multi-cámara**: Archivos separados por cámara: `video_8890989_central.mp4`, `video_8890989_izq.mp4`, etc.

## Scripts de Utilidad

Consulta `scripts/README.md` para scripts de testing y validación.

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

**Versión**: 1.2.0

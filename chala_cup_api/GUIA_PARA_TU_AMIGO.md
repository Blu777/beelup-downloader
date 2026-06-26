# ⚽ Guía de Integración Web: Videoteca Chala Cup Club

*(Esta guía está redactada específicamente para que se la envíes al desarrollador de **https://chala-cup-club.vercel.app/**)*

---

## ¡Hola Desarrollador de Chala Cup Club! 👋

Desde el servidor oficial de descargas de partidos (**Beelup Downloader** de Tiago en `https://beelup.tiagonatale.com`), hemos dejado habilitada una conexión pública optimizada con cabeceras `CORS` universales y soporte para streaming por fragmentos (`Range requests`).

De esta forma, **los usuarios de tu página web podrán ver los partidos enteros y las jugadas destacadas (clips) directamente incrustados en tu sitio de Vercel**, sin que tu servidor consuma espacio ni ancho de banda.

---

## 🚀 Integración en tu página en 2 pasos

Hemos creado un Widget web nativo (*Vanilla Javascript*) ultraliviano, con diseño moderno **Dark Mode** y **Glassmorphism**, selector de cámaras en vivo y lista de clips con saltos de tiempo automáticos.

### Paso 1: Añadir el archivo estático
Copia el archivo **`chala_video_gallery.js`** en la carpeta de activos públicos de tu proyecto frontend (ejemplo: `public/chala_video_gallery.js`).

### Paso 2: Montar el reproductor

#### A. Si usas HTML estándar o Astro:
```html
<!-- Contenedor de la galería -->
<div id="videoteca-chala"></div>

<!-- Script del Widget -->
<script src="/chala_video_gallery.js"></script>
<script>
  document.addEventListener('DOMContentLoaded', () => {
    new ChalaVideoGallery(
      document.getElementById('videoteca-chala'),
      "https://beelup.tiagonatale.com"
    );
  });
</script>
```

#### B. Si usas Next.js / React:
```jsx
import { useEffect } from 'react';

export default function ReplaysSection() {
  useEffect(() => {
    // Cargar el script de forma dinámica
    const script = document.createElement('script');
    script.src = '/chala_video_gallery.js';
    script.onload = () => {
      if (window.ChalaVideoGallery) {
        new window.ChalaVideoGallery(
          document.getElementById('videoteca-chala'),
          "https://beelup.tiagonatale.com"
        );
      }
    };
    document.body.appendChild(script);

    return () => {
      document.body.removeChild(script);
    };
  }, []);

  return <div id="videoteca-chala" style={{ minHeight: '80vh' }} />;
}
```

---

## 📡 Estructura del Endpoint REST Público (API v2)

Si prefieres no usar nuestro Widget y armar tu propia interfaz visual personalizada en React / Tailwind, puedes consultar directamente nuestro catálogo JSON público:

* **URL:** `GET https://beelup.tiagonatale.com/api/public/catalog`
* **CORS:** `Access-Control-Allow-Origin: *` habilitado.
* **Formato de respuesta:**

```json
{
  "generator": "BeelupDownloader-ChalaAPI/2.1.2",
  "total_matches": 25,
  "matches": [
    {
      "match_id": "26745803",
      "title": "MEGAFUTBOL - SAN JUSTO / Martes 17/2",
      "date": "2026-02-17",
      "complejo": "MEGAFUTBOL - SAN JUSTO",
      "cancha": "Cancha 32",
      "cover_url": "https://lh5.googleusercontent.com/...",
      "full_videos": [
        {
          "cam_id": "central",
          "label": "Cámara 1 (Central)",
          "stream_url": "/api/stream/2026-02-17_video_26745803_central.mp4",
          "size_mb": 591.8
        }
      ],
      "clips": [
        {
          "clip_id": "clip_video_26745803_central_...",
          "name": "Golazo al ángulo",
          "stream_url": "/api/clips/stream/clip_video_...mp4",
          "download_url": "/api/clips/download/clip_video_...mp4",
          "duration_seconds": 15.5,
          "size_mb": 12.4
        }
      ]
    }
  ]
}
```

> [!NOTE]
> Para reproducir un video en HTML5 `<video>`, simplemente concatena nuestro dominio base: `https://beelup.tiagonatale.com` + `stream_url`. Nuestro servidor responde peticiones `HTTP 206 Partial Content` de forma nativa para permitir adelantar el video sin interrupciones.

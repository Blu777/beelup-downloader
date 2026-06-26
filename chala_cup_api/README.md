# Chala Cup Club API Python SDK & CLI

SDK oficial en Python (Síncrono/Asíncrono), CLI de terminal y Gateway Flask para **[CHALA CUP CLUB](https://chala-cup-club.vercel.app/)**.

Desarrollado específicamente tras investigar a fondo la arquitectura REST API v0.1.0 (FastAPI) en Vercel.

## Características

* **Modelos Tipados:** Dataclasses puras de Python para `Player`, `NextMatch`, `BootstrapData`, `PlayerStats` y `GeneralStats`.
* **Cálculo Automático de Chalalytics:** Implementa las fórmulas oficiales del torneo:
  * Consumo: $1.5\text{ porros} \times \text{partido}$.
  * Gramos: $1.5\text{g} \times \text{porro}$.
  * Tasa de Motalidad: $\frac{6\text{ lesionados}}{\text{ediciones totales}} \times 100$.
* **Soporte CLI:** Consultá el parte dominical y los rankings desde cualquier terminal sin escribir código.
* **Sesiones Persistentes:** Guarda automáticamente tu `X-Chala-Token` en `.chala_token`.
* **Microservicio Gateway:** Listo para enlazar partidos de Beelup Downloader con actas de Chala Cup.

---

## Uso desde la Línea de Comandos (CLI)

Ejecutá el módulo directamente con Python:

### Ver estado de la próxima fecha y Chalalytics
```bash
python -m chala_cup_api.cli status
```

### Ver tabla de posiciones (Top Porreros)
```bash
python -m chala_cup_api.cli leaderboard
```

### Iniciar sesión al Growshop digital
```bash
python -m chala_cup_api.cli login -e tu_mail@gmail.com
```

### Anotarse al partido del domingo
```bash
python -m chala_cup_api.cli signup
```

---

## Uso desde Código Python

### Cliente Síncrono (`ChalaCupClient`)

```python
from chala_cup_api import ChalaCupClient, PlayerStats

client = ChalaCupClient()

# 1. Obtener Bootstrap (Estado completo)
state = client.get_bootstrap()
print(f"Próximo partido: {state.next_match.date_label}")

# 2. Login
client.login("ogait2003@gmail.com", "mi_clave_super_secreta")

# 3. Votar stats de un compañero
stats = PlayerStats(pace=85, shooting=80, passing=78, dribbling=82, defense=70, physical=75)
client.vote_player_stats("7fc104931e9944e19464b7dfdb426ce5", stats)

# 4. Descargar mi carta PNG
client.download_my_card("carta_tiago.png")
```

### Cliente Asíncrono (`AsyncChalaCupClient`)

```python
import asyncio
from chala_cup_api import AsyncChalaCupClient

async def main():
    client = AsyncChalaCupClient()
    try:
        state = await client.get_bootstrap()
        print(f"Anotados: {state.next_match.signed_count}")
    finally:
        await client.close()

asyncio.run(main())
```

---

## Levantar Gateway Microservice

```bash
python -m chala_cup_api.gateway
```
Expone endpoints REST en `http://localhost:5050/api/v1/tournament/overview`.

---

## Incrustar Videoteca en la Web de Chala Cup Club

Tu servidor local ya está publicado en producción bajo **`https://beelup.tiagonatale.com`**. Para que tu amigo muestre todos los replays y clips en su página web:

1. Copiar el archivo **`chala_video_gallery.js`** a su proyecto o servidor.
2. Incrustar el siguiente HTML en su página web:

```html
<div id="videoteca-chala"></div>
<script src="chala_video_gallery.js"></script>
<script>
  new ChalaVideoGallery(
    document.getElementById('videoteca-chala'),
    "https://beelup.tiagonatale.com"
  );
</script>
```
El widget cuenta con un fallback inteligente: si el backend en producción aún no se actualizó con la nueva ruta `/api/public/catalog`, consulta automáticamente `/api/videos` y `/api/clips` en `beelup.tiagonatale.com` y reconstruye la videoteca al instante.

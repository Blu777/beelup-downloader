import time
import threading
import os
import subprocess
import asyncio
import aiohttp
import aiofiles
import zipfile
import logging
import shutil
from datetime import datetime, timedelta
from filelock import FileLock

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Status dict to keep track of downloads
# Format: { "beelup_id|camara": { "status": "downloading"|"completed"|"error", "progress": 0-100, "file": "path", "error": "msg", "timestamp": datetime } }
download_status = {}
download_status_lock = threading.Lock()

# Cleanup old status entries after 24 hours
MAX_STATUS_AGE_HOURS = 24

DOWNLOAD_DIR = "downloads"
TEMP_DIR = "temp"

# All possible cameras in order
ALL_CAMERAS = [
    {"id": "central", "label": "Cámara 1 (Central)"},
    {"id": "izq",     "label": "Cámara 2 (Izquierda)"},
    {"id": "der",     "label": "Cámara 3 (Derecha)"},
]

# Ensure directories exist
for d in [DOWNLOAD_DIR, TEMP_DIR]:
    if not os.path.exists(d):
        os.makedirs(d)

def _build_playlist_url(beelup_id, camara=""):
    url = f"https://beelup.com/obtener.video.playlist.php?id={beelup_id}&formato=json"
    if camara:
        url += f"&camara={camara}"
    return url

def _status_key(beelup_id, camara=""):
    return f"{beelup_id}|{camara}" if camara else beelup_id

def _cleanup_old_status():
    """Remove old completed/error status entries to prevent memory leak."""
    with download_status_lock:
        cutoff = datetime.now() - timedelta(hours=MAX_STATUS_AGE_HOURS)
        keys_to_remove = []
        for key, status in download_status.items():
            if status.get("status") in ["completed", "error"]:
                ts = status.get("timestamp")
                if ts and ts < cutoff:
                    keys_to_remove.append(key)
        for key in keys_to_remove:
            logger.info(f"Cleaning up old status entry: {key}")
            del download_status[key]

def _check_disk_space(required_mb=1000):
    """Check if sufficient disk space is available."""
    try:
        stat = shutil.disk_usage(DOWNLOAD_DIR)
        free_mb = stat.free / (1024 * 1024)
        return free_mb >= required_mb
    except Exception as e:
        logger.warning(f"Could not check disk space: {e}")
        return True  # Allow download to proceed if check fails

async def _check_single_camera(session, cam, beelup_id):
    """Returns cam dict if available, else None."""
    url = _build_playlist_url(beelup_id, cam["id"])
    try:
        async with session.get(url, timeout=10) as r:
            if r.status == 200:
                data = await r.json(content_type=None)
                if len(data.get("segmentos", [])) > 0:
                    return cam
    except Exception:
        pass
    return None

async def _detect_cameras_async(beelup_id):
    """Check all cameras concurrently."""
    async with aiohttp.ClientSession() as session:
        results = await asyncio.gather(
            *[_check_single_camera(session, cam, beelup_id) for cam in ALL_CAMERAS]
        )
    # Preserve original order, filter out None
    return [cam for cam in results if cam is not None]

def detect_cameras(beelup_id):
    """Synchronously detect available cameras for a match. Returns list of camera dicts."""
    loop = asyncio.new_event_loop()
    try:
        return loop.run_until_complete(_detect_cameras_async(beelup_id))
    except Exception as e:
        logger.error(f"Camera detection failed for {beelup_id}: {e}")
        return [ALL_CAMERAS[0]]  # Fallback to central only
    finally:
        loop.close()

def start_download_all(beelup_id, cameras):
    """Download all cameras sequentially, then zip them. Uses key '{id}|all'."""
    _cleanup_old_status()
    
    if not _check_disk_space():
        raise Exception("Espacio insuficiente en disco")
    
    key = _status_key(beelup_id, "all")
    with download_status_lock:
        if key in download_status and download_status[key]["status"] == "downloading":
            return
        download_status[key] = {
            "status": "downloading",
            "progress": 0,
            "file": None,
            "error": None,
            "current_cam": None,
            "timestamp": datetime.now(),
        }
    thread = threading.Thread(target=_run_all_worker, args=(beelup_id, cameras))
    thread.daemon = True
    thread.start()

def _run_all_worker(beelup_id, cameras):
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        loop.run_until_complete(_run_all_worker_async(beelup_id, cameras))
    except Exception as e:
        key = _status_key(beelup_id, "all")
        download_status[key]["status"] = "error"
        download_status[key]["error"] = str(e)
    finally:
        loop.close()

async def _run_all_worker_async(beelup_id, cameras):
    """Download cameras sequentially, updating aggregate progress live."""
    key       = _status_key(beelup_id, "all")
    cam_count = len(cameras)
    completed_files = []

    for cam_idx, cam in enumerate(cameras):
        cam_id    = cam["id"]
        cam_label = cam["label"]
        cam_key   = _status_key(beelup_id, cam_id)

        download_status[key]["current_cam"] = cam_label
        download_status[cam_key] = {
            "status": "downloading", "progress": 0, "file": None, "error": None
        }

        # Run the single-camera download as an async task
        task = asyncio.create_task(_download_video_worker_async(beelup_id, cam_id))

        # Monitor per-camera progress and map to aggregate while task runs
        while not task.done():
            cam_prog = download_status[cam_key].get("progress", 0)
            # Each camera occupies (1/cam_count) of the 0-98% range
            all_prog = ((cam_idx + cam_prog / 100) / cam_count) * 98
            download_status[key]["progress"] = round(all_prog, 1)
            await asyncio.sleep(0.5)

        # Propagate any exception from the task
        await task

        cam_status = download_status.get(cam_key, {})
        if cam_status.get("status") == "error":
            raise Exception(f"Error en {cam_label}: {cam_status.get('error', '')}")

        final_file = cam_status.get("file")
        if final_file and os.path.exists(final_file):
            completed_files.append(final_file)

        # Snap to exact slice boundary after each camera
        download_status[key]["progress"] = round(((cam_idx + 1) / cam_count) * 98, 1)

    # Build ZIP
    download_status[key]["status"]      = "comprimiendo (ZIP)"
    download_status[key]["current_cam"] = None
    
    date_str = ""
    if completed_files:
        import re
        fname = os.path.basename(completed_files[0])
        m = re.search(r"^(\d{4}-\d{2}-\d{2})_video_", fname)
        if m:
            date_str = m.group(1) + "_"
    
    # Add timestamp to prevent overwrites
    timestamp_str = datetime.now().strftime("%H%M%S")
    zip_path = os.path.join(DOWNLOAD_DIR, f"Beelup_{date_str}{beelup_id}_todas_las_camaras_{timestamp_str}.zip")
    with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zf:
        for fpath in completed_files:
            zf.write(fpath, arcname=os.path.basename(fpath))

    download_status[key]["progress"] = 100
    download_status[key]["status"]   = "completed"
    download_status[key]["file"]     = zip_path


def get_zip_path(beelup_id):
    """Return the ZIP path for a multi-camera download, or None if not ready."""
    key = _status_key(beelup_id, "all")
    s = download_status.get(key, {})
    if s.get("status") == "completed" and s.get("file"):
        return s["file"]
    return None

def start_download(beelup_id, camara=""):
    """Starts the download in a background thread"""
    _cleanup_old_status()
    
    if not _check_disk_space():
        raise Exception("Espacio insuficiente en disco")
    
    key = _status_key(beelup_id, camara)
    with download_status_lock:
        if key in download_status and download_status[key]["status"] == "downloading":
            return  # Already downloading

        download_status[key] = {
            "status": "downloading",
            "progress": 0,
            "file": None,
            "error": None,
            "timestamp": datetime.now(),
        }

    thread = threading.Thread(target=_run_async_worker, args=(beelup_id, camara))
    thread.daemon = True
    thread.start()

def _run_async_worker(beelup_id, camara=""):
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        loop.run_until_complete(_download_video_worker_async(beelup_id, camara))
    except Exception as e:
        key = _status_key(beelup_id, camara)
        download_status[key]["status"] = "error"
        download_status[key]["error"] = str(e)
    finally:
        loop.close()

async def _download_segment_async(session, url, index, key, semaphore):
    temp_file = os.path.join(TEMP_DIR, f"{key.replace('|','_')}_{index}.ts")

    async with semaphore:
        for attempt in range(5):
            try:
                async with session.get(url, timeout=30) as r:
                    if r.status == 200:
                        # Validate Content-Type
                        content_type = r.headers.get('Content-Type', '').lower()
                        if content_type and 'text/html' in content_type:
                            raise Exception(f"Segmento {index} retornó HTML en vez de video")
                        
                        async with aiofiles.open(temp_file, 'wb') as f:
                            async for chunk in r.content.iter_chunked(65536):
                                await f.write(chunk)
                        # Validate segment has actual content
                        if os.path.exists(temp_file) and os.path.getsize(temp_file) > 0:
                            return index, temp_file
                        else:
                            raise Exception(f"Segmento {index} descargado está vacío")
                    elif r.status == 429:
                        await asyncio.sleep(3 * (attempt + 1))
                    else:
                        await asyncio.sleep(2 * (attempt + 1))
            except asyncio.TimeoutError:
                await asyncio.sleep(2 * (attempt + 1))
            except Exception as e:
                if attempt < 4:
                    await asyncio.sleep(2 * (attempt + 1))
                else:
                    raise Exception(f"Error en segmento {index} luego de 5 intentos: {e}")

        raise Exception(f"No se pudo descargar el segmento {index} luego de múltiples intentos")

async def _download_video_worker_async(beelup_id, camara=""):
    key = _status_key(beelup_id, camara)
    try:
        playlist_url = _build_playlist_url(beelup_id, camara)

        # Step 1: Fetch metadata
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(playlist_url, timeout=10) as json_r:
                    if json_r.status != 200:
                        raise Exception("No se pudo obtener la información de Beelup. Verifica el ID.")
                    segment_list = await json_r.json(content_type=None)
        except Exception as e:
            raise Exception("No se pudo obtener la información de Beelup. Verifica la conexión.")

        if "segmentos" not in segment_list or len(segment_list["segmentos"]) == 0:
            raise Exception("No se encontraron segmentos para este video.")

        # Extract complejo and cancha from playlist JSON
        playlist_complejo = segment_list.get("complejo", "")
        playlist_cancha   = str(segment_list.get("cancha", ""))

        # Step 2: Download segments CONCURRENTLY
        segment_cnt = len(segment_list["segmentos"])

        # Fetch metadata for the date and title concurrently
        date_str = ""
        match_title = ""
        try:
            date_url = f"https://beelup.com/partido?id={beelup_id}"
            async with aiohttp.ClientSession() as session_date:
                async with session_date.get(date_url, timeout=10) as r_date:
                    if r_date.status == 200:
                        html = await r_date.text()
                        import re
                        m = re.search(r"var inicio_video = '(\d{4}-\d{2}-\d{2})", html)
                        if m:
                            date_str = m.group(1)
                        
                        # Extract title
                        m_title = re.search(r"<title>(.*?)</title>", html, re.IGNORECASE)
                        if m_title:
                            match_title = m_title.group(1).replace(" | Beelup", "").strip()
                            # Save title, complejo and cancha to metadata JSON with file locking
                            import json
                            meta_file = os.path.join(DOWNLOAD_DIR, "metadata.json")
                            lock_file = meta_file + ".lock"
                            
                            with FileLock(lock_file, timeout=10):
                                meta_data = {}
                                if os.path.exists(meta_file):
                                    try:
                                        with open(meta_file, "r", encoding="utf-8") as f:
                                            meta_data = json.load(f)
                                    except:
                                        pass
                                if beelup_id not in meta_data or not isinstance(meta_data[beelup_id], dict):
                                    meta_data[beelup_id] = {}
                                meta_data[beelup_id]["title"]    = match_title
                                meta_data[beelup_id]["complejo"] = playlist_complejo
                                meta_data[beelup_id]["cancha"]   = playlist_cancha
                                with open(meta_file, "w", encoding="utf-8") as f:
                                    json.dump(meta_data, f, ensure_ascii=False, indent=2)

        except Exception as e:
            print("Error fetching match date/title:", e)

        # Build output filenames — include camera suffix when relevant
        cam_suffix = f"_{camara}" if camara else ""
        date_prefix = f"{date_str}_" if date_str else ""
        
        ts_output_file  = os.path.join(DOWNLOAD_DIR, f"{date_prefix}video_{beelup_id}{cam_suffix}.ts")
        mp4_output_file = os.path.join(DOWNLOAD_DIR, f"{date_prefix}video_{beelup_id}{cam_suffix}.mp4")

        downloaded_segments = 0
        temp_files_ordered = [None] * segment_cnt

        # Max 8 concurrent downloads — more causes Beelup to throttle/cut response early
        semaphore = asyncio.Semaphore(8)

        async with aiohttp.ClientSession() as session:
            tasks = [
                _download_segment_async(session, v["url"], i, key, semaphore)
                for i, v in enumerate(segment_list["segmentos"])
            ]

            for f in asyncio.as_completed(tasks):
                index, temp_file = await f
                temp_files_ordered[index] = temp_file

                downloaded_segments += 1
                percent = (downloaded_segments * 100) / segment_cnt
                download_status[key]["progress"] = min(round(percent, 2), 99.0)

        # Step 3: Assemble the final file
        download_status[key]["status"] = "ensamblando"
        with open(ts_output_file, 'wb') as outfile:
            for temp_file in temp_files_ordered:
                if temp_file and os.path.exists(temp_file):
                    with open(temp_file, 'rb') as infile:
                        while chunk := infile.read(1024 * 1024 * 5):
                            outfile.write(chunk)
                    # Safe cleanup with error handling
                    try:
                        os.remove(temp_file)
                    except Exception as e:
                        logger.warning(f"Could not remove temp file {temp_file}: {e}")
                else:
                    raise Exception(f"Falta el archivo temporal {temp_file} durante el ensamblaje")

        final_file = ts_output_file

        # Step 4: Try ffmpeg remux
        download_status[key]["status"] = "remuxeando (ffmpeg)"
        try:
            subprocess.run(["ffmpeg", "-version"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=True)
            has_ffmpeg = True
        except (subprocess.CalledProcessError, FileNotFoundError):
            has_ffmpeg = False

        if has_ffmpeg:
            try:
                cmd = [
                    "ffmpeg", "-y", "-i", ts_output_file,
                    "-c", "copy", "-bsf:a", "aac_adtstoasc",
                    mp4_output_file
                ]
                # Run ffmpeg with low priority to avoid crushing the system.
                # On Windows use BELOW_NORMAL_PRIORITY_CLASS; on Linux/Docker use nice.
                import sys
                popen_kwargs = dict(stdout=subprocess.DEVNULL, stderr=subprocess.PIPE)
                if sys.platform == "win32":
                    popen_kwargs["creationflags"] = subprocess.BELOW_NORMAL_PRIORITY_CLASS
                else:
                    cmd = ["nice", "-n", "10"] + cmd
                proc = subprocess.Popen(cmd, **popen_kwargs)
                _, stderr_out = proc.communicate()
                if proc.returncode == 0 and os.path.exists(mp4_output_file):
                    os.remove(ts_output_file)
                    final_file = mp4_output_file
                else:
                    err_msg = stderr_out.decode(errors='ignore')[-500:] if stderr_out else "sin detalles"
                    print(f"ffmpeg terminó con código {proc.returncode}: {err_msg}")
                    if os.path.exists(mp4_output_file):
                        os.remove(mp4_output_file)
            except Exception as e:
                print(f"Error remuxeando con ffmpeg: {e}")
                if os.path.exists(mp4_output_file):
                    os.remove(mp4_output_file)

        # Mark as complete
        with download_status_lock:
            download_status[key]["progress"] = 100
            download_status[key]["status"] = "completed"
            download_status[key]["file"] = final_file
            download_status[key]["timestamp"] = datetime.now()

    except Exception as e:
        logger.error(f"Download error for {key}: {e}")
        with download_status_lock:
            download_status[key]["status"] = "error"
            download_status[key]["error"] = str(e)
            download_status[key]["timestamp"] = datetime.now()

def get_progress(beelup_id, camara=""):
    key = _status_key(beelup_id, camara)
    with download_status_lock:
        if key not in download_status:
            return {"status": "not_found"}
        # Return a copy to avoid external modifications
        status = download_status[key].copy()
        # Remove timestamp from response (internal use only)
        status.pop("timestamp", None)
        return status

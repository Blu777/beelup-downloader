from flask import Flask, render_template, request, jsonify, send_file, make_response, redirect
import os
import re
import hmac
import hashlib
import json
import math
import subprocess
import sys
import time
import uuid
from threading import Lock
import downloader_core

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY") or hashlib.sha256(f"bdl|{os.environ.get('ADMIN_PIN', '')}|{os.path.realpath(__file__)}".encode()).hexdigest()

@app.after_request
def no_cache(response):
    if "text/html" in response.content_type:
        response.headers["Cache-Control"] = "no-store, no-cache, must-revalidate, max-age=0"
        response.headers["Pragma"] = "no-cache"
        response.headers["Expires"] = "0"
    return response

# ── Admin auth ────────────────────────────────────────────────────────────────
ADMIN_PIN  = os.environ.get("ADMIN_PIN", "")
_AUTH_COOKIE = "bdl_admin"
_TRUST_PROXY_HEADERS = os.environ.get("TRUST_PROXY_HEADERS", "").strip().lower() in {"1", "true", "yes", "on"}
_RATE_LIMIT_BUCKETS = {}
_RATE_LIMIT_LOCK = Lock()
_RATE_LIMIT_MAX_BUCKETS = 2048
_JSON_LOCK = Lock()
_CATALOG_CACHE_LOCK = Lock()
_CATALOG_CACHE_TTL_SECONDS = 2.0
_CATALOG_CACHE = {
    "videos": {"signature": None, "payload": None, "expires_at": 0.0},
    "clips": {"signature": None, "payload": None, "expires_at": 0.0},
}

def _make_token(pin: str) -> str:
    """HMAC-signed token so the cookie can't be forged."""
    return hmac.new(app.secret_key.encode(), pin.encode(), hashlib.sha256).hexdigest()

def _is_admin() -> bool:
    """Return True if the request carries a valid admin cookie."""
    if not ADMIN_PIN:
        return False
    token = request.cookies.get(_AUTH_COOKIE, "")
    return hmac.compare_digest(token, _make_token(ADMIN_PIN))

def _client_ip() -> str:
    remote_ip = request.remote_addr or "unknown"
    if not _TRUST_PROXY_HEADERS:
        return remote_ip
    forwarded_for = request.headers.get("X-Forwarded-For", "")
    if forwarded_for:
        return forwarded_for.split(",")[0].strip() or remote_ip
    return remote_ip

def _is_secure_request() -> bool:
    if request.is_secure:
        return True
    forwarded_proto = request.headers.get("X-Forwarded-Proto", "")
    return forwarded_proto.split(",")[0].strip().lower() == "https"

def _prune_rate_limit_hits(hits: list[float], now: float, window_seconds: int) -> list[float]:
    return [ts for ts in hits if now - ts < window_seconds]

def _cleanup_rate_limit_buckets_locked(now: float) -> None:
    stale_keys = []
    for key, entry in list(_RATE_LIMIT_BUCKETS.items()):
        window_seconds = max(int(entry.get("window_seconds", 0)), 1)
        hits = _prune_rate_limit_hits(entry.get("hits", []), now, window_seconds)
        if hits:
            entry["hits"] = hits
            _RATE_LIMIT_BUCKETS[key] = entry
        else:
            stale_keys.append(key)
    for key in stale_keys:
        _RATE_LIMIT_BUCKETS.pop(key, None)
    if len(_RATE_LIMIT_BUCKETS) > _RATE_LIMIT_MAX_BUCKETS:
        overflow = len(_RATE_LIMIT_BUCKETS) - _RATE_LIMIT_MAX_BUCKETS
        oldest_keys = sorted(
            _RATE_LIMIT_BUCKETS,
            key=lambda bucket_key: _RATE_LIMIT_BUCKETS[bucket_key]["hits"][-1] if _RATE_LIMIT_BUCKETS[bucket_key]["hits"] else float("-inf"),
        )[:overflow]
        for key in oldest_keys:
            _RATE_LIMIT_BUCKETS.pop(key, None)

def _is_rate_limited(scope: str, max_hits: int, window_seconds: int) -> bool:
    now = time.time()
    key = (scope, _client_ip())
    with _RATE_LIMIT_LOCK:
        _cleanup_rate_limit_buckets_locked(now)
        entry = _RATE_LIMIT_BUCKETS.get(key)
        if not entry:
            return False
        hits = _prune_rate_limit_hits(entry.get("hits", []), now, window_seconds)
        if hits:
            entry["hits"] = hits
            entry["window_seconds"] = window_seconds
            _RATE_LIMIT_BUCKETS[key] = entry
        else:
            _RATE_LIMIT_BUCKETS.pop(key, None)
        return len(hits) >= max_hits

def _record_rate_limit_hit(scope: str, window_seconds: int) -> None:
    now = time.time()
    key = (scope, _client_ip())
    with _RATE_LIMIT_LOCK:
        _cleanup_rate_limit_buckets_locked(now)
        entry = _RATE_LIMIT_BUCKETS.get(key, {"hits": [], "window_seconds": window_seconds})
        hits = _prune_rate_limit_hits(entry.get("hits", []), now, window_seconds)
        hits.append(now)
        entry["hits"] = hits
        entry["window_seconds"] = window_seconds
        _RATE_LIMIT_BUCKETS[key] = entry

def _reset_rate_limit(scope: str) -> None:
    key = (scope, _client_ip())
    with _RATE_LIMIT_LOCK:
        _RATE_LIMIT_BUCKETS.pop(key, None)

def _consume_rate_limit(scope: str, max_hits: int, window_seconds: int) -> bool:
    if _is_rate_limited(scope, max_hits, window_seconds):
        return False
    _record_rate_limit_hit(scope, window_seconds)
    return True

# ── Security helpers ──────────────────────────────────────────────────────────

# Only alphanumeric characters are valid for IDs and camera names.
_ID_RE  = re.compile(r"^\w{1,64}$")
_CAM_RE = re.compile(r"^(central|izq|der)$")
_VIDEO_FILE_RE = re.compile(r"^(?:(\d{4}-\d{2}-\d{2})_)?video_(\w+?)(?:_(central|izq|der))?\.(mp4|ts)$")

def _safe_id(value: str) -> str | None:
    """Return the value if it looks like a valid Beelup ID, else None."""
    v = value.strip()
    return v if _ID_RE.match(v) else None

def _safe_cam(value: str) -> str | None:
    """Return the value if it is a known camera name (or empty), else None."""
    v = value.strip()
    if v == "":
        return v
    return v if _CAM_RE.match(v) else None

def _safe_download_path(filename: str) -> str | None:
    """
    Resolve the absolute path and verify it stays inside DOWNLOAD_DIR.
    Returns None if the path escapes the directory (path-traversal guard).
    """
    base = os.path.realpath(downloader_core.DOWNLOAD_DIR)
    target = os.path.realpath(os.path.join(downloader_core.DOWNLOAD_DIR, filename))
    # Fixed logic: target must start with base + separator (not be base itself)
    if not target.startswith(base + os.sep):
        return None
    return target

def _safe_clip_path(filename: str) -> str | None:
    clips_dir = os.path.join(downloader_core.DOWNLOAD_DIR, "clips")
    base = os.path.realpath(clips_dir)
    target = os.path.realpath(os.path.join(clips_dir, filename))
    if not target.startswith(base + os.sep):
        return None
    return target

def _parse_video_filename(filename: str) -> tuple[str, str] | None:
    match = _VIDEO_FILE_RE.match(os.path.basename(filename))
    if not match:
        return None
    match_id = match.group(2)
    cam_id = match.group(3) or ""
    return match_id, cam_id

def _write_json_atomic(filepath: str, data) -> None:
    tmp_path = f"{filepath}.tmp"
    with open(tmp_path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    os.replace(tmp_path, filepath)

def _load_json_dict(filepath: str) -> dict:
    if not os.path.exists(filepath):
        return {}
    try:
        with open(filepath, "r", encoding="utf-8") as f:
            loaded = json.load(f)
        return loaded if isinstance(loaded, dict) else {}
    except Exception:
        return {}

def _path_mtime(filepath: str) -> float | None:
    try:
        return os.path.getmtime(filepath)
    except OSError:
        return None

def _get_cached_catalog_payload(name: str, signature) -> dict | None:
    now = time.time()
    with _CATALOG_CACHE_LOCK:
        entry = _CATALOG_CACHE.get(name)
        if not entry:
            return None
        if entry["signature"] == signature and entry["expires_at"] > now:
            return entry["payload"]
    return None

def _set_cached_catalog_payload(name: str, signature, payload: dict) -> None:
    with _CATALOG_CACHE_LOCK:
        _CATALOG_CACHE[name] = {
            "signature": signature,
            "payload": payload,
            "expires_at": time.time() + _CATALOG_CACHE_TTL_SECONDS,
        }

def _update_json_dict(filepath: str, mutate) -> None:
    with _JSON_LOCK:
        data = {}
        if os.path.exists(filepath):
            try:
                with open(filepath, "r", encoding="utf-8") as f:
                    loaded = json.load(f)
                if isinstance(loaded, dict):
                    data = loaded
            except Exception:
                data = {}
        mutate(data)
        _write_json_atomic(filepath, data)

def _extract_beelup_id(raw: str) -> str | None:
    """Extract and validate a Beelup match ID from either a bare ID or a URL."""
    raw = raw.strip()
    if "beelup.com" in raw:
        m = re.search(r"id=(\w+)", raw)
        return m.group(1) if m else None
    return _safe_id(raw)

VERSION = "2.1.0"

_COVERS = {
    "CONTAINER": "https://lh5.googleusercontent.com/p/AF1QipOhj41z6lD0gALX-w_S4LPEpPZJ298Yt_-xR2rR=w408-h306-k-no",
    "MEGAFUTBOL": "https://lh5.googleusercontent.com/p/AF1QipNxPof9xXXiXzTqRLEy8lV1a79YvPscW8xQkR=w408-h306-k-no"
}

_CAM_LABELS = {
    "central": "Cámara 1 (Central)",
    "izq":     "Cámara 2 (Izquierda)",
    "der":     "Cámara 3 (Derecha)",
    "":        "Cámara única",
}

# ── Routes ────────────────────────────────────────────────────────────────────

@app.route("/")
def index():
    return render_template("index.html", version=VERSION, is_admin=_is_admin())

@app.route("/player")
def player():
    return render_template("player.html", version=VERSION, is_admin=_is_admin())

@app.route("/manage")
def manage_page():
    if not _is_admin():
        return render_template("index.html", version=VERSION, is_admin=False, _force_admin_modal=True)
    return render_template("manage.html", version=VERSION, is_admin=True)

@app.route("/admin")
def admin_page():
    return redirect("/manage")

@app.route("/api/admin/login", methods=["POST"])
def admin_login():
    if _is_rate_limited("admin_login", 5, 300):
        return jsonify({"error": "Demasiados intentos. Intenta nuevamente en unos minutos."}), 429
    data = request.get_json(silent=True) or {}
    pin  = data.get("pin", "").strip()
    if not ADMIN_PIN:
        return jsonify({"error": "Admin no configurado en el servidor"}), 503
    if not pin or not hmac.compare_digest(pin, ADMIN_PIN):
        _record_rate_limit_hit("admin_login", 300)
        return jsonify({"error": "PIN incorrecto"}), 401
    _reset_rate_limit("admin_login")
    resp = make_response(jsonify({"ok": True}))
    resp.set_cookie(_AUTH_COOKIE, _make_token(pin), httponly=True, samesite="Strict", secure=_is_secure_request(), max_age=86400 * 7)
    return resp

@app.route("/api/admin/logout", methods=["POST"])
def admin_logout():
    resp = make_response(jsonify({"ok": True}))
    resp.delete_cookie(_AUTH_COOKIE, httponly=True, samesite="Strict", secure=_is_secure_request())
    return resp

@app.route("/api/admin/status")
def admin_status():
    return jsonify({"is_admin": _is_admin(), "pin_configured": bool(ADMIN_PIN)})

@app.route("/api/videos")
def list_videos():
    """List downloaded videos grouped by match ID with camera info."""
    dl_dir = downloader_core.DOWNLOAD_DIR
    meta_file = os.path.join(dl_dir, "metadata.json")
    signature = (
        _path_mtime(dl_dir),
        _path_mtime(meta_file),
    )
    cached_payload = _get_cached_catalog_payload("videos", signature)
    if cached_payload is not None:
        return jsonify(cached_payload)

    matches = {}

    meta_data = _load_json_dict(meta_file)

    try:
        filenames = sorted(os.listdir(dl_dir))
    except OSError:
        filenames = []

    for fname in filenames:
        if not (fname.endswith(".mp4") or fname.endswith(".ts")):
            continue
        m = re.search(r"^(?:(\d{4}-\d{2}-\d{2})_)?video_(\w+?)(?:_(central|izq|der))?\.(mp4|ts)$", fname)
        if not m:
            continue
        match_date = m.group(1) or ""
        match_id   = m.group(2)
        cam_id     = m.group(3) or ""

        try:
            size_mb = round(os.path.getsize(os.path.join(dl_dir, fname)) / (1024 * 1024), 1)
        except OSError:
            continue

        if match_id not in matches:
            raw_meta    = meta_data.get(match_id, "")
            # Support both legacy string format and new dict format
            if isinstance(raw_meta, dict):
                match_title     = raw_meta.get("title", "")
                match_complejo  = raw_meta.get("complejo", "")
                match_cancha    = raw_meta.get("cancha", "")
            else:
                match_title     = raw_meta
                match_complejo  = ""
                match_cancha    = ""
            cover_url = ""
            upper_title = match_title.upper()
            if "CONTAINER" in upper_title:
                cover_url = _COVERS["CONTAINER"]
            elif "MEGAFUTBOL" in upper_title:
                cover_url = _COVERS["MEGAFUTBOL"]
                
            matches[match_id] = {
                "id":       match_id, 
                "date":     match_date, 
                "title":    match_title,
                "complejo": match_complejo,
                "cancha":   match_cancha,
                "cover_url": cover_url,
                "cameras": []
            }
        elif match_date and not matches[match_id].get("date"):
            # If we found a date from another camera file, populate it
            matches[match_id]["date"] = match_date

        existing_cam = next((c for c in matches[match_id]["cameras"] if c["cam_id"] == cam_id), None)
        if existing_cam is None:
            matches[match_id]["cameras"].append({
                "cam_id":   cam_id,
                "label":    _CAM_LABELS.get(cam_id, f"Cámara ({cam_id})"),
                "filename": fname,
                "size_mb":  size_mb,
            })
        elif fname.endswith(".mp4") and existing_cam["filename"].endswith(".ts"):
            existing_cam["filename"] = fname
            existing_cam["size_mb"]  = size_mb

    cam_order = ["izq", "central", "der", ""]
    for m in matches.values():
        m["cameras"].sort(key=lambda c: cam_order.index(c["cam_id"]) if c["cam_id"] in cam_order else 99)
        named = [c for c in m["cameras"] if c["cam_id"] != ""]
        if named:
            m["cameras"] = named

    payload = {"matches": list(matches.values())}
    _set_cached_catalog_payload("videos", signature, payload)
    return jsonify(payload)

@app.route("/api/stream/<path:filename>")
def stream_video(filename):
    """Stream a video file for inline browser playback (supports Range requests)."""
    # Guard: only serve files inside DOWNLOAD_DIR, only .mp4/.ts
    if not (filename.endswith(".mp4") or filename.endswith(".ts")):
        return "Tipo de archivo no permitido", 403

    filepath = _safe_download_path(filename)
    if filepath is None:
        return "Acceso denegado", 403
    if not os.path.exists(filepath):
        return "File not found", 404

    # Whitelist MIME types — never trust guess_type alone
    mime = "video/mp2t" if filepath.endswith(".ts") else "video/mp4"
    return send_file(filepath, mimetype=mime, conditional=True)

@app.route("/api/cameras/<beelup_id>")
def get_cameras(beelup_id):
    """Detect available cameras for a given match ID (admin only)."""
    if not _is_admin():
        return jsonify({"error": "No autorizado"}), 401
    if not _safe_id(beelup_id):
        return jsonify({"error": "ID de partido inválido"}), 400
    try:
        cameras = downloader_core.detect_cameras(beelup_id)
        return jsonify({"cameras": cameras}), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/api/download_all", methods=["POST"])
def start_download_all():
    """Start downloading all cameras for a given match, then zip them."""
    if not _is_admin():
        return jsonify({"error": "No autorizado"}), 401
    data = request.json or {}
    raw_input = data.get("url_or_id", "").strip()
    cameras   = data.get("cameras", [])

    if not raw_input:
        return jsonify({"error": "Por favor ingresa un ID o URL"}), 400

    beelup_id = _extract_beelup_id(raw_input)
    if not beelup_id:
        return jsonify({"error": "ID de partido inválido o URL incorrecta"}), 400

    if not cameras:
        return jsonify({"error": "No se recibieron datos de cámaras"}), 400
    
    # Validate camera data structure
    valid_cam_ids = {"central", "izq", "der"}
    for cam in cameras:
        if not isinstance(cam, dict):
            return jsonify({"error": "Datos de cámara inválidos"}), 400
        cam_id = cam.get("id", "")
        if cam_id not in valid_cam_ids:
            return jsonify({"error": f"ID de cámara inválido: {cam_id}"}), 400
        if "label" not in cam:
            return jsonify({"error": "Falta etiqueta de cámara"}), 400

    try:
        downloader_core.start_download_all(beelup_id, cameras)
        return jsonify({"message": "Descarga de todas las cámaras iniciada", "id": beelup_id}), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/api/progress_all/<beelup_id>")
def get_progress_all(beelup_id):
    if not _safe_id(beelup_id):
        return jsonify({"error": "ID inválido"}), 400
    status = downloader_core.get_progress(beelup_id, "all")
    return jsonify(status)

@app.route("/api/clip/<path:filename>", methods=["POST"])
def download_clip(filename):
    """Generate, save and stream a MP4 clip from a video file using ffmpeg (admin only)."""
    if not _is_admin():
        return jsonify({"error": "No autorizado"}), 401
    if not _consume_rate_limit("clip", 6, 60):
        return jsonify({"error": "Demasiados clips solicitados. Espera un minuto e intenta otra vez."}), 429
    data = request.get_json(silent=True) or {}
    try:
        start = float(data.get("start", 0))
        end   = float(data.get("end", 0))
    except (TypeError, ValueError):
        return jsonify({"error": "Tiempos inválidos"}), 400

    if not math.isfinite(start) or not math.isfinite(end) or start < 0 or end < 0:
        return jsonify({"error": "Tiempos inválidos"}), 400
    if end <= start:
        return jsonify({"error": "El tiempo de fin debe ser mayor al de inicio"}), 400
    if (end - start) > 3600:
        return jsonify({"error": "El clip no puede ser mayor a 1 hora"}), 400

    if not (filename.endswith(".mp4") or filename.endswith(".ts")):
        return "Tipo de archivo no permitido", 403

    filepath = _safe_download_path(filename)
    if filepath is None:
        return "Acceso denegado", 403
    if not os.path.exists(filepath):
        return "File not found", 404

    source_meta = _parse_video_filename(filename)
    if source_meta is None:
        return jsonify({"error": "Archivo de video inválido"}), 400
    match_id, cam_id = source_meta

    duration = end - start
    base     = os.path.splitext(os.path.basename(filename))[0]
    clip_id  = uuid.uuid4().hex[:8]
    out_name = f"clip_{base}_{int(start * 1000)}ms-{int(end * 1000)}ms_{clip_id}.mp4"

    clips_dir = os.path.join(downloader_core.DOWNLOAD_DIR, "clips")
    os.makedirs(clips_dir, exist_ok=True)
    out_path = os.path.join(clips_dir, out_name)

    cmd = ["ffmpeg", "-y",
           "-ss", str(start),
           "-i", filepath,
           "-t", str(duration),
           "-c:v", "libx264",
           "-preset", "veryfast",
           "-crf", "23",
           "-c:a", "aac",
           "-movflags", "+faststart",
           out_path]
    if sys.platform != "win32":
        cmd = ["nice", "-n", "10"] + cmd

    try:
        proc = subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    except FileNotFoundError:
        return jsonify({"error": "ffmpeg no está instalado en el servidor"}), 500

    if proc.returncode != 0 or not os.path.exists(out_path):
        return jsonify({"error": "Error al generar el clip"}), 500

    # Save clip metadata
    if match_id:
        clips_meta_file = os.path.join(clips_dir, "clips_metadata.json")
        try:
            def mutate(clips_meta):
                clips_meta[out_name] = {
                    "match_id": match_id,
                    "cam_id":   cam_id,
                    "start":    start,
                    "end":      end,
                    "filename": out_name,
                }

            _update_json_dict(clips_meta_file, mutate)
        except Exception:
            pass

    return jsonify({
        "ok": True,
        "filename": out_name,
        "download_url": f"/api/clips/download/{out_name}",
        "size_mb": round(os.path.getsize(out_path) / (1024 * 1024), 1),
    })

@app.route("/api/clips")
def list_clips():
    """List saved clips grouped by match_id, enriched with match metadata."""
    clips_dir = os.path.join(downloader_core.DOWNLOAD_DIR, "clips")
    clips_meta_file = os.path.join(clips_dir, "clips_metadata.json")
    meta_file = os.path.join(downloader_core.DOWNLOAD_DIR, "metadata.json")
    signature = (
        _path_mtime(clips_dir),
        _path_mtime(clips_meta_file),
        _path_mtime(meta_file),
    )
    cached_payload = _get_cached_catalog_payload("clips", signature)
    if cached_payload is not None:
        return jsonify(cached_payload)

    clips_meta = _load_json_dict(clips_meta_file)
    match_meta = _load_json_dict(meta_file)

    groups = {}
    if os.path.isdir(clips_dir):
        try:
            clip_filenames = sorted(os.listdir(clips_dir))
        except OSError:
            clip_filenames = []
        for fname in clip_filenames:
            if not fname.endswith(".mp4"):
                continue
            fpath = os.path.join(clips_dir, fname)
            try:
                size_mb = round(os.path.getsize(fpath) / (1024 * 1024), 1)
            except OSError:
                continue
            meta    = clips_meta.get(fname, {})
            mid     = meta.get("match_id", "unknown")

            raw = match_meta.get(mid, {})
            if isinstance(raw, dict):
                title = raw.get("title", "")
            else:
                title = raw

            if mid not in groups:
                groups[mid] = {"match_id": mid, "match_title": title, "clips": []}

            groups[mid]["clips"].append({
                "filename": fname,
                "start":    meta.get("start"),
                "end":      meta.get("end"),
                "cam_id":   meta.get("cam_id", ""),
                "size_mb":  size_mb,
            })

    payload = {"groups": list(groups.values())}
    _set_cached_catalog_payload("clips", signature, payload)
    return jsonify(payload)

@app.route("/api/clips/stream/<path:filename>")
def stream_clip(filename):
    """Stream a saved clip for inline playback."""
    filepath = _safe_clip_path(filename)
    if filepath is None or not filename.endswith(".mp4"):
        return "Acceso denegado", 403
    if not os.path.exists(filepath):
        return "File not found", 404
    return send_file(filepath, mimetype="video/mp4", conditional=True)

@app.route("/api/clips/download/<path:filename>")
def download_saved_clip(filename):
    """Download a saved clip as an attachment."""
    filepath = _safe_clip_path(filename)
    if filepath is None or not filename.endswith(".mp4"):
        return "Acceso denegado", 403
    if not os.path.exists(filepath):
        return "File not found", 404
    return send_file(filepath, mimetype="video/mp4", as_attachment=True, download_name=os.path.basename(filepath))

@app.route("/api/clips/delete/<path:filename>", methods=["DELETE"])
def delete_clip(filename):
    """Delete a saved clip (admin only)."""
    if not _is_admin():
        return jsonify({"error": "No autorizado"}), 401
    clips_dir = os.path.join(downloader_core.DOWNLOAD_DIR, "clips")
    filepath = _safe_clip_path(filename)
    if filepath is None or not filename.endswith(".mp4"):
        return "Acceso denegado", 403
    try:
        if os.path.exists(filepath):
            os.remove(filepath)
        clips_meta_file = os.path.join(clips_dir, "clips_metadata.json")
        if os.path.exists(clips_meta_file):
            def mutate(clips_meta):
                clips_meta.pop(filename, None)

            _update_json_dict(clips_meta_file, mutate)
    except Exception as e:
        return jsonify({"error": str(e)}), 500
    return jsonify({"ok": True})

@app.route("/api/match/<beelup_id>", methods=["DELETE"])
def delete_match(beelup_id):
    """Delete all video/zip files for a given match (admin only)."""
    if not _is_admin():
        return jsonify({"error": "No autorizado"}), 401
    if not _safe_id(beelup_id):
        return jsonify({"error": "ID inválido"}), 400
    dl_dir = downloader_core.DOWNLOAD_DIR
    deleted = []
    try:
        for fname in list(os.listdir(dl_dir)):
            fpath = os.path.join(dl_dir, fname)
            if not os.path.isfile(fpath):
                continue
            if fname.endswith((".mp4", ".ts")):
                m = re.search(r"^(?:\d{4}-\d{2}-\d{2}_)?video_(\w+?)(?:_(central|izq|der))?\.(mp4|ts)$", fname)
                if m and m.group(1) == beelup_id:
                    os.remove(fpath)
                    deleted.append(fname)
            elif fname.endswith(".zip") and f"_{beelup_id}_todas_las_camaras_" in fname:
                os.remove(fpath)
                deleted.append(fname)
        meta_file = os.path.join(dl_dir, "metadata.json")
        if os.path.exists(meta_file):
            def mutate(meta):
                meta.pop(beelup_id, None)

            _update_json_dict(meta_file, mutate)
        clips_dir = os.path.join(dl_dir, "clips")
        clips_meta_file = os.path.join(clips_dir, "clips_metadata.json")
        if os.path.exists(clips_meta_file):
            with _JSON_LOCK:
                try:
                    with open(clips_meta_file, "r", encoding="utf-8") as f:
                        loaded = json.load(f)
                except Exception:
                    loaded = {}
                clips_meta = loaded if isinstance(loaded, dict) else {}
                to_remove = [k for k, v in clips_meta.items() if v.get("match_id") == beelup_id]
                for clip_fname in to_remove:
                    clips_meta.pop(clip_fname, None)
                _write_json_atomic(clips_meta_file, clips_meta)
            for clip_fname in to_remove:
                clip_path = os.path.join(clips_dir, clip_fname)
                if os.path.exists(clip_path):
                    os.remove(clip_path)
                    deleted.append(f"clips/{clip_fname}")
        return jsonify({"ok": True, "deleted": deleted})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/api/clip_status")
def clip_status():
    """Check if ffmpeg is available for server-side clipping."""
    try:
        subprocess.run(["ffmpeg", "-version"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=True)
        return jsonify({"available": True})
    except (subprocess.CalledProcessError, FileNotFoundError):
        return jsonify({"available": False})

@app.route("/api/file_zip/<beelup_id>")
def download_zip(beelup_id):
    if not _is_admin():
        return jsonify({"error": "No autorizado"}), 401
    if not _safe_id(beelup_id):
        return jsonify({"error": "ID inválido"}), 400
    zip_path = downloader_core.get_zip_path(beelup_id)
    if zip_path and os.path.exists(zip_path):
        label = os.path.basename(zip_path)
        return send_file(zip_path, as_attachment=True, download_name=label)
    return "Archivo ZIP no encontrado", 404

@app.route("/api/download", methods=["POST"])
def start_download():
    if not _is_admin():
        return jsonify({"error": "No autorizado"}), 401
    data = request.json or {}
    raw_input = data.get("url_or_id", "").strip()
    camara    = data.get("camara", "").strip()

    if not raw_input:
        return jsonify({"error": "Por favor ingresa un ID o URL"}), 400

    beelup_id = _extract_beelup_id(raw_input)
    if not beelup_id:
        return jsonify({"error": "ID de partido inválido o URL incorrecta"}), 400

    safe_cam = _safe_cam(camara)
    if safe_cam is None:
        return jsonify({"error": "Nombre de cámara inválido"}), 400

    try:
        downloader_core.start_download(beelup_id, safe_cam)
        return jsonify({"message": "Descarga iniciada", "id": beelup_id, "camara": safe_cam}), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/api/progress/<beelup_id>")
def get_progress(beelup_id):
    if not _safe_id(beelup_id):
        return jsonify({"error": "ID inválido"}), 400
    camara = request.args.get("camara", "").strip()
    safe_cam = _safe_cam(camara)
    if safe_cam is None:
        return jsonify({"error": "Nombre de cámara inválido"}), 400
    status = downloader_core.get_progress(beelup_id, safe_cam)
    return jsonify(status)

@app.route("/api/file/<beelup_id>")
def download_file(beelup_id):
    if not _is_admin():
        return jsonify({"error": "No autorizado"}), 401
    if not _safe_id(beelup_id):
        return jsonify({"error": "ID inválido"}), 400

    camara = request.args.get("camara", "").strip()
    safe_cam = _safe_cam(camara)
    if safe_cam is None:
        return jsonify({"error": "Nombre de cámara inválido"}), 400

    cam_suffix = f"_{safe_cam}" if safe_cam else ""
    dl_dir = downloader_core.DOWNLOAD_DIR
    
    # Optimized: construct expected filenames instead of iterating directory
    # Try to find files with or without date prefix
    possible_files = [
        f"video_{beelup_id}{cam_suffix}.mp4",
        f"video_{beelup_id}{cam_suffix}.ts",
    ]
    
    # Also check for date-prefixed versions
    try:
        for fname in os.listdir(dl_dir):
            if fname.endswith(f"video_{beelup_id}{cam_suffix}.mp4"):
                possible_files.insert(0, fname)  # Prefer mp4
            elif fname.endswith(f"video_{beelup_id}{cam_suffix}.ts"):
                possible_files.append(fname)
    except Exception:
        pass
    
    # Try each possible file
    for fname in possible_files:
        filepath = _safe_download_path(fname)
        if filepath and os.path.exists(filepath):
            return send_file(filepath, as_attachment=True, download_name=fname)

    return "Archivo no encontrado", 404

if __name__ == "__main__":
    app.run(host="0.0.0.0", debug=False, port=5000)

from flask import Flask, render_template, request, jsonify, send_file, Response, make_response
import os
import re
import mimetypes
import hmac
import hashlib
import downloader_core

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "change-me-in-production")

# ── Admin auth ────────────────────────────────────────────────────────────────
ADMIN_PIN  = os.environ.get("ADMIN_PIN", "")
_AUTH_COOKIE = "bdl_admin"

def _make_token(pin: str) -> str:
    """HMAC-signed token so the cookie can't be forged."""
    return hmac.new(app.secret_key.encode(), pin.encode(), hashlib.sha256).hexdigest()

def _is_admin() -> bool:
    """Return True if the request carries a valid admin cookie."""
    if not ADMIN_PIN:
        return False
    token = request.cookies.get(_AUTH_COOKIE, "")
    return hmac.compare_digest(token, _make_token(ADMIN_PIN))

# ── Security helpers ──────────────────────────────────────────────────────────

# Only alphanumeric characters are valid for IDs and camera names.
_ID_RE  = re.compile(r"^\w{1,64}$")
_CAM_RE = re.compile(r"^(central|izq|der)$")

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

def _extract_beelup_id(raw: str) -> str | None:
    """Extract and validate a Beelup match ID from either a bare ID or a URL."""
    raw = raw.strip()
    if "beelup.com" in raw:
        m = re.search(r"id=(\w+)", raw)
        return m.group(1) if m else None
    return _safe_id(raw)

VERSION = "1.2.0"

# ── Routes ────────────────────────────────────────────────────────────────────

@app.route("/")
def index():
    from flask import redirect
    return redirect("/player")

@app.route("/player")
def player():
    return render_template("player.html", version=VERSION, is_admin=_is_admin())

@app.route("/admin")
def admin_page():
    if not _is_admin():
        return render_template("player.html", version=VERSION, is_admin=False, _force_admin_modal=True)
    return render_template("index.html", version=VERSION, is_admin=True)

@app.route("/api/admin/login", methods=["POST"])
def admin_login():
    data = request.json or {}
    pin  = data.get("pin", "").strip()
    if not ADMIN_PIN:
        return jsonify({"error": "Admin no configurado en el servidor"}), 503
    if not pin or not hmac.compare_digest(pin, ADMIN_PIN):
        return jsonify({"error": "PIN incorrecto"}), 401
    resp = make_response(jsonify({"ok": True}))
    resp.set_cookie(_AUTH_COOKIE, _make_token(pin), httponly=True, samesite="Strict", max_age=86400 * 7)
    return resp

@app.route("/api/admin/logout", methods=["POST"])
def admin_logout():
    resp = make_response(jsonify({"ok": True}))
    resp.delete_cookie(_AUTH_COOKIE)
    return resp

@app.route("/api/admin/status")
def admin_status():
    return jsonify({"is_admin": _is_admin(), "pin_configured": bool(ADMIN_PIN)})

@app.route("/api/videos")
def list_videos():
    """List downloaded videos grouped by match ID with camera info."""
    dl_dir = downloader_core.DOWNLOAD_DIR
    matches = {}

    import json
    meta_data = {}
    meta_file = os.path.join(dl_dir, "metadata.json")
    if os.path.exists(meta_file):
        try:
            with open(meta_file, "r", encoding="utf-8") as f:
                meta_data = json.load(f)
        except Exception:
            pass

    COVERS = {
        "CONTAINER": "https://lh5.googleusercontent.com/p/AF1QipOhj41z6lD0gALX-w_S4LPEpPZJ298Yt_-xR2rR=w408-h306-k-no",
        "MEGAFUTBOL": "https://lh5.googleusercontent.com/p/AF1QipNxPof9xXXiXzTqRLEy8lV1a79YvPscW8xQkR=w408-h306-k-no"
    }

    cam_labels = {
        "central": "Cámara 1 (Central)",
        "izq":     "Cámara 2 (Izquierda)",
        "der":     "Cámara 3 (Derecha)",
        "":        "Cámara única",
    }

    for fname in sorted(os.listdir(dl_dir)):
        if not (fname.endswith(".mp4") or fname.endswith(".ts")):
            continue
        m = re.search(r"^(?:(\d{4}-\d{2}-\d{2})_)?video_(\w+?)(?:_(central|izq|der))?\.(mp4|ts)$", fname)
        if not m:
            continue
        match_date = m.group(1) or ""
        match_id   = m.group(2)
        cam_id     = m.group(3) or ""

        size_mb = round(os.path.getsize(os.path.join(dl_dir, fname)) / (1024 * 1024), 1)

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
                cover_url = COVERS["CONTAINER"]
            elif "MEGAFUTBOL" in upper_title:
                cover_url = COVERS["MEGAFUTBOL"]
                
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

        matches[match_id]["cameras"].append({
            "cam_id":   cam_id,
            "label":    cam_labels.get(cam_id, f"Cámara ({cam_id})"),
            "filename": fname,
            "size_mb":  size_mb,
        })

    cam_order = ["izq", "central", "der", ""]
    for m in matches.values():
        m["cameras"].sort(key=lambda c: cam_order.index(c["cam_id"]) if c["cam_id"] in cam_order else 99)
        named = [c for c in m["cameras"] if c["cam_id"] != ""]
        if named:
            m["cameras"] = named

    return jsonify({"matches": list(matches.values())})

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
    """Detect available cameras for a given match ID."""
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

@app.route("/api/clip/<path:filename>")
def download_clip(filename):
    """Generate, save and stream a MP4 clip from a video file using ffmpeg."""
    import subprocess, sys, json as _json
    try:
        start     = float(request.args.get("start", 0))
        end       = float(request.args.get("end", 0))
        match_id  = request.args.get("match_id", "").strip()
        cam_id    = request.args.get("cam_id", "").strip()
    except (TypeError, ValueError):
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

    duration = end - start
    base     = os.path.splitext(os.path.basename(filename))[0]
    out_name = f"clip_{base}_{int(start)}s-{int(end)}s.mp4"

    clips_dir = os.path.join(downloader_core.DOWNLOAD_DIR, "clips")
    os.makedirs(clips_dir, exist_ok=True)
    out_path = os.path.join(clips_dir, out_name)

    cmd = ["ffmpeg", "-y",
           "-ss", str(start),
           "-i", filepath,
           "-t", str(duration),
           "-c", "copy",
           "-movflags", "frag_keyframe+empty_moov+faststart",
           "-f", "mp4",
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
            clips_meta = {}
            if os.path.exists(clips_meta_file):
                with open(clips_meta_file, "r", encoding="utf-8") as f:
                    clips_meta = _json.load(f)
            clips_meta[out_name] = {
                "match_id": match_id,
                "cam_id":   cam_id,
                "start":    start,
                "end":      end,
                "filename": out_name,
            }
            with open(clips_meta_file, "w", encoding="utf-8") as f:
                _json.dump(clips_meta, f, ensure_ascii=False, indent=2)
        except Exception:
            pass

    return send_file(out_path, mimetype="video/mp4", as_attachment=True, download_name=out_name)

@app.route("/api/clips")
def list_clips():
    """List saved clips grouped by match_id, enriched with match metadata."""
    import json as _json
    clips_dir = os.path.join(downloader_core.DOWNLOAD_DIR, "clips")
    clips_meta_file = os.path.join(clips_dir, "clips_metadata.json")
    meta_file = os.path.join(downloader_core.DOWNLOAD_DIR, "metadata.json")

    clips_meta = {}
    match_meta = {}

    if os.path.exists(clips_meta_file):
        try:
            with open(clips_meta_file, "r", encoding="utf-8") as f:
                clips_meta = _json.load(f)
        except Exception:
            pass

    if os.path.exists(meta_file):
        try:
            with open(meta_file, "r", encoding="utf-8") as f:
                match_meta = _json.load(f)
        except Exception:
            pass

    groups = {}
    if os.path.isdir(clips_dir):
        for fname in sorted(os.listdir(clips_dir)):
            if not fname.endswith(".mp4"):
                continue
            fpath = os.path.join(clips_dir, fname)
            size_mb = round(os.path.getsize(fpath) / (1024 * 1024), 1)
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

    return jsonify({"groups": list(groups.values())})

@app.route("/api/clips/stream/<path:filename>")
def stream_clip(filename):
    """Stream a saved clip for inline playback."""
    clips_dir = os.path.join(downloader_core.DOWNLOAD_DIR, "clips")
    filepath  = os.path.realpath(os.path.join(clips_dir, filename))
    base      = os.path.realpath(clips_dir)
    if not filepath.startswith(base + os.sep) or not filename.endswith(".mp4"):
        return "Acceso denegado", 403
    if not os.path.exists(filepath):
        return "File not found", 404
    return send_file(filepath, mimetype="video/mp4", conditional=True)

@app.route("/api/clips/delete/<path:filename>", methods=["DELETE"])
def delete_clip(filename):
    """Delete a saved clip (admin only)."""
    import json as _json
    if not _is_admin():
        return jsonify({"error": "No autorizado"}), 401
    clips_dir = os.path.join(downloader_core.DOWNLOAD_DIR, "clips")
    filepath  = os.path.realpath(os.path.join(clips_dir, filename))
    base      = os.path.realpath(clips_dir)
    if not filepath.startswith(base + os.sep) or not filename.endswith(".mp4"):
        return "Acceso denegado", 403
    try:
        if os.path.exists(filepath):
            os.remove(filepath)
        clips_meta_file = os.path.join(clips_dir, "clips_metadata.json")
        if os.path.exists(clips_meta_file):
            with open(clips_meta_file, "r", encoding="utf-8") as f:
                clips_meta = _json.load(f)
            clips_meta.pop(filename, None)
            with open(clips_meta_file, "w", encoding="utf-8") as f:
                _json.dump(clips_meta, f, ensure_ascii=False, indent=2)
    except Exception as e:
        return jsonify({"error": str(e)}), 500
    return jsonify({"ok": True})

@app.route("/api/clip_status")
def clip_status():
    """Check if ffmpeg is available for server-side clipping."""
    import subprocess
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

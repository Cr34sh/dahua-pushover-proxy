import logging
import subprocess
import tempfile
import time
from urllib.parse import quote

import requests
from requests.auth import HTTPDigestAuth

logger = logging.getLogger(__name__)

JPEG_MAGIC = b"\xff\xd8"


def _save_tmp(data):
    with tempfile.NamedTemporaryFile(delete=False, suffix=".jpg") as tmp:
        tmp.write(data)
        return tmp.name


def _snapshot_http(camera, timeout, retries=1):
    url = f"http://{camera.ip}/cgi-bin/snapshot.cgi"
    auth = HTTPDigestAuth(camera.username, camera.password)
    last_err = None
    for attempt in range(retries + 1):
        try:
            r = requests.get(url, auth=auth, timeout=timeout)
        except requests.RequestException as e:
            return None, f"HTTP: {e}"
        if r.status_code == 200 and r.content[:2] == JPEG_MAGIC:
            return r.content, None
        last_err = f"HTTP {r.status_code}"
        # 401/403/404 no se arreglan reintentando
        if r.status_code in (401, 403, 404):
            break
        if attempt < retries:
            time.sleep(1)
    return None, last_err


def _snapshot_rtsp(camera, timeout):
    user = quote(camera.username or "", safe="")
    pwd = quote(camera.password or "", safe="")
    url = (f"rtsp://{user}:{pwd}@{camera.ip}:554/"
           f"cam/realmonitor?channel=1&subtype=0")
    cmd = [
        "ffmpeg", "-hide_banner", "-loglevel", "error",
        "-rtsp_transport", "tcp", "-i", url,
        "-frames:v", "1", "-q:v", "2",
        "-f", "image2pipe", "-vcodec", "mjpeg", "-",
    ]
    try:
        p = subprocess.run(cmd, capture_output=True, timeout=timeout)
    except FileNotFoundError:
        return None, "RTSP: ffmpeg no instalado en el contenedor"
    except subprocess.TimeoutExpired:
        return None, "RTSP: timeout"
    if p.returncode == 0 and p.stdout[:2] == JPEG_MAGIC:
        return p.stdout, None
    err = p.stderr.decode(errors="replace").strip()
    if camera.password:
        err = err.replace(camera.password, "***").replace(pwd, "***")
    return None, f"RTSP: {err[-300:] or 'sin datos'}"


def fetch_snapshot(camera, timeout=10):
    """Devuelve (ruta_jpg_temporal, None) o (None, mensaje_error).
    Intenta snapshot.cgi y, si falla, extrae un fotograma por RTSP."""
    data, http_err = _snapshot_http(camera, timeout)
    if data:
        return _save_tmp(data), None

    logger.warning(f"snapshot.cgi falló en {camera.name} ({http_err}), probando RTSP")
    data, rtsp_err = _snapshot_rtsp(camera, timeout)
    if data:
        return _save_tmp(data), None

    return None, f"{http_err} | {rtsp_err}"

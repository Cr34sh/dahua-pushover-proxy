from flask import Flask, request
import requests
import tempfile
import os
from requests.auth import HTTPDigestAuth

# Configuración Pushover (añadir como variables de entorno o .env)
PUSHOVER_TOKEN = os.getenv("PUSHOVER_TOKEN")
PUSHOVER_USER = os.getenv("PUSHOVER_USER")

# Configuración de cámaras (reemplazar con datos reales en producción)
CAMARAS = {
    "alerta": {
        "ip": "CAMERA_IP",
        "user": "CAMERA_USER",
        "pass": "CAMERA_PASS",
        "title": "Movimiento",
        "message": "Detectado en cámara del patio"
    },
    "cara": {
        "ip": "CAMERA_IP",
        "user": "CAMERA_USER",
        "pass": "CAMERA_PASS",
        "title": "Reconocimiento facial",
        "message": "Se ha detectado una cara en la entrada"
    },
    "puerta": {
        "ip": "CAMERA_IP",
        "user": "CAMERA_USER",
        "pass": "CAMERA_PASS",
        "title": "Puerta abierta",
        "message": "Acceso por puerta lateral"
    }
}

app = Flask(__name__)

@app.route('/<evento>', methods=['GET'])
def notificar(evento):
    if evento not in CAMARAS:
        return f"Evento '{evento}' no definido", 404

    cam = CAMARAS[evento]
    snapshot_url = f"http://{cam['ip']}/cgi-bin/snapshot.cgi"
    auth = HTTPDigestAuth(cam["user"], cam["pass"])

    try:
        r = requests.get(snapshot_url, auth=auth, stream=True, timeout=5)
        if r.status_code != 200:
            return f"Error al obtener imagen de cámara {evento}: {r.status_code}", 500

        with tempfile.NamedTemporaryFile(delete=False, suffix=".jpg") as tmp:
            for chunk in r.iter_content(1024):
                tmp.write(chunk)
            tmp_path = tmp.name

        with open(tmp_path, 'rb') as img:
            requests.post("https://api.pushover.net/1/messages.json", data={
                "token": PUSHOVER_TOKEN,
                "user": PUSHOVER_USER,
                "title": cam["title"],
                "message": cam["message"]
            }, files={"attachment": img})

        os.remove(tmp_path)
        return f"OK - Notificación '{evento}' enviada con imagen"

    except Exception as e:
        return f"Error: {str(e)}", 500

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)

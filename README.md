# Dahua to Pushover Proxy

Este microservicio permite recibir eventos de cámaras Dahua (como detección de movimiento o reconocimiento facial) y enviar notificaciones enriquecidas a Pushover con imágenes adjuntas en tiempo real.

## Estructura del proyecto

```
dahua-pushover-proxy/
├── app/
│   └── app.py
├── docker-compose.yml
├── .env.example
└── README.md
```

## Instalación

1. Clona este repositorio:
```bash
git clone https://github.com/Cr34sh/dahua-pushover-proxy.git
cd dahua-pushover-proxy
```

2. Crea un archivo `.env` basado en `.env.example`:

```bash
cp .env.example .env
```

3. Edita `app/app.py` y reemplaza las IPs, usuarios y contraseñas de tus cámaras Dahua.

4. Inicia el servicio:

```bash
docker-compose up -d
```

## Uso

Haz que la cámara Dahua dispare peticiones HTTP GET a las siguientes rutas según el evento:

- `/alerta` → Movimiento
- `/cara` → Reconocimiento facial
- `/puerta` → Acceso

Por ejemplo:

```
http://TU_SERVIDOR:5005/alerta
```
En el menu de la cámara crea el servidor (http://IPCAMARA/#/index/ServerList) 
Con los datos del Proxy IP y Puerto 

En los eventos añade un ultimo evento tipo "Enviar Comando" seleciona el servidor y añade el comando "alerta", "cara" ...


## Opicional varias camaras envian alertas.

## Si tienes varias camaras, duplica la parte de eventos con diferentes nombres y los datos de IP, usuario y password
```
/alerta-cam1 IP X.X.X.100
/alerta-cam2 IP X.X.X.101
/alerta-cam3 IP X.X.X.102
```
## Configuración de cámaras (reemplazar con datos reales en producción)
```
CAMARAS = {
    "alerta-cam1": {
        "ip": "CAMERA_IP",
        "user": "CAMERA_USER",
        "pass": "CAMERA_PASS",
        "title": "Movimiento",
        "message": "Detectado en cámara del patio"
    },
    "alerta-cam2": {
        "ip": "CAMERA_IP",
        "user": "CAMERA_USER",
        "pass": "CAMERA_PASS",
        "title": "Reconocimiento facial",
        "message": "Se ha detectado una cara en la entrada"
    },
    "alerta-cam3": {
        "ip": "CAMERA_IP",
        "user": "CAMERA_USER",
        "pass": "CAMERA_PASS",
        "title": "Puerta abierta",
        "message": "Acceso por puerta lateral"
    }
}
```
---

MIT License.

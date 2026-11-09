# CamPush (Dahua to Pushover Proxy)

CamPush es una solución escalable para entornos corporativos que actúa como puente entre cámaras de seguridad Dahua y múltiples servicios de notificación (Pushover, Email, FTP).

## 🚀 Características (v0.9 Alpha/Beta)

- **Panel Web Administrativo**: Gestiona todas tus cámaras y configuraciones desde una interfaz web moderna y centralizada.
- **Multiusuario**: Sistema protegido por usuario y contraseña, con gestión de cuentas de operadores.
- **Multi-Notificación Simultánea**:
  - **Pushover**: Notificaciones móviles inmediatas y enriquecidas con imagen.
  - **Email (SMTP Clásico)**: Soporte para envíos estándar por servidores de correo.
  - **Email (Microsoft 365 - Graph API)**: *[En fase de pruebas]* Integración nativa sin necesidad de protocolos SMTP inseguros. 
  - **FTP**: Subida automática de capturas ordenadas en carpetas por cámara.
- **Motor de Eventos y Diagnóstico**:
  - Catálogo de eventos predefinidos: Movimiento, Cruce de línea, Reconocimiento Facial, Matrículas, Errores de SD, Alarmas, Manipulación (Tampering) y Detección de Audio.
  - **Botón "Probar"**: Herramienta de diagnóstico síncrono para verificar conexión a la cámara y entrega de notificaciones en tiempo real, sin depender de alarmas físicas.
- **Control y Auditoría**: 
  - **Registro de notificaciones enviadas**: Un historial detallado con autolimpieza de 30 días para trazar el éxito o fallo técnico de cada envío por canal.
- **Horarios e Inteligencia Geográfica**: 
  - Define horas activas semanales.
  - Importación automática offline de Festivos (Nacionales y Autonómicos de España) para silenciar alertas en días no laborables.
- **Personalización Visual**: Permite la carga de un logo corporativo propio desde la interfaz web, conservándose en el entorno de despliegue.

## 📦 Instalación (Docker)

La arquitectura de despliegue principal es **Docker**. Todos los datos sensibles, bases de datos y logotipos se almacenan en un volumen persistente seguro (`/data`).

1. Asegúrate de tener instalado `docker` y `docker-compose` en tu servidor.
2. Clona este repositorio:
   ```bash
   git clone https://github.com/Cr34sh/dahua-pushover-proxy.git
   cd dahua-pushover-proxy
   ```
3. Crea el fichero `.env` con la clave de sesión (no se versiona):
   ```bash
   cp .env.example .env
   sed -i "s/^SECRET_KEY=.*/SECRET_KEY=$(python3 -c 'import secrets; print(secrets.token_hex(32))')/" .env
   ```
   Los ajustes propios del despliegue (red externa, IP fija, DNS) se ponen en `docker-compose.override.yml`, partiendo de `docker-compose.override.yml.example`.
4. Construye y levanta el contenedor:
   ```bash
   docker compose up -d --build
   ```
   La imagen incluye `ffmpeg`: si `snapshot.cgi` de una cámara falla, la captura se obtiene del flujo RTSP (puerto 554).
5. El servicio estará disponible en el puerto `8080` de tu servidor. 
   - Acceso Web: `http://TU_IP_DEL_SERVIDOR:8080`
   - **Credenciales iniciales**: `admin` / `admin` *(Se recomienda encarecidamente cambiar la contraseña en el primer inicio de sesión)*.

## 📷 Configuración de Cámaras Dahua

1. Entra al menú de configuración web de tu cámara Dahua.
2. Ve a **Event > Alarm > Alarm Server** (o equivalente en tu modelo) y añade un servidor:
   - **Address:** La IP donde está instalado CamPush.
   - **Port:** 8080.
3. En las opciones del evento (ej. Detección de Movimiento, IVS), activa la opción **Send Command** o **HTTP Post**.
4. Usa como comando el identificador del evento (ej: `movimiento`, `cara` o `alarma`).
   - La URL completa a la que llamará la cámara será `http://TU_IP_DEL_SERVIDOR/movimiento`. CamPush identificará qué cámara ha saltado gracias a su dirección IP de origen, obteniendo la captura y enviando las notificaciones configuradas.

---
Licencia MIT.

from flask import Blueprint, request, jsonify
import requests
from requests.auth import HTTPDigestAuth
import tempfile
import os
import threading
import logging
from .models import db, Camera, Setting, EventTemplate, NotificationLog
from .utils_schedule import is_active_now
from .utils_notify import get_settings, notify_pushover, notify_email, notify_ftp

api_bp = Blueprint('api', __name__)
logger = logging.getLogger(__name__)

def process_notifications(app_context, camera_id, event_type, temp_path, log_id):
    # This runs in a thread
    app_context.push()
    try:
        camera = Camera.query.get(camera_id)
        if not camera:
            return
            
        settings = get_settings(db, Setting)
        
        # Format title and message using EventTemplate
        evt_template = EventTemplate.query.filter_by(event_id=event_type).first()
        if evt_template:
            title = evt_template.title.replace('{camera_name}', camera.name)
            message = evt_template.message.replace('{camera_name}', camera.name)
        else:
            title = f"Evento en {camera.name}"
            message = f"Se ha detectado: {event_type.capitalize()}"
        
        # Initialize log
        from datetime import datetime, timedelta
        
        # Cleanup old logs (older than 30 days)
        thirty_days_ago = datetime.utcnow() - timedelta(days=30)
        NotificationLog.query.filter(NotificationLog.timestamp < thirty_days_ago).delete()
        
        status_push = "N/A"
        status_email = "N/A"
        status_ftp = "N/A"
        
        # Send via configured channels for this camera
        if camera.enable_push:
            success, msg = notify_pushover(title, message, temp_path, settings)
            status_push = msg if success else f"Error: {msg}"
        
        if camera.enable_email:
            success, msg = notify_email(title, message, temp_path, settings)
            status_email = msg if success else f"Error: {msg}"
            
        if camera.enable_ftp:
            success, msg = notify_ftp(camera.name, temp_path, settings)
            status_ftp = msg if success else f"Error: {msg}"
            
        # Update log
        log = NotificationLog.query.get(log_id)
        if log:
            log.status_push = status_push
            log.status_email = status_email
            log.status_ftp = status_ftp
            db.session.commit()
            
    except Exception as e:
        logger.error(f"Error processing notifications: {e}")
        db.session.rollback()
    finally:
        # Cleanup temporary file
        if os.path.exists(temp_path):
            try:
                os.remove(temp_path)
            except OSError as e:
                logger.error(f"Failed to delete temp file: {e}")
        db.session.remove()

@api_bp.route('/<event_type>', methods=['GET'])
def webhook(event_type):
    # Get request IP: allow test_ip parameter for manual testing, then X-Forwarded-For, then remote_addr
    source_ip = request.args.get('test_ip')
    if not source_ip:
        forwarded = request.headers.get('X-Forwarded-For')
        if forwarded:
            source_ip = forwarded.split(',')[0].strip()
        else:
            source_ip = request.remote_addr
    
    # Check if active
    force_test = request.args.get('force', type=int) == 1
    if not is_active_now() and not force_test:
        logger.info(f"Ignored event '{event_type}' from {source_ip} due to schedule.")
        
        camera = Camera.query.filter_by(ip=source_ip).first()
        cam_name = camera.name if camera else f"IP Desconocida ({source_ip})"
        new_log = NotificationLog(
            camera_name=cam_name,
            event_type=event_type,
            status_push="Ignorado (Horario)",
            status_email="Ignorado (Horario)",
            status_ftp="Ignorado (Horario)"
        )
        db.session.add(new_log)
        db.session.commit()
        
        return jsonify({"status": "ignored", "reason": "schedule"}), 200
        
    camera = Camera.query.filter_by(ip=source_ip).first()
    if not camera:
        logger.warning(f"Unknown camera IP: {source_ip}")
        new_log = NotificationLog(
            camera_name=f"IP Desconocida ({source_ip})",
            event_type=event_type,
            status_push="IP Rechazada",
            status_email="IP Rechazada",
            status_ftp="IP Rechazada"
        )
        db.session.add(new_log)
        db.session.commit()
        return jsonify({"status": "error", "reason": "unknown_ip"}), 404
        
    # Connect to camera and fetch snapshot
    snapshot_url = f"http://{camera.ip}/cgi-bin/snapshot.cgi"
    auth = HTTPDigestAuth(camera.username, camera.password)
    
    try:
        r = requests.get(snapshot_url, auth=auth, stream=True, timeout=10)
        if r.status_code != 200:
            logger.error(f"Failed to get snapshot from {camera.name}: Status {r.status_code}")
            return jsonify({"status": "error", "reason": "camera_unreachable"}), 502
            
        # Save to temp file
        with tempfile.NamedTemporaryFile(delete=False, suffix=".jpg") as tmp:
            for chunk in r.iter_content(1024):
                tmp.write(chunk)
            tmp_path = tmp.name
            
        # Launch background thread for notifications
        from flask import current_app
        app_context = current_app.app_context()
        
        # Create initial log
        new_log = NotificationLog(
            camera_name=camera.name,
            event_type=event_type,
            status_push="Procesando..." if camera.enable_push else "N/A",
            status_email="Procesando..." if camera.enable_email else "N/A",
            status_ftp="Procesando..." if camera.enable_ftp else "N/A"
        )
        db.session.add(new_log)
        db.session.commit()
        
        thread = threading.Thread(target=process_notifications, args=(app_context, camera.id, event_type, tmp_path, new_log.id))
        thread.start()
        
        return jsonify({"status": "processing", "event": event_type, "camera": camera.name}), 202
        
    except Exception as e:
        logger.error(f"Exception during webhook: {e}")
        return jsonify({"status": "error", "reason": "internal_error"}), 500

from flask import Blueprint, render_template, request, redirect, url_for, flash
from flask_login import login_user, login_required, logout_user, current_user
from .models import db, User, Camera, Schedule, Holiday, Setting, EventTemplate
from . import bcrypt

web_bp = Blueprint('web', __name__)

@web_bp.route('/')
@login_required
def index():
    return redirect(url_for('web.cameras'))

@web_bp.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('web.index'))
    
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        user = User.query.filter_by(username=username).first()
        
        if user and bcrypt.check_password_hash(user.password_hash, password):
            login_user(user)
            next_page = request.args.get('next')
            return redirect(next_page) if next_page else redirect(url_for('web.index'))
        else:
            flash('Login incorrecto. Por favor, revisa tus credenciales.', 'danger')
            
    return render_template('login.html')

@web_bp.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('web.login'))

@web_bp.route('/cameras', methods=['GET', 'POST'])
@login_required
def cameras():
    if request.method == 'POST':
        action = request.form.get('action')
        if action == 'add':
            name = request.form.get('name')
            ip_address = request.form.get('ip')
            username = request.form.get('username')
            password = request.form.get('password')
            enable_push = request.form.get('enable_push') == 'on'
            enable_email = request.form.get('enable_email') == 'on'
            enable_ftp = request.form.get('enable_ftp') == 'on'
            
            if name and ip_address:
                new_cam = Camera(
                    name=name, ip=ip_address, username=username, password=password,
                    enable_push=enable_push, enable_email=enable_email, enable_ftp=enable_ftp
                )
                db.session.add(new_cam)
                db.session.commit()
                flash('Cámara añadida correctamente.', 'success')
            else:
                flash('Todos los campos son requeridos.', 'danger')
                
        elif action == 'delete':
            cam_id = request.form.get('cam_id')
            cam = Camera.query.get(cam_id)
            if cam:
                db.session.delete(cam)
                db.session.commit()
                flash('Cámara eliminada.', 'success')
                
        elif action == 'update_notifications':
            cam_id = request.form.get('cam_id')
            cam = Camera.query.get(cam_id)
            if cam:
                cam.enable_push = request.form.get('enable_push') == 'on'
                cam.enable_email = request.form.get('enable_email') == 'on'
                cam.enable_ftp = request.form.get('enable_ftp') == 'on'
                db.session.commit()
                flash('Configuración de notificaciones actualizada.', 'success')
        
        elif action == 'mass_enable_push':
            for cam in Camera.query.all():
                cam.enable_push = True
            db.session.commit()
            flash('Notificaciones Push activadas para todas las cámaras.', 'success')
            
        elif action == 'mass_enable_email':
            for cam in Camera.query.all():
                cam.enable_email = True
            db.session.commit()
            flash('Notificaciones de Email activadas para todas las cámaras.', 'success')
            
        elif action == 'mass_enable_ftp':
            for cam in Camera.query.all():
                cam.enable_ftp = True
            db.session.commit()
            flash('Notificaciones FTP activadas para todas las cámaras.', 'success')
                
        elif action == 'test':
            cam_id = request.form.get('cam_id')
            cam = Camera.query.get(cam_id)
            if cam:
                import requests
                from requests.auth import HTTPDigestAuth
                import tempfile
                import os
                from .utils_notify import get_settings, notify_pushover, notify_email, notify_ftp
                
                snapshot_url = f"http://{cam.ip}/cgi-bin/snapshot.cgi"
                auth = HTTPDigestAuth(cam.username, cam.password)
                try:
                    r = requests.get(snapshot_url, auth=auth, stream=True, timeout=5)
                    if r.status_code != 200:
                        flash(f'Error: La cámara no respondió a la captura (HTTP {r.status_code}). Verifica IP y credenciales.', 'danger')
                    else:
                        with tempfile.NamedTemporaryFile(delete=False, suffix=".jpg") as tmp:
                            for chunk in r.iter_content(1024):
                                tmp.write(chunk)
                            tmp_path = tmp.name
                        
                        settings = get_settings(db, Setting)
                        title = f"Test desde {cam.name}"
                        message = "Esta es una notificación de prueba generada desde la interfaz web."
                        
                        results = []
                        status_push, status_email, status_ftp = "N/A", "N/A", "N/A"
                        
                        if cam.enable_push:
                            ok, msg = notify_pushover(title, message, tmp_path, settings)
                            status_push = msg if ok else f"Error: {msg}"
                            results.append(f"Push: {'✅ OK' if ok else f'❌ Falló ({msg})'}")
                        if cam.enable_email:
                            ok, msg = notify_email(title, message, tmp_path, settings)
                            status_email = msg if ok else f"Error: {msg}"
                            results.append(f"Email: {'✅ OK' if ok else f'❌ Falló ({msg})'}")
                        if cam.enable_ftp:
                            ok, msg = notify_ftp(cam.name, tmp_path, settings)
                            status_ftp = msg if ok else f"Error: {msg}"
                            results.append(f"FTP: {'✅ OK' if ok else f'❌ Falló ({msg})'}")
                            
                        if os.path.exists(tmp_path):
                            os.remove(tmp_path)
                            
                        # Registrar en el Log
                        from .models import NotificationLog
                        new_log = NotificationLog(
                            camera_name=cam.name,
                            event_type="Test (Manual)",
                            status_push=status_push,
                            status_email=status_email,
                            status_ftp=status_ftp
                        )
                        db.session.add(new_log)
                        db.session.commit()
                            
                        if not results:
                            flash('Captura obtenida OK desde la cámara, pero no tiene activado Push, Email ni FTP en la tabla.', 'success')
                        else:
                            # Use info category for mixed results, or success
                            flash(f'Prueba completada: ' + ' | '.join(results), 'success')
                            
                except requests.exceptions.RequestException as e:
                    flash(f'Error de red al conectar con la cámara: {str(e)}', 'danger')

        return redirect(url_for('web.cameras'))
        
    cameras_list = Camera.query.all()
    # Check if config is locked (we store this in session or pass as a flag, 
    # but the prompt implies it's a frontend toggle that enables/disables inputs, 
    # or a persistent state. Let's make it persistent per user or global.)
    # Actually, a frontend JS toggle is the most UX friendly for "Bloquear configuracion con un boton".
    return render_template('cameras.html', cameras=cameras_list)

@web_bp.route('/users', methods=['GET', 'POST'])
@login_required
def users():
    if request.method == 'POST':
        action = request.form.get('action')
        if action == 'add':
            username = request.form.get('username')
            password = request.form.get('password')
            if username and password:
                existing = User.query.filter_by(username=username).first()
                if existing:
                    flash('El nombre de usuario ya existe.', 'danger')
                else:
                    hashed_pw = bcrypt.generate_password_hash(password).decode('utf-8')
                    new_user = User(username=username, password_hash=hashed_pw)
                    db.session.add(new_user)
                    db.session.commit()
                    flash('Usuario creado correctamente.', 'success')
        
        elif action == 'delete':
            user_id = request.form.get('user_id')
            user_to_delete = User.query.get(user_id)
            if user_to_delete:
                if user_to_delete.id == current_user.id:
                    flash('No puedes eliminar tu propio usuario activo.', 'danger')
                else:
                    db.session.delete(user_to_delete)
                    db.session.commit()
                    flash('Usuario eliminado.', 'success')
                    
        elif action == 'change_password':
            new_password = request.form.get('new_password')
            if new_password:
                current_user.password_hash = bcrypt.generate_password_hash(new_password).decode('utf-8')
                db.session.commit()
                flash('Tu contraseña ha sido actualizada.', 'success')
                
        return redirect(url_for('web.users'))
        
    users_list = User.query.all()
    return render_template('users.html', users=users_list)

@web_bp.route('/logs', methods=['GET', 'POST'])
@login_required
def logs():
    from .models import NotificationLog
    if request.method == 'POST':
        action = request.form.get('action')
        if action == 'clear':
            db.session.query(NotificationLog).delete()
            db.session.commit()
            flash('Todos los registros han sido eliminados.', 'success')
        return redirect(url_for('web.logs'))
        
    logs_list = NotificationLog.query.order_by(NotificationLog.timestamp.desc()).all()
    return render_template('logs.html', logs=logs_list)

@web_bp.route('/events', methods=['GET', 'POST'])
@login_required
def events():
    if request.method == 'POST':
        action = request.form.get('action')
        if action == 'add':
            event_id = request.form.get('event_id')
            title = request.form.get('title')
            message = request.form.get('message')
            
            if event_id and title and message:
                existing = EventTemplate.query.filter_by(event_id=event_id).first()
                if existing:
                    flash('Ese ID de evento ya existe.', 'danger')
                else:
                    new_evt = EventTemplate(event_id=event_id, title=title, message=message)
                    db.session.add(new_evt)
                    db.session.commit()
                    flash('Plantilla de evento creada.', 'success')
                    
        elif action == 'delete':
            e_id = request.form.get('event_id')
            evt = EventTemplate.query.get(e_id)
            if evt:
                db.session.delete(evt)
                db.session.commit()
                flash('Plantilla de evento eliminada.', 'success')
                
        return redirect(url_for('web.events'))
        
    events_list = EventTemplate.query.all()
    return render_template('events.html', events=events_list)

@web_bp.route('/schedules', methods=['GET', 'POST'])
@login_required
def schedules():
    from datetime import datetime
    
    if request.method == 'POST':
        action = request.form.get('action')
        
        if action == 'save_schedules':
            # This logic will delete existing and recreate or update
            db.session.query(Schedule).delete()
            for day in range(7):
                start_str = request.form.get(f'start_{day}')
                end_str = request.form.get(f'end_{day}')
                if start_str and end_str:
                    try:
                        start_time = datetime.strptime(start_str, '%H:%M').time()
                        end_time = datetime.strptime(end_str, '%H:%M').time()
                        s = Schedule(day_of_week=day, start_time=start_time, end_time=end_time)
                        db.session.add(s)
                    except ValueError:
                        pass
            db.session.commit()
            flash('Horarios guardados.', 'success')
            
        elif action == 'add_holiday':
            date_str = request.form.get('date')
            desc = request.form.get('description')
            if date_str:
                try:
                    date_obj = datetime.strptime(date_str, '%Y-%m-%d').date()
                    h = Holiday(date=date_obj, description=desc)
                    db.session.add(h)
                    db.session.commit()
                    flash('Festivo añadido.', 'success')
                except Exception as e:
                    flash('Error al añadir festivo.', 'danger')
                    
        elif action == 'delete_holiday':
            h_id = request.form.get('holiday_id')
            h = Holiday.query.get(h_id)
            if h:
                db.session.delete(h)
                db.session.commit()
                flash('Festivo eliminado.', 'success')
                
        elif action == 'import_holidays':
            year = int(request.form.get('year', 2025))
            region = request.form.get('region')
            
            try:
                import holidays
                
                if region == 'ALL':
                    es_holidays = holidays.ES(years=year)
                    region_name = "Nacional"
                else:
                    es_holidays = holidays.ES(years=year, subdiv=region)
                    region_name = f"Autonómico ({region})"
                    
                added = 0
                for date, name in es_holidays.items():
                    existing = Holiday.query.filter_by(date=date).first()
                    if not existing:
                        h = Holiday(date=date, description=name)
                        db.session.add(h)
                        added += 1
                
                db.session.commit()
                flash(f'Importación completada. Se han añadido {added} nuevos festivos para {year} ({region_name}).', 'success')
            except ImportError:
                flash('Error: La librería holidays no está instalada.', 'danger')
            except Exception as e:
                flash(f'Error al importar festivos: {str(e)}', 'danger')
                
        return redirect(url_for('web.schedules'))
        
    schedules_db = Schedule.query.all()
    # Create a dictionary for easier rendering in template
    sched_dict = {s.day_of_week: s for s in schedules_db}
    holidays_db = Holiday.query.order_by(Holiday.date).all()
    
    import datetime
    current_year = datetime.datetime.now().year
    return render_template('schedules.html', schedules=sched_dict, holidays=holidays_db, current_year=current_year)

@web_bp.route('/custom_logo')
def get_custom_logo():
    import os
    from flask import send_from_directory, current_app
    
    # Check if custom logo exists in data directory
    data_dir = os.path.join(os.getcwd(), 'data')
    custom_logo_path = os.path.join(data_dir, 'custom_logo.png')
    
    if os.path.exists(custom_logo_path):
        return send_from_directory(data_dir, 'custom_logo.png')
    
    # Fallback to default static logo
    return redirect(url_for('static', filename='images/logo.png'))

@web_bp.route('/settings', methods=['GET', 'POST'])
@login_required
def settings():
    import os
    from werkzeug.utils import secure_filename
    
    if request.method == 'POST':
        # List of expected setting keys
        keys = [
            'pushover_token', 'pushover_user',
            'email_provider', 'ms_tenant_id', 'ms_client_id', 'ms_client_secret',
            'smtp_server', 'smtp_port', 'smtp_user', 'smtp_pass', 'smtp_from', 'smtp_to',
            'ftp_server', 'ftp_port', 'ftp_user', 'ftp_pass', 'ftp_path'
        ]
        for key in keys:
            val = request.form.get(key, '')
            setting = Setting.query.filter_by(key=key).first()
            if setting:
                setting.value = val
            else:
                new_setting = Setting(key=key, value=val)
                db.session.add(new_setting)
        
        # Logo upload logic
        if 'logo_file' in request.files:
            file = request.files['logo_file']
            if file and file.filename != '':
                # Ensure it's an image (simple check)
                if file.filename.lower().endswith(('.png', '.jpg', '.jpeg')):
                    data_dir = os.path.join(os.getcwd(), 'data')
                    os.makedirs(data_dir, exist_ok=True)
                    # We always save as custom_logo.png to keep it simple and overwrite
                    save_path = os.path.join(data_dir, 'custom_logo.png')
                    file.save(save_path)
                else:
                    flash('El logo debe ser un archivo PNG o JPG.', 'danger')

        db.session.commit()
        flash('Configuración guardada correctamente.', 'success')
        return redirect(url_for('web.settings'))
        
    settings_db = Setting.query.all()
    # Convert list to dict
    s_dict = {s.key: s.value for s in settings_db}
    return render_template('settings.html', settings=s_dict)

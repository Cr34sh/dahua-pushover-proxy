import requests
import smtplib
import ftplib
import os
import logging
from email.message import EmailMessage
import traceback
from datetime import datetime

logger = logging.getLogger(__name__)

def get_settings(db, Setting):
    settings_db = Setting.query.all()
    return {s.key: s.value for s in settings_db}

def notify_pushover(title, message, image_path, settings):
    token = settings.get('pushover_token')
    user = settings.get('pushover_user')
    if not token or not user:
        logger.error("Pushover credentials missing in settings.")
        return False, "Credenciales faltantes en configuración"
        
    try:
        with open(image_path, 'rb') as img:
            resp = requests.post("https://api.pushover.net/1/messages.json", data={
                "token": token,
                "user": user,
                "title": title,
                "message": message
            }, files={"attachment": img})
            
            if resp.status_code == 200:
                logger.info("Pushover notification sent.")
                return True, "Enviado"
            else:
                logger.error(f"Pushover error: {resp.text}")
                return False, f"Error API: {resp.status_code}"
    except Exception as e:
        logger.error(f"Exception sending Pushover: {e}")
        return False, f"Excepción: {str(e)}"

def notify_o365_graph(title, message, image_path, settings):
    tenant_id = settings.get('ms_tenant_id')
    client_id = settings.get('ms_client_id')
    client_secret = settings.get('ms_client_secret')
    sender = settings.get('smtp_from')
    recipient = settings.get('smtp_to')
    
    if not all([tenant_id, client_id, client_secret, sender, recipient]):
        logger.error("Faltan credenciales de O365 Graph API.")
        return False, "Credenciales O365 faltantes"
        
    try:
        # 1. Get Access Token
        token_url = f"https://login.microsoftonline.com/{tenant_id}/oauth2/v2.0/token"
        token_data = {
            'grant_type': 'client_credentials',
            'client_id': client_id,
            'client_secret': client_secret,
            'scope': 'https://graph.microsoft.com/.default'
        }
        token_r = requests.post(token_url, data=token_data)
        token_r.raise_for_status()
        access_token = token_r.json().get('access_token')
        
        # 2. Prepare Email Data
        import base64
        with open(image_path, 'rb') as img:
            img_b64 = base64.b64encode(img.read()).decode('utf-8')
            
        email_data = {
            "message": {
                "subject": title,
                "body": {
                    "contentType": "Text",
                    "content": message
                },
                "toRecipients": [
                    {
                        "emailAddress": {
                            "address": recipient
                        }
                    }
                ],
                "attachments": [
                    {
                        "@odata.type": "#microsoft.graph.fileAttachment",
                        "name": "snapshot.jpg",
                        "contentType": "image/jpeg",
                        "contentBytes": img_b64
                    }
                ]
            },
            "saveToSentItems": "false"
        }
        
        # 3. Send Email
        send_url = f"https://graph.microsoft.com/v1.0/users/{sender}/sendMail"
        headers = {
            'Authorization': f'Bearer {access_token}',
            'Content-Type': 'application/json'
        }
        send_r = requests.post(send_url, headers=headers, json=email_data)
        send_r.raise_for_status()
        
        logger.info("O365 Graph API Email sent successfully.")
        return True, "Enviado"
    except Exception as e:
        logger.error(f"Exception sending O365 Email: {e}")
        return False, f"Error O365: {str(e)}"

def notify_email(title, message, image_path, settings):
    provider = settings.get('email_provider', 'none')
    if provider == 'none':
        return False, "Email deshabilitado globalmente"
    elif provider == 'o365':
        return notify_o365_graph(title, message, image_path, settings)
    
    # Fallback to SMTP
    server = settings.get('smtp_server')
    port = settings.get('smtp_port')
    user = settings.get('smtp_user')
    password = settings.get('smtp_pass')
    sender = settings.get('smtp_from')
    recipient = settings.get('smtp_to')
    
    if not all([server, port, user, password, sender, recipient]):
        logger.error("Email credentials/settings missing.")
        return False, "Credenciales SMTP faltantes"
        
    try:
        msg = EmailMessage()
        msg['Subject'] = title
        msg['From'] = sender
        msg['To'] = recipient
        msg.set_content(message)
        
        with open(image_path, 'rb') as img:
            img_data = img.read()
            msg.add_attachment(img_data, maintype='image', subtype='jpeg', filename='snapshot.jpg')
            
        with smtplib.SMTP(server, int(port)) as smtp:
            smtp.ehlo()
            smtp.starttls()
            smtp.ehlo()
            smtp.login(user, password)
            smtp.send_message(msg)
            
        logger.info("SMTP Email sent successfully.")
        return True, "Enviado"
    except Exception as e:
        logger.error(f"Exception sending SMTP Email: {e}")
        traceback.print_exc()
        return False, f"Error SMTP: {str(e)}"

def notify_ftp(camera_name, image_path, settings):
    server = settings.get('ftp_server')
    port = settings.get('ftp_port', '21')
    user = settings.get('ftp_user')
    password = settings.get('ftp_pass')
    base_path = settings.get('ftp_path', '/')
    
    if not all([server, user, password]):
        logger.error("FTP settings missing.")
        return False, "Credenciales FTP faltantes"
        
    try:
        ftp = ftplib.FTP()
        ftp.connect(server, int(port))
        ftp.login(user, password)
        
        # Navigate to base path
        try:
            ftp.cwd(base_path)
        except ftplib.error_perm:
            logger.error(f"Base FTP path {base_path} not accessible.")
            return False, "Ruta base FTP inaccesible"
            
        # Try to change to camera directory, or create it
        try:
            ftp.cwd(camera_name)
        except ftplib.error_perm:
            # Create if not exist
            ftp.mkd(camera_name)
            ftp.cwd(camera_name)
            
        # Generate filename with timestamp
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"{camera_name}_{timestamp}.jpg"
        
        with open(image_path, 'rb') as file:
            ftp.storbinary(f'STOR {filename}', file)
            
        ftp.quit()
        logger.info(f"FTP upload successful: {filename}")
        return True, "Enviado"
    except Exception as e:
        logger.error(f"Exception uploading to FTP: {e}")
        return False, f"Error FTP: {str(e)}"

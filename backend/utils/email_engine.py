import os
import smtplib
import json
import time
import requests # Added for Brevo API
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# SMTP Config (Fallback)
SMTP_SERVER = os.getenv("SMTP_SERVER", "smtp.hostinger.com")
SMTP_PORT = int(os.getenv("SMTP_PORT", 465))
# Ensure we handle the potentially quoted string from env or simple string
try:
    _acc = os.getenv("EMAIL_ACCOUNT_BRANISLAV", "hello@arcigy.group:password")
    if ":" in _acc:
        SMTP_USER, SMTP_PASS = _acc.strip('"\'').split(":", 1)
    else:
        SMTP_USER = os.getenv("SMTP_USER")
        SMTP_PASS = os.getenv("SMTP_PASS")
except:
    SMTP_USER, SMTP_PASS = None, None

# Brevo Config (Primary)
BREVO_API_KEY = os.getenv("BREVO_API_KEY")
SENDER_EMAIL = "hello@arcigy.group" # This must be a verified sender in Brevo
SENDER_NAME = "ArciGy"

def get_paths():
    """
    Fixed relative path based on deployed structure:
    /app/backend/utils/email_engine.py
    /app/templates/premium_email.html
    Relationship: ../../templates/premium_email.html
    """
    try:
        current_dir = os.path.dirname(os.path.abspath(__file__)) # /app/backend/utils
        root_dir = os.path.dirname(os.path.dirname(current_dir)) # /app
        
        template_path = os.path.join(root_dir, "templates", "premium_email.html")
        asset_path = os.path.join(root_dir, "assets", "cyber_socials_layout.jpg")
        
        return template_path, asset_path, root_dir
    except Exception as e:
        print(f"Path calc error: {e}")
        return None, None, str(e)

def get_template():
    template_path, _, root_dir = get_paths()
    debug_info = f"Root: {root_dir}, Target: {template_path}"
    
    try:
        if template_path and os.path.exists(template_path):
            with open(template_path, 'r', encoding='utf-8') as f:
                return f.read()
        else:
            debug_info += f" - EXIST CHECK FAILED (Contents of root: {os.listdir(root_dir) if root_dir and os.path.exists(root_dir) else 'N/A'})"
    except Exception as e:
        debug_info += f" - READ ERROR: {e}"
        
    # Fallback with DEBUG info visible to user
    return f"""<html>
    <body style='font-family: sans-serif; padding: 20px;'>
        <h2 style='color: red;'>⚠️ Email Template Error</h2>
        <p>The system could not load the premium email template.</p>
        <div style='background: #eee; padding: 10px; border-radius: 5px; font-family: monospace;'>
            <strong>Debug Info:</strong><br>
            {debug_info}
        </div>
        <hr>
        <h3>Original Content:</h3>
        <p>{{greeting}}</p>
        <p>{{details}}</p>
        <br>
        <a href='{{confirm_url}}' style='padding: 10px 20px; background: #007bff; color: white; text-decoration: none;'>Confirm Appointment</a>
    </body>
    </html>"""

def format_datetime(iso_string, lang='sk'):
    try:
        from datetime import datetime
        if not iso_string or iso_string == "null": return "---"
        dt = datetime.fromisoformat(iso_string.replace('Z', '+00:00'))
        if lang == 'sk':
            months = ["", "január", "február", "marec", "apríl", "máj", "jún", "júl", "august", "september", "október", "november", "december"]
            return f"{dt.day}. {months[dt.month]} {dt.year} o {dt.strftime('%H:%M')}"
        return dt.strftime("%B %d, %Y at %H:%M")
    except: return iso_string

def send_confirmation_email(to_email, name, action_type, details, confirm_url, lang='sk'):
    """Sends confirmation email using Brevo API (Primary) or Hostinger SMTP (Backup)."""
    try:
        # Fix: Unpack 3 values (ignore root_dir here)
        template_path, asset_path, _ = get_paths()
        html_base = get_template()
        pretty_date = format_datetime(details, lang)
        
        # Translation logic
        if lang == 'sk':
            subject = "Potvrdenie termínu | ArciGy"
            greeting = f"Dobrý deň, {name}!"
            description = {
                "book": f"Váš nový termín na diagnostiku je: <b>{pretty_date}</b>.",
                "cancel": f"Zrušenie termínu: <b>{pretty_date}</b>.",
                "reschedule": f"Presun termínu: <b>{pretty_date}</b>."
            }.get(action_type, "")
        else:
            subject = "Booking Confirmation | ArciGy"
            greeting = f"Hello, {name}!"
            description = {
                "book": f"Your appointment is set for: <b>{pretty_date}</b>.",
                "cancel": f"Appointment cancelled: <b>{pretty_date}</b>.",
                "reschedule": f"Appointment rescheduled: <b>{pretty_date}</b>."
            }.get(action_type, "")

        # Prepare HTML with Public Image URL (No attachments)
        # Use existing ENV or fallback to known Railway URL
        base_url = os.getenv("WEB_BASE_URL", "https://web-production-a42d.up.railway.app") 
        # Safety: ensure no trailing slash for clean join, though we construct explicitly
        if base_url.endswith("/"): base_url = base_url[:-1]
        
        image_url = f"{base_url}/assets/cyber_socials_layout.jpg"
        
        # Replace the CID reference with the Real URL
        html_content = html_base.replace("cid:cyber_socials_layout", image_url)
        
        # Inject dynamic data
        html_content = html_content.replace("{greeting}", greeting).replace("{details}", description).replace("{confirm_url}", confirm_url).replace("{email_id}", str(int(time.time())))

        # 1. ATTEMPT BREVO API (Primary)
        if BREVO_API_KEY:
            print(f"   🚀 Attempting to send via Brevo API (Asset URL: {image_url})...")
            try:
                url = "https://api.brevo.com/v3/smtp/email"
                headers = {
                    "accept": "application/json",
                    "api-key": BREVO_API_KEY.strip(),
                    "content-type": "application/json"
                }
                
                payload = {
                    "sender": {
                        "name": SENDER_NAME,
                        "email": SENDER_EMAIL
                    },
                    "to": [
                        {
                            "email": to_email,
                            "name": name
                        }
                    ],
                    "subject": subject,
                    "htmlContent": html_content,
                    "textContent": f"{greeting}\n\n{str(description).replace('<b>','').replace('</b>','')}\n\nConfirm here: {confirm_url}"
                }
                
                # No attachments needed anymore!

                response = requests.post(url, json=payload, headers=headers, timeout=10)
                
                if response.status_code in [200, 201, 202]:
                    print(f"   ✅ Email sent successfully via Brevo API. Response: {response.json()}")
                    return True
                else:
                    print(f"   ⚠️ Brevo API Error: {response.status_code} - {response.text}")
                    # Continue to fallback
            except Exception as brevo_err:
                print(f"   ❌ Brevo API Connection Failed: {brevo_err}")
                # Continue to fallback

        # 2. FALLBACK TO HOSTINGER SMTP
        print("   ⚠️ Trying Hostinger SMTP as fallback...")
        try:
            msg = MIMEMultipart('alternative')
            msg['Subject'] = subject
            msg['From'] = f"{SENDER_NAME} <{SENDER_EMAIL}>"
            msg['To'] = to_email
            msg.attach(MIMEText(html_content, 'html'))
            
            if SMTP_USER and SMTP_PASS:
                with smtplib.SMTP_SSL(SMTP_SERVER, 465, timeout=15) as server:
                    server.login(SMTP_USER, SMTP_PASS)
                    server.send_message(msg)
                print("   ✅ Email sent successfully via Hostinger SMTP.")
                return True
            else:
                 print("   ❌ Hostinger SMTP Credentials missing.")
                 return False
        except Exception as smtp_err:
             print(f"   ❌ Hostinger SMTP Failed: {smtp_err}")
             return False

    except Exception as e:
        print(f"CRITICAL Email Error: {e}")
        return False

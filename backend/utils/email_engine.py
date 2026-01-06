import os
import smtplib
import json
import imaplib
import time
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.image import MIMEImage
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# SMTP Config (Fallback)
SMTP_SERVER = os.getenv("SMTP_SERVER", "smtp.hostinger.com")
SMTP_PORT = int(os.getenv("SMTP_PORT", 465))
EMAIL_ACCOUNT_BRANISLAV = os.getenv("EMAIL_ACCOUNT_BRANISLAV", "branislav@arcigy.com:password")

# Resend Config (Primary)
RESEND_API_KEY = os.getenv("RESEND_API_KEY")
FROM_EMAIL = os.getenv("FROM_EMAIL", "onboarding@resend.dev") # Default Resend test email

def get_paths():
    """Helper to get correct paths relative to Arcigy_website root."""
    try:
        current_file = os.path.abspath(__file__)
        base_dir_rel = os.path.dirname(os.path.dirname(os.path.dirname(current_file)))
        if os.path.exists(os.path.join(base_dir_rel, "assets")):
             base_dir = base_dir_rel
        else:
             base_dir = os.path.join(os.getcwd(), "cloud_automations", "Arcigy_website")
    except:
        base_dir = os.getcwd()

    template_path = os.path.join(base_dir, "templates", "premium_email.html")
    asset_path = os.path.join(base_dir, "assets", "cyber_socials_layout.jpg")
    return template_path, asset_path

def get_template():
    template_path, _ = get_paths()
    try:
        if os.path.exists(template_path):
            with open(template_path, 'r', encoding='utf-8') as f:
                return f.read()
    except: pass
    return "<html><body><h2>Potvrdenie termínu</h2><p>{greeting}</p><p>{details}</p><br><a href='{confirm_url}'>Potvrdiť termín</a></body></html>"

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
    """Sends confirmation email using Resend (Cloud friendly) or SMTP (Backup)."""
    try:
        template_path, asset_path = get_paths()
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

        html_content = html_base.replace("{greeting}", greeting).replace("{details}", description).replace("{confirm_url}", confirm_url).replace("{email_id}", str(int(time.time())))

        # 1. ATTEMPT RESEND (Recommended for Railway)
        if RESEND_API_KEY:
            try:
                import resend
                resend.api_key = RESEND_API_KEY
                
                params = {
                    "from": f"ArciGy <{FROM_EMAIL}>",
                    "to": [to_email],
                    "subject": subject,
                    "html": html_content,
                }
                
                # Attach background image if exists
                if os.path.exists(asset_path):
                    import base64
                    with open(asset_path, "rb") as f:
                        content = base64.b64encode(f.read()).decode()
                        params["attachments"] = [{
                            "filename": "cyber_socials_layout.jpg",
                            "content": content
                        }]

                resend.Emails.send(params)
                print("   ✅ Email sent successfully via Resend API.")
                return True
            except Exception as res_err:
                print(f"   ❌ Resend Error: {res_err}")
                # Fall through to SMTP

        # 2. FALLBACK TO SMTP
        print("   ⚠️ Resend not available or failed. Trying SMTP fallback...")
        try:
            # Parse SMTP Credentials
            if ":" in EMAIL_ACCOUNT_BRANISLAV:
                user, pw = EMAIL_ACCOUNT_BRANISLAV.strip('"\'').split(":", 1)
            else:
                user, pw = os.getenv("SMTP_USER"), os.getenv("SMTP_PASS")

            msg = MIMEMultipart('alternative')
            msg['Subject'] = subject
            msg['From'] = f"ArciGy <{user}>"
            msg['To'] = to_email
            msg.attach(MIMEText(html_content, 'html'))

            # Railway-safe SMTP (Port 587)
            with smtplib.SMTP(SMTP_SERVER, 587, timeout=10) as server:
                server.starttls()
                server.login(user, pw)
                server.send_message(msg)
            
            print("   ✅ Email sent successfully via SMTP Fallback.")
            return True
        except Exception as smtp_err:
            print(f"   ❌ SMTP Fallback also failed: {smtp_err}")
            return False

    except Exception as e:
        print(f"CRITICAL Email Error: {e}")
        return False

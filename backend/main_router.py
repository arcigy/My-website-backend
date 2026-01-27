from fastapi import FastAPI, BackgroundTasks, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import RedirectResponse, JSONResponse, FileResponse
from fastapi.staticfiles import StaticFiles # Added for serving images
from pydantic import BaseModel
from typing import List, Optional, Any
import os
import uvicorn
import sys
import urllib.parse

app = FastAPI()
print("🚀 DEPLOYMENT: UPDATED BREVO + ASSETS")
# Check Brevo Key
if os.getenv("BREVO_API_KEY"):
    print(f"✅ BREVO API KEY IS READY. Length: {len(os.getenv('BREVO_API_KEY'))}")
else:
    print("❌ BREVO API KEY IS MISSING in Environment Variables!")

# Enable Static Files for Assets (Images)
base_dir = os.path.dirname(os.path.abspath(__file__)) # backend/
root_dir = os.path.dirname(base_dir) # cloud_automations/Arcigy_website
assets_path = os.path.join(root_dir, "assets")

if os.path.exists(assets_path):
    app.mount("/assets", StaticFiles(directory=assets_path), name="assets")
    print(f"✅ Assets mounted from: {assets_path}")
else:
    print(f"⚠️ Assets dir NOT found at: {assets_path}")

# 1. CANONICAL REDIRECT (Force www.arcigy.com)
@app.middleware("http")
async def force_canonical_host(request: Request, call_next):
    host = request.headers.get("host", "")
    if host and "www.arcigy.com" not in host and "localhost" not in host and "127.0.0.1" not in host:
        # Construct new URL on the primary domain
        url = str(request.url).replace(host, "www.arcigy.com")
        if url.startswith("http://"):
            url = url.replace("http://", "https://")
        return RedirectResponse(url=url, status_code=301)
    
    response = await call_next(request)
    return response

# 2. NUCLEAR CORS (Allow everything explicitly via regex to support credentials if needed)
app.add_middleware(
    CORSMiddleware,
    allow_origin_regex=".*",
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class ChatMessage(BaseModel):
    message: str
    conversationID: str
    history: List[Any]
    lang: Optional[str] = "sk"
    userData: Optional[ Any] = None

class BookingConfirm(BaseModel):
    bookingTime: Any
    email: Any
    name: Any
    phone: Any = "null"
    lang: Any = "sk"
    conversationID: Any = None

class AuditSubmit(BaseModel):
    fullname: str
    email: str
    phone: str
    company: str
    pitch: str
    turnover: str
    journey: str
    dream: str
    problem: str
    bottleneck: str

class PreAuditIntake(BaseModel):
    name: str = ""
    email: str = ""
    business_name: str = ""
    industry: str = ""
    employees: str = ""
    what_sell: str = ""
    typical_customer: str = ""
    source: List[str] = []
    top_tasks: str = ""
    magic_wand: str = ""
    leads_challenge: str = ""
    sales_team: str = ""
    closing_issues: str = ""
    delivery_time: str = ""
    ops_recurring: str = ""
    support_headaches: str = ""
    ai_experience: str = ""
    which_ai_tools: str = ""
    success_definition: str = ""
    specific_focus: str = ""
    referrer: str = "Unknown"

# Global reference for safe access
tony_module = None
try:
    # Try package-style import first (for production)
    import backend.tony_backend as tony_backend
    tony_module = tony_backend
    print("✅ Logic Module loaded via [backend.tony_backend]")
except ImportError:
    try:
        # Try local import (for local dev)
        import tony_backend
        tony_module = tony_backend
        print("✅ Logic Module loaded via [tony_backend]")
    except ImportError as e:
        print(f"❌ Logic Module FAILED to load: {e}")
        import traceback
        traceback.print_exc()

# @app.get("/")
# def home():
#     return {"status": "online", "agent": "Tony AI"}

@app.post("/webhook/chat")
async def chat_endpoint(data: ChatMessage, background_tasks: BackgroundTasks):
    print(f"🔹 POST /webhook/chat HIT. Message: {data.message[:20]}...")
    
    if not tony_module:
        print("❌ tony_backend module is NOT loaded.")
        return {"response": "Internal System Error: Logic module not loaded.", "intention": "error"}

    try:
        # Pass userData to the reasoning engine
        response_json, formatted_history = tony_module.get_tony_response(
            data.message, data.conversationID, data.history, data.lang, data.userData
        )
        if hasattr(tony_module, 'persist_conversation'):
             background_tasks.add_task(tony_module.persist_conversation, data.conversationID, data.message, response_json, formatted_history)
        return response_json
    except Exception as e:
        print(f"❌ Chat Logic Error: {e}")
        return {"response": "Prepáčte, mám technické ťažkosti.", "intention": "error"}

@app.post("/webhook/calendar-availability-check")
async def availability_endpoint():
    try:
        from calendar_engine import get_calendar_availability
        return get_calendar_availability()
    except Exception as e:
        return []

@app.post("/webhook/calendar-initiate-book")
async def initiate_booking(data: BookingConfirm, background_tasks: BackgroundTasks):
    print(f"🔹 Booking Initiation received for: {data.email}")
    try:
        from calendar_engine import confirm_booking
        # 1. Confirm with Cal.com
        result = confirm_booking(
            data.bookingTime, data.email, data.name, data.phone, data.conversationID
        )
        
        # 2. Persist to Supabase if successful
        if result.get("status") == "success" and tony_module:
            if hasattr(tony_module, 'persist_booking'):
                background_tasks.add_task(tony_module.persist_booking, data.dict())
        
        return result
    except Exception as e:
        print(f"❌ Booking Error: {e}")
        return {"status": "error", "message": str(e)}

@app.post("/webhook/audit-submit")
async def audit_submit(data: AuditSubmit, background_tasks: BackgroundTasks):
    print(f"🔹 Audit Submission received for: {data.email}")
    if not tony_module:
        return {"status": "error", "message": "Backend logic not loaded"}
    
    try:
        if hasattr(tony_module, 'persist_audit'):
            background_tasks.add_task(tony_module.persist_audit, data.dict())
            return {"status": "success", "message": "Audit data received and persistence scheduled"}
        else:
            return {"status": "error", "message": "Persistence function missing"}
    except Exception as e:
        print(f"❌ Audit Webhook Error: {e}")
        return {"status": "error", "message": str(e)}

@app.post("/webhook/pre-audit-submit")
async def pre_audit_submit(data: PreAuditIntake, background_tasks: BackgroundTasks):
    print(f"🔹 Pre-Audit Intake received from: {data.email} via {data.referrer}")
    if not tony_module:
         return {"status": "error", "message": "Backend logic not loaded", "ai_message": None}

    try:
        # 1. Persist Data (Background)
        if hasattr(tony_module, 'persist_pre_audit'):
            background_tasks.add_task(tony_module.persist_pre_audit, data.dict())
        else:
            print("❌ tony_backend.persist_pre_audit NOT FOUND")

        # 2. Generate AI Confirmation (Foreground - wait for it to display on frontend)
        ai_msg = None
        if hasattr(tony_module, 'generate_audit_confirmation'):
            # Running this synchronously because we need the return value immediately for the redirect page
            ai_msg = tony_module.generate_audit_confirmation(data.dict())
        
        return {"status": "success", "message": "Intake received", "ai_message": ai_msg}

    except Exception as e:
        print(f"❌ Pre-Audit Webhook Error: {e}")
        return {"status": "error", "message": str(e), "ai_message": None}

@app.get("/webhook/verify-email")
async def verify_email_endpoint(email: str, lang: str = "sk"):
    is_valid, message, suggestion = False, "Internal Error", None
    try:
        from backend.utils.email_validator import validate_email_deep
        is_valid, message, suggestion = validate_email_deep(email, lang)
    except ImportError:
        try:
            from utils.email_validator import validate_email_deep
            is_valid, message, suggestion = validate_email_deep(email, lang)
        except ImportError as e:
            print(f"❌ Email Validator import error: {e}")
            return {"valid": True, "message": "Validation bypassed", "suggestion": None}

    return {
        "valid": is_valid,
        "message": message,
        "suggestion": suggestion
    }

# EXPLICIT ROUTES FOR CLEAN URLs (SEO)
@app.get("/about", include_in_schema=False)
async def get_about():
    return FileResponse(os.path.join(public_html_path, "about.html"))

@app.get("/services", include_in_schema=False)
async def get_services():
    return FileResponse(os.path.join(public_html_path, "services.html"))

@app.get("/pricing", include_in_schema=False)
async def get_pricing():
    return FileResponse(os.path.join(public_html_path, "pricing.html"))

@app.get("/contact", include_in_schema=False)
async def get_contact():
    return FileResponse(os.path.join(public_html_path, "contact.html"))

# MOUNT STATIC SITE (Must be last to avoid blocking API routes)
if os.path.exists(public_html_path):
    app.mount("/", StaticFiles(directory=public_html_path, html=True), name="static_site")
    print(f"✅ Website mounted from: {public_html_path}")
else:
    print(f"⚠️ public_html NOT found at: {public_html_path}")

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=int(os.getenv("PORT", 8000)))

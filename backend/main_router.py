from fastapi import FastAPI, BackgroundTasks, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import RedirectResponse, JSONResponse
from fastapi.staticfiles import StaticFiles # Added for serving images
from pydantic import BaseModel
from typing import List, Optional, Any
import os
import uvicorn
import sys
import urllib.parse

# ... (imports logic)

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

class BookingConfirm(BaseModel):
    bookingTime: Any
    email: Any
    name: Any
    phone: Any = "null"
    lang: Any = "sk"
    conversationID: Any = None

# Global reference for safe access
tony_module = None
try:
    import tony_backend
    tony_module = tony_backend
except ImportError:
    pass

@app.get("/")
def home():
    return {"status": "online", "agent": "Tony AI"}

@app.post("/webhook/chat")
async def chat_endpoint(data: ChatMessage, background_tasks: BackgroundTasks):
    print(f"🔹 POST /webhook/chat HIT. Message: {data.message[:20]}...")
    
    if not tony_module:
        print("❌ tony_backend module is NOT loaded.")
        return {"response": "Internal System Error: Logic module not loaded.", "intention": "error"}

    try:
        # Reverting to direct call like before
        response_json, formatted_history = tony_module.get_tony_response(
            data.message, data.conversationID, data.history, data.lang
        )
        if hasattr(tony_module, 'supabase') and tony_module.supabase:
             background_tasks.add_task(tony_module.persist_conversation, data.conversationID, data.message, response_json, formatted_history)
        return response_json
    except Exception as e:
        print(f"❌ Chat Logic Error: {e}")
        return {"response": "Prepáčte, mám technické ťažkosti.", "intention": "error"}

@app.post("/webhook/calendar-availability-check")
async def availability_endpoint():
    try:
        return calendar_engine.get_calendar_availability()
    except Exception as e:
        return []

@app.post("/webhook/calendar-initiate-book")
async def initiate_booking(data: BookingConfirm, background_tasks: BackgroundTasks):
    try:
        base_url = os.getenv("WEB_BASE_URL", "https://my-website-backend-production-25c8.up.railway.app")
        params = {
            "action": "book",
            "time": data.bookingTime,
            "email": data.email,
            "name": data.name,
            "phone": data.phone,
            "lang": data.lang,
            "cid": data.conversationID
        }
        confirm_url = f"{base_url}/webhook/confirm?{urllib.parse.urlencode(params)}"
        
        # This now sends on background but returns OK immediately
        background_tasks.add_task(
            email_engine.send_confirmation_email,
            data.email, data.name, "book", data.bookingTime, confirm_url, data.lang
        )
        return {"status": "verification_sent"}
    except Exception as e:
        return {"status": "error", "message": str(e)}

@app.get("/webhook/confirm")
async def confirm_action(action: str, time: str, email: str, name: str, phone: str = "null", lang: str = "sk", cid: Optional[str] = None):
    try:
        frontend_url = os.getenv("FRONTEND_BASE_URL", "https://arcigy.com")
        if action == "book":
            res = calendar_engine.confirm_booking(time, email, name, phone, cid)
            if res["status"] == "success":
                target = f"{frontend_url}/.tmp/public_html/confirmation.html?lang={lang}&name={urllib.parse.quote(name)}"
                return RedirectResponse(url=target)
        return {"status": "error", "message": "Failed"}
    except Exception as e:
        return {"status": "error", "message": str(e)}

if __name__ == "__main__":
    # CRITICAL: respect Railway PORT but default to 8001 if local
    port = int(os.environ.get("PORT", 8001))
    uvicorn.run(app, host="0.0.0.0", port=port)

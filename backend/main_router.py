import os
import sys

# PRIORITY 1: Ensure Python finds our modules immediately
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
if BASE_DIR not in sys.path:
    sys.path.append(BASE_DIR)
if os.path.dirname(BASE_DIR) not in sys.path:
    sys.path.append(os.path.dirname(BASE_DIR))

print("🚀 SERVER STARTING UP...")

from fastapi import FastAPI, BackgroundTasks, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import RedirectResponse, JSONResponse
from pydantic import BaseModel
from typing import List, Optional, Any
import uvicorn
import urllib.parse

# Import modules with absolute direct path
try:
    import tony_backend
    import calendar_engine
    from utils import email_engine
    print("✅ Modules loaded successfully")
except Exception as e:
    print(f"❌ Module Load Error: {e}")

app = FastAPI()

# SIMPLEST CORS - This is the safest way to avoid 502 on Options
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["GET", "POST", "OPTIONS"],
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

@app.get("/")
def home():
    print("GET / request")
    return {"status": "online", "system": "ArciGy Tony AI"}

@app.post("/webhook/chat")
async def chat_endpoint(data: ChatMessage, background_tasks: BackgroundTasks):
    print(f"POST /webhook/chat from {data.conversationID}")
    try:
        response_json, formatted_history = tony_backend.get_tony_response(
            data.message, data.conversationID, data.history, data.lang
        )
        if tony_backend.persist_conversation:
             background_tasks.add_task(tony_backend.persist_conversation, data.conversationID, data.message, response_json, formatted_history)
        return response_json
    except Exception as e:
        print(f"❌ Chat Error: {e}")
        return {"response": "Prepáčte, mám technické ťažkosti.", "intention": "error"}

@app.post("/webhook/calendar-availability-check")
async def availability_endpoint():
    print("POST /webhook/calendar-availability-check")
    try:
        return calendar_engine.get_calendar_availability()
    except Exception as e:
        print(f"❌ Availability Error: {e}")
        return []

@app.post("/webhook/calendar-initiate-book")
async def initiate_booking(data: BookingConfirm, background_tasks: BackgroundTasks):
    print(f"POST /webhook/calendar-initiate-book for {data.email}")
    try:
        base_url = os.getenv("WEB_BASE_URL", "https://my-website-backend-production-4247.up.railway.app")
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
        
        background_tasks.add_task(
            email_engine.send_confirmation_email,
            data.email, data.name, "book", data.bookingTime, confirm_url, data.lang
        )
        return {"status": "verification_sent", "message": "Queued"}
    except Exception as e:
        print(f"❌ Booking Error: {e}")
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
    # Railway passes the port as an environment variable
    target_port = int(os.environ.get("PORT", 8001))
    print(f"Starting server on port {target_port}")
    uvicorn.run(app, host="0.0.0.0", port=target_port)

if __name__ == "__main__":
    port = int(os.getenv("PORT", 8001))
    uvicorn.run(app, host="0.0.0.0", port=port)

import os
import sys
import uvicorn
import urllib.parse
from fastapi import FastAPI, BackgroundTasks, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import RedirectResponse, JSONResponse
from pydantic import BaseModel
from typing import List, Optional, Any

# Ensure modules are discoverable
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
if BASE_DIR not in sys.path: sys.path.append(BASE_DIR)

print("🚀 ARCI-BACKEND STARTING...")

# Delayed imports for stability
try:
    import tony_backend
    import calendar_engine
    from utils import email_engine
    print("✅ Logic engines loaded.")
except Exception as e:
    print(f"❌ Critical Load Error: {e}")

app = FastAPI()

# 1. LOGGING MIDDLEWARE - See every request in Railway logs
@app.middleware("http")
async def log_requests(request: Request, call_next):
    print(f">>> {request.method} {request.url.path}")
    try:
        response = await call_next(request)
        print(f"<<< Status: {response.status_code}")
        return response
    except Exception as e:
        print(f"!!! SERVER ERROR: {e}")
        return JSONResponse(status_code=500, content={"error": "Internal error"})

# 2. PERMISSIVE CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Models
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
def health():
    return {"status": "online", "agent": "Tony AI"}

@app.post("/webhook/chat")
async def chat_v2(data: ChatMessage, background_tasks: BackgroundTasks):
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
async def availability_v2():
    try:
        return calendar_engine.get_calendar_availability()
    except Exception as e:
        return []

@app.post("/webhook/calendar-initiate-book")
async def book_v2(data: BookingConfirm, background_tasks: BackgroundTasks):
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
        background_tasks.add_task(email_engine.send_confirmation_email, data.email, data.name, "book", data.bookingTime, confirm_url, data.lang)
        return {"status": "verification_sent"}
    except Exception as e:
        return {"status": "error", "message": str(e)}

@app.get("/webhook/confirm")
async def confirm_v2(action: str, time: str, email: str, name: str, phone: str = "null", lang: str = "sk", cid: Optional[str] = None):
    try:
        frontend_url = os.getenv("FRONTEND_BASE_URL", "https://arcigy.com")
        if action == "book":
            res = calendar_engine.confirm_booking(time, email, name, phone, cid)
            if res["status"] == "success":
                return RedirectResponse(url=f"{frontend_url}/.tmp/public_html/confirmation.html?lang={lang}&name={urllib.parse.quote(name)}")
        return JSONResponse(content={"status": "error"})
    except Exception as e:
        return JSONResponse(status_code=500, content={"error": str(e)})

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8001))
    uvicorn.run(app, host="0.0.0.0", port=port)

if __name__ == "__main__":
    port = int(os.getenv("PORT", 8001))
    uvicorn.run(app, host="0.0.0.0", port=port)

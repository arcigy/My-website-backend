from fastapi import FastAPI, HTTPException, Request, BackgroundTasks, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import RedirectResponse, JSONResponse
from pydantic import BaseModel
from typing import List, Optional, Any
import os
import uvicorn
import urllib.parse

# Standard Imports from the backend package
try:
    from backend import tony_backend
    from backend import calendar_engine
    from backend.utils import email_engine
except ImportError:
    # Local dev fallback
    import tony_backend
    import calendar_engine
    import utils.email_engine as email_engine

app = FastAPI(title="Tony AI - ArciGy Cloud")

# Robust CORS Configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Data Models
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
def health_check():
    return {"status": "active", "bridge": "online"}

@app.post("/webhook/chat")
async def chat_endpoint(data: ChatMessage, background_tasks: BackgroundTasks):
    try:
        response_json, formatted_history = tony_backend.get_tony_response(
            data.message, data.conversationID, data.history, data.lang
        )
        if tony_backend.persist_conversation:
             background_tasks.add_task(tony_backend.persist_conversation, data.conversationID, data.message, response_json, formatted_history)
        return response_json
    except Exception as e:
        print(f"❌ Chat Error: {e}")
        return {"response": "Prepáčte, mám technické ťažkosti. Skúste to prosím neskôr.", "intention": "error"}

@app.post("/webhook/calendar-availability-check")
async def availability_endpoint():
    try:
        return calendar_engine.get_calendar_availability()
    except Exception as e:
        print(f"❌ Availability Error: {e}")
        return []

@app.post("/webhook/calendar-initiate-book")
async def initiate_booking(data: BookingConfirm, background_tasks: BackgroundTasks):
    try:
        base_url = os.getenv("WEB_BASE_URL", "https://my-website-backend-production-4247.up.railway.app")
        
        # Build the confirmation URL
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
        
        # Send Email via Background Task
        background_tasks.add_task(
            email_engine.send_confirmation_email,
            data.email, data.name, "book", data.bookingTime, confirm_url, data.lang
        )
        
        return {"status": "verification_sent", "message": "Email queued."}
    except Exception as e:
        print(f"❌ Booking Start Error: {e}")
        return {"status": "error", "message": str(e)}

@app.get("/webhook/confirm")
async def confirm_action_webhook(action: str, time: str, email: str, name: str, phone: str = "null", lang: str = "sk", cid: Optional[str] = None):
    try:
        frontend_url = os.getenv("FRONTEND_BASE_URL", "https://arcigy.com")
        if action == "book":
            res = calendar_engine.confirm_booking(time, email, name, phone, cid)
            if res["status"] == "success":
                # Success redirect to confirmation page
                target = f"{frontend_url}/.tmp/public_html/confirmation.html?lang={lang}&name={urllib.parse.quote(name)}"
                return RedirectResponse(url=target)
            return {"status": "error", "message": res.get("message")}
        return {"status": "error", "message": "Invalid link"}
    except Exception as e:
        print(f"❌ Confirm Error: {e}")
        return {"status": "error", "message": str(e)}

if __name__ == "__main__":
    port = int(os.getenv("PORT", 8001))
    uvicorn.run(app, host="0.0.0.0", port=port)

if __name__ == "__main__":
    port = int(os.getenv("PORT", 8001))
    uvicorn.run(app, host="0.0.0.0", port=port)

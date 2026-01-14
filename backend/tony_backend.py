import os
import json
import datetime
from openai import OpenAI
from supabase import create_client, Client
from dotenv import load_dotenv

# Load environment variables from various possible locations
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
# Check local, parent, and grandparent for .env
env_paths = [
    os.path.join(BASE_DIR, ".env"),
    os.path.join(os.path.dirname(BASE_DIR), ".env"),
    os.path.join(os.path.dirname(os.path.dirname(BASE_DIR)), ".env"),
    os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(BASE_DIR))), ".env")
]

for p in env_paths:
    if os.path.exists(p):
        load_dotenv(p, override=True)
        break
else:
    load_dotenv(override=True)

# Helper to mask secret keys in logs
def mask_key(k):
    if not k: return "MISSING"
    return k[:4] + "..." + k[-4:] if len(k) > 8 else "***"

# Configurations
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_SERVICE_ROLE_KEY")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

print(f"🤖 Tony Initialization:")
print(f"   OPENAI_KEY: {mask_key(OPENAI_API_KEY)}")
print(f"   SUPABASE_URL: {'SET' if SUPABASE_URL else 'MISSING'}")
print(f"   SUPABASE_KEY: {mask_key(SUPABASE_KEY)}")

# Initialize clients
supabase: Client = None
if SUPABASE_URL and SUPABASE_KEY:
    try:
        supabase = create_client(SUPABASE_URL, SUPABASE_KEY)
        print("   ✅ Supabase: Connected")
    except Exception as e:
        print(f"   ❌ Supabase Error: {e}")

openai_client: OpenAI = None
if OPENAI_API_KEY:
    try:
        openai_client = OpenAI(api_key=OPENAI_API_KEY)
        print("   ✅ OpenAI: Connected")
    except Exception as e:
        print(f"   ❌ OpenAI Error: {e}")
else:
    print("   ❌ OpenAI: NOT CONFIGURED")

# Load Knowledge Base and System Prompt
KNOWLEDGE_PATH = os.path.join(os.path.dirname(__file__), "arcigy_knowledge.md")
LOGICAL_PROMPT_PATH = os.path.join(os.path.dirname(__file__), "tony_prompt.md")
DEV_PROMPT_PATH = os.path.join(os.path.dirname(__file__), "..", "..", "..", "directives", "tony_prompt.md")
PROMPT_PATH = LOGICAL_PROMPT_PATH if os.path.exists(LOGICAL_PROMPT_PATH) else DEV_PROMPT_PATH

def load_knowledge_base():
    try:
        if os.path.exists(KNOWLEDGE_PATH):
            with open(KNOWLEDGE_PATH, "r", encoding="utf-8") as f:
                return f.read()
    except Exception as e:
        print(f"Error loading knowledge base: {e}")
    return ""

def load_system_prompt():
    try:
        prompt_content = ""
        if os.path.exists(PROMPT_PATH):
            with open(PROMPT_PATH, "r", encoding="utf-8") as f:
                prompt_content = f.read()
        
        knowledge = load_knowledge_base()
        if knowledge:
            prompt_content += "\n\n## 📚 BUSINESS KNOWLEDGE BASE\n" + knowledge
            
        return prompt_content
    except Exception as e:
        print(f"Error loading prompt: {e}")
        return "You are Tony, a helpful AI assistant for ArciGy."

def persist_conversation(conversation_id, message, output, formatted_history):
    """
    Handles database updates in the background.
    """
    if not supabase:
        print("⚠️ Supabase client not initialized. Skipping persistence.")
        return
    try:
        # 1. Update Memory
        conv_data = {
            "messageID": conversation_id,
            "conversation": formatted_history + f"\nUser: {message}\nBot: {output.get('response', '')}"
        }
        try:
            supabase.table("ConversationMemory").upsert(conv_data, on_conflict="messageID").execute()
        except Exception as db_err:
            print(f"Database Warning (Memory): {db_err}")

        # 2. Update Leads (Patients)
        ext = output.get("extractedData", {})
        
        # Primary fields from legacy keys or extractedData
        p_forname = output.get("forname")
        p_surname = output.get("surname")
        p_email = output.get("email")
        p_phone = output.get("phone")

        # If any is "null", try to fill from extractedData (especially company/turnover)
        is_valid = all(x and x != "null" for x in [p_forname, p_surname, p_email, p_phone])
        
        if is_valid:
            patient_data = {
                "forename": p_forname,
                "surname": p_surname,
                "email": p_email,
                "phone": p_phone,
                "company": ext.get("company") if ext.get("company") != "null" else None,
                "turnover": ext.get("turnover") if ext.get("turnover") != "null" else None
            }
            # Clean up Nones
            patient_data = {k: v for k, v in patient_data.items() if v is not None}
            
            try:
                supabase.table("Patients").upsert(patient_data, on_conflict="phone").execute()
            except Exception as db_err:
                print(f"Database Warning (Patients): {db_err}")
    except Exception as e:
        print(f"Background Persistence Error: {e}")

def persist_audit(data: dict):
    """
    Saves the full AI Business Audit data to Supabase.
    """
    if not supabase:
        print("⚠️ Supabase not initialized. Cannot persist audit.")
        return
    
    try:
        # Clean data (ensure no "null" strings go into the DB if we want real Nulls)
        clean_data = {k: (v if v != "null" else None) for k, v in data.items()}
        
        # Upsert by email - if the user exists, we update their audit info
        supabase.table("AIAudits").upsert(clean_data, on_conflict="email").execute()
        print(f"✅ Audit successfully persisted for: {clean_data.get('email')}")
    except Exception as e:
        print(f"❌ Supabase Audit Error: {e}")

def persist_booking(data: dict):
    """
    Saves a confirmed calendar booking to Supabase.
    """
    if not supabase:
        print("⚠️ Supabase not initialized. Cannot persist booking.")
        return
    
    try:
        # Clean data
        clean_data = {k: (v if v != "null" else None) for k, v in data.items()}
        
        # Upsert by email and bookingTime to avoid duplicates if they book the same slot
        # Note: This assumes a composite unique key or just handling by email/time
        supabase.table("CalendarBookings").upsert(clean_data, on_conflict="email,bookingTime").execute()
        print(f"✅ Booking successfully persisted for: {clean_data.get('email')} at {clean_data.get('bookingTime')}")
    except Exception as e:
        print(f"❌ Supabase Booking Error: {e}")

def get_tony_response(message, conversation_id, history, user_lang=None, user_data=None):
    """
    Handles the AI reasoning using the external prompt.
    """
    try:
        # 1. Format history
        formatted_history = ""
        if isinstance(history, list):
            formatted_history = "\n".join([f"{m.get('type', 'unknown').capitalize()}: {m.get('text', '')}" for m in history])
        
        # 2. Get AI Response
        system_prompt = load_system_prompt()
        if not openai_client:
            raise Exception("OpenAI client not initialized. Check OPENAI_API_KEY variable.")
            
        if "{now}" in system_prompt:
            system_prompt = system_prompt.replace("{now}", str(datetime.datetime.now()))
        
        # Guide the AI on the required language
        detected_lang = user_lang if user_lang else ('sk' if any(word in message.lower() for word in ['ahoj', 'chcem', 'termin', 'ano', 'dobry']) else 'en')
        lang_instruction = f"IMPORTANT: Respond in {detected_lang.upper()} language." if detected_lang else ""

        # Format User Data for Context
        user_ctx_str = ""
        if user_data:
            try:
                user_ctx_str = f"USER DATA (Known info): {json.dumps(user_data, ensure_ascii=False)}\n\n"
            except:
                pass

        response = openai_client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": system_prompt + f"\n\n{lang_instruction}\nIMPORTANT: Respond ONLY with a raw JSON object. No markdown blocks."},
                {"role": "user", "content": f"{user_ctx_str}HISTÓRIA KONVERZÁCIE:\n{formatted_history}\n\nAKTUÁLNA SPRÁVA OD POUŽÍVATEĽA: {message}"}
            ],
            response_format={"type": "json_object"}
        )
        
        raw_text = response.choices[0].message.content.strip()
        
        try:
            output = json.loads(raw_text)
        except json.JSONDecodeError:
            start = raw_text.find('{')
            end = raw_text.rfind('}')
            if start != -1 and end != -1:
                output = json.loads(raw_text[start:end+1])
            else:
                raise
        
        lang = user_lang if user_lang else ('sk' if any(word in message.lower() for word in ['ahoj', 'chcem', 'termin', 'ano', 'dobry']) else 'en')
        output['lang'] = lang
        
        return output, formatted_history

    except Exception as e:
        import traceback
        print(f"Error in Tony AI: {e}")
        traceback.print_exc()
        return {
            "intention": "question",
            "response": "Prepáč, niečo sa pokazilo. Skús prosím znova.",
            "error": str(e)
        }, ""

if __name__ == "__main__":
    # Local Test
    test_msg = "Ahoj, ja som Branislav Laubert, moj email je hello@arcigy.group a tel cislo +421912345678. Chcem demo."
    result = get_tony_response(test_msg, "test_conv_123", [])
    print(json.dumps(result, indent=2))

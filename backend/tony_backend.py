import os
import json
import datetime
import psycopg2
from psycopg2.extras import Json
import google.generativeai as genai

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
        load_dotenv(p, override=False) # Respect system env vars
        break
else:
    load_dotenv(override=False)


# Helper to mask secret keys in logs
def mask_key(k):
    if not k: return "MISSING"
    return k[:4] + "..." + k[-4:] if len(k) > 8 else "***"

# Configurations
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-1.5-flash") # Default to 1.5 if 2.0 isn't set, but we set it in .env


# Database Configuration
DATABASE_URL = os.getenv("DATABASE_URL")
DB_HOST = os.getenv("DB_HOST", "shinkansen.proxy.rlwy.net")
DB_PORT = os.getenv("DB_PORT", "51580")
DB_NAME = os.getenv("DB_NAME", "railway")
DB_USER = os.getenv("DB_USER", "postgres")
DB_PASS = os.getenv("DB_PASSWORD", "xqhcUQFWracYZcigUmiiUNBYRbUAaOEO")

print(f"🤖 Tony Initialization (Postgres Edition):")
print(f"   GEMINI_KEY: {mask_key(GEMINI_API_KEY)}")
print(f"   DB_MODE: {'DATABASE_URL' if DATABASE_URL else 'FALLBACK_PARAMS'}")

# --- DATABASE MANAGER ---
class DatabaseManager:
    def __init__(self):
        self.db_url = DATABASE_URL
        self.conn_params = {
            "host": DB_HOST,
            "port": DB_PORT,
            "database": DB_NAME,
            "user": DB_USER,
            "password": DB_PASS
        }

    def get_connection(self):
        try:
            if self.db_url:
                return psycopg2.connect(self.db_url)
            return psycopg2.connect(**self.conn_params)
        except Exception as e:
            print(f"❌ Database Connection Error: {e}")
            return None

    def execute_query(self, query, params=None):
        conn = self.get_connection()
        if not conn: return
        try:
            with conn:
                with conn.cursor() as cur:
                    cur.execute(query, params)
        except Exception as e:
            print(f"❌ Query Error: {e}")
        finally:
            conn.close()

db = DatabaseManager()

# Start initialization
print(f"🤖 Tony Initialization (Postgres Edition):")

# Helper to look for key anywhere
def get_key():
    return os.getenv("GEMINI_API_KEY") or os.getenv("GEMINI_KEY")

GEMINI_API_KEY = get_key()
print(f"   GEMINI_KEY Found: {mask_key(GEMINI_API_KEY)}")

# Initialize Gemini
if GEMINI_API_KEY:
    try:
        genai.configure(api_key=GEMINI_API_KEY)
        print(f"   ✅ Gemini: Connected (Model: {GEMINI_MODEL})")
    except Exception as e:
        print(f"   ❌ Gemini Error: {e}")
else:
    print("   ❌ Gemini: NOT CONFIGURED (Environment variables found: " + ", ".join([k for k in os.environ.keys() if "GEMINI" in k]) + ")")


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

# --- PERSISTENCE FUNCTIONS (REWRITTEN FOR POSTGRES) ---

def persist_conversation(conversation_id, message, output, formatted_history):
    """
    Handles database updates for chat history and lead extraction.
    """
    try:
        # 1. Update Memory
        full_conversation = formatted_history + f"\nUser: {message}\nBot: {output.get('response', '')}"
        
        query_memory = """
            INSERT INTO "ConversationMemory" ("messageID", "conversation", "created_at")
            VALUES (%s, %s, NOW())
            ON CONFLICT ("messageID") 
            DO UPDATE SET "conversation" = EXCLUDED."conversation";
        """
        db.execute_query(query_memory, (conversation_id, full_conversation))

        # 2. Update Leads (Patients)
        ext = output.get("extractedData", {})
        p_forname = output.get("forname")
        p_surname = output.get("surname")
        p_email = output.get("email")
        p_phone = output.get("phone")

        is_valid = all(x and x != "null" for x in [p_forname, p_surname, p_email, p_phone])
        
        if is_valid:
            # Prepare extra info for 'other_relevant_info' since we don't have company/turnover columns anymore
            extra_info = {}
            if ext.get("company") and ext.get("company") != "null":
                extra_info["company"] = ext.get("company")
            if ext.get("turnover") and ext.get("turnover") != "null":
                extra_info["turnover"] = ext.get("turnover")
            
            other_info_str = json.dumps(extra_info) if extra_info else None
            
            query_patient = """
                INSERT INTO "Patients" ("forename", "surname", "email", "phone", "other_relevant_info", "created_at")
                VALUES (%s, %s, %s, %s, %s, NOW())
                ON CONFLICT ("phone") 
                DO UPDATE SET 
                    "email" = EXCLUDED."email",
                    "other_relevant_info" = COALESCE(EXCLUDED."other_relevant_info", "Patients"."other_relevant_info");
            """
            db.execute_query(query_patient, (p_forname, p_surname, p_email, p_phone, other_info_str))

    except Exception as e:
        print(f"Background Persistence Error: {e}")

def persist_audit(data: dict):
    """
    Saves the full AI Business Audit data.
    """
    try:
        clean_data = {k: (v if v != "null" else None) for k, v in data.items()}
        
        query = """
            INSERT INTO "AIAudits" (
                "fullname", "email", "phone", "company", "pitch", 
                "turnover", "journey", "dream", "problem", "bottleneck", "created_at"
            ) VALUES (
                %(fullname)s, %(email)s, %(phone)s, %(company)s, %(pitch)s,
                %(turnover)s, %(journey)s, %(dream)s, %(problem)s, %(bottleneck)s, NOW()
            )
            ON CONFLICT ("email") 
            DO UPDATE SET 
                "fullname" = EXCLUDED."fullname",
                "phone" = EXCLUDED."phone",
                "company" = EXCLUDED."company",
                "pitch" = EXCLUDED."pitch",
                "problem" = EXCLUDED."problem";
        """
        db.execute_query(query, clean_data)
        print(f"✅ Audit successfully persisted for: {clean_data.get('email')}")
    except Exception as e:
        print(f"❌ Postgres Audit Error: {e}")

def persist_booking(data: dict):
    """
    Saves a confirmed calendar booking.
    """
    try:
        clean_data = {k: (v if v != "null" else None) for k, v in data.items()}
        
        query = """
            INSERT INTO "CalendarBookings" (
                "bookingTime", "email", "name", "phone", "lang", "conversationID", "created_at"
            ) VALUES (
                %(bookingTime)s, %(email)s, %(name)s, %(phone)s, %(lang)s, %(conversationID)s, NOW()
            )
            ON CONFLICT ("email", "bookingTime") DO NOTHING;
        """
        db.execute_query(query, clean_data)
        print(f"✅ Booking persisted for: {clean_data.get('email')}")
    except Exception as e:
        print(f"❌ Postgres Booking Error: {e}")

def persist_pre_audit(data: dict):
    """
    Saves the Pre-Audit Intake form.
    """
    try:
        clean_data = {k: (v if v != "" else None) for k, v in data.items()}
        
        # Determine source correctly (jsonb compatible)
        source_val = Json(clean_data.get('source', []))
        
        # Prepare params to match exact columns
        params = {
            'name': clean_data.get('name'),
            'email': clean_data.get('email'),
            'business_name': clean_data.get('business_name'),
            'industry': clean_data.get('industry'),
            'employees': clean_data.get('employees'),
            'what_sell': clean_data.get('what_sell'),
            'typical_customer': clean_data.get('typical_customer'),
            'source': source_val,
            'top_tasks': clean_data.get('top_tasks'),
            'magic_wand': clean_data.get('magic_wand'),
            'leads_challenge': clean_data.get('leads_challenge'),
            'sales_team': clean_data.get('sales_team'),
            'closing_issues': clean_data.get('closing_issues'),
            'delivery_time': clean_data.get('delivery_time'),
            'ops_recurring': clean_data.get('ops_recurring'),
            'support_headaches': clean_data.get('support_headaches'),
            'ai_experience': clean_data.get('ai_experience'),
            'which_ai_tools': clean_data.get('which_ai_tools'),
            'success_definition': clean_data.get('success_definition'),
            'specific_focus': clean_data.get('specific_focus'),
            'referrer': clean_data.get('referrer')
        }

        query = """
            INSERT INTO "PreAuditIntakes" (
                "name", "email", "business_name", "industry", "employees", "what_sell", 
                "typical_customer", "source", "top_tasks", "magic_wand", "leads_challenge", 
                "sales_team", "closing_issues", "delivery_time", "ops_recurring", 
                "support_headaches", "ai_experience", "which_ai_tools", "success_definition", 
                "specific_focus", "referrer", "created_at"
            ) VALUES (
                %(name)s, %(email)s, %(business_name)s, %(industry)s, %(employees)s, %(what_sell)s,
                %(typical_customer)s, %(source)s, %(top_tasks)s, %(magic_wand)s, %(leads_challenge)s,
                %(sales_team)s, %(closing_issues)s, %(delivery_time)s, %(ops_recurring)s,
                %(support_headaches)s, %(ai_experience)s, %(which_ai_tools)s, %(success_definition)s,
                %(specific_focus)s, %(referrer)s, NOW()
            );
        """
        db.execute_query(query, params)
        print(f"✅ Pre-Audit persisted for: {clean_data.get('email')}")
    except Exception as e:
        print(f"❌ Postgres Pre-Audit Error: {e}")

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
        # 2. Get AI Response
        current_key = os.getenv("GEMINI_API_KEY") or os.getenv("GEMINI_KEY")
        if current_key:
            current_key = current_key.strip('"').strip("'") # Auto-remove quotes if user included them
            
        if not current_key:
            all_keys = [k for k in os.environ.keys() if "GEMINI" in k]
            raise Exception(f"Gemini API key not initialized. I see these keys: {all_keys}. Make sure GEMINI_API_KEY is set in Railway Variables.")
            
        system_prompt = load_system_prompt()
        if "{now}" in system_prompt:
            system_prompt = system_prompt.replace("{now}", str(datetime.datetime.now()))
        
        detected_lang = user_lang if user_lang else ('sk' if any(word in message.lower() for word in ['ahoj', 'chcem', 'termin', 'ano', 'dobry']) else 'en')
        lang_instruction = f"IMPORTANT: Respond in {detected_lang.upper()} language." if detected_lang else ""

        user_ctx_str = ""
        if user_data:
            try:
                user_ctx_str = f"USER DATA (Known info): {json.dumps(user_data, ensure_ascii=False)}\n\n"
            except:
                pass

        model = genai.GenerativeModel(
            model_name=GEMINI_MODEL,
            generation_config={"response_mime_type": "application/json"}
        )
        
        prompt = (
            f"{system_prompt}\n\n"
            f"{lang_instruction}\n"
            "IMPORTANT: Respond ONLY with a raw JSON object. No markdown blocks.\n\n"
            f"{user_ctx_str}"
            "HISTÓRIA KONVERZÁCIE:\n"
            f"{formatted_history}\n\n"
            f"AKTUÁLNA SPRÁVA OD POUŽÍVATEĽA: {message}"
        )

        response = model.generate_content(prompt)
        raw_text = response.text.strip()
        
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
        error_msg = str(e)
        print(f"Error in Tony AI: {error_msg}")
        traceback.print_exc()
        return {
            "intention": "error",
            "response": f"Tony Error: {error_msg}", 
            "error": error_msg
        }, ""

def generate_audit_confirmation(data: dict):
    """
    Generates a witty, personalized confirmation message based on audit data.
    """
    if not GEMINI_API_KEY:
        return None

    try:
        name = data.get('name', 'Neznámy')
        business = data.get('business_name', '')
        industry = data.get('industry', '')
        problem = data.get('leads_challenge', '') or data.get('closing_issues', '') or 'generic business problems'
        
        system_prompt = """
        You are Tony, a witty and slightly cheeky AI business consultant for ArciGy. 
        Your task is to generate a SHORT, FUNNY, ONE-LINER confirmation message for a user who just submitted a business audit form.
        
        Guidelines:
        - Be witty but friendly. A tiny bit of roasting is okay if it's about their industry struggles, but don't be offensive.
        - Reference their industry or specific problem if possible.
        - Keep it under 25 words.
        - Respond in SLOVAK language (unless the input suggests English, but default to Slovak).
        """

        user_prompt = f"User: {name}, Business: {business}, Industry: {industry}, Main Pain Point: {problem}. Generate the one-liner."

        model = genai.GenerativeModel(GEMINI_MODEL)
        response = model.generate_content(f"{system_prompt}\n\n{user_prompt}")

        return response.text.strip()

    except Exception as e:
        print(f"❌ Auto-Reply Generation Error: {e}")
        return None

if __name__ == "__main__":
    # Local Test
    test_msg = "Ahoj, ja som Branislav Laubert..."
    # You can comment out to avoid unintentional DB writes on import
    # result = get_tony_response(test_msg, "test_conv_psql", [])
    # print(json.dumps(result, indent=2))


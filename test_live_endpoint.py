import requests
import json
import psycopg2
from psycopg2.extras import RealDictCursor
import time

BACKEND_URL = "https://my-website-backend-production-c000.up.railway.app"

DB_HOST = "shinkansen.proxy.rlwy.net"
DB_PORT = "51580"
DB_NAME = "railway"
DB_USER = "postgres"
DB_PASS = "xqhcUQFWracYZcigUmiiUNBYRbUAaOEO"

def check_db(email):
    """Check if a record exists in the DB for this email."""
    try:
        conn = psycopg2.connect(host=DB_HOST, port=DB_PORT, database=DB_NAME, user=DB_USER, password=DB_PASS)
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute('SELECT fullname, email, created_at FROM "AIAudits" WHERE email = %s;', (email,))
            row = cur.fetchone()
        conn.close()
        return row
    except Exception as e:
        return f"DB check error: {e}"

def check_preaudit_db(email):
    """Check if a pre-audit record exists for this email."""
    try:
        conn = psycopg2.connect(host=DB_HOST, port=DB_PORT, database=DB_NAME, user=DB_USER, password=DB_PASS)
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute('SELECT name, email, business_name, created_at FROM "PreAuditIntakes" WHERE email = %s;', (email,))
            row = cur.fetchone()
        conn.close()
        return row
    except Exception as e:
        return f"DB check error: {e}"

def test_audit_submit():
    print("\n=== TEST 1: /webhook/audit-submit ===")
    test_email = "live-test-audit@arcigy.test"
    payload = {
        "fullname": "Live Test User",
        "email": test_email,
        "phone": "+421999000111",
        "company": "Test Live Co",
        "pitch": "We sell AI consultancy to businesses",
        "turnover": "100k-500k",
        "journey": "Lead -> Demo -> Close",
        "dream": "Fully automated ops",
        "problem": "Manual repetitive tasks",
        "bottleneck": "Sales pipeline"
    }
    try:
        r = requests.post(f"{BACKEND_URL}/webhook/audit-submit", json=payload, timeout=15)
        print(f"  Response status: {r.status_code}")
        print(f"  Response body: {r.json()}")
        
        print("  Waiting 3s for background task...")
        time.sleep(3)
        
        row = check_db(test_email)
        if row:
            print(f"  [SUCCESS] DB record found: {row}")
        else:
            print(f"  [FAILURE] No DB record found for {test_email}")
    except Exception as e:
        print(f"  [ERROR] {e}")

def test_pre_audit_submit():
    print("\n=== TEST 2: /webhook/pre-audit-submit ===")
    test_email = "live-test-preaudit@arcigy.test"
    payload = {
        "name": "Live Test Pre",
        "email": test_email,
        "business_name": "Live Pre Corp",
        "industry": "Tech",
        "employees": "6-15",
        "what_sell": "SaaS platform",
        "typical_customer": "SMB owners",
        "source": ["SEO", "Referrals"],
        "top_tasks": "Sales, Support, Reporting",
        "magic_wand": "Automate sales follow-ups",
        "leads_challenge": "Not enough inbound",
        "sales_team": "Just me",
        "closing_issues": "Long sales cycles",
        "delivery_time": "Onboarding is slow",
        "ops_recurring": "",
        "support_headaches": "Repetitive questions",
        "ai_experience": "Tried but failed",
        "which_ai_tools": "ChatGPT",
        "success_definition": "10x more leads automated",
        "specific_focus": "Lead gen",
        "referrer": "Andrej"
    }
    try:
        r = requests.post(f"{BACKEND_URL}/webhook/pre-audit-submit", json=payload, timeout=15)
        print(f"  Response status: {r.status_code}")
        print(f"  Response body: {r.json()}")
        
        print("  Waiting 3s for background task...")
        time.sleep(3)
        
        row = check_preaudit_db(test_email)
        if row:
            print(f"  [SUCCESS] DB record found: {row}")
        else:
            print(f"  [FAILURE] No DB record found for {test_email}")
    except Exception as e:
        print(f"  [ERROR] {e}")

if __name__ == "__main__":
    print(f"Testing backend: {BACKEND_URL}")
    
    # Check health first
    try:
        r = requests.get(f"{BACKEND_URL}/health", timeout=10)
        print(f"Health check: {r.status_code} {r.text[:100]}")
    except Exception as e:
        print(f"Health check failed: {e}")
    
    test_audit_submit()
    test_pre_audit_submit()
    
    print("\nDone.")

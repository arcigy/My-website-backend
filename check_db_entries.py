
import os
import psycopg2
from psycopg2.extras import RealDictCursor

# Database Configuration from tony_backend.py
DB_HOST = "shinkansen.proxy.rlwy.net"
DB_PORT = "51580"
DB_NAME = "railway"
DB_USER = "postgres"
DB_PASS = "xqhcUQFWracYZcigUmiiUNBYRbUAaOEO"

def check_db():
    try:
        conn = psycopg2.connect(
            host=DB_HOST,
            port=DB_PORT,
            database=DB_NAME,
            user=DB_USER,
            password=DB_PASS
        )
        print("Connection successful!")
        
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            # Check AIAudits
            print("\n--- Last 5 entries in AIAudits ---")
            cur.execute('SELECT fullname, email, company, created_at FROM "AIAudits" ORDER BY created_at DESC LIMIT 5;')
            rows = cur.fetchall()
            if not rows:
                print("No entries found in AIAudits.")
            for row in rows:
                print(row)
            
            # Check PreAuditIntakes
            print("\n--- Last 5 entries in PreAuditIntakes ---")
            cur.execute('SELECT name, email, business_name, created_at FROM "PreAuditIntakes" ORDER BY created_at DESC LIMIT 5;')
            rows = cur.fetchall()
            if not rows:
                print("No entries found in PreAuditIntakes.")
            for row in rows:
                print(row)
        
        conn.close()
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    check_db()

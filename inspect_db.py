
import psycopg2
from psycopg2.extras import RealDictCursor

DB_HOST = "shinkansen.proxy.rlwy.net"
DB_PORT = "51580"
DB_NAME = "railway"
DB_USER = "postgres"
DB_PASS = "xqhcUQFWracYZcigUmiiUNBYRbUAaOEO"

def list_tables_and_data():
    try:
        conn = psycopg2.connect(
            host=DB_HOST,
            port=DB_PORT,
            database=DB_NAME,
            user=DB_USER,
            password=DB_PASS
        )
        print("Connection successful!")
        
        with conn.cursor() as cur:
            # List all tables in the public schema
            cur.execute("""
                SELECT table_name 
                FROM information_schema.tables 
                WHERE table_schema = 'public'
            """)
            tables = cur.fetchall()
            print(f"Tables found: {[t[0] for t in tables]}")
            
            for table in tables:
                table_name = table[0]
                cur.execute(f'SELECT COUNT(*) FROM "{table_name}"')
                count = cur.fetchone()[0]
                print(f"Table '{table_name}' has {count} rows.")
                
        conn.close()
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    list_tables_and_data()

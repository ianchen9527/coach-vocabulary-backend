import psycopg2
from psycopg2.extensions import ISOLATION_LEVEL_AUTOCOMMIT

def create_test_db():
    # Connect to 'postgres' db to create new db
    try:
        conn = psycopg2.connect(
            dbname="postgres",
            user="postgres",
            password="postgres",
            host="localhost",
            port=5432
        )
        conn.set_isolation_level(ISOLATION_LEVEL_AUTOCOMMIT)
        cur = conn.cursor()
        
        # Check if exists
        cur.execute("SELECT 1 FROM pg_database WHERE datname = 'coach_vocabulary_test'")
        exists = cur.fetchone()
        
        if not exists:
            print("Creating database coach_vocabulary_test...")
            cur.execute("CREATE DATABASE coach_vocabulary_test")
            print("Database created.")
        else:
            print("Database coach_vocabulary_test already exists.")
            
        cur.close()
        conn.close()
    except Exception as e:
        print(f"Error creating DB: {e}")
        # Try without password if that failed? Or assume user 'ianchen' if postgres failed.
        # But config.py says postgres:postgres.

if __name__ == "__main__":
    create_test_db()

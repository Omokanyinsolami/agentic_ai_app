import psycopg2

def create_database():
    conn = psycopg2.connect(
        dbname="postgres",
        user="postgres",
        password="Ayodele95",
        host="localhost",
        port="5432"
    )
    conn.autocommit = True
    cur = conn.cursor()
    try:
        cur.execute("SELECT 1 FROM pg_database WHERE datname = 'agentic_academic_db';")
        exists = cur.fetchone()
        if not exists:
            cur.execute('CREATE DATABASE agentic_academic_db;')
            print("Database 'agentic_academic_db' created.")
        else:
            print("Database 'agentic_academic_db' already exists.")
    except Exception as e:
        print(f"Error creating database: {e}")
    finally:
        cur.close()
        conn.close()

if __name__ == "__main__":
    create_database()

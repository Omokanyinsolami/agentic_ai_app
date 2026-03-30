import os

import psycopg2
from dotenv import load_dotenv

from db_ops import get_db_config

load_dotenv()


def create_database():
    target_db = os.getenv("DB_NAME", "agentic_academic_db")
    admin_db = os.getenv("DB_ADMIN_DB", "postgres")

    conn = psycopg2.connect(**get_db_config(dbname=admin_db))
    conn.autocommit = True
    cur = conn.cursor()
    try:
        cur.execute("SELECT 1 FROM pg_database WHERE datname = %s;", (target_db,))
        exists = cur.fetchone()
        if not exists:
            cur.execute(f'CREATE DATABASE "{target_db}";')
            print(f"Database '{target_db}' created.")
        else:
            print(f"Database '{target_db}' already exists.")
    except Exception as e:
        print(f"Error creating database: {e}")
    finally:
        cur.close()
        conn.close()


if __name__ == "__main__":
    create_database()

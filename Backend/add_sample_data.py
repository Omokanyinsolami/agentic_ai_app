import psycopg2
from psycopg2 import sql

def get_connection():
    return psycopg2.connect(
        dbname="agentic_academic_db",
        user="postgres",
        password="Ayodele95",
        host="localhost",
        port="5432"
    )

def add_sample_data():
    conn = get_connection()
    cur = conn.cursor()
    try:
        # Add a sample user (only name is required, other fields optional)
        cur.execute("""
            INSERT INTO user_profiles (name, academic_program, preferences, history)
            VALUES (%s, %s, %s, %s)
            RETURNING id;
        """, ("Alice Example", "Computer Science", None, None))
        user_id = cur.fetchone()[0]

        # Add a sample task
        cur.execute("""
            INSERT INTO tasks (user_id, title, description, status, deadline, priority)
            VALUES (%s, %s, %s, %s, %s, %s)
            RETURNING id;
        """, (user_id, "Write Literature Review", "Draft the literature review section of the dissertation.", "pending", "2026-03-10", 1))
        task_id = cur.fetchone()[0]

        # Add a sample resource
        cur.execute("""
            INSERT INTO resources (user_id, title, link, description)
            VALUES (%s, %s, %s, %s)
            RETURNING id;
        """, (user_id, "LangGraph Documentation", "https://langchain-ai.github.io/langgraph/", "Official documentation for LangGraph."))
        resource_id = cur.fetchone()[0]

        conn.commit()
        print(f"Sample user, task, and resource added. User ID: {user_id}, Task ID: {task_id}, Resource ID: {resource_id}")
    except Exception as e:
        conn.rollback()
        print(f"Error adding sample data: {e}")
    finally:
        cur.close()
        conn.close()

if __name__ == "__main__":
    add_sample_data()

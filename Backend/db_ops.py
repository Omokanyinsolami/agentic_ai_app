import psycopg2
from typing import List, Dict, Any

DB_NAME = "agentic_academic_db"
DB_USER = "postgres"
DB_PASSWORD = "Ayodele95"
DB_HOST = "localhost"
DB_PORT = "5432"

def get_connection():
    return psycopg2.connect(
        dbname=DB_NAME,
        user=DB_USER,
        password=DB_PASSWORD,
        host=DB_HOST,
        port=DB_PORT
    )

def add_task(user_id: int, title: str, description: str, deadline: str, priority: int, status: str, dependencies: List[int]=None):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("""
        INSERT INTO tasks (user_id, title, description, deadline, priority, status, dependencies)
        VALUES (%s, %s, %s, %s, %s, %s, %s)
        RETURNING id;
    """, (user_id, title, description, deadline, priority, status, dependencies))
    task_id = cur.fetchone()[0]
    conn.commit()
    cur.close()
    conn.close()
    return task_id

def get_tasks(user_id: int) -> List[Dict[str, Any]]:
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT id, title, description, deadline, priority, status, dependencies FROM tasks WHERE user_id = %s", (user_id,))
    rows = cur.fetchall()
    cur.close()
    conn.close()
    return [
        {
            "id": row[0],
            "title": row[1],
            "description": row[2],
            "deadline": row[3],
            "priority": row[4],
            "status": row[5],
            "dependencies": row[6],
        } for row in rows
    ]

def update_task_status(task_id: int, status: str):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("UPDATE tasks SET status = %s WHERE id = %s", (status, task_id))
    conn.commit()
    cur.close()
    conn.close()

def delete_task(task_id: int):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("DELETE FROM tasks WHERE id = %s", (task_id,))
    conn.commit()
    cur.close()
    conn.close()

# Similar CRUD functions can be created for user_profiles and resources as needed.

if __name__ == "__main__":
    print("Sample tasks for user 1:")
    print(get_tasks(1))

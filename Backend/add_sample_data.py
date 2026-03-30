from db_ops import get_connection


def add_sample_data():
    conn = get_connection()
    cur = conn.cursor()
    try:
        cur.execute(
            """
            INSERT INTO user_profiles (name, academic_program, preferences, history)
            VALUES (%s, %s, %s, %s)
            RETURNING id;
            """,
            ("Alice Example", "Computer Science", None, None),
        )
        user_id = cur.fetchone()[0]

        cur.execute(
            """
            INSERT INTO tasks (user_id, title, description, status, deadline, priority)
            VALUES (%s, %s, %s, %s, %s, %s)
            RETURNING id;
            """,
            (
                user_id,
                "Write Literature Review",
                "Draft the literature review section of the dissertation.",
                "pending",
                "2026-03-10",
                1,
            ),
        )
        task_id = cur.fetchone()[0]

        test_tasks = [
            (
                user_id,
                "Finish Literature Review",
                "Complete the literature review section.",
                "pending",
                "2026-03-07 10:00",
                1,
            ),
            (
                user_id,
                "Prepare Methodology Draft",
                "Draft methodology chapter.",
                "pending",
                "2026-03-08 14:00",
                2,
            ),
            (
                user_id,
                "Review AI Ethics Paper",
                "Read and annotate AI ethics paper.",
                "pending",
                "2026-03-09 16:00",
                3,
            ),
        ]
        for task in test_tasks:
            cur.execute(
                """
                INSERT INTO tasks (user_id, title, description, status, deadline, priority)
                VALUES (%s, %s, %s, %s, %s, %s)
                """,
                task,
            )

        cur.execute(
            """
            INSERT INTO resources (user_id, title, link, description)
            VALUES (%s, %s, %s, %s)
            RETURNING id;
            """,
            (
                user_id,
                "LangGraph Documentation",
                "https://langchain-ai.github.io/langgraph/",
                "Official documentation for LangGraph.",
            ),
        )
        resource_id = cur.fetchone()[0]

        conn.commit()
        print(
            f"Sample user, task, and resource added. User ID: {user_id}, "
            f"Task ID: {task_id}, Resource ID: {resource_id}"
        )
    except Exception as e:
        conn.rollback()
        print(f"Error adding sample data: {e}")
    finally:
        cur.close()
        conn.close()


if __name__ == "__main__":
    add_sample_data()

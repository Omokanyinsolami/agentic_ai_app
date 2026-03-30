"""
Database migration: add scheduling tables for agentic AI scheduling.
"""

from db_ops import get_connection


def add_schedule_tables():
    conn = get_connection()
    cur = conn.cursor()
    try:
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS student_availability (
                id SERIAL PRIMARY KEY,
                user_id INTEGER REFERENCES user_profiles(id) ON DELETE CASCADE,
                day_of_week INTEGER NOT NULL CHECK (day_of_week >= 0 AND day_of_week <= 6),
                start_time TIME NOT NULL,
                end_time TIME NOT NULL,
                location VARCHAR(100),
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                CONSTRAINT valid_time_range CHECK (end_time > start_time),
                CONSTRAINT unique_availability UNIQUE (user_id, day_of_week, start_time)
            );
            """
        )

        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS scheduled_slots (
                id SERIAL PRIMARY KEY,
                user_id INTEGER REFERENCES user_profiles(id) ON DELETE CASCADE,
                task_id INTEGER REFERENCES tasks(id) ON DELETE CASCADE,
                scheduled_date DATE NOT NULL,
                start_time TIME NOT NULL,
                end_time TIME NOT NULL,
                status VARCHAR(50) DEFAULT 'scheduled',
                ai_reasoning TEXT,
                confidence_score FLOAT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                CONSTRAINT valid_slot_time CHECK (end_time > start_time)
            );
            """
        )

        cur.execute("ALTER TABLE user_profiles ADD COLUMN IF NOT EXISTS password_hash TEXT;")
        cur.execute("ALTER TABLE tasks ADD COLUMN IF NOT EXISTS deleted BOOLEAN DEFAULT FALSE;")
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS user_sessions (
                id SERIAL PRIMARY KEY,
                user_id INTEGER NOT NULL REFERENCES user_profiles(id) ON DELETE CASCADE,
                token_hash VARCHAR(128) NOT NULL UNIQUE,
                created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
                expires_at TIMESTAMP NOT NULL,
                revoked BOOLEAN NOT NULL DEFAULT FALSE,
                revoked_at TIMESTAMP
            );
            """
        )

        cur.execute("CREATE INDEX IF NOT EXISTS idx_availability_user ON student_availability(user_id);")
        cur.execute("CREATE INDEX IF NOT EXISTS idx_scheduled_user_date ON scheduled_slots(user_id, scheduled_date);")
        cur.execute("CREATE INDEX IF NOT EXISTS idx_scheduled_task ON scheduled_slots(task_id);")
        cur.execute("CREATE INDEX IF NOT EXISTS idx_user_sessions_user_id ON user_sessions(user_id);")
        cur.execute("CREATE INDEX IF NOT EXISTS idx_user_sessions_expires_at ON user_sessions(expires_at);")

        conn.commit()
        print("Scheduling tables created successfully!")
    finally:
        cur.close()
        conn.close()


if __name__ == "__main__":
    add_schedule_tables()

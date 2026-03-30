from db_ops import get_connection


def init_db():
    conn = get_connection()
    cur = conn.cursor()
    try:
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS user_profiles (
                id SERIAL PRIMARY KEY,
                name VARCHAR(100) NOT NULL,
                email VARCHAR(100) UNIQUE,
                academic_program VARCHAR(100),
                password_hash TEXT,
                preferences JSONB,
                history JSONB
            );
            """
        )

        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS tasks (
                id SERIAL PRIMARY KEY,
                user_id INTEGER REFERENCES user_profiles(id) ON DELETE CASCADE,
                title VARCHAR(200) NOT NULL,
                description TEXT,
                deadline TIMESTAMP,
                priority INTEGER,
                status VARCHAR(50),
                deleted BOOLEAN DEFAULT FALSE,
                dependencies INTEGER[],
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
            """
        )

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

        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS resources (
                id SERIAL PRIMARY KEY,
                user_id INTEGER REFERENCES user_profiles(id) ON DELETE CASCADE,
                title VARCHAR(200),
                link TEXT,
                description TEXT
            );
            """
        )

        conn.commit()
        print("Database tables created successfully!")
    finally:
        cur.close()
        conn.close()


if __name__ == "__main__":
    init_db()

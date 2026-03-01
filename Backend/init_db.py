import psycopg2

# Update these as needed
DB_NAME = "agentic_academic_db"
DB_USER = "postgres"
DB_PASSWORD = "Ayodele95"
DB_HOST = "localhost"
DB_PORT = "5432"

conn = psycopg2.connect(
    dbname=DB_NAME,
    user=DB_USER,
    password=DB_PASSWORD,
    host=DB_HOST,
    port=DB_PORT
)
cur = conn.cursor()

# User Profiles Table
cur.execute("""
CREATE TABLE IF NOT EXISTS user_profiles (
    id SERIAL PRIMARY KEY,
    name VARCHAR(100) NOT NULL,
    email VARCHAR(100) UNIQUE,
    academic_program VARCHAR(100),
    preferences JSONB,
    history JSONB
);
""")

# Tasks Table
cur.execute("""
CREATE TABLE IF NOT EXISTS tasks (
    id SERIAL PRIMARY KEY,
    user_id INTEGER REFERENCES user_profiles(id) ON DELETE CASCADE,
    title VARCHAR(200) NOT NULL,
    description TEXT,
    deadline TIMESTAMP,
    priority INTEGER,
    status VARCHAR(50),
    dependencies INTEGER[],
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
""")

# Resources Table
cur.execute("""
CREATE TABLE IF NOT EXISTS resources (
    id SERIAL PRIMARY KEY,
    user_id INTEGER REFERENCES user_profiles(id) ON DELETE CASCADE,
    title VARCHAR(200),
    link TEXT,
    description TEXT
);
""")

conn.commit()
cur.close()
conn.close()

print("Database tables created successfully!")

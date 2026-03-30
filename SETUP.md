# Agentic AI Database Setup Guide

Use this guide to recreate the PostgreSQL database schema for the Agentic AI app on a new machine.

## Prerequisites

- PostgreSQL is installed
- PostgreSQL service is running
- Python 3.12 is installed
- You have the project files on the machine

## 1. Open PowerShell in the project folder

```powershell
open a terminal and go to the prototype folder by typing
cd prototype
cd backend
```

## 2. Create and activate the Python virtual environment

This project should use Python 3.12.

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\Activate.ps1
# python -m pip install --upgrade pip
# pip install -r Backend\requirements.txt
```

## 3. Create the backend environment file

<!-- Copy the example env file and open it for editing.

```powershell
Copy-Item Backend\.env.example Backend\.env
notepad Backend\.env -->
```

## 4. Fill in the database settings in `Backend\.env`

```env
DB_NAME=agentic_academic_db
DB_USER=postgres
DB_PASSWORD=your_postgres_password
DB_HOST=localhost
DB_PORT=5432
DB_CONNECT_TIMEOUT=5
DB_ADMIN_DB=postgres

```

### Notes

- `DB_NAME` is the application database that will be created.
- `DB_ADMIN_DB=postgres` tells the script to connect to PostgreSQL's default admin database first.

## 5. Create the application database

Run the database creation script:

```powershell
.\.venv\Scripts\python.exe Backend\create_db.py
```

Expected result:

- If successful, it creates `agentic_academic_db`
- If it already exists, the script will say so

## 6. Create the core tables

```powershell
.\.venv\Scripts\python.exe Backend\init_db.py
```

This creates:

- `user_profiles`
- `tasks`
- `user_sessions`
- `resources`

## 7. Create the scheduling tables

```powershell
.\.venv\Scripts\python.exe Backend\add_schedule_tables.py
```

This creates:

- `student_availability`
- `scheduled_slots`

It also ensures:

- `password_hash` exists on `user_profiles`
- `deleted` exists on `tasks`

## 8. Verify the schema

If `psql` is installed:

```powershell
psql -U postgres -d agentic_academic_db -c "\dt"
```

You should see these tables:

- `user_profiles`
- `tasks`
- `user_sessions`
- `resources`
- `student_availability`
- `scheduled_slots`

If using pgAdmin:

1. Open pgAdmin
2. Connect to your PostgreSQL server
3. Open the `agentic_academic_db` database
4. Go to `Schemas > public > Tables`
5. Confirm the tables listed above exist

## 9. If the database already exists

If the database was already created manually, skip Step 5 and just run:

```powershell
.\.venv\Scripts\python.exe Backend\init_db.py
.\.venv\Scripts\python.exe Backend\add_schedule_tables.py
```

## Common Issues

### Connection failed

Usually caused by:

- PostgreSQL is not running
- wrong `DB_PASSWORD`
- wrong `DB_HOST` or `DB_PORT`

### Permission denied when creating database

Usually means:

- `DB_USER` does not have permission to create databases

In that case, either:

- use a PostgreSQL admin account
- create the database manually in pgAdmin, then run the schema scripts

### Python version issue

Use Python `3.12.x` for this project.

## Full Command Summary

```powershell
cd "C:\path\to\Agentic AI app"
py -3.12 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -r Backend\requirements.txt
Copy-Item Backend\.env.example Backend\.env
notepad Backend\.env
.\.venv\Scripts\python.exe Backend\create_db.py
.\.venv\Scripts\python.exe Backend\init_db.py
.\.venv\Scripts\python.exe Backend\add_schedule_tables.py
```

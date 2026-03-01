# langgraph_agent.py
"""
Academic Task Agent with LangGraph + PostgreSQL

Features
--------
Tasks
- show [user_id] [--status STATUS] [--search KEYWORD] [--sort deadline|priority|created_at] [--desc]
- add [user_id]
- update <task_id>
- delete <task_id>

Users
- user create
- user show <user_id>
- user update <user_id>
- user delete <user_id>
- user list
- use <user_id>
- whoami

Reminders
- remind [user_id] [--days N] [--send-email]

Import / Export
- export [user_id] <filepath> [--status STATUS] [--search KEYWORD] [--sort deadline|priority|created_at] [--desc]
- import [user_id] <filepath>

Other
- help
- exit

Environment variables (.env)
----------------------------
Required:
DB_NAME
DB_USER
DB_PASSWORD
DB_HOST
DB_PORT

Optional for email reminders:
SMTP_HOST
SMTP_PORT
SMTP_USER
SMTP_PASSWORD
SMTP_FROM
SMTP_USE_TLS=true
"""

import os
import csv
import io
import shlex
import smtplib
from pathlib import Path
from email.message import EmailMessage
from datetime import datetime, date, timedelta
from typing import Optional, Any
from typing_extensions import TypedDict, Annotated, Literal

import psycopg2
from psycopg2 import IntegrityError
from dotenv import load_dotenv
from langchain_core.messages import HumanMessage, AIMessage, BaseMessage
from langgraph.graph import StateGraph, START, END
from langgraph.graph.message import add_messages


# ----------------------------
# Load environment variables
# ----------------------------
load_dotenv()


# ----------------------------
# DB helpers
# ----------------------------
def get_db_settings() -> dict:
    """Read DB settings from environment and fail fast if any are missing."""
    settings = {
        "dbname": os.getenv("DB_NAME"),
        "user": os.getenv("DB_USER"),
        "password": os.getenv("DB_PASSWORD"),
        "host": os.getenv("DB_HOST"),
        "port": os.getenv("DB_PORT"),
    }
    missing = [k.upper() for k, v in settings.items() if not v]
    if missing:
        raise ValueError(
            f"Missing required environment variables: {', '.join(missing)}"
        )
    return settings


def get_connection():
    """Open a new PostgreSQL connection."""
    return psycopg2.connect(**get_db_settings())


def ensure_schema() -> None:
    """
    Create minimal schema if missing.

    This is deliberately conservative:
    - creates users if missing
    - creates tasks if missing
    - adds created_at to tasks if missing

    If your existing tables use different names/columns, adjust here once.
    """
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                CREATE TABLE IF NOT EXISTS users (
                    id SERIAL PRIMARY KEY,
                    name TEXT NOT NULL,
                    email TEXT UNIQUE NOT NULL,
                    program TEXT,
                    created_at TIMESTAMP NOT NULL DEFAULT NOW()
                );
                """
            )

            cur.execute(
                """
                CREATE TABLE IF NOT EXISTS tasks (
                    id SERIAL PRIMARY KEY,
                    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
                    title TEXT NOT NULL,
                    description TEXT,
                    deadline DATE,
                    priority INTEGER NOT NULL DEFAULT 3,
                    status TEXT NOT NULL DEFAULT 'pending',
                    created_at TIMESTAMP NOT NULL DEFAULT NOW()
                );
                """
            )

            cur.execute(
                """
                ALTER TABLE tasks
                ADD COLUMN IF NOT EXISTS created_at TIMESTAMP NOT NULL DEFAULT NOW();
                """
            )
        conn.commit()


# ----------------------------
# LangGraph state
# ----------------------------
class AgentState(TypedDict):
    messages: Annotated[list[BaseMessage], add_messages]


def _last_human_text(state: AgentState) -> str:
    """Return the last human message content."""
    msgs = state.get("messages", [])
    for m in reversed(msgs):
        if isinstance(m, HumanMessage):
            return (m.content or "").strip()
        if isinstance(m, dict) and "content" in m:
            return str(m["content"]).strip()
    return ""


# ----------------------------
# Parsing / validation helpers
# ----------------------------
def _parse_csv_payload(text: str):
    """
    Parse payload after the first colon as CSV.
    Example:
      add_task: 1,"Title","Desc",2026-03-15,2,pending
    """
    payload = text.split(":", 1)[1].strip() if ":" in text else ""
    if not payload:
        return None, "Missing payload."

    try:
        reader = csv.reader(io.StringIO(payload), skipinitialspace=True)
        parts = next(reader)
        return parts, None
    except Exception:
        return None, "Could not parse CSV payload."


def _parse_kv_payload(text: str) -> dict[str, str]:
    """
    Parse payload after the first colon in the form:
      key=value; key2=value2

    Example:
      show_tasks: user_id=5; status=pending; search=report; sort=deadline; order=desc
    """
    payload = text.split(":", 1)[1].strip() if ":" in text else ""
    if not payload:
        return {}

    result: dict[str, str] = {}
    for chunk in payload.split(";"):
        chunk = chunk.strip()
        if not chunk:
            continue
        if "=" not in chunk:
            continue
        key, value = chunk.split("=", 1)
        result[key.strip()] = value.strip()
    return result


def _build_kv_command(prefix: str, **kwargs) -> str:
    """
    Build a command string like:
      prefix: key=value; key2=value2
    """
    parts = []
    for k, v in kwargs.items():
        if v is None or v == "":
            continue
        if isinstance(v, bool):
            v = str(v).lower()
        parts.append(f"{k}={v}")
    return f"{prefix}: " + "; ".join(parts)


def _validate_deadline(deadline_raw: str):
    """
    Validate a deadline string. Accepts ISO date strings.
    Returns (normalized_deadline, error_message).
    """
    if not deadline_raw:
        return None, None

    try:
        parsed = datetime.fromisoformat(deadline_raw)
        return parsed.date().isoformat(), None
    except Exception:
        return None, "Deadline must be in YYYY-MM-DD format, e.g. 2026-03-15"


def _to_int(value: Any, field_name: str):
    """Convert to int with a clearer error."""
    try:
        return int(str(value).strip())
    except Exception:
        raise ValueError(f"{field_name} must be an integer.")


def _normalize_status(status: str) -> str:
    """
    Normalize task status to a predictable lowercase form.
    Example: 'In Progress' -> 'in_progress'
    """
    return status.strip().lower().replace(" ", "_")


def _parse_bool(value: Optional[str]) -> bool:
    """Parse a truthy/falsy string."""
    if value is None:
        return False
    return value.strip().lower() in {"1", "true", "yes", "y", "on"}


def _allowed_sort(sort_by: Optional[str]) -> str:
    """
    Whitelist sort columns to avoid SQL injection.
    """
    allowed = {
        "deadline": "deadline",
        "priority": "priority",
        "created_at": "created_at",
    }
    return allowed.get((sort_by or "deadline").strip().lower(), "deadline")


def _allowed_order(order: Optional[str]) -> str:
    """Whitelist sort direction."""
    return "DESC" if str(order or "").strip().lower() == "desc" else "ASC"


def _split_positionals_and_options(tokens: list[str]) -> tuple[list[str], dict[str, Any]]:
    """
    Split a shell-like token list into positionals and --options.

    Example:
      ['show', '5', '--status', 'pending', '--desc']
    becomes:
      (['5'], {'status': 'pending', 'desc': True})
    """
    positionals: list[str] = []
    options: dict[str, Any] = {}
    i = 0
    while i < len(tokens):
        tok = tokens[i]
        if tok.startswith("--"):
            key = tok[2:]
            if key in {"desc", "send-email"}:
                options[key] = True
                i += 1
                continue

            if i + 1 >= len(tokens):
                raise ValueError(f"Option {tok} requires a value.")
            options[key] = tokens[i + 1]
            i += 2
        else:
            positionals.append(tok)
            i += 1
    return positionals, options


# ----------------------------
# Shared task query helper
# ----------------------------
def fetch_tasks(
    user_id: int,
    status: Optional[str] = None,
    search: Optional[str] = None,
    sort_by: Optional[str] = "deadline",
    order: Optional[str] = "asc",
) -> list[tuple]:
    """
    Fetch tasks for a user with optional filtering/search/sorting.
    """
    safe_sort = _allowed_sort(sort_by)
    safe_order = _allowed_order(order)

    base_query = """
        SELECT id, title, description, deadline, priority, status, created_at
        FROM tasks
        WHERE user_id = %s
    """
    params: list[Any] = [user_id]

    if status:
        base_query += " AND LOWER(status) = LOWER(%s)"
        params.append(status)

    if search:
        base_query += " AND (title ILIKE %s OR description ILIKE %s)"
        keyword = f"%{search}%"
        params.extend([keyword, keyword])

    # Safe because safe_sort and safe_order come from whitelists.
    if safe_sort == "deadline":
        base_query += f" ORDER BY deadline {safe_order} NULLS LAST, id DESC"
    else:
        base_query += f" ORDER BY {safe_sort} {safe_order}, id DESC"

    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(base_query, tuple(params))
            return cur.fetchall()


# ----------------------------
# Optional email reminder helper
# ----------------------------
def send_email_notification(to_email: str, subject: str, body: str) -> tuple[bool, str]:
    """
    Send an email if SMTP settings are configured.
    Returns (success, message).
    """
    smtp_host = os.getenv("SMTP_HOST")
    smtp_port = os.getenv("SMTP_PORT")
    smtp_user = os.getenv("SMTP_USER")
    smtp_password = os.getenv("SMTP_PASSWORD")
    smtp_from = os.getenv("SMTP_FROM")
    smtp_use_tls = _parse_bool(os.getenv("SMTP_USE_TLS", "true"))

    required = [smtp_host, smtp_port, smtp_user, smtp_password, smtp_from]
    if not all(required):
        return False, "SMTP settings are not fully configured in .env."

    try:
        msg = EmailMessage()
        msg["Subject"] = subject
        msg["From"] = smtp_from
        msg["To"] = to_email
        msg.set_content(body)

        with smtplib.SMTP(smtp_host, int(smtp_port)) as server:
            if smtp_use_tls:
                server.starttls()
            server.login(smtp_user, smtp_password)
            server.send_message(msg)

        return True, f"Reminder email sent to {to_email}."
    except Exception as e:
        return False, f"Failed to send email: {e}"


# ----------------------------
# Router
# ----------------------------
def route(
    state: AgentState,
) -> Literal[
    "help",
    "show_tasks",
    "add_task",
    "update_task",
    "delete_task",
    "create_user",
    "get_user",
    "update_user",
    "delete_user",
    "list_users",
    "export_tasks",
    "import_tasks",
    "reminders",
]:
    text = _last_human_text(state).lower()

    if text.startswith("show_tasks:"):
        return "show_tasks"
    if text.startswith("add_task:"):
        return "add_task"
    if text.startswith("update_task:"):
        return "update_task"
    if text.startswith("delete_task:"):
        return "delete_task"
    if text.startswith("create_user:"):
        return "create_user"
    if text.startswith("get_user:"):
        return "get_user"
    if text.startswith("update_user:"):
        return "update_user"
    if text.startswith("delete_user:"):
        return "delete_user"
    if text.startswith("list_users:"):
        return "list_users"
    if text.startswith("export_tasks:"):
        return "export_tasks"
    if text.startswith("import_tasks:"):
        return "import_tasks"
    if text.startswith("reminders:"):
        return "reminders"

    return "help"


# ----------------------------
# Help node
# ----------------------------
def help_node(state: AgentState) -> dict:
    msg = """Available commands

TASKS
-----
show <user_id> [--status STATUS] [--search KEYWORD] [--sort deadline|priority|created_at] [--desc]
  Examples:
    show 5
    show 5 --status pending
    show 5 --search dissertation
    show 5 --sort priority --desc

add <user_id>
  Example:
    add 5

update <task_id>
  Example:
    update 12

delete <task_id>
  Example:
    delete 12

USERS
-----
user create
user show <user_id>
user update <user_id>
user delete <user_id>
user list

  Examples:
    user create
    user show 3
    user update 3
    user delete 3
    user list

CURRENT USER
------------
use <user_id>
whoami

  Examples:
    use 5
    whoami

REMINDERS
---------
remind [user_id] [--days N] [--send-email]

  Examples:
    remind 5
    remind 5 --days 7
    remind 5 --days 3 --send-email

EXPORT / IMPORT
---------------
export [user_id] <filepath> [--status STATUS] [--search KEYWORD] [--sort deadline|priority|created_at] [--desc]
import [user_id] <filepath>

  Examples:
    export 5 tasks.csv
    export 5 pending_tasks.csv --status pending --sort deadline
    import 5 tasks.csv

OTHER
-----
help
exit

Notes
-----
- If you use 'use <user_id>', later commands can omit the user_id:
    show --status pending
    add
    export backup.csv
    remind --days 3
- Quote file paths with spaces:
    export 5 "C:/Users/You/Desktop/tasks backup.csv"
"""
    return {"messages": [AIMessage(content=msg)]}


# ----------------------------
# Task nodes
# ----------------------------
def get_user_tasks(state: AgentState) -> dict:
    """
    Internal command format:
      show_tasks: user_id=5; status=pending; search=report; sort=deadline; order=desc
    """
    params = _parse_kv_payload(_last_human_text(state))

    try:
        user_id = _to_int(params.get("user_id"), "user_id")
        status = params.get("status")
        search = params.get("search")
        sort_by = params.get("sort", "deadline")
        order = params.get("order", "asc")

        rows = fetch_tasks(
            user_id=user_id,
            status=status,
            search=search,
            sort_by=sort_by,
            order=order,
        )
    except Exception as e:
        return {"messages": [AIMessage(content=f"Error while fetching tasks: {e}")]}

    if not rows:
        return {"messages": [AIMessage(content=f"No matching tasks found for user {user_id}.")]}

    lines = [f"Tasks for user {user_id}:"]
    for task_id, title, desc, deadline, priority, status, created_at in rows:
        lines.append(
            f"- [{task_id}] {title} | status={status} | priority={priority} | due={deadline} | created_at={created_at}\n"
            f"  desc: {desc}"
        )

    return {"messages": [AIMessage(content="\n".join(lines))]}


def add_task_to_db(state: AgentState) -> dict:
    """
    Internal command format:
      add_task: user_id,title,description,deadline,priority,status
    """
    text = _last_human_text(state)
    parts, err = _parse_csv_payload(text)
    if err:
        return {
            "messages": [
                AIMessage(
                    content='Invalid payload. Example:\nadd_task: 1, "Title", "Desc", 2026-03-15, 3, pending'
                )
            ]
        }

    if len(parts) < 6:
        return {
            "messages": [
                AIMessage(content="Not enough fields for add_task. Need 6 values.")
            ]
        }

    try:
        user_id = _to_int(parts[0], "user_id")
        title = parts[1].strip()
        description = parts[2].strip()
        deadline, deadline_err = _validate_deadline(parts[3].strip())
        if deadline_err:
            raise ValueError(deadline_err)
        priority = _to_int(parts[4], "priority")
        status = _normalize_status(parts[5])

        if not title:
            raise ValueError("Title cannot be empty.")

        with get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    INSERT INTO tasks (user_id, title, description, deadline, priority, status)
                    VALUES (%s, %s, %s, %s, %s, %s)
                    RETURNING id
                    """,
                    (user_id, title, description, deadline, priority, status),
                )
                new_id = cur.fetchone()[0]
            conn.commit()

        return {
            "messages": [
                AIMessage(content=f"Task added successfully for user {user_id} with id={new_id}.")
            ]
        }
    except Exception as e:
        return {"messages": [AIMessage(content=f"Error while adding task: {e}")]}


def update_task_in_db(state: AgentState) -> dict:
    """
    Internal command format:
      update_task: task_id,title,description,deadline,priority,status
    """
    text = _last_human_text(state)
    parts, err = _parse_csv_payload(text)
    if err:
        return {
            "messages": [
                AIMessage(
                    content='Invalid payload. Example:\nupdate_task: 12, "New Title", "New Desc", 2026-03-20, 2, in_progress'
                )
            ]
        }

    if len(parts) < 6:
        return {
            "messages": [
                AIMessage(content="Not enough fields for update_task. Need 6 values.")
            ]
        }

    try:
        task_id = _to_int(parts[0], "task_id")
        title = parts[1].strip()
        description = parts[2].strip()
        deadline, deadline_err = _validate_deadline(parts[3].strip())
        if deadline_err:
            raise ValueError(deadline_err)
        priority = _to_int(parts[4], "priority")
        status = _normalize_status(parts[5])

        if not title:
            raise ValueError("Title cannot be empty.")

        with get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    UPDATE tasks
                    SET title = %s,
                        description = %s,
                        deadline = %s,
                        priority = %s,
                        status = %s
                    WHERE id = %s
                    RETURNING id
                    """,
                    (title, description, deadline, priority, status, task_id),
                )
                row = cur.fetchone()
            conn.commit()

        if not row:
            return {"messages": [AIMessage(content=f"Task {task_id} not found.")]}

        return {"messages": [AIMessage(content=f"Task {task_id} updated successfully.")]}
    except Exception as e:
        return {"messages": [AIMessage(content=f"Error while updating task: {e}")]}


def delete_task_from_db(state: AgentState) -> dict:
    """
    Internal command format:
      delete_task: task_id
    """
    text = _last_human_text(state)

    try:
        task_id = _to_int(text.split(":", 1)[1].strip(), "task_id")

        with get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    DELETE FROM tasks
                    WHERE id = %s
                    RETURNING id
                    """,
                    (task_id,),
                )
                row = cur.fetchone()
            conn.commit()

        if not row:
            return {"messages": [AIMessage(content=f"Task {task_id} not found.")]}

        return {"messages": [AIMessage(content=f"Task {task_id} deleted successfully.")]}
    except Exception as e:
        return {"messages": [AIMessage(content=f"Error while deleting task: {e}")]}


# ----------------------------
# User nodes
# ----------------------------
def create_user_profile(state: AgentState) -> dict:
    """
    Internal command format:
      create_user: name,email,program
    """
    text = _last_human_text(state)
    parts, err = _parse_csv_payload(text)
    if err:
        return {
            "messages": [
                AIMessage(
                    content='Invalid payload. Example:\ncreate_user: "David", "david@example.com", "MSc Data Science"'
                )
            ]
        }

    if len(parts) < 3:
        return {
            "messages": [
                AIMessage(content="Not enough fields for create_user. Need 3 values.")
            ]
        }

    try:
        name = parts[0].strip()
        email = parts[1].strip()
        program = parts[2].strip()

        if not name:
            raise ValueError("Name cannot be empty.")
        if not email:
            raise ValueError("Email cannot be empty.")

        with get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    INSERT INTO user_profiles (name, email, academic_program)
                    VALUES (%s, %s, %s)
                    RETURNING id
                    """,
                    (name, email, program),
                )
                user_id = cur.fetchone()[0]
            conn.commit()

        return {
            "messages": [
                AIMessage(content=f"User created successfully with id={user_id}.")
            ]
        }
    except IntegrityError:
        return {"messages": [AIMessage(content="A user with that email already exists.")]}
    except Exception as e:
        return {"messages": [AIMessage(content=f"Error while creating user: {e}")]}


def get_user_profile(state: AgentState) -> dict:
    """
    Internal command format:
      get_user: user_id
    """
    text = _last_human_text(state)

    try:
        user_id = _to_int(text.split(":", 1)[1].strip(), "user_id")

        with get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    SELECT id, name, academic_program
                    FROM user_profiles
                    WHERE id = %s
                    """,
                    (user_id,),
                )
                row = cur.fetchone()

        if not row:
            return {"messages": [AIMessage(content=f"User {user_id} not found.")]}

        uid, name, academic_program = row
        return {
            "messages": [
                AIMessage(
                    content=(
                        f"User Profile\n"
                        f"------------\n"
                        f"id: {uid}\n"
                        f"name: {name}\n"
                        f"academic_program: {academic_program}"
                    )
                )
            ]
        }
    except Exception as e:
        return {"messages": [AIMessage(content=f"Error while fetching user: {e}")]}


def update_user_profile(state: AgentState) -> dict:
    """
    Internal command format:
      update_user: user_id,name,email,program
    """
    text = _last_human_text(state)
    parts, err = _parse_csv_payload(text)
    if err:
        return {
            "messages": [
                AIMessage(
                    content='Invalid payload. Example:\nupdate_user: 5, "David", "david@example.com", "MSc AI"'
                )
            ]
        }

    if len(parts) < 4:
        return {
            "messages": [
                AIMessage(content="Not enough fields for update_user. Need 4 values.")
            ]
        }

    try:
        user_id = _to_int(parts[0], "user_id")
        name = parts[1].strip()
        email = parts[2].strip()
        program = parts[3].strip()

        if not name:
            raise ValueError("Name cannot be empty.")
        if not email:
            raise ValueError("Email cannot be empty.")

        with get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    UPDATE user_profiles
                    SET name = %s,
                        academic_program = %s
                    WHERE id = %s
                    RETURNING id
                    """,
                    (name, program, user_id),
                )
                row = cur.fetchone()
            conn.commit()

        if not row:
            return {"messages": [AIMessage(content=f"User {user_id} not found.")]}

        return {"messages": [AIMessage(content=f"User {user_id} updated successfully.")]}
    except IntegrityError:
        return {"messages": [AIMessage(content="Another user already uses that email.")]}
    except Exception as e:
        return {"messages": [AIMessage(content=f"Error while updating user: {e}")]}


def delete_user_profile(state: AgentState) -> dict:
    """
    Internal command format:
      delete_user: user_id
    """
    text = _last_human_text(state)

    try:
        user_id = _to_int(text.split(":", 1)[1].strip(), "user_id")

        with get_connection() as conn:
            with conn.cursor() as cur:
                # Count tasks first for better feedback
                cur.execute("SELECT COUNT(*) FROM tasks WHERE user_id = %s", (user_id,))
                task_count = cur.fetchone()[0]

                cur.execute(
                    """
                    DELETE FROM user_profiles
                    WHERE id = %s
                    RETURNING id
                    """,
                    (user_id,),
                )
                row = cur.fetchone()
            conn.commit()

        if not row:
            return {"messages": [AIMessage(content=f"User {user_id} not found.")]}

        return {
            "messages": [
                AIMessage(
                    content=f"User {user_id} deleted successfully. {task_count} related task(s) were also removed."
                )
            ]
        }
    except Exception as e:
        return {"messages": [AIMessage(content=f"Error while deleting user: {e}")]}


def list_users(state: AgentState) -> dict:
    """
    Internal command format:
      list_users:
    """
    try:
        with get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    SELECT id, name, academic_program
                    FROM user_profiles
                    ORDER BY id ASC
                    """
                )
                rows = cur.fetchall()

        if not rows:
            return {"messages": [AIMessage(content="No users found.")]}

        lines = ["Users:"]
        for user_id, name, academic_program in rows:
            lines.append(
                f"- [{user_id}] {name} | academic_program={academic_program}"
            )

        return {"messages": [AIMessage(content="\n".join(lines))]}
    except Exception as e:
        return {"messages": [AIMessage(content=f"Error while listing users: {e}")]}


# ----------------------------
# Export / Import nodes
# ----------------------------
def export_tasks_to_csv(state: AgentState) -> dict:
    """
    Internal command format:
      export_tasks: user_id=5; filepath=tasks.csv; status=pending; search=report; sort=deadline; order=asc
    """
    params = _parse_kv_payload(_last_human_text(state))

    try:
        user_id = _to_int(params.get("user_id"), "user_id")
        filepath = params.get("filepath")
        if not filepath:
            raise ValueError("filepath is required.")

        rows = fetch_tasks(
            user_id=user_id,
            status=params.get("status"),
            search=params.get("search"),
            sort_by=params.get("sort", "deadline"),
            order=params.get("order", "asc"),
        )

        path = Path(filepath).expanduser().resolve()
        path.parent.mkdir(parents=True, exist_ok=True)

        with path.open("w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerow(
                ["id", "user_id", "title", "description", "deadline", "priority", "status", "created_at"]
            )
            for task_id, title, description, deadline, priority, status, created_at in rows:
                writer.writerow(
                    [task_id, user_id, title, description, deadline, priority, status, created_at]
                )

        return {
            "messages": [
                AIMessage(content=f"Exported {len(rows)} task(s) to {path}")
            ]
        }
    except Exception as e:
        return {"messages": [AIMessage(content=f"Error while exporting tasks: {e}")]}


def import_tasks_from_csv(state: AgentState) -> dict:
    """
    Internal command format:
      import_tasks: user_id=5; filepath=tasks.csv
    """
    params = _parse_kv_payload(_last_human_text(state))

    try:
        user_id = _to_int(params.get("user_id"), "user_id")
        filepath = params.get("filepath")
        if not filepath:
            raise ValueError("filepath is required.")

        path = Path(filepath).expanduser().resolve()
        if not path.exists():
            raise FileNotFoundError(f"File not found: {path}")

        imported = 0
        skipped = 0
        errors: list[str] = []

        with path.open("r", newline="", encoding="utf-8") as f:
            reader = csv.DictReader(f)

            required_columns = {"title", "description", "deadline", "priority", "status"}
            missing_cols = required_columns - set(reader.fieldnames or [])
            if missing_cols:
                raise ValueError(
                    f"CSV is missing required columns: {', '.join(sorted(missing_cols))}"
                )

            with get_connection() as conn:
                with conn.cursor() as cur:
                    for idx, row in enumerate(reader, start=2):
                        try:
                            title = (row.get("title") or "").strip()
                            description = (row.get("description") or "").strip()
                            deadline_raw = (row.get("deadline") or "").strip()
                            priority_raw = (row.get("priority") or "").strip()
                            status_raw = (row.get("status") or "").strip()

                            if not title:
                                raise ValueError("title is empty")

                            deadline, deadline_err = _validate_deadline(deadline_raw)
                            if deadline_err and deadline_raw:
                                raise ValueError(deadline_err)

                            priority = _to_int(priority_raw or "3", "priority")
                            status = _normalize_status(status_raw or "pending")

                            cur.execute(
                                """
                                INSERT INTO tasks (user_id, title, description, deadline, priority, status)
                                VALUES (%s, %s, %s, %s, %s, %s)
                                """,
                                (user_id, title, description, deadline, priority, status),
                            )
                            imported += 1
                        except Exception as row_err:
                            skipped += 1
                            errors.append(f"Row {idx}: {row_err}")

                conn.commit()

        summary = [f"Imported {imported} task(s) for user {user_id}. Skipped {skipped} row(s)."]
        if errors:
            summary.append("Import issues:")
            summary.extend(f"- {err}" for err in errors[:10])  # show first 10 only

        return {"messages": [AIMessage(content="\n".join(summary))]}
    except Exception as e:
        return {"messages": [AIMessage(content=f"Error while importing tasks: {e}")]}


# ----------------------------
# Reminder node
# ----------------------------
def send_reminders(state: AgentState) -> dict:
    """
    Internal command format:
      reminders: user_id=5; days=3; send_email=true
    """
    params = _parse_kv_payload(_last_human_text(state))

    try:
        user_id = _to_int(params.get("user_id"), "user_id")
        days = _to_int(params.get("days", "3"), "days")
        send_email = _parse_bool(params.get("send_email"))

        today = date.today()
        cutoff = today + timedelta(days=days)

        with get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    SELECT title, deadline, priority, status
                    FROM tasks
                    WHERE user_id = %s
                      AND deadline IS NOT NULL
                      AND deadline BETWEEN %s AND %s
                      AND LOWER(status) NOT IN ('done', 'completed')
                    ORDER BY deadline ASC, priority DESC
                    """,
                    (user_id, today.isoformat(), cutoff.isoformat()),
                )
                rows = cur.fetchall()

                cur.execute(
                    """
                    SELECT name, email
                    FROM user_profiles
                    WHERE id = %s
                    """,
                    (user_id,),
                )
                user_row = cur.fetchone()

        if not user_row:
            return {"messages": [AIMessage(content=f"User {user_id} not found.")]}

        name, email = user_row

        if not rows:
            return {
                "messages": [
                    AIMessage(
                        content=f"No upcoming incomplete tasks due in the next {days} day(s) for user {user_id}."
                    )
                ]
            }

        lines = [
            f"Upcoming tasks for {name} (user {user_id}) due in the next {days} day(s):"
        ]
        for title, deadline, priority, status in rows:
            lines.append(f"- {title} | due={deadline} | priority={priority} | status={status}")

        summary = "\n".join(lines)

        if send_email:
            if email:
                subject = f"Academic Task Reminder - next {days} day(s)"
                ok, message = send_email_notification(email, subject, summary)
                summary += f"\n\nEmail status: {message}"
            else:
                summary += "\n\nEmail status: No email address found for user."

        return {"messages": [AIMessage(content=summary)]}
    except Exception as e:
        return {"messages": [AIMessage(content=f"Error while generating reminders: {e}")]}


# ----------------------------
# Build graph
# ----------------------------
def build_graph():
    builder = StateGraph(AgentState)

    builder.add_node("help", help_node)
    builder.add_node("show_tasks", get_user_tasks)
    builder.add_node("add_task", add_task_to_db)
    builder.add_node("update_task", update_task_in_db)
    builder.add_node("delete_task", delete_task_from_db)
    builder.add_node("create_user", create_user_profile)
    builder.add_node("get_user", get_user_profile)
    builder.add_node("update_user", update_user_profile)
    builder.add_node("delete_user", delete_user_profile)
    builder.add_node("list_users", list_users)
    builder.add_node("export_tasks", export_tasks_to_csv)
    builder.add_node("import_tasks", import_tasks_from_csv)
    builder.add_node("reminders", send_reminders)

    builder.add_conditional_edges(
        START,
        route,
        {
            "help": "help",
            "show_tasks": "show_tasks",
            "add_task": "add_task",
            "update_task": "update_task",
            "delete_task": "delete_task",
            "create_user": "create_user",
            "get_user": "get_user",
            "update_user": "update_user",
            "delete_user": "delete_user",
            "list_users": "list_users",
            "export_tasks": "export_tasks",
            "import_tasks": "import_tasks",
            "reminders": "reminders",
        },
    )

    # Each graph invocation should end after one routed command
    builder.add_edge("help", END)
    builder.add_edge("show_tasks", END)
    builder.add_edge("add_task", END)
    builder.add_edge("update_task", END)
    builder.add_edge("delete_task", END)
    builder.add_edge("create_user", END)
    builder.add_edge("get_user", END)
    builder.add_edge("update_user", END)
    builder.add_edge("delete_user", END)
    builder.add_edge("list_users", END)
    builder.add_edge("export_tasks", END)
    builder.add_edge("import_tasks", END)
    builder.add_edge("reminders", END)

    return builder.compile()


graph = build_graph()


def agent_workflow(command_text: str):
    """Run a single graph invocation for one command."""
    return graph.invoke({"messages": [HumanMessage(content=command_text)]})


# ----------------------------
# CLI helpers
# ----------------------------
def resolve_user_id(
    maybe_user_id: Optional[str],
    current_user_id: Optional[int],
    command_name: str,
) -> int:
    """
    Resolve a user id from:
    1) explicit command arg, else
    2) current_user_id from `use`, else
    3) raise a helpful error
    """
    if maybe_user_id:
        return _to_int(maybe_user_id, "user_id")

    if current_user_id is not None:
        return current_user_id

    raise ValueError(
        f"{command_name} requires a user_id, or first run: use <user_id>"
    )


def print_result(result: dict) -> None:
    """Print the last AIMessage content from a graph result."""
    try:
        print(result["messages"][-1].content)
    except Exception:
        print("Unexpected result format.")
        print(result)


# ----------------------------
# CLI runner
# ----------------------------
if __name__ == "__main__":
    # Make sure schema exists before users start typing commands.
    ensure_schema()

    current_user_id: Optional[int] = None

    print("\nAcademic Task Agent (Interactive Mode)")
    print("Type 'help' for commands. Type 'exit' to quit.\n")

    while True:
        try:
            raw = input("Command> ").strip()
            if not raw:
                continue

            tokens = shlex.split(raw)
            command = tokens[0].lower()

            if command == "exit":
                print("Goodbye!")
                break

            if command == "help":
                print_result(agent_workflow("help"))
                continue

            if command == "whoami":
                if current_user_id is None:
                    print("No current user selected. Use: use <user_id>")
                else:
                    print(f"Current user: {current_user_id}")
                continue

            if command == "use":
                if len(tokens) != 2:
                    print("Usage: use <user_id>")
                    continue

                user_id = _to_int(tokens[1], "user_id")
                result = agent_workflow(f"get_user: {user_id}")
                content = result["messages"][-1].content
                print(content)
                if "not found" not in content.lower():
                    current_user_id = user_id
                continue

            if command == "show":
                positionals, options = _split_positionals_and_options(tokens[1:])
                explicit_user_id = positionals[0] if positionals else None
                user_id = resolve_user_id(explicit_user_id, current_user_id, "show")

                internal = _build_kv_command(
                    "show_tasks",
                    user_id=user_id,
                    status=options.get("status"),
                    search=options.get("search"),
                    sort=options.get("sort", "deadline"),
                    order="desc" if options.get("desc") else "asc",
                )
                print_result(agent_workflow(internal))
                continue

            if command == "add":
                positionals, _options = _split_positionals_and_options(tokens[1:])
                explicit_user_id = positionals[0] if positionals else None
                user_id = resolve_user_id(explicit_user_id, current_user_id, "add")

                print("Enter task details:")
                title = input("  Title: ").strip()
                description = input("  Description: ").strip()
                deadline = input("  Deadline (YYYY-MM-DD): ").strip()
                priority = input("  Priority (number): ").strip()
                status = input("  Status: ").strip()

                output = io.StringIO()
                writer = csv.writer(output)
                writer.writerow([user_id, title, description, deadline, priority, status])
                payload = output.getvalue().strip()

                print_result(agent_workflow(f"add_task: {payload}"))
                continue

            if command == "update":
                if len(tokens) != 2:
                    print("Usage: update <task_id>")
                    continue

                task_id = _to_int(tokens[1], "task_id")

                print("Enter updated task details:")
                title = input("  New Title: ").strip()
                description = input("  New Description: ").strip()
                deadline = input("  New Deadline (YYYY-MM-DD): ").strip()
                priority = input("  New Priority (number): ").strip()
                status = input("  New Status: ").strip()

                output = io.StringIO()
                writer = csv.writer(output)
                writer.writerow([task_id, title, description, deadline, priority, status])
                payload = output.getvalue().strip()

                print_result(agent_workflow(f"update_task: {payload}"))
                continue

            if command == "delete":
                if len(tokens) != 2:
                    print("Usage: delete <task_id>")
                    continue

                task_id = _to_int(tokens[1], "task_id")
                confirm = input(f"Are you sure you want to delete task {task_id}? (y/n): ").strip().lower()
                if confirm != "y":
                    print("Delete cancelled.")
                    continue

                print_result(agent_workflow(f"delete_task: {task_id}"))
                continue

            if command == "user":
                if len(tokens) < 2:
                    print("Usage: user <create|show|update|delete|list> ...")
                    continue

                sub = tokens[1].lower()

                if sub == "create":
                    print("Enter user details:")
                    name = input("  Name: ").strip()
                    email = input("  Email: ").strip()
                    program = input("  Program: ").strip()

                    output = io.StringIO()
                    writer = csv.writer(output)
                    writer.writerow([name, email, program])
                    payload = output.getvalue().strip()

                    result = agent_workflow(f"create_user: {payload}")
                    print_result(result)
                    continue

                if sub == "show":
                    if len(tokens) != 3:
                        print("Usage: user show <user_id>")
                        continue

                    user_id = _to_int(tokens[2], "user_id")
                    print_result(agent_workflow(f"get_user: {user_id}"))
                    continue

                if sub == "update":
                    if len(tokens) != 3:
                        print("Usage: user update <user_id>")
                        continue

                    user_id = _to_int(tokens[2], "user_id")
                    print("Enter updated user details:")
                    name = input("  New Name: ").strip()
                    email = input("  New Email: ").strip()
                    program = input("  New Program: ").strip()

                    output = io.StringIO()
                    writer = csv.writer(output)
                    writer.writerow([user_id, name, email, program])
                    payload = output.getvalue().strip()

                    result = agent_workflow(f"update_user: {payload}")
                    print_result(result)
                    continue

                if sub == "delete":
                    if len(tokens) != 3:
                        print("Usage: user delete <user_id>")
                        continue

                    user_id = _to_int(tokens[2], "user_id")
                    confirm = input(
                        f"Are you sure you want to delete user {user_id} and their tasks? (y/n): "
                    ).strip().lower()
                    if confirm != "y":
                        print("Delete cancelled.")
                        continue

                    result = agent_workflow(f"delete_user: {user_id}")
                    print_result(result)

                    if current_user_id == user_id:
                        current_user_id = None
                    continue

                if sub == "list":
                    print_result(agent_workflow("list_users:"))
                    continue

                print("Unknown user command. Use: user <create|show|update|delete|list>")
                continue

            if command == "export":
                positionals, options = _split_positionals_and_options(tokens[1:])
                if not positionals:
                    print("Usage: export [user_id] <filepath> [--status STATUS] [--search KEYWORD] [--sort deadline|priority|created_at] [--desc]")
                    continue

                if len(positionals) == 1:
                    user_id = resolve_user_id(None, current_user_id, "export")
                    filepath = positionals[0]
                else:
                    user_id = resolve_user_id(positionals[0], current_user_id, "export")
                    filepath = positionals[1]

                internal = _build_kv_command(
                    "export_tasks",
                    user_id=user_id,
                    filepath=filepath,
                    status=options.get("status"),
                    search=options.get("search"),
                    sort=options.get("sort", "deadline"),
                    order="desc" if options.get("desc") else "asc",
                )
                print_result(agent_workflow(internal))
                continue

            if command == "import":
                positionals, _options = _split_positionals_and_options(tokens[1:])
                if not positionals:
                    print("Usage: import [user_id] <filepath>")
                    continue

                if len(positionals) == 1:
                    user_id = resolve_user_id(None, current_user_id, "import")
                    filepath = positionals[0]
                else:
                    user_id = resolve_user_id(positionals[0], current_user_id, "import")
                    filepath = positionals[1]

                internal = _build_kv_command(
                    "import_tasks",
                    user_id=user_id,
                    filepath=filepath,
                )
                print_result(agent_workflow(internal))
                continue

            if command == "remind":
                positionals, options = _split_positionals_and_options(tokens[1:])
                explicit_user_id = positionals[0] if positionals else None
                user_id = resolve_user_id(explicit_user_id, current_user_id, "remind")

                internal = _build_kv_command(
                    "reminders",
                    user_id=user_id,
                    days=options.get("days", "3"),
                    send_email=bool(options.get("send-email")),
                )
                print_result(agent_workflow(internal))
                continue

            print("Unknown command. Type 'help' for a list of commands.")

        except KeyboardInterrupt:
            print("\nInterrupted. Type 'exit' to quit.")
        except Exception as e:
            print(f"Error: {e}")
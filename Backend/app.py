from flask import Flask, request, jsonify, g
from flask_cors import CORS
import os
import re
import sys
import hashlib
import secrets
from functools import wraps
from datetime import datetime, timedelta, timezone
from dotenv import load_dotenv
from werkzeug.security import generate_password_hash, check_password_hash

load_dotenv()

from langgraph_agent import agent_workflow

app = Flask(__name__)
# Allow CORS from any origin for deployment flexibility
CORS(app, origins=os.getenv('CORS_ORIGINS', '*').split(','))

# Validation helpers
VALID_EMAIL_DOMAINS = [
    'gmail.com', 'yahoo.com', 'outlook.com', 'hotmail.com', 'icloud.com',
    'mail.com', 'protonmail.com', 'aol.com', 'zoho.com', 'yandex.com',
    'gmx.com', 'live.com', 'msn.com'
]

def validate_email(email):
    """Validate email format and domain"""
    if not email:
        return False, "Email is required"
    
    # Basic email format check
    email_pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    if not re.match(email_pattern, email):
        return False, "Invalid email format"
    
    domain = email.split('@')[1].lower()
    
    # Check if domain is in allowed list or is an educational domain
    is_valid = (
        domain in VALID_EMAIL_DOMAINS or
        domain.endswith('.edu') or
        domain.endswith('.ac.uk') or
        domain.endswith('.edu.ng') or
        any(domain.endswith(f'.{d}') for d in VALID_EMAIL_DOMAINS)
    )
    
    if not is_valid:
        return False, f"Please use a valid email provider (gmail.com, yahoo.com, outlook.com, or educational domains)"
    
    return True, None

def validate_name(name):
    """Validate full name format: FirstName LastName"""
    if not name:
        return False, "Name is required"
    
    name = name.strip()
    
    if len(name) < 5:
        return False, "Full name must be at least 5 characters"
    
    if len(name) > 100:
        return False, "Full name must be less than 100 characters"
    
    parts = name.split()
    if len(parts) < 2:
        return False, "Please enter full name as 'FirstName LastName'"
    
    # Each name part should start with uppercase and be at least 2 characters
    for part in parts:
        if len(part) < 2:
            return False, "Each name part must be at least 2 characters"
        if not part[0].isupper():
            return False, "Each name should start with an uppercase letter"
        if not part.isalpha():
            return False, "Name should contain only letters"
    
    return True, None

def validate_task(data):
    """Validate task data"""
    errors = {}
    
    if not data.get('title'):
        errors['title'] = "Task title is required"
    elif len(data['title']) < 3:
        errors['title'] = "Task title must be at least 3 characters"
    elif len(data['title']) > 200:
        errors['title'] = "Task title must be less than 200 characters"
    
    if data.get('description') and len(data['description']) > 1000:
        errors['description'] = "Description must be less than 1000 characters"
    
    if data.get('deadline'):
        try:
            from datetime import datetime
            deadline = datetime.strptime(data['deadline'], '%Y-%m-%d')
            if deadline.date() < datetime.now().date():
                errors['deadline'] = "Deadline must be today or a future date"
        except ValueError:
            errors['deadline'] = "Invalid date format"
    
    valid_priorities = ['low', 'medium', 'high', '1', '2', '3', '4', '5', 1, 2, 3, 4, 5]
    if data.get('priority') and data['priority'] not in valid_priorities:
        errors['priority'] = "Priority must be low, medium, high, or 1-5"
    
    valid_statuses = ['pending', 'in_progress', 'completed', 'done']
    if data.get('status') and data['status'] not in valid_statuses:
        errors['status'] = "Status must be pending, in_progress, or completed"
    
    return len(errors) == 0, errors

# Priority mapping helpers
def priority_int_to_string(priority_int):
    """Convert integer priority to string label"""
    if priority_int <= 2:
        return 'high'
    elif priority_int <= 3:
        return 'medium'
    else:
        return 'low'

def priority_string_to_int(priority_str):
    """Convert string priority to integer"""
    priority_map = {'high': 1, 'medium': 3, 'low': 5}
    return priority_map.get(priority_str.lower(), 3)


SESSION_TTL_HOURS = int(os.getenv('SESSION_TTL_HOURS', '12'))


def _coerce_expiry(expires_at):
    """Normalize timezone-aware timestamps to naive UTC for comparison."""
    if hasattr(expires_at, 'tzinfo') and expires_at.tzinfo is not None:
        return expires_at.replace(tzinfo=None)
    return expires_at


def _ensure_session_table(cur):
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
        )
        """
    )
    cur.execute("CREATE INDEX IF NOT EXISTS idx_user_sessions_user_id ON user_sessions(user_id)")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_user_sessions_expires_at ON user_sessions(expires_at)")


def _hash_token(token):
    return hashlib.sha256(token.encode('utf-8')).hexdigest()


def _create_session(cur, user_id):
    _ensure_session_table(cur)
    raw_token = secrets.token_urlsafe(48)
    token_hash = _hash_token(raw_token)
    expires_at = datetime.utcnow() + timedelta(hours=SESSION_TTL_HOURS)
    cur.execute(
        """
        INSERT INTO user_sessions (user_id, token_hash, expires_at)
        VALUES (%s, %s, %s)
        """,
        (user_id, token_hash, expires_at),
    )
    return raw_token, expires_at


def _get_bearer_token():
    auth_header = request.headers.get('Authorization', '').strip()
    if not auth_header.startswith('Bearer '):
        return None
    token = auth_header.split(' ', 1)[1].strip()
    return token or None


def _get_user_from_token(token):
    from db_ops import get_connection

    conn = get_connection()
    cur = conn.cursor()
    try:
        _ensure_session_table(cur)
        token_hash = _hash_token(token)
        cur.execute(
            """
            SELECT us.user_id, us.expires_at, up.name, up.email, up.academic_program
            FROM user_sessions us
            JOIN user_profiles up ON up.id = us.user_id
            WHERE us.token_hash = %s AND us.revoked = FALSE
            """,
            (token_hash,),
        )
        row = cur.fetchone()
        if not row:
            return None, 'Invalid session token'

        expires_at = _coerce_expiry(row[1])
        if expires_at <= datetime.utcnow():
            cur.execute(
                "UPDATE user_sessions SET revoked = TRUE, revoked_at = CURRENT_TIMESTAMP WHERE token_hash = %s",
                (token_hash,),
            )
            conn.commit()
            return None, 'Session expired. Please login again.'

        return (
            {
                'id': row[0],
                'name': row[2],
                'email': row[3],
                'program': row[4],
                'expires_at': row[1].isoformat() if hasattr(row[1], 'isoformat') else str(row[1]),
            },
            None,
        )
    finally:
        cur.close()
        conn.close()


def _revoke_token(token):
    from db_ops import get_connection

    conn = get_connection()
    cur = conn.cursor()
    try:
        _ensure_session_table(cur)
        cur.execute(
            """
            UPDATE user_sessions
            SET revoked = TRUE, revoked_at = CURRENT_TIMESTAMP
            WHERE token_hash = %s AND revoked = FALSE
            RETURNING id
            """,
            (_hash_token(token),),
        )
        revoked = cur.fetchone()
        conn.commit()
        return bool(revoked)
    finally:
        cur.close()
        conn.close()


def require_auth(route_handler):
    """Require a valid bearer token and attach user to Flask global context."""

    @wraps(route_handler)
    def wrapped(*args, **kwargs):
        token = _get_bearer_token()
        if not token:
            return jsonify({'error': 'Authorization token is required'}), 401

        user, error = _get_user_from_token(token)
        if error:
            return jsonify({'error': error}), 401

        g.auth_token = token
        g.auth_user = user
        return route_handler(*args, **kwargs)

    return wrapped


def _trigger_adaptation(user_id, trigger):
    """
    Best-effort adaptation trigger.
    Task mutations should remain successful even if adaptation fails.
    """
    try:
        from langgraph_agent import adapt_schedule_to_changes

        return adapt_schedule_to_changes(user_id, trigger=trigger)
    except Exception as exc:
        return {'success': False, 'error': str(exc)}


def _database_health():
    from db_ops import get_connection

    conn = None
    cur = None
    try:
        conn = get_connection()
        cur = conn.cursor()
        cur.execute("SELECT 1")
        cur.fetchone()
        return {'status': 'ok'}, None
    except Exception as exc:
        return {'status': 'error', 'detail': str(exc)}, exc
    finally:
        if cur:
            cur.close()
        if conn:
            conn.close()


@app.route('/health', methods=['GET'])
@app.route('/api/health', methods=['GET'])
def health_check():
    """Lightweight deployment health check with a database probe."""
    database, error = _database_health()
    status_code = 200 if error is None else 503
    return jsonify(
        {
            'status': 'ok' if error is None else 'degraded',
            'database': database,
            'python_version': f'{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}',
            'timestamp': datetime.now(timezone.utc).isoformat(),
        }
    ), status_code

@app.route('/api/tasks', methods=['GET'])
@require_auth
def get_tasks():
    """Get tasks with optional filtering and sorting controls."""
    user_id = g.auth_user['id']

    status_filter = request.args.get('status', '').strip()
    priority_filter = request.args.get('priority', '').strip()
    deadline_from = request.args.get('deadline_from', '').strip()
    deadline_to = request.args.get('deadline_to', '').strip()
    search = request.args.get('search', '').strip().lower()
    sort_by = request.args.get('sort_by', 'deadline').strip().lower()
    sort_order = request.args.get('sort_order', 'asc').strip().lower()

    try:
        from db_ops import get_connection

        conn = get_connection()
        cur = conn.cursor()

        where_clauses = ["user_id = %s", "(deleted = FALSE OR deleted IS NULL)"]
        values = [user_id]

        if status_filter:
            statuses = [s.strip() for s in status_filter.split(',') if s.strip()]
            if statuses:
                placeholders = ','.join(['%s'] * len(statuses))
                where_clauses.append(f"status IN ({placeholders})")
                values.extend(statuses)

        if priority_filter:
            priorities = []
            for item in [p.strip().lower() for p in priority_filter.split(',') if p.strip()]:
                if item.isdigit():
                    priorities.append(int(item))
                elif item in ('high', 'medium', 'low'):
                    priorities.append(priority_string_to_int(item))
            if priorities:
                placeholders = ','.join(['%s'] * len(priorities))
                where_clauses.append(f"priority IN ({placeholders})")
                values.extend(priorities)

        if deadline_from:
            where_clauses.append("deadline >= %s")
            values.append(deadline_from)

        if deadline_to:
            where_clauses.append("deadline <= %s")
            values.append(deadline_to)

        if search:
            where_clauses.append("(LOWER(title) LIKE %s OR LOWER(COALESCE(description, '')) LIKE %s)")
            search_pattern = f"%{search}%"
            values.extend([search_pattern, search_pattern])

        sort_columns = {
            'deadline': 'deadline',
            'priority': 'priority',
            'created_at': 'created_at',
            'title': 'LOWER(title)',
            'status': 'status',
        }
        if sort_by not in sort_columns:
            sort_by = 'deadline'
        if sort_order not in ('asc', 'desc'):
            sort_order = 'asc'

        if sort_by == 'deadline':
            order_by = f"deadline {sort_order.upper()} NULLS LAST, priority ASC, created_at DESC"
        else:
            order_by = f"{sort_columns[sort_by]} {sort_order.upper()}, created_at DESC"

        query = f"""
            SELECT id, title, description, deadline, priority, status, created_at
            FROM tasks
            WHERE {' AND '.join(where_clauses)}
            ORDER BY {order_by}
        """
        cur.execute(query, values)
        rows = cur.fetchall()
        cur.close()
        conn.close()

        tasks = []
        for row in rows:
            deadline = row[3]
            if deadline:
                deadline = deadline.strftime('%Y-%m-%d') if hasattr(deadline, 'strftime') else str(deadline).split(' ')[0]

            priority_int = row[4] if row[4] else 3
            priority_str = priority_int_to_string(priority_int)

            tasks.append(
                {
                    'id': row[0],
                    'title': row[1],
                    'description': row[2] or '',
                    'deadline': deadline,
                    'priority': priority_str,
                    'status': row[5] or 'pending',
                    'created_at': row[6].isoformat() if row[6] else None,
                }
            )

        return jsonify(tasks)
    except Exception as e:
        return jsonify({'error': f'Error fetching tasks: {str(e)}'}), 500

@app.route('/api/tasks', methods=['POST'])
@require_auth
def add_task():
    data = request.json or {}
    data['user_id'] = g.auth_user['id']

    # Validate task data
    is_valid, errors = validate_task(data)
    if not is_valid:
        return jsonify({'error': 'Validation failed', 'errors': errors}), 400

    # Convert string priority to integer
    priority = data.get('priority', 'medium')
    if isinstance(priority, str):
        priority = priority_string_to_int(priority)

    payload = f"add_task: {data['user_id']}, \"{data['title']}\", \"{data.get('description', '')}\", {data.get('deadline', '')}, {priority}, {data.get('status', 'pending')}"
    result = agent_workflow(payload)
    adaptation = _trigger_adaptation(data['user_id'], 'task_created')
    return jsonify(
        {
            'message': result['messages'][-1].content,
            'adaptation_triggered': adaptation.get('success', False),
        }
    )

@app.route('/api/tasks/<int:task_id>', methods=['PUT'])
@require_auth
def update_task(task_id):
    """Update an existing task"""
    data = request.json or {}

    if not data:
        return jsonify({'error': 'No data provided'}), 400

    try:
        from db_ops import get_connection

        conn = get_connection()
        cur = conn.cursor()

        # Build dynamic update query based on provided fields
        update_fields = []
        values = []

        if 'title' in data:
            update_fields.append('title = %s')
            values.append(data['title'])

        if 'description' in data:
            update_fields.append('description = %s')
            values.append(data['description'])

        if 'deadline' in data:
            update_fields.append('deadline = %s')
            values.append(data['deadline'] if data['deadline'] else None)

        if 'priority' in data:
            priority = data['priority']
            if isinstance(priority, str):
                priority = priority_string_to_int(priority)
            update_fields.append('priority = %s')
            values.append(priority)

        if 'status' in data:
            update_fields.append('status = %s')
            values.append(data['status'])

        if not update_fields:
            return jsonify({'error': 'No valid fields to update'}), 400

        values.extend([task_id, g.auth_user['id']])
        query = f"""
            UPDATE tasks
            SET {', '.join(update_fields)}
            WHERE id = %s AND user_id = %s AND (deleted = FALSE OR deleted IS NULL)
            RETURNING id
        """

        cur.execute(query, values)
        result = cur.fetchone()
        conn.commit()
        cur.close()
        conn.close()

        if result:
            adaptation = _trigger_adaptation(g.auth_user['id'], 'task_updated')
            return jsonify(
                {
                    'message': 'Task updated successfully',
                    'id': result[0],
                    'adaptation_triggered': adaptation.get('success', False),
                }
            )
        return jsonify({'error': 'Task not found'}), 404
    except Exception as e:
        return jsonify({'error': f'Error updating task: {str(e)}'}), 500

@app.route('/api/users', methods=['GET'])
def get_users():
	result = agent_workflow("list_users:")
	lines = result['messages'][-1].content.split('\n')
	users = []
	for line in lines:
		if line.startswith('-'):
			match = __import__('re').match(r"- \[(\d+)\] (.+?) \|", line)
			if match:
				users.append({
					'id': int(match.group(1)),
					'name': match.group(2)
				})
	return jsonify(users)

@app.route('/api/users/login', methods=['POST'])
def login_user():
    """Login by email and password and return an expiring bearer token."""
    data = request.json or {}
    email = data.get('email', '').strip().lower()
    password = data.get('password', '')

    if not email:
        return jsonify({'error': 'Email is required'}), 400
    if not password:
        return jsonify({'error': 'Password is required'}), 400

    # Validate email format
    email_valid, email_error = validate_email(email)
    if not email_valid:
        return jsonify({'error': email_error}), 400

    # Get user and verify password
    try:
        from db_ops import get_connection

        conn = get_connection()
        cur = conn.cursor()
        cur.execute(
            "SELECT id, name, email, academic_program, password_hash FROM user_profiles WHERE LOWER(email) = %s",
            (email,),
        )
        user = cur.fetchone()

        if not user:
            cur.close()
            conn.close()
            return jsonify({'error': 'Account not found. Please create an account first.'}), 404

        # Verify password
        if not user[4] or not check_password_hash(user[4], password):
            cur.close()
            conn.close()
            return jsonify({'error': 'Invalid password'}), 401

        token, expires_at = _create_session(cur, user[0])
        conn.commit()
        cur.close()
        conn.close()

        return jsonify(
            {
                'user': {
                    'id': user[0],
                    'name': user[1],
                    'email': user[2],
                    'program': user[3],
                },
                'token': token,
                'expires_at': expires_at.isoformat(),
            }
        )
    except Exception as e:
        return jsonify({'error': f'Error logging in: {str(e)}'}), 500

@app.route('/api/users', methods=['POST'])
def create_user():
    data = request.json or {}

    # Validate name
    name_valid, name_error = validate_name(data.get('name', ''))
    if not name_valid:
        return jsonify({'error': name_error}), 400

    # Validate email
    email_valid, email_error = validate_email(data.get('email', ''))
    if not email_valid:
        return jsonify({'error': email_error}), 400

    # Validate password
    password = data.get('password', '')
    if not password or len(password) < 6:
        return jsonify({'error': 'Password must be at least 6 characters'}), 400

    # Format name properly (capitalize each word)
    formatted_name = ' '.join(word.capitalize() for word in data['name'].strip().split())
    email = data['email'].strip().lower()
    program = data.get('program', '')
    password_hash = generate_password_hash(password)

    # Check if user already exists
    try:
        from db_ops import get_connection

        conn = get_connection()
        cur = conn.cursor()
        cur.execute("SELECT id FROM user_profiles WHERE LOWER(email) = %s", (email,))
        existing = cur.fetchone()
        if existing:
            cur.close()
            conn.close()
            return jsonify({'error': 'An account with this email already exists. Please login instead.'}), 400

        # Insert user directly with password hash
        cur.execute(
            """
            INSERT INTO user_profiles (name, email, academic_program, password_hash)
            VALUES (%s, %s, %s, %s)
            RETURNING id, name, email, academic_program
            """,
            (formatted_name, email, program, password_hash),
        )
        user = cur.fetchone()
        token = None
        expires_at = None
        if user:
            token, expires_at = _create_session(cur, user[0])

        conn.commit()
        cur.close()
        conn.close()

        if user:
            return jsonify(
                {
                    'message': 'Account created successfully!',
                    'user': {'id': user[0], 'name': user[1], 'email': user[2], 'program': user[3]},
                    'token': token,
                    'expires_at': expires_at.isoformat() if expires_at else None,
                }
            )
    except Exception as e:
        return jsonify({'error': f'Error creating account: {str(e)}'}), 500

    return jsonify({'error': 'Failed to create account'}), 500


@app.route('/api/users/session', methods=['GET'])
@require_auth
def get_session_status():
    """Validate current token and return authenticated user/session metadata."""
    return jsonify({'user': g.auth_user, 'expires_at': g.auth_user.get('expires_at')})


@app.route('/api/users/logout', methods=['POST'])
@require_auth
def logout_user():
    token = getattr(g, 'auth_token', None)
    if not token:
        return jsonify({'error': 'No active token found'}), 400

    revoked = _revoke_token(token)
    return jsonify({'message': 'Logged out successfully', 'revoked': revoked})

@app.route('/api/tasks/<int:task_id>', methods=['DELETE'])
@require_auth
def delete_task(task_id):
    """Soft delete - marks task as deleted without removing from database."""
    try:
        from db_ops import get_connection

        conn = get_connection()
        cur = conn.cursor()
        cur.execute(
            """
            UPDATE tasks
            SET deleted = TRUE
            WHERE id = %s AND user_id = %s AND (deleted = FALSE OR deleted IS NULL)
            RETURNING id, title
            """,
            (task_id, g.auth_user['id']),
        )
        result = cur.fetchone()
        conn.commit()
        cur.close()
        conn.close()

        if result:
            adaptation = _trigger_adaptation(g.auth_user['id'], 'task_deleted')
            return jsonify(
                {
                    'message': f'Task "{result[1]}" removed successfully',
                    'id': result[0],
                    'adaptation_triggered': adaptation.get('success', False),
                }
            )
        return jsonify({'error': 'Task not found'}), 404
    except Exception as e:
        return jsonify({'error': f'Error deleting task: {str(e)}'}), 500


@app.route('/api/tasks/deleted', methods=['GET'])
@require_auth
def get_deleted_tasks():
    """List deleted tasks so users can recover them."""
    try:
        from db_ops import get_connection

        conn = get_connection()
        cur = conn.cursor()
        cur.execute(
            """
            SELECT id, title, description, deadline, priority, status, created_at
            FROM tasks
            WHERE user_id = %s AND deleted = TRUE
            ORDER BY created_at DESC
            """,
            (g.auth_user['id'],),
        )
        rows = cur.fetchall()
        cur.close()
        conn.close()

        deleted_tasks = []
        for row in rows:
            deadline = row[3]
            if deadline:
                deadline = deadline.strftime('%Y-%m-%d') if hasattr(deadline, 'strftime') else str(deadline).split(' ')[0]
            priority_int = row[4] if row[4] else 3
            deleted_tasks.append(
                {
                    'id': row[0],
                    'title': row[1],
                    'description': row[2] or '',
                    'deadline': deadline,
                    'priority': priority_int_to_string(priority_int),
                    'status': row[5] or 'pending',
                    'created_at': row[6].isoformat() if row[6] else None,
                }
            )
        return jsonify(deleted_tasks)
    except Exception as e:
        return jsonify({'error': f'Error fetching deleted tasks: {str(e)}'}), 500


@app.route('/api/tasks/<int:task_id>/restore', methods=['POST'])
@require_auth
def restore_deleted_task(task_id):
    """Restore a previously soft-deleted task."""
    try:
        from db_ops import get_connection

        conn = get_connection()
        cur = conn.cursor()
        cur.execute(
            """
            UPDATE tasks
            SET deleted = FALSE
            WHERE id = %s AND user_id = %s AND deleted = TRUE
            RETURNING id, title
            """,
            (task_id, g.auth_user['id']),
        )
        result = cur.fetchone()
        conn.commit()
        cur.close()
        conn.close()

        if result:
            adaptation = _trigger_adaptation(g.auth_user['id'], 'task_restored')
            return jsonify(
                {
                    'message': f'Task "{result[1]}" restored successfully',
                    'id': result[0],
                    'adaptation_triggered': adaptation.get('success', False),
                }
            )
        return jsonify({'error': 'Deleted task not found'}), 404
    except Exception as e:
        return jsonify({'error': f'Error restoring task: {str(e)}'}), 500

@app.route('/api/reminders', methods=['POST'])
@require_auth
def send_reminder():
    data = request.json or {}
    user_id = g.auth_user['id']
    payload = f"reminders: user_id={user_id}; days={data.get('days', 3)}; send_email=true"
    result = agent_workflow(payload)
    return jsonify({'message': result['messages'][-1].content})

@app.route('/api/chat', methods=['POST'])
@require_auth
def chat():
    """Natural language chat interface to the LangGraph agent."""
    data = request.json or {}
    message = data.get('message', '').strip()
    user_id = g.auth_user['id']

    if not message:
        return jsonify({'error': 'Message is required'}), 400

    msg_lower = message.lower()

    # Bulk status update shortcut
    if ('update' in msg_lower or 'mark' in msg_lower or 'change' in msg_lower) and (
        'completed' in msg_lower
        or 'done' in msg_lower
        or 'pending' in msg_lower
        or 'in_progress' in msg_lower
        or 'in progress' in msg_lower
    ):
        target_status = None
        if 'completed' in msg_lower or 'done' in msg_lower or 'complete' in msg_lower:
            target_status = 'completed'
        elif 'in progress' in msg_lower or 'in_progress' in msg_lower or 'started' in msg_lower:
            target_status = 'in_progress'
        elif 'pending' in msg_lower:
            target_status = 'pending'

        if target_status:
            source_statuses = []
            if 'all' in msg_lower or ('pending' not in msg_lower and 'in progress' not in msg_lower and 'in_progress' not in msg_lower):
                if target_status == 'completed':
                    source_statuses = ['pending', 'in_progress']
                elif target_status == 'in_progress':
                    source_statuses = ['pending']
                elif target_status == 'pending':
                    source_statuses = ['in_progress', 'completed']
            else:
                if 'pending' in msg_lower and target_status != 'pending':
                    source_statuses.append('pending')
                if ('in progress' in msg_lower or 'in_progress' in msg_lower) and target_status != 'in_progress':
                    source_statuses.append('in_progress')

            if source_statuses:
                try:
                    from db_ops import get_connection

                    conn = get_connection()
                    cur = conn.cursor()
                    placeholders = ','.join(['%s'] * len(source_statuses))
                    cur.execute(
                        f"""
                        UPDATE tasks SET status = %s
                        WHERE user_id = %s AND status IN ({placeholders}) AND (deleted = FALSE OR deleted IS NULL)
                        RETURNING id, title, status
                        """,
                        [target_status, user_id] + source_statuses,
                    )
                    updated = cur.fetchall()
                    conn.commit()
                    cur.close()
                    conn.close()

                    if updated:
                        _trigger_adaptation(user_id, 'chat_bulk_status_update')
                        count = len(updated)
                        task_names = ', '.join([t[1] for t in updated[:5]])
                        if count > 5:
                            task_names += f' and {count - 5} more'
                        return jsonify({'response': f'Done. Updated {count} task(s) to {target_status}: {task_names}'})
                    return jsonify({'response': f'No tasks found to update. Tasks may already be {target_status}.'})
                except Exception as e:
                    return jsonify({'error': f'Error updating tasks: {str(e)}'}), 500

    # Show tasks variations
    if any(phrase in msg_lower for phrase in ['show my tasks', 'show tasks', 'list tasks', 'my tasks', 'what are my tasks', 'what tasks']):
        status_filter = ''
        if 'pending' in msg_lower:
            status_filter = '; status=pending'
        elif 'completed' in msg_lower or 'done' in msg_lower:
            status_filter = '; status=completed'
        elif 'in progress' in msg_lower:
            status_filter = '; status=in_progress'
        message = f"show_tasks: user_id={user_id}{status_filter}"

    # Add task variations
    elif any(phrase in msg_lower for phrase in ['add task', 'create task', 'new task', 'add a task']):
        message = f"agentic: user_id={user_id}; {message}"

    # Reminder variations
    elif any(phrase in msg_lower for phrase in ['remind me', 'send reminder', 'email reminder', 'upcoming tasks', 'due soon', "what's due"]):
        days = 7
        if 'tomorrow' in msg_lower:
            days = 1
        elif 'week' in msg_lower:
            days = 7
        elif 'today' in msg_lower:
            days = 0
        message = f"reminders: user_id={user_id}; days={days}; send_email=false"

    elif any(phrase in msg_lower for phrase in ['how can i', 'how do i', 'how to', 'help me', 'tips', 'advice', 'better manage', 'manage my', 'suggest', 'recommend']):
        if 'deadline' in msg_lower or 'time' in msg_lower or 'schedule' in msg_lower:
            return jsonify({'response': 'Tips for Managing Deadlines:\n1. Set realistic deadlines\n2. Prioritize tasks\n3. Break large tasks down\n4. Review conflicts regularly\n5. Use reminders'})

    try:
        result = agent_workflow(message)
        response = result['messages'][-1].content

        if any(keyword in msg_lower for keyword in ['add task', 'create task', 'delete task', 'update task', 'mark all']):
            _trigger_adaptation(user_id, 'chat_task_mutation')

        if 'Available commands' in response or 'TASKS\n-----' in response or 'show <user_id>' in response:
            return jsonify(
                {
                    'response': (
                        "I can help with task management commands:\n"
                        '- "show my tasks"\n'
                        '- "mark all tasks as completed"\n'
                        '- "remind me about upcoming deadlines"'
                    )
                }
            )

        return jsonify({'response': response})
    except Exception as e:
        return jsonify({'error': f'Error processing request: {str(e)}'}), 500
@app.route('/api/tasks/conflicts', methods=['GET'])
@require_auth
def check_conflicts():
	"""Check for task deadline conflicts"""
	user_id = g.auth_user['id']
	
	try:
		from db_ops import get_connection
		from datetime import datetime, timedelta
		
		conn = get_connection()
		cur = conn.cursor()
		
		# Get all tasks with deadlines (excluding deleted)
		cur.execute("""
			SELECT id, title, deadline, priority, status 
			FROM tasks 
			WHERE user_id = %s AND deadline IS NOT NULL AND status != 'completed' AND (deleted = FALSE OR deleted IS NULL)
			ORDER BY deadline
		""", (user_id,))
		tasks = cur.fetchall()
		cur.close()
		conn.close()
		
		conflicts = []
		
		# Check for multiple high-priority tasks on same day
		task_by_date = {}
		for task in tasks:
			task_id, title, deadline, priority, status = task
			if deadline:
				date_key = deadline.strftime('%Y-%m-%d') if hasattr(deadline, 'strftime') else str(deadline)[:10]
				if date_key not in task_by_date:
					task_by_date[date_key] = []
				task_by_date[date_key].append({
					'id': task_id,
					'title': title,
					'priority': priority_int_to_string(priority) if isinstance(priority, int) else priority,
					'deadline': date_key
				})
		
		# Find dates with multiple tasks (potential conflicts)
		for date_key, date_tasks in task_by_date.items():
			if len(date_tasks) > 2:
				conflicts.append({
					'type': 'overload',
					'date': date_key,
					'message': f'{len(date_tasks)} tasks due on {date_key}',
					'tasks': date_tasks
				})
			
			# Check for multiple high priority tasks on same day
			high_priority = [t for t in date_tasks if t['priority'] == 'high']
			if len(high_priority) > 1:
				conflicts.append({
					'type': 'priority_conflict',
					'date': date_key,
					'message': f'{len(high_priority)} high-priority tasks on {date_key}',
					'tasks': high_priority
				})
		
		# Check for tasks due very soon (within 24 hours)
		now = datetime.now()
		for task in tasks:
			task_id, title, deadline, priority, status = task
			if deadline:
				try:
					if isinstance(deadline, str):
						deadline = datetime.strptime(deadline[:10], '%Y-%m-%d')
					time_left = deadline - now
					if timedelta(0) < time_left < timedelta(days=1):
						conflicts.append({
							'type': 'urgent',
							'date': deadline.strftime('%Y-%m-%d') if hasattr(deadline, 'strftime') else str(deadline)[:10],
							'message': f'Task "{title}" is due within 24 hours!',
							'tasks': [{'id': task_id, 'title': title}]
						})
				except:
					pass
		
		return jsonify({'conflicts': conflicts, 'total': len(conflicts)})
	except Exception as e:
		return jsonify({'error': f'Error checking conflicts: {str(e)}'}), 500


# =============================================
# SCHEDULING ENDPOINTS - Agentic AI Features
# =============================================

@app.route('/api/availability', methods=['GET'])
@require_auth
def get_availability():
	"""Get student's weekly availability pattern"""
	user_id = g.auth_user['id']
	
	try:
		from db_ops import get_connection
		conn = get_connection()
		cur = conn.cursor()
		
		cur.execute("""
			SELECT id, day_of_week, start_time, end_time, location
			FROM student_availability
			WHERE user_id = %s
			ORDER BY day_of_week, start_time
		""", (user_id,))
		
		rows = cur.fetchall()
		cur.close()
		conn.close()
		
		days = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']
		availability = []
		for row in rows:
			availability.append({
				'id': row[0],
				'day_of_week': row[1],
				'day_name': days[row[1]],
				'start_time': str(row[2])[:5],  # HH:MM
				'end_time': str(row[3])[:5],
				'location': row[4] or ''
			})
		
		return jsonify(availability)
	except Exception as e:
		return jsonify({'error': f'Error fetching availability: {str(e)}'}), 500


@app.route('/api/availability', methods=['POST'])
@require_auth
def add_availability():
	"""Add a new availability slot for a student"""
	data = request.json or {}
	
	required_fields = ['day_of_week', 'start_time', 'end_time']
	for field in required_fields:
		if field not in data:
			return jsonify({'error': f'{field} is required'}), 400
	
	try:
		from db_ops import get_connection
		conn = get_connection()
		cur = conn.cursor()
		
		cur.execute("""
			INSERT INTO student_availability (user_id, day_of_week, start_time, end_time, location)
			VALUES (%s, %s, %s, %s, %s)
			RETURNING id
		""", (g.auth_user['id'], data['day_of_week'], data['start_time'], data['end_time'], data.get('location', '')))
		
		slot_id = cur.fetchone()[0]
		conn.commit()
		cur.close()
		conn.close()
		
		adaptation = _trigger_adaptation(g.auth_user['id'], 'availability_added')
		return jsonify({'message': 'Availability slot added', 'id': slot_id, 'adaptation_triggered': adaptation.get('success', False)})
	except Exception as e:
		return jsonify({'error': f'Error adding availability: {str(e)}'}), 500


@app.route('/api/availability/<int:slot_id>', methods=['DELETE'])
@require_auth
def delete_availability(slot_id):
	"""Delete an availability slot"""
	try:
		from db_ops import get_connection
		conn = get_connection()
		cur = conn.cursor()
		
		cur.execute("DELETE FROM student_availability WHERE id = %s AND user_id = %s RETURNING id", (slot_id, g.auth_user['id']))
		result = cur.fetchone()
		conn.commit()
		cur.close()
		conn.close()
		
		if result:
			adaptation = _trigger_adaptation(g.auth_user['id'], 'availability_deleted')
			return jsonify({'message': 'Availability slot deleted', 'adaptation_triggered': adaptation.get('success', False)})
		else:
			return jsonify({'error': 'Slot not found'}), 404
	except Exception as e:
		return jsonify({'error': f'Error deleting availability: {str(e)}'}), 500


@app.route('/api/schedule', methods=['GET'])
@require_auth
def get_schedule():
	"""Get the current generated schedule for a user"""
	user_id = g.auth_user['id']
	start_date = request.args.get('start_date')
	end_date = request.args.get('end_date')
	
	try:
		from db_ops import get_connection
		from datetime import datetime, timedelta
		
		conn = get_connection()
		cur = conn.cursor()
		
		# Default: get schedule for the next 7 days
		if not start_date:
			start_date = datetime.now().date().isoformat()
		if not end_date:
			end_date = (datetime.now().date() + timedelta(days=7)).isoformat()
		
		cur.execute("""
			SELECT ss.id, ss.task_id, t.title, ss.scheduled_date, 
			       ss.start_time, ss.end_time, ss.status, ss.ai_reasoning, ss.confidence_score
			FROM scheduled_slots ss
			JOIN tasks t ON ss.task_id = t.id
			WHERE ss.user_id = %s AND ss.scheduled_date BETWEEN %s AND %s
			ORDER BY ss.scheduled_date, ss.start_time
		""", (user_id, start_date, end_date))
		
		rows = cur.fetchall()
		cur.close()
		conn.close()
		
		schedule = []
		for row in rows:
			schedule.append({
				'id': row[0],
				'task_id': row[1],
				'task_title': row[2],
				'date': row[3].isoformat() if hasattr(row[3], 'isoformat') else str(row[3]),
				'start_time': str(row[4])[:5],
				'end_time': str(row[5])[:5],
				'status': row[6],
				'ai_reasoning': row[7],
				'confidence': row[8]
			})
		
		return jsonify(schedule)
	except Exception as e:
		return jsonify({'error': f'Error fetching schedule: {str(e)}'}), 500


@app.route('/api/schedule/generate', methods=['POST'])
@require_auth
def generate_schedule():
	"""
	Generate an optimized schedule using AI.
	
	This is the CORE AGENTIC FEATURE: The system autonomously
	analyzes tasks, availability, and constraints to place 
	tasks in optimal time slots.
	"""
	data = request.json or {}
	user_id = g.auth_user['id']
	
	try:
		from langgraph_agent import generate_ai_schedule
		from datetime import datetime
		
		# Get optional parameters
		start_date = data.get('start_date', datetime.now().date().isoformat())
		days_ahead = data.get('days_ahead', 7)
		
		# Call the agentic scheduling function
		result = generate_ai_schedule(user_id, start_date, days_ahead)
		
		return jsonify(result)
	except ImportError as e:
		return jsonify({'error': f'Scheduling module not available: {str(e)}'}), 500
	except Exception as e:
		return jsonify({'error': f'Error generating schedule: {str(e)}'}), 500


@app.route('/api/schedule/adapt', methods=['POST'])
@require_auth
def adapt_schedule():
	"""
	Trigger schedule adaptation when constraints change.
	
	This demonstrates FEEDBACK-BASED ADAPTATION: When a task
	changes or new constraints are added, the AI re-evaluates
	and adjusts the schedule autonomously.
	"""
	data = request.json or {}
	user_id = g.auth_user['id']
	trigger = data.get('trigger', 'manual')  # What caused the adaptation
	
	try:
		from langgraph_agent import adapt_schedule_to_changes
		
		result = adapt_schedule_to_changes(user_id, trigger=trigger)
		
		return jsonify(result)
	except ImportError as e:
		return jsonify({'error': f'Adaptation module not available: {str(e)}'}), 500
	except Exception as e:
		return jsonify({'error': f'Error adapting schedule: {str(e)}'}), 500


@app.route('/api/schedule/slot/<int:slot_id>', methods=['PUT'])
@require_auth
def update_schedule_slot(slot_id):
	"""Update a scheduled slot (e.g., mark as completed)"""
	data = request.json
	
	try:
		from db_ops import get_connection
		conn = get_connection()
		cur = conn.cursor()
		
		update_fields = []
		values = []
		
		if 'status' in data:
			update_fields.append('status = %s')
			values.append(data['status'])
		
		if 'start_time' in data:
			update_fields.append('start_time = %s')
			values.append(data['start_time'])
		
		if 'end_time' in data:
			update_fields.append('end_time = %s')
			values.append(data['end_time'])
		
		update_fields.append('updated_at = CURRENT_TIMESTAMP')
		
		if not update_fields:
			return jsonify({'error': 'No fields to update'}), 400
		
		values.extend([slot_id, g.auth_user['id']])
		query = f"UPDATE scheduled_slots SET {', '.join(update_fields)} WHERE id = %s AND user_id = %s RETURNING id"
		
		cur.execute(query, values)
		result = cur.fetchone()
		conn.commit()
		cur.close()
		conn.close()
		
		if result:
			return jsonify({'message': 'Schedule slot updated', 'id': result[0]})
		else:
			return jsonify({'error': 'Slot not found'}), 404
	except Exception as e:
		return jsonify({'error': f'Error updating slot: {str(e)}'}), 500


if __name__ == "__main__":
	port = int(os.getenv('PORT', 5000))
	debug = os.getenv('FLASK_DEBUG', 'true').lower() == 'true'
	app.run(host='0.0.0.0', port=port, debug=debug)


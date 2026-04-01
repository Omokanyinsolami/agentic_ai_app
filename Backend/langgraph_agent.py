# langgraph_agent.py
"""
Academic Task Agent with LangGraph + PostgreSQL + Groq LLM

This is a TRUE AGENTIC AI system that uses:
1. Goal-directed autonomy via LLM reasoning
2. Feedback-based adaptation through conversation context
3. Tool use (database operations) orchestrated by AI decisions

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
GROQ_API_KEY

Optional for email reminders:
EMAIL_PROVIDER=auto
BREVO_API_KEY
BREVO_FROM_EMAIL
BREVO_FROM_NAME
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
import json
import shlex
import smtplib
from pathlib import Path
from email.message import EmailMessage
from datetime import datetime, date, timedelta
from urllib import error as urllib_error
from urllib import request as urllib_request
from typing import Optional, Any
from typing_extensions import TypedDict, Annotated, Literal

import psycopg2
from psycopg2 import IntegrityError
from dotenv import load_dotenv
from langchain_core.messages import HumanMessage, AIMessage, BaseMessage, SystemMessage
from langgraph.graph import StateGraph, START, END
from langgraph.graph.message import add_messages

# Groq LLM for true agentic reasoning
try:
    from langchain_groq import ChatGroq
    GROQ_AVAILABLE = True
except ImportError:
    GROQ_AVAILABLE = False
    print("Warning: langchain-groq not installed. Run: pip install langchain-groq")


# ----------------------------
# Load environment variables
# ----------------------------
load_dotenv()


# ----------------------------
# LLM Setup for Agentic Reasoning
# ----------------------------
def get_llm():
    """Initialize Groq LLM for agentic reasoning."""
    if not GROQ_AVAILABLE:
        return None
    
    api_key = os.getenv("GROQ_API_KEY")
    if not api_key or api_key == "your_groq_api_key_here":
        return None
    
    try:
        return ChatGroq(
            model="llama-3.3-70b-versatile",  # Current Groq model (updated from 3.1)
            temperature=0.3,
            api_key=api_key
        )
    except Exception as e:
        print(f"Warning: Could not initialize Groq LLM: {e}")
        return None


# Global LLM instance (lazy loaded)
_llm_instance = None

def get_llm_instance():
    """Get or create the global LLM instance."""
    global _llm_instance
    if _llm_instance is None:
        _llm_instance = get_llm()
    return _llm_instance


# ----------------------------
# Agentic AI Reasoning Functions
# ----------------------------
TASK_AGENT_SYSTEM_PROMPT = """You are an intelligent academic task management assistant for MSc students.

Your capabilities:
1. UNDERSTAND natural language requests about tasks, deadlines, and priorities
2. REASON about task prioritization based on deadlines, workload, and importance
3. PROVIDE thoughtful advice on time management and study planning
4. EXPLAIN your recommendations clearly

When analyzing tasks, consider:
- Deadline proximity (urgent tasks first)
- Task complexity and estimated duration
- Dependencies between tasks
- Student's available time and workload balance

Always be helpful, concise, and supportive. Use emojis sparingly for friendliness.
"""


def llm_understand_intent(user_message: str, user_id: Optional[int] = None) -> dict:
    """
    Use LLM to understand user intent from natural language.
    
    This is TRUE AGENTIC BEHAVIOR: The AI reasons about what the user wants
    rather than relying on pattern matching.
    
    Returns: {
        "intent": "show_tasks" | "add_task" | "update_task" | "delete_task" | 
                  "advice" | "prioritize" | "help" | "greeting" | "unknown",
        "parameters": {...extracted params...},
        "reasoning": "explanation of understanding"
    }
    """
    llm = get_llm_instance()
    if not llm:
        # Fallback to pattern matching if LLM unavailable
        return {"intent": "fallback", "parameters": {}, "reasoning": "LLM not available"}
    
    try:
        prompt = f"""Analyze this user message and determine their intent and all required fields for task creation.

User message: "{user_message}"
{f"Current user ID: {user_id}" if user_id else ""}

Determine the intent from these options:
- show_tasks: User wants to see their tasks
- add_task: User wants to create a new task
- update_task: User wants to modify an existing task
- delete_task: User wants to remove a task
- advice: User wants study/time management advice
- prioritize: User wants help prioritizing their tasks
- help: User wants to know available commands
- greeting: User is just saying hello
- unknown: Cannot determine intent

For add_task, extract ALL required fields:
- title: required
- description: optional (default "")
- deadline: required (in YYYY-MM-DD HH:MM format if possible, do not default to 12:00 AM)
- priority: required (accept high/medium/low or 1-5, map to integer: high=1, medium=3, low=5)
- user_id: required
- status: required (default "pending")

If deadline time is missing, ask user for a specific time or default to 17:00 (end of day).
If priority is missing or ambiguous, ask user to clarify or default to medium (3).

Respond in this exact JSON format:
{{"intent": "...", "parameters": {{...}}, "reasoning": "brief explanation"}}
"""
        
        response = llm.invoke([
            SystemMessage(content="You are an intent classification system. Respond only with valid JSON."),
            HumanMessage(content=prompt)
        ])
        
        # Parse JSON response
        import json
        result = json.loads(response.content)
        return result
        
    except Exception as e:
        return {"intent": "fallback", "parameters": {}, "reasoning": f"Error: {e}"}


def llm_prioritize_tasks(tasks: list, user_name: str = "Student") -> str:
    """
    Use LLM to analyze tasks and provide intelligent prioritization advice.
    
    This is TRUE AGENTIC REASONING: The AI thinks about the student's workload
    and makes personalized recommendations.
    """
    llm = get_llm_instance()
    if not llm or not tasks:
        return None
    
    try:
        # Format tasks for analysis
        task_summary = []
        for t in tasks:
            task_id, title, desc, deadline, priority, status, created = t
            deadline_str = deadline.strftime('%Y-%m-%d %H:%M') if hasattr(deadline, 'strftime') else str(deadline)
            priority_str = 'high' if priority == 1 else 'medium' if priority == 3 else 'low'
            task_summary.append(f"- ID:{task_id} | '{title}' | Due: {deadline_str} | Priority: {priority_str} | Status: {status}")
        
        tasks_text = "\n".join(task_summary)
        today = date.today().isoformat()
        
        prompt = f"""As an academic task management AI, analyze these tasks and provide robust prioritization advice.

Today's date: {today}
Student: {user_name}

Current tasks:
{tasks_text}

Provide a detailed, actionable analysis:
1. Which task(s) need immediate attention and why?
2. Are there any deadline conflicts or risks?
3. Explain why one task is prioritised over another (consider deadline, priority, workload, and time of day).
4. One specific recommendation for today.

Keep your response concise (under 150 words), friendly, and use 1-2 relevant emojis. Make the explanation clear and human-friendly.
"""
        
        response = llm.invoke([
            SystemMessage(content=TASK_AGENT_SYSTEM_PROMPT),
            HumanMessage(content=prompt)
        ])
        
        return response.content
        
    except Exception as e:
        return None


def llm_generate_advice(user_question: str, tasks: list = None, user_name: str = "Student") -> str:
    """
    Use LLM to generate personalized study/time management advice.
    
    This demonstrates GOAL-DIRECTED AUTONOMY: The AI understands the student's
    situation and provides thoughtful guidance.
    """
    llm = get_llm_instance()
    if not llm:
        return "I'd love to help with advice, but my AI reasoning is currently unavailable. Please check your GROQ_API_KEY."
    
    try:
        # Include task context if available
        context = ""
        if tasks:
            task_summary = []
            for t in tasks[:5]:  # Limit to 5 tasks for context
                task_id, title, desc, deadline, priority, status, created = t
                task_summary.append(f"- '{title}' due {deadline} (priority {priority}, {status})")
            context = f"\n\nStudent's current tasks:\n" + "\n".join(task_summary)
        
        prompt = f"""Student {user_name} asks: "{user_question}"
{context}

Provide helpful, personalized advice. Be concise (under 100 words), practical, and encouraging.
"""
        
        response = llm.invoke([
            SystemMessage(content=TASK_AGENT_SYSTEM_PROMPT),
            HumanMessage(content=prompt)
        ])
        
        return response.content
        
    except Exception as e:
        return f"I encountered an issue generating advice: {e}"


def llm_explain_schedule(schedule_data: dict, user_name: str = "Student") -> str:
    """
    Use LLM to explain scheduling decisions.
    
    This provides EXPLAINABILITY: The AI can articulate why it made certain
    recommendations, a key feature of trustworthy agentic systems.
    """
    llm = get_llm_instance()
    if not llm:
        return None
    
    try:
        prompt = f"""Explain this task schedule to {user_name} in a friendly, helpful way.

Schedule data:
{schedule_data}

Provide a robust explanation (under 120 words) of:
1. Why tasks are ordered this way (consider deadline, priority, time of day, workload balance)
2. Any potential concerns with the schedule
3. One tip for success
4. If multiple tasks are scheduled on the same day, explain the reasoning for their order and time allocation.
"""
        
        response = llm.invoke([
            SystemMessage(content=TASK_AGENT_SYSTEM_PROMPT),
            HumanMessage(content=prompt)
        ])
        
        return response.content
        
    except Exception as e:
        return None


# ----------------------------
# Agentic Schedule Generation
# ----------------------------
def generate_ai_schedule(user_id: int, start_date: str = None, days_ahead: int = 7) -> dict:
    """
    CORE AGENTIC FUNCTION: Generate an optimized study schedule.
    
    This demonstrates the three pillars of agentic AI:
    1. GOAL-DIRECTED AUTONOMY: The agent pursues the goal of creating
       an effective schedule without step-by-step user guidance.
    2. TOOL USE: The agent queries the database and uses LLM reasoning.
    3. FEEDBACK-BASED ADAPTATION: The agent explains its decisions and
       can adjust when constraints change.
    
    Algorithm:
    1. Fetch tasks with deadlines (workload to schedule)
    2. Fetch student availability (when they can work)
    3. Use LLM to intelligently assign tasks to slots
    4. Store scheduled slots in database
    5. Return schedule with explanations
    """
    from datetime import datetime, timedelta, date as date_type
    import json as json_module
    
    if not start_date:
        start_date = datetime.now().date().isoformat()
    
    # Parse start date
    if isinstance(start_date, str):
        start = datetime.strptime(start_date, '%Y-%m-%d').date()
    else:
        start = start_date
    
    end = start + timedelta(days=days_ahead)
    
    result = {
        'success': False,
        'schedule': [],
        'reasoning': '',
        'warnings': [],
        'stats': {}
    }
    
    try:
        conn = get_connection()
        cur = conn.cursor()
        
        # 1. Get all pending tasks for this user with deadlines
        cur.execute("""
            SELECT id, title, description, deadline, priority, status, created_at
            FROM tasks
            WHERE user_id = %s 
              AND status NOT IN ('completed', 'done')
              AND (deleted = FALSE OR deleted IS NULL)
            ORDER BY deadline ASC NULLS LAST, priority ASC
        """, (user_id,))
        tasks = cur.fetchall()
        
        if not tasks:
            result['success'] = True
            result['reasoning'] = "No pending tasks to schedule. You're all caught up! 🎉"
            cur.close()
            conn.close()
            return result
        
        # 2. Get student availability
        cur.execute("""
            SELECT day_of_week, start_time, end_time, location
            FROM student_availability
            WHERE user_id = %s
            ORDER BY day_of_week, start_time
        """, (user_id,))
        availability = cur.fetchall()
        
        # If no availability set, create default (9 AM - 5 PM weekdays)
        if not availability:
            result['warnings'].append("No availability set. Using default schedule (9 AM - 5 PM on weekdays). Set your availability for better results!")
            availability = [
                (0, '09:00', '12:00', 'Default'),  # Monday morning
                (0, '14:00', '17:00', 'Default'),  # Monday afternoon
                (1, '09:00', '12:00', 'Default'),  # Tuesday morning
                (1, '14:00', '17:00', 'Default'),  # Tuesday afternoon
                (2, '09:00', '12:00', 'Default'),  # Wednesday morning
                (2, '14:00', '17:00', 'Default'),  # Wednesday afternoon
                (3, '09:00', '12:00', 'Default'),  # Thursday morning
                (3, '14:00', '17:00', 'Default'),  # Thursday afternoon
                (4, '09:00', '12:00', 'Default'),  # Friday morning
                (4, '14:00', '17:00', 'Default'),  # Friday afternoon
            ]
        
        # 3. Build available time slots for the date range
        available_slots = []
        current = start
        while current <= end:
            day_num = current.weekday()  # 0=Monday, 6=Sunday
            for avail in availability:
                if avail[0] == day_num:
                    available_slots.append({
                        'date': current.isoformat(),
                        'day_name': current.strftime('%A'),
                        'start_time': str(avail[1])[:5],
                        'end_time': str(avail[2])[:5],
                        'location': avail[3] if len(avail) > 3 else ''
                    })
            current += timedelta(days=1)
        
        if not available_slots:
            result['success'] = False
            result['reasoning'] = f"No available time slots in the next {days_ahead} days. Please add your availability first."
            cur.close()
            conn.close()
            return result
        
        # 4. Use LLM to create intelligent schedule
        user_name = get_user_name(user_id)
        llm = get_llm_instance()
        
        # Format tasks for LLM
        task_info = []
        for t in tasks:
            task_id, title, desc, deadline, priority, status, created = t
            deadline_str = deadline.strftime('%Y-%m-%d') if hasattr(deadline, 'strftime') else str(deadline)[:10] if deadline else 'No deadline'
            task_info.append({
                'id': task_id,
                'title': title,
                'deadline': deadline_str,
                'priority': priority if priority else 3,
                'status': status
            })
        
        if llm:
            # Use LLM for intelligent scheduling
            schedule_prompt = f"""You are an intelligent academic scheduler for {user_name}.

Today's date: {start.isoformat()}
Scheduling window: {start.isoformat()} to {end.isoformat()}

TASKS TO SCHEDULE:
{json_module.dumps(task_info, indent=2)}

AVAILABLE TIME SLOTS:
{json_module.dumps(available_slots[:20], indent=2)}  {"(More slots available)" if len(available_slots) > 20 else ""}

Create an optimal schedule following these rules:
1. HIGH PRIORITY tasks (priority 1-2) should be scheduled first and in earlier slots
2. Tasks with NEAR DEADLINES should be scheduled before their deadline
3. SPREAD workload - don't overload a single day
4. Provide 1-2 hour slots per task (based on complexity)

Respond in EXACT JSON format:
{{
  "scheduled_tasks": [
    {{
      "task_id": <int>,
      "date": "YYYY-MM-DD",
      "start_time": "HH:MM",
      "end_time": "HH:MM",
      "reasoning": "Brief explanation"
    }}
  ],
  "overall_reasoning": "1-2 sentence summary of schedule strategy",
  "warnings": ["any concerns about deadlines or workload"]
}}

Only schedule tasks that have available slots. Each task should appear at most once.
"""
            
            try:
                response = llm.invoke([
                    SystemMessage(content="You are a precise scheduling assistant. Respond only with valid JSON."),
                    HumanMessage(content=schedule_prompt)
                ])
                
                # Parse LLM response
                llm_schedule = json_module.loads(response.content)
                
                # Clear existing scheduled slots for this date range
                cur.execute("""
                    DELETE FROM scheduled_slots 
                    WHERE user_id = %s AND scheduled_date BETWEEN %s AND %s
                """, (user_id, start.isoformat(), end.isoformat()))
                
                # Insert new scheduled slots
                scheduled_items = []
                for item in llm_schedule.get('scheduled_tasks', []):
                    cur.execute("""
                        INSERT INTO scheduled_slots 
                        (user_id, task_id, scheduled_date, start_time, end_time, status, ai_reasoning, confidence_score)
                        VALUES (%s, %s, %s, %s, %s, 'scheduled', %s, %s)
                        RETURNING id
                    """, (
                        user_id,
                        item['task_id'],
                        item['date'],
                        item['start_time'],
                        item['end_time'],
                        item.get('reasoning', 'AI scheduled'),
                        0.85  # Default confidence
                    ))
                    slot_id = cur.fetchone()[0]
                    
                    # Find task title
                    task_title = next((t['title'] for t in task_info if t['id'] == item['task_id']), 'Unknown Task')
                    
                    scheduled_items.append({
                        'id': slot_id,
                        'task_id': item['task_id'],
                        'task_title': task_title,
                        'date': item['date'],
                        'start_time': item['start_time'],
                        'end_time': item['end_time'],
                        'reasoning': item.get('reasoning', '')
                    })
                
                conn.commit()
                
                result['success'] = True
                result['schedule'] = scheduled_items
                result['reasoning'] = llm_schedule.get('overall_reasoning', 'Schedule generated using AI optimization.')
                result['warnings'].extend(llm_schedule.get('warnings', []))
                result['stats'] = {
                    'tasks_scheduled': len(scheduled_items),
                    'total_tasks': len(tasks),
                    'days_covered': days_ahead
                }
                
            except json_module.JSONDecodeError as e:
                # LLM didn't return valid JSON, fall back to algorithmic
                result['warnings'].append(f"AI response parsing failed, using algorithmic scheduling: {str(e)}")
                result = _algorithmic_schedule(cur, conn, user_id, tasks, available_slots, task_info, result, start, end)
                
        else:
            # No LLM available, use algorithmic scheduling
            result['warnings'].append("AI scheduling not available (no LLM configured). Using algorithmic scheduling.")
            result = _algorithmic_schedule(cur, conn, user_id, tasks, available_slots, task_info, result, start, end)
        
        cur.close()
        conn.close()
        
        return result
        
    except Exception as e:
        return {
            'success': False,
            'schedule': [],
            'reasoning': f'Error generating schedule: {str(e)}',
            'warnings': [],
            'stats': {}
        }


def _algorithmic_schedule(cur, conn, user_id, tasks, available_slots, task_info, result, start, end):
    """
    Fallback algorithmic scheduler when LLM is not available.
    Uses Earliest Deadline First (EDF) with priority weighting.
    """
    from datetime import datetime
    
    # Sort tasks by deadline (earliest first), then by priority (lowest number = highest priority)
    sorted_tasks = sorted(task_info, key=lambda t: (
        t['deadline'] if t['deadline'] != 'No deadline' else '9999-12-31',
        t['priority']
    ))
    
    # Clear existing scheduled slots for this date range
    cur.execute("""
        DELETE FROM scheduled_slots 
        WHERE user_id = %s AND scheduled_date BETWEEN %s AND %s
    """, (user_id, start.isoformat(), end.isoformat()))
    
    scheduled_items = []
    used_slots = set()
    
    for task in sorted_tasks:
        # Find first available slot
        for i, slot in enumerate(available_slots):
            slot_key = f"{slot['date']}_{slot['start_time']}"
            if slot_key not in used_slots:
                # Schedule this task in this slot
                reasoning = f"Scheduled based on deadline ({task['deadline']}) and priority ({task['priority']})"
                
                cur.execute("""
                    INSERT INTO scheduled_slots 
                    (user_id, task_id, scheduled_date, start_time, end_time, status, ai_reasoning, confidence_score)
                    VALUES (%s, %s, %s, %s, %s, 'scheduled', %s, %s)
                    RETURNING id
                """, (
                    user_id,
                    task['id'],
                    slot['date'],
                    slot['start_time'],
                    slot['end_time'],
                    reasoning,
                    0.7  # Lower confidence for algorithmic
                ))
                slot_id = cur.fetchone()[0]
                
                scheduled_items.append({
                    'id': slot_id,
                    'task_id': task['id'],
                    'task_title': task['title'],
                    'date': slot['date'],
                    'start_time': slot['start_time'],
                    'end_time': slot['end_time'],
                    'reasoning': reasoning
                })
                
                used_slots.add(slot_key)
                break
    
    conn.commit()
    
    result['success'] = True
    result['schedule'] = scheduled_items
    result['reasoning'] = 'Schedule generated using Earliest Deadline First algorithm with priority weighting.'
    result['stats'] = {
        'tasks_scheduled': len(scheduled_items),
        'total_tasks': len(tasks),
        'days_covered': (end - start).days
    }
    
    return result


def adapt_schedule_to_changes(user_id: int, trigger: str = "manual") -> dict:
    """
    AGENTIC ADAPTATION: Re-evaluate and adjust schedule when constraints change.
    
    This function embodies FEEDBACK-BASED ADAPTATION:
    - When a task deadline changes, re-prioritize
    - When new tasks are added, incorporate them
    - When tasks are completed, free up slots
    
    The LLM explains what changed and why the schedule was adjusted.
    """
    from datetime import datetime, timedelta
    
    result = {
        'success': False,
        'changes': [],
        'reasoning': '',
        'new_schedule': []
    }
    
    try:
        conn = get_connection()
        cur = conn.cursor()
        
        # Get current scheduled slots
        today = datetime.now().date()
        cur.execute("""
            SELECT ss.id, ss.task_id, t.title, t.status, t.deadline, ss.scheduled_date
            FROM scheduled_slots ss
            JOIN tasks t ON ss.task_id = t.id
            WHERE ss.user_id = %s AND ss.scheduled_date >= %s
            ORDER BY ss.scheduled_date
        """, (user_id, today.isoformat()))
        
        current_slots = cur.fetchall()
        changes = []
        
        # Check for completed tasks that need slots removed
        for slot in current_slots:
            slot_id, task_id, title, status, deadline, scheduled_date = slot
            if status in ('completed', 'done'):
                changes.append({
                    'type': 'slot_freed',
                    'task': title,
                    'reason': 'Task was marked as completed'
                })
                cur.execute("DELETE FROM scheduled_slots WHERE id = %s", (slot_id,))
        
        # Check for tasks with passed deadlines
        for slot in current_slots:
            slot_id, task_id, title, status, deadline, scheduled_date = slot
            if deadline and hasattr(deadline, 'date'):
                if deadline.date() < today and status not in ('completed', 'done'):
                    changes.append({
                        'type': 'overdue_warning',
                        'task': title,
                        'reason': f'Deadline ({deadline.date()}) has passed but task is not complete'
                    })
        
        conn.commit()
        cur.close()
        conn.close()
        
        # Re-generate schedule with updated constraints
        if changes:
            new_schedule_result = generate_ai_schedule(user_id, today.isoformat(), 7)
            result['new_schedule'] = new_schedule_result.get('schedule', [])
        
        # Use LLM to explain changes if available
        llm = get_llm_instance()
        if llm and changes:
            user_name = get_user_name(user_id)
            explain_prompt = f"""Explain these schedule changes to {user_name} in a friendly way:

Trigger: {trigger}
Changes detected:
{changes}

Be brief (2-3 sentences) and encouraging.
"""
            try:
                response = llm.invoke([
                    SystemMessage(content=TASK_AGENT_SYSTEM_PROMPT),
                    HumanMessage(content=explain_prompt)
                ])
                result['reasoning'] = response.content
            except:
                result['reasoning'] = f"Your schedule has been updated based on {len(changes)} change(s)."
        else:
            result['reasoning'] = "Schedule reviewed. No changes needed." if not changes else f"Made {len(changes)} adjustment(s) to your schedule."
        
        result['success'] = True
        result['changes'] = changes
        
        return result
        
    except Exception as e:
        return {
            'success': False,
            'changes': [],
            'reasoning': f'Error adapting schedule: {str(e)}',
            'new_schedule': []
        }


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

    connect_timeout = os.getenv("DB_CONNECT_TIMEOUT", "").strip()
    if connect_timeout:
        settings["connect_timeout"] = int(connect_timeout)

    sslmode = os.getenv("DB_SSLMODE", "").strip()
    if sslmode:
        settings["sslmode"] = sslmode

    return settings


def get_connection():
    """Open a new PostgreSQL connection."""
    return psycopg2.connect(**get_db_settings())


# ----------------------------
# Human-friendly formatting helpers
# ----------------------------
def get_user_name(user_id: int) -> str:
    """Get user's name from database for personalized responses."""
    try:
        with get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT name FROM user_profiles WHERE id = %s", (user_id,))
                row = cur.fetchone()
                if row:
                    return row[0].split()[0]  # Return first name
        return f"User {user_id}"
    except:
        return f"User {user_id}"


def format_date_friendly(date_val) -> str:
    """Convert date/datetime to human-friendly format."""
    if not date_val:
        return "No due date"
    try:
        if hasattr(date_val, 'strftime'):
            return date_val.strftime('%B %d, %Y')  # e.g., "March 03, 2026"
        # Handle string dates
        date_str = str(date_val)[:10]
        from datetime import datetime
        dt = datetime.strptime(date_str, '%Y-%m-%d')
        return dt.strftime('%B %d, %Y')
    except:
        return str(date_val)[:10]


def format_priority_friendly(priority) -> str:
    """Convert priority number to friendly label."""
    try:
        p = int(priority)
        if p <= 2:
            return "🔴 High Priority"
        elif p <= 3:
            return "🟡 Medium Priority"
        else:
            return "🟢 Low Priority"
    except:
        return str(priority)


def format_status_friendly(status) -> str:
    """Convert status to friendly label with emoji."""
    status = str(status).lower()
    if status in ('completed', 'done'):
        return "✅ Completed"
    elif status == 'in_progress':
        return "🔄 In Progress"
    else:
        return "📋 Pending"


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
def _send_email_via_brevo_api(to_email: str, subject: str, body: str) -> tuple[bool, str]:
    api_key = os.getenv("BREVO_API_KEY")
    from_email = os.getenv("BREVO_FROM_EMAIL")
    from_name = os.getenv("BREVO_FROM_NAME", "Agentic AI Prototype")

    if not api_key or not from_email:
        return False, "Brevo API settings are not fully configured in .env."

    payload = {
        "sender": {
            "email": from_email,
            "name": from_name,
        },
        "to": [{"email": to_email}],
        "subject": subject,
        "textContent": body,
    }

    request = urllib_request.Request(
        "https://api.brevo.com/v3/smtp/email",
        data=json.dumps(payload).encode("utf-8"),
        headers={
            "accept": "application/json",
            "api-key": api_key,
            "content-type": "application/json",
        },
        method="POST",
    )

    try:
        with urllib_request.urlopen(request, timeout=15) as response:
            if 200 <= response.status < 300:
                return True, f"Reminder email sent to {to_email} via Brevo API."
            return False, f"Brevo API returned unexpected status {response.status}."
    except urllib_error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="ignore")
        return False, f"Brevo API request failed with {exc.code}: {detail or exc.reason}"
    except Exception as exc:
        return False, f"Brevo API request failed: {exc}"


def _send_email_via_smtp(to_email: str, subject: str, body: str) -> tuple[bool, str]:
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

        return True, f"Reminder email sent to {to_email} via SMTP."
    except Exception as e:
        return False, f"Failed to send email via SMTP: {e}"


def send_email_notification(to_email: str, subject: str, body: str) -> tuple[bool, str]:
    """
    Send an email using the configured provider.
    Brevo API is preferred for free-host deployment because it uses HTTPS
    instead of blocked SMTP ports on some free platforms.
    Returns (success, message).
    """
    provider = os.getenv("EMAIL_PROVIDER", "auto").strip().lower()

    if provider == "brevo":
        return _send_email_via_brevo_api(to_email, subject, body)
    if provider == "smtp":
        return _send_email_via_smtp(to_email, subject, body)

    if os.getenv("BREVO_API_KEY") and os.getenv("BREVO_FROM_EMAIL"):
        return _send_email_via_brevo_api(to_email, subject, body)

    return _send_email_via_smtp(to_email, subject, body)


# ----------------------------
# Router (with LLM-enhanced intent detection)
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
    "agentic_chat",
]:
    text = _last_human_text(state).lower()

    # First check for explicit internal commands (from CLI/API)
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
    
    # For natural language input, use LLM to understand intent (AGENTIC REASONING)
    if text.startswith("chat:") or text.startswith("agentic:"):
        return "agentic_chat"
    
    # Check for natural language task creation (route to agentic_chat for LLM parsing)
    add_task_keywords = ["add task", "create task", "new task", "add a task", "schedule task"]
    if any(kw in text for kw in add_task_keywords):
        return "agentic_chat"
    
    # Check for advice/help keywords that should trigger agentic chat
    advice_keywords = ["advice", "help me", "prioritize", "suggest", "recommend", "how do i", "what should", "tips"]
    if any(kw in text for kw in advice_keywords):
        return "agentic_chat"

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
        return {"messages": [AIMessage(content=f"Sorry, I couldn't fetch your tasks: {e}")]}

    # Get user's first name for personalization
    user_name = get_user_name(user_id)

    if not rows:
        return {"messages": [AIMessage(content=f"Hi {user_name}! 📭 You don't have any tasks yet.\n\nWould you like me to help you add one? Just say something like:\n\"Add a task to complete my assignment by next Friday\"")]}

    # Build friendly response
    task_count = len(rows)
    greeting = f"Hi {user_name}! 📋 Here are your {task_count} task{'s' if task_count > 1 else ''}:\n"
    
    lines = [greeting, "─" * 40]
    
    for idx, (task_id, title, desc, deadline, priority, status, created_at) in enumerate(rows, 1):
        friendly_date = format_date_friendly(deadline)
        friendly_priority = format_priority_friendly(priority)
        friendly_status = format_status_friendly(status)
        
        task_block = f"""
📌 **{title}**
   {desc if desc else '(No description)'}
   📅 Due: {friendly_date}
   {friendly_priority} | {friendly_status}
   [Task ID: {task_id}]"""
        lines.append(task_block)
    
    lines.append("\n─" * 40)
    
    # Add AI-powered prioritization advice (TRUE AGENTIC REASONING)
    ai_advice = llm_prioritize_tasks(rows, user_name)
    if ai_advice:
        lines.append("\n\n🤖 **AI Analysis:**")
        lines.append(ai_advice)
        lines.append("")
    
    lines.append("\n💡 **Quick actions:**")
    lines.append("• Update a task status: \"update_task: <task_id>, status=completed\"")
    lines.append("• Delete a task: \"delete_task: <task_id>\"")
    lines.append("• Ask for advice: \"How should I prioritize my tasks?\"")

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

        user_name = get_user_name(user_id)
        friendly_date = format_date_friendly(deadline)
        friendly_priority = format_priority_friendly(priority)
        
        response = f"""✅ Great, {user_name}! I've added your new task:

📌 **{title}**
   {description if description else '(No description)'}
   📅 Due: {friendly_date}
   {friendly_priority}
   
Task ID: {new_id}

Would you like to see all your tasks? Just say "show my tasks"."""

        return {
            "messages": [
                AIMessage(content=response)
            ]
        }
    except Exception as e:
        return {"messages": [AIMessage(content=f"Sorry, I couldn't add that task: {e}")]}


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

        # Get task details before deleting for friendly message
        task_title = None
        with get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT title FROM tasks WHERE id = %s", (task_id,))
                row = cur.fetchone()
                if row:
                    task_title = row[0]
                
                cur.execute(
                    """
                    DELETE FROM tasks
                    WHERE id = %s
                    RETURNING id
                    """,
                    (task_id,),
                )
                deleted = cur.fetchone()
            conn.commit()

        if not deleted:
            return {"messages": [AIMessage(content=f"🔍 I couldn't find task #{task_id}. It may have already been deleted.\n\nWant to see your current tasks? Just say \"show my tasks\".")]}

        response = f"""🗑️ Done! I've deleted the task:

   **{task_title if task_title else f'Task #{task_id}'}**

Need to add a new task or see your remaining tasks?"""

        return {"messages": [AIMessage(content=response)]}
    except Exception as e:
        return {"messages": [AIMessage(content=f"Sorry, I couldn't delete that task: {e}")]}


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
            return {"messages": [AIMessage(content=f"🔍 I couldn't find that user. Please check the user ID and try again.")]}

        name, email = user_row
        first_name = name.split()[0] if name else "there"

        if not rows:
            return {
                "messages": [
                    AIMessage(
                        content=f"🎉 Great news, {first_name}! You have no urgent tasks due in the next {days} day(s). Keep up the good work!"
                    )
                ]
            }

        # Build friendly reminder message
        task_count = len(rows)
        lines = [
            f"⏰ Hey {first_name}! Here's your reminder:\n",
            f"You have **{task_count} task{'s' if task_count > 1 else ''}** due in the next {days} day(s):\n",
            "─" * 35
        ]
        
        for title, deadline, priority, status in rows:
            friendly_date = format_date_friendly(deadline)
            friendly_priority = format_priority_friendly(priority)
            lines.append(f"\n📌 **{title}**")
            lines.append(f"   📅 Due: {friendly_date}")
            lines.append(f"   {friendly_priority}")

        lines.append("\n" + "─" * 35)

        summary = "\n".join(lines)

        if send_email:
            if email:
                subject = f"⏰ Task Reminder: {task_count} task(s) due soon"
                email_body = summary.replace("**", "")  # Remove markdown for email
                ok, message = send_email_notification(email, subject, email_body)
                if ok:
                    summary += f"\n\n📧 Email sent to {email}!"
                else:
                    summary += f"\n\n⚠️ Couldn't send email: {message}"
            else:
                summary += "\n\n⚠️ No email address on file for sending reminders."

        summary += "\n\n💡 Need to update any task? Just let me know!"

        return {"messages": [AIMessage(content=summary)]}
    except Exception as e:
        return {"messages": [AIMessage(content=f"Sorry, I had trouble generating your reminder: {e}")]}


# ----------------------------
# Agentic Chat Node (TRUE AI REASONING)
# ----------------------------
def agentic_chat(state: AgentState) -> dict:
    """
    Handle natural language interactions using LLM reasoning.
    
    This is the CORE AGENTIC BEHAVIOR:
    - Understands user intent through AI reasoning
    - Provides personalized advice based on task context
    - Demonstrates goal-directed autonomy
    """
    text = _last_human_text(state)
    
    # Remove prefix if present
    if text.lower().startswith("chat:"):
        text = text[5:].strip()
    elif text.lower().startswith("agentic:"):
        text = text[8:].strip()
    
    # Parse optional user_id from the message
    user_id = None
    params = _parse_kv_payload(_last_human_text(state))
    if params.get("user_id"):
        try:
            user_id = _to_int(params.get("user_id"), "user_id")
        except:
            pass
    
    # Get user name and tasks for context
    user_name = "Student"
    tasks = []
    if user_id:
        user_name = get_user_name(user_id)
        try:
            tasks = fetch_tasks(user_id=user_id, status=None, search=None)
        except:
            pass
    
    # Check if LLM is available
    llm = get_llm_instance()
    if not llm:
        return {"messages": [AIMessage(content="""🤖 AI reasoning is not available right now.

**To enable full agentic AI features:**
1. Get a free API key from: https://console.groq.com/keys
2. Add it to your .env file: GROQ_API_KEY=your_key_here
3. Restart the application

In the meantime, you can still use these commands:
• show <user_id> - View your tasks
• add <user_id> - Add a new task
• help - See all available commands
""")]}
    
    # Use LLM to understand intent and generate response
    intent_result = llm_understand_intent(text, user_id)
    intent = intent_result.get("intent", "unknown")
    
    # Handle different intents
    if intent == "advice" or intent == "prioritize":
        advice = llm_generate_advice(text, tasks, user_name)
        return {"messages": [AIMessage(content=advice)]}
    
    elif intent == "greeting":
        return {"messages": [AIMessage(content=f"Hello {user_name}! 👋 I'm your AI academic task assistant. How can I help you today?\n\nYou can ask me to:\n• Show your tasks\n• Help prioritize your work\n• Give study advice\n• Add or update tasks")]}
    
    elif intent == "show_tasks" and user_id:
        rows = fetch_tasks(user_id=user_id)
        if rows:
            advice = llm_prioritize_tasks(rows, user_name)
            task_list = "\n".join([f"• {r[1]} (due {r[3]})" for r in rows[:5]])
            response = f"📋 Here's a quick look at your tasks:\n{task_list}"
            if advice:
                response += f"\n\n🤖 **My advice:**\n{advice}"
            return {"messages": [AIMessage(content=response)]}
        else:
            return {"messages": [AIMessage(content=f"You don't have any tasks yet, {user_name}. Would you like to add one?")]}
    
    elif intent == "add_task":
        # Handle natural language task creation using LLM-extracted parameters
        params = intent_result.get("parameters", {})
        title = params.get("title", "").strip()
        description = params.get("description", "").strip()
        deadline_str = params.get("deadline", "").strip()
        priority_raw = params.get("priority", 3)
        status = params.get("status", "pending")
        task_user_id = params.get("user_id") or user_id
        
        if not title:
            return {"messages": [AIMessage(content="I couldn't understand the task title. Please say something like: 'Add task: Review AI paper by next Monday, high priority'")]}
        
        if not task_user_id:
            return {"messages": [AIMessage(content="I need to know which user this task is for. Please make sure you're logged in.")]}
        
        # Parse deadline with proper time handling
        from datetime import datetime, timedelta
        deadline = None
        if deadline_str:
            try:
                # Try parsing various formats
                for fmt in ['%Y-%m-%d %H:%M', '%Y-%m-%d', '%Y/%m/%d %H:%M', '%Y/%m/%d']:
                    try:
                        deadline = datetime.strptime(deadline_str, fmt)
                        break
                    except:
                        continue
                
                # If no time was specified and it's just a date, use 17:00 (end of day)
                if deadline and deadline.hour == 0 and deadline.minute == 0:
                    if '%H' not in deadline_str and ':' not in deadline_str:
                        deadline = deadline.replace(hour=17, minute=0)
            except Exception as e:
                deadline = None
        
        # If still no deadline, try relative parsing
        if not deadline and deadline_str:
            text_lower = deadline_str.lower()
            now = datetime.now()
            if 'today' in text_lower:
                deadline = now.replace(hour=17, minute=0, second=0, microsecond=0)
            elif 'tomorrow' in text_lower:
                deadline = (now + timedelta(days=1)).replace(hour=17, minute=0, second=0, microsecond=0)
            elif 'monday' in text_lower:
                days_ahead = (0 - now.weekday()) % 7
                if days_ahead == 0:
                    days_ahead = 7
                deadline = (now + timedelta(days=days_ahead)).replace(hour=17, minute=0, second=0, microsecond=0)
            elif 'next week' in text_lower:
                deadline = (now + timedelta(days=7)).replace(hour=17, minute=0, second=0, microsecond=0)
        
        if not deadline:
            deadline = datetime.now() + timedelta(days=7)
            deadline = deadline.replace(hour=17, minute=0, second=0, microsecond=0)
        
        # Parse priority (handle string or int)
        priority = 3  # Default medium
        if isinstance(priority_raw, int):
            priority = priority_raw
        elif isinstance(priority_raw, str):
            priority_lower = priority_raw.lower()
            if priority_lower in ['1', 'high', 'urgent']:
                priority = 1
            elif priority_lower in ['2']:
                priority = 2
            elif priority_lower in ['3', 'medium', 'normal']:
                priority = 3
            elif priority_lower in ['4']:
                priority = 4
            elif priority_lower in ['5', 'low']:
                priority = 5
        
        # Insert task into database
        try:
            with get_connection() as conn:
                with conn.cursor() as cur:
                    cur.execute(
                        """
                        INSERT INTO tasks (user_id, title, description, deadline, priority, status)
                        VALUES (%s, %s, %s, %s, %s, %s)
                        RETURNING id
                        """,
                        (task_user_id, title, description, deadline, priority, status),
                    )
                    new_id = cur.fetchone()[0]
                conn.commit()
            
            friendly_date = format_date_friendly(deadline)
            friendly_priority = format_priority_friendly(priority)
            
            response = f"""✅ Great, {user_name}! I've added your new task:

📌 **{title}**
   {description if description else '(No description)'}
   📅 Due: {friendly_date}
   {friendly_priority}
   
Task ID: {new_id}

Would you like to see all your tasks? Just say "show my tasks"."""

            return {"messages": [AIMessage(content=response)]}
        except Exception as e:
            return {"messages": [AIMessage(content=f"Sorry, I couldn't add that task: {e}")]}
    
    else:
        # General AI response for other queries
        advice = llm_generate_advice(text, tasks, user_name)
        return {"messages": [AIMessage(content=advice)]}


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
    builder.add_node("agentic_chat", agentic_chat)  # LLM-powered reasoning node

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
            "agentic_chat": "agentic_chat",  # Route to AI reasoning
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
    builder.add_edge("agentic_chat", END)  # AI chat ends after response

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

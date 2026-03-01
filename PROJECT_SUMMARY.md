# Academic Task Manager - Project Summary

## Executive Summary

This project developed an **Agentic AI Academic Task Manager** - an intelligent system designed to help MSc students manage coursework, deadlines, and academic tasks through AI-powered automation, scheduling, and reminders.

---

## 1. Framework Evaluation and Selection

### Frameworks Tested

We evaluated three leading agentic AI frameworks to determine the most suitable foundation for our academic task management system:

#### 1.1 AutoGen (Microsoft)
**Test File:** `test_autogen.py`

```python
from autogen import AssistantAgent, UserProxyAgent
assistant = AssistantAgent(name="assistant")
user = UserProxyAgent(name="user", human_input_mode="NEVER", code_execution_config={"use_docker": False})
user.initiate_chat(assistant, message="Hello, AutoGen!")
```

**Findings:**
- **Pros:** Multi-agent conversation capabilities, good for collaborative AI tasks
- **Cons:** Heavy dependency on external LLM APIs, complex configuration for simple workflows, overkill for structured task management
- **Verdict:** Not selected - designed primarily for multi-agent conversations rather than structured state management

#### 1.2 CrewAI
**Test File:** `test_crewai.py`

```python
from crewai import Agent, Task, Crew
from crewai.tools import tool

@tool
def example_tool() -> str:
    """A simple tool that says hello."""
    return "Hello from CrewAI!"

agent = Agent(name="TestAgent", role="Greeter", goal="Say hello", backstory="...", tools=[example_tool])
task = Task(description="Say hello", agent=agent)
crew = Crew(tasks=[task])
results = crew.run()
```

**Findings:**
- **Pros:** Role-based agent design, good abstraction for team-like AI workflows
- **Cons:** Requires LLM for every operation (expensive), role-based model doesn't fit well with CRUD operations, steeper learning curve
- **Verdict:** Not selected - role-based paradigm doesn't align with task management workflows

#### 1.3 LangGraph (LangChain)
**Test File:** `test_langgraph.py`

```python
from langgraph.graph import StateGraph, START, END
from typing_extensions import TypedDict, Literal

class MyState(TypedDict):
    value: int
    target: int

def increment(state: MyState) -> dict:
    return {"value": state["value"] + 1}

def should_continue(state: MyState) -> Literal["increment", END]:
    return "increment" if state["value"] < state["target"] else END

builder = StateGraph(MyState)
builder.add_node("increment", increment)
builder.add_edge(START, "increment")
builder.add_conditional_edges("increment", should_continue)
graph = builder.compile()
```

**Findings:**
- **Pros:** 
  - Explicit state management with TypedDict
  - Graph-based workflow design for clear routing
  - Conditional edges for dynamic decision-making
  - Works without requiring LLM API calls for every operation
  - Direct database integration possible
  - Lightweight and efficient
- **Cons:** More manual setup required
- **Verdict:** ✅ **SELECTED** - Best fit for structured, state-driven task management

### Why LangGraph Was Chosen

| Criteria | AutoGen | CrewAI | LangGraph |
|----------|---------|--------|-----------|
| State Management | Limited | Limited | Excellent |
| LLM Dependency | High | High | Optional |
| Workflow Control | Conversational | Role-based | Graph-based |
| Database Integration | Complex | Complex | Simple |
| Cost Efficiency | Low | Low | High |
| Suitability for CRUD | Poor | Poor | Excellent |

**Key Decision Factors:**
1. **State-First Architecture:** LangGraph's TypedDict state management aligns perfectly with database CRUD operations
2. **Deterministic Routing:** Conditional edges allow precise control over workflow paths without LLM overhead
3. **Cost Efficiency:** Core operations don't require expensive LLM API calls
4. **Flexibility:** Easy to extend with additional nodes and edges as requirements evolve
5. **Testability:** Graph structure makes unit testing straightforward

---

## 2. System Architecture

### 2.1 Three-Tier Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                     FRONTEND (React)                        │
│  - Modern UI with CSS gradients and cards                   │
│  - User management interface                                │
│  - Task CRUD operations                                     │
│  - Reminder triggers                                        │
│  - Responsive design                                        │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│                   BACKEND (Flask API)                       │
│  - RESTful endpoints (/api/users, /api/tasks, /api/reminders)│
│  - CORS support for cross-origin requests                   │
│  - JSON response formatting                                 │
│  - Environment-based configuration                          │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│                  AGENT CORE (LangGraph)                     │
│  - StateGraph with TypedDict state management               │
│  - Conditional routing based on command prefixes            │
│  - Nodes: help, show_tasks, add_task, update_task,         │
│           delete_task, create_user, list_users, reminders   │
│  - Email notification integration                           │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│                  DATABASE (PostgreSQL)                      │
│  - user_profiles: id, name, email, academic_program         │
│  - tasks: id, user_id, title, description, deadline,        │
│           priority, status, created_at                      │
│  - Full CRUD support with foreign key constraints           │
└─────────────────────────────────────────────────────────────┘
```

### 2.2 LangGraph Agent Workflow

```
                    ┌───────────────┐
                    │     START     │
                    └───────┬───────┘
                            │
                            ▼
                    ┌───────────────┐
                    │    Router     │◄─── Analyzes command prefix
                    └───────┬───────┘
                            │
        ┌───────────────────┼───────────────────┐
        │           │       │       │           │
        ▼           ▼       ▼       ▼           ▼
   ┌─────────┐ ┌─────────┐ ┌─────────┐ ┌─────────┐ ┌─────────┐
   │  help   │ │show_task│ │add_task │ │create_  │ │reminders│
   │         │ │         │ │         │ │  user   │ │         │
   └────┬────┘ └────┬────┘ └────┬────┘ └────┬────┘ └────┬────┘
        │           │           │           │           │
        └───────────┴───────────┴───────────┴───────────┘
                            │
                            ▼
                    ┌───────────────┐
                    │      END      │
                    └───────────────┘
```

---

## 3. Features Implemented

### 3.1 User Management
- Create users with name, email, and academic program
- List all users
- View individual user profiles
- Update user information
- Delete users (cascades to tasks)

### 3.2 Task Management
- Create tasks with title, description, deadline, priority, and status
- View tasks filtered by user, status, or search keywords
- Update task details and status
- Delete tasks
- Sort by deadline, priority, or creation date

### 3.3 Reminders
- Send email reminders for upcoming deadlines
- Configurable reminder window (default: 5 days)
- SMTP integration (Gmail supported)
- Task summary in reminder emails

### 3.4 Data Operations
- Export tasks to CSV
- Import tasks from CSV
- Bulk operations support

---

## 4. Technical Implementation Details

### 4.1 Backend Dependencies
```
flask              # Web framework
flask-cors         # Cross-origin support
psycopg2-binary    # PostgreSQL driver
python-dotenv      # Environment variables
typing_extensions  # Type hints
langchain-core     # LangChain foundation
langgraph          # Agent workflow framework
gunicorn           # Production WSGI server
```

### 4.2 Frontend Stack
- React 18.2 with functional components and hooks
- CSS3 with gradients, animations, and responsive design
- Fetch API for backend communication
- Environment-based API URL configuration

### 4.3 Database Schema
```sql
CREATE TABLE user_profiles (
    id SERIAL PRIMARY KEY,
    name VARCHAR(100) NOT NULL,
    email VARCHAR(100) UNIQUE,
    academic_program VARCHAR(100)
);

CREATE TABLE tasks (
    id SERIAL PRIMARY KEY,
    user_id INTEGER REFERENCES user_profiles(id) ON DELETE CASCADE,
    title VARCHAR(200) NOT NULL,
    description TEXT,
    deadline TIMESTAMP,
    priority INTEGER,
    status VARCHAR(50),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

---

## 5. Deployment Guide

### 5.1 Local Development
```bash
# Backend
cd Backend
pip install -r requirements.txt
python app.py

# Frontend
cd Frontend
npm install
npm start
```

### 5.2 Production Deployment
- **Backend:** Render, Heroku, or Railway with PostgreSQL
- **Frontend:** Vercel, Netlify, or GitHub Pages
- **Database:** Supabase, Render PostgreSQL, or ElephantSQL

---

## 6. Future Enhancements

1. **Natural Language Processing:** Allow users to add tasks via conversational input
2. **Smart Scheduling:** Automatic task prioritization based on deadlines and workload
3. **Calendar Integration:** Sync with Google Calendar or Outlook
4. **Mobile App:** React Native or Flutter implementation
5. **AI-Powered Suggestions:** Recommend optimal study schedules
6. **Collaboration Features:** Share tasks and schedules with study groups

---

## 7. Conclusion

The Agentic AI Academic Task Manager demonstrates the practical application of LangGraph for building intelligent, state-driven applications. By carefully evaluating multiple frameworks and selecting the most appropriate technology, we created a system that is:

- **Efficient:** Minimal LLM dependency for routine operations
- **Scalable:** Clean architecture supports future enhancements
- **User-Friendly:** Modern UI with intuitive workflow
- **Maintainable:** Well-structured codebase with clear separation of concerns

The project validates LangGraph as an excellent choice for agentic AI applications requiring structured state management and deterministic workflows.

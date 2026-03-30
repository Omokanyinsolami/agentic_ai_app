# Dissertation Design Report: Agentic AI for Education

**Student:** Kehinde Anthony Arowolo (S2461801)  
**Programme:** MSc Computer Science  
**Date:** March 2026

---

## 1. Introduction

This report presents the design and evaluation plan for an agentic AI system (hereafter referred to as "the agent") that supports MSc students in managing academic tasks such as coursework, independent study, and project milestones. The agent aims to move beyond static to-do lists and reminders by providing intelligent prioritization, constraint-aware scheduling, and adaptation when deadlines or available study time change. The design adopts a practical definition of agentic AI as goal-directed behaviour with autonomy and feedback-based adaptation (Sapkota et al., 2025; Bandi et al., 2025).

### 1.1 Novelty and Contribution

This work makes several distinct contributions that differentiate it from existing AI planners and productivity tools:

1. **Hybrid Architecture**: Unlike conventional calendar applications that simply display tasks, the agent actively reasons about constraints and generates feasible schedules. Unlike pure LLM-based chatbots that provide general advice without persistent state, the agent maintains a structured representation of tasks, deadlines, and constraints, enabling it to detect conflicts and adapt schedules over time.

2. **Bridge Between Classical and Modern AI**: The system bridges the gap between classical constraint-based scheduling algorithms (which are effective but rigid) and modern LLM-based interaction (which is flexible but often unreliable for structured planning).

3. **Empirical Contribution**: By combining graph-based deterministic routing (via LangGraph) with natural language interaction and real-time conflict detection, the agent provides a novel hybrid architecture that achieves both reliability and usability. This positions the work as an empirical contribution to agentic AI research, demonstrating how goal-directed autonomous behaviour can be operationalised in a constrained academic planning domain.

### 1.2 Project Aims and Objectives

1. Design a task management prototype that can prioritize and schedule academic tasks under constraints (deadlines, fixed commitments, available study blocks).
2. Implement an agent workflow that adapts schedules when new tasks appear or constraints change.
3. Evaluate the agent in a controlled simulated academic environment using objective performance metrics and reproducible scenario testing.

### 1.3 Research Questions and Hypotheses

**Research Questions:**
- **RQ1 (Efficiency)**: Does the agent reduce planning time compared with a baseline rule-based scheduler in realistic MSc scenarios?
- **RQ2 (Schedule quality)**: Does the agent produce schedules with fewer conflicts and higher deadline compliance than the baseline?
- **RQ3 (Adaptation)**: How effectively does the agent adapt schedules when constraints change (new tasks, shifted deadlines, lost time blocks)?

**Hypotheses:**
- **H1**: The agent will generate feasible schedules faster than the baseline scheduler in complex scenarios.
- **H2**: Agent-generated schedules will have fewer conflicts and higher deadline compliance rates than baseline schedules.
- **H3**: The agent will successfully adapt to constraint changes with minimal disruption to existing task allocations.

### 1.4 System Limitations and Assumptions

- The agent is evaluated in simulation and controlled scenario testing rather than long-term real-world deployment.
- Performance depends on the completeness and accuracy of user-provided task details (deadlines, estimated durations, constraints).
- The project focuses on academic task management, not general productivity or non-academic life planning.

---

## 2. Literature Review and Background

This chapter provides a comprehensive review of relevant literature across three key domains: AI applications in education, agentic AI systems for educational support, and the software frameworks that enable agentic behaviour.

### 2.1 Advances in AI for Education

#### 2.1.1 Generative AI in Teaching and Assessment

Generative AI, particularly large language models (LLMs), has transformed educational technology. These systems now support:

- **Intelligent Tutoring**: AI-powered tutoring systems provide personalised explanations, adapt to student learning pace, and offer immediate feedback (Deng et al., 2025).
- **Automated Assessment**: LLMs assist in grading essays, providing formative feedback, and identifying learning gaps.
- **Content Generation**: AI generates practice problems, study materials, and summaries tailored to curriculum objectives.

#### 2.1.2 Meta-Analyses and Educational Technology Studies

Recent meta-analyses provide empirical evidence for AI effectiveness in education:

- **Deng et al. (2025)** conducted a systematic review of 50+ experimental studies, finding that ChatGPT-based interventions improved academic performance by 0.4–0.6 standard deviations on average, with strongest effects in writing and comprehension tasks.
- **Bhuiyan et al. (2025)** examined adoption patterns, finding that student AI literacy and institutional support significantly moderate effectiveness.

#### 2.1.3 Self-Regulated Learning Support

AI tools increasingly support self-regulated learning (SRL) by:
- Prompting metacognitive reflection
- Tracking learning progress
- Suggesting study strategies based on performance patterns

However, studies caution that over-reliance on AI may reduce student agency if not carefully designed (Bhuiyan et al., 2025).

### 2.2 Advances in Agentic AI for Education

#### 2.2.1 Defining Agentic AI in Educational Contexts

Agentic AI refers to systems exhibiting three core properties (Sapkota et al., 2025):

1. **Goal-Directed Autonomy**: The system pursues objectives without step-by-step human guidance.
2. **Tool Use**: The agent orchestrates external resources (databases, APIs, calculators) to achieve goals.
3. **Feedback-Based Adaptation**: The system adjusts behaviour based on environmental changes and outcomes.

In education, agentic AI manifests as:
- **Adaptive Tutoring Agents**: Systems that autonomously adjust difficulty, select problems, and modify explanations based on student performance.
- **Autonomous Learning Companions**: AI assistants that proactively suggest resources, remind students of deadlines, and track progress.
- **Planning Assistants**: Agents that generate and adapt study schedules based on constraints and goals.

#### 2.2.2 Comparison with Prior Agentic Systems

| System Type | Autonomy Level | Adaptation | Tool Use | Educational Focus |
|-------------|----------------|------------|----------|-------------------|
| Traditional Calendars | None | None | None | Low |
| Rule-Based Schedulers | Low | Limited | None | Medium |
| LLM Chatbots | Medium | Limited | Limited | Medium |
| **This Agent** | **High** | **Full** | **Extensive** | **High** |

Our agent distinguishes itself by combining:
- Persistent state management (unlike stateless chatbots)
- Constraint-aware scheduling (unlike simple to-do apps)
- Natural language interaction (unlike rigid form-based systems)
- Autonomous replanning (unlike static rule-based schedulers)

#### 2.2.3 Evaluation Frameworks for Educational Agents

Mohammadi et al. (2025) propose evaluation dimensions for LLM agents:
- **Task completion rate**: Does the agent achieve stated goals?
- **Efficiency**: How quickly does it complete tasks?
- **Robustness**: Does it handle edge cases gracefully?
- **Explainability**: Can users understand its decisions?

These dimensions inform our evaluation design (Chapter 7).

### 2.3 Overview of Agentic Software Frameworks

#### 2.3.1 LangGraph

LangGraph (developed by LangChain) is a graph-based orchestration framework for building stateful, multi-step agent workflows.

**Key Features:**
- **StateGraph**: Directed graph where nodes represent processing steps and edges define transitions.
- **Conditional Routing**: Edges can be conditional, enabling dynamic workflow paths.
- **Persistence**: Built-in state management allows agents to maintain context across interactions.
- **Human-in-the-Loop**: Supports breakpoints for human review and intervention.

**Why LangGraph for This Project:**
LangGraph's deterministic graph structure ensures reliable, testable behaviour—critical for academic scheduling where predictability matters. Unlike pure LLM chains, LangGraph separates reasoning from execution, enabling systematic debugging and evaluation.

#### 2.3.2 AutoGen

AutoGen (Microsoft) enables multi-agent conversations where multiple AI agents collaborate to solve problems.

**Key Features:**
- Multi-agent orchestration
- Code execution capabilities
- Customizable agent roles

**Comparison with LangGraph:**
While AutoGen excels at collaborative problem-solving, LangGraph's single-agent, workflow-focused design better suits our scheduling task where deterministic behaviour is prioritised over multi-agent negotiation.

#### 2.3.3 ReAct Framework

ReAct (Reason + Act) interleaves reasoning traces with action execution, enabling LLMs to plan and execute in alternating steps.

**Pattern:**
```
Thought: I need to check the user's available time slots.
Action: query_availability(user_id=1)
Observation: [Monday 9-12, Tuesday 14-17, ...]
Thought: The task deadline is Friday, so I should schedule it early in the week.
Action: schedule_task(task_id=5, slot="Monday 9-11")
```

**Application in This Project:**
Our agent incorporates ReAct-style reasoning in the LLM scheduling node, where the model reasons about constraints before generating slot assignments.

#### 2.3.4 Toolformer-Based Architectures

Toolformer (Schick et al., 2023) demonstrated that LLMs can learn to use tools (calculators, search engines, databases) by embedding API calls in generated text.

**Relevance:**
Our agent uses tool-calling patterns where the LLM generates structured JSON to invoke database operations, schedule queries, and conflict checks.

#### 2.3.5 Memory-Augmented Agent Platforms

Modern agentic systems augment LLMs with external memory:
- **Short-term memory**: Conversation context within a session.
- **Long-term memory**: Persistent storage of user preferences, task history, and learned patterns.

Our agent implements memory through:
- PostgreSQL database for persistent task/schedule storage
- LangGraph state for session context
- User profile storage for preferences

#### 2.3.6 Workflow Orchestration Comparison

| Framework | Architecture | Determinism | State Management | Best For |
|-----------|-------------|-------------|------------------|----------|
| LangGraph | Graph-based | High | Built-in | Single-agent workflows |
| AutoGen | Multi-agent | Medium | Per-agent | Collaborative tasks |
| ReAct | Sequential | Medium | External | Reasoning chains |
| LangChain | Chain-based | Medium | Limited | Simple pipelines |

---

## 3. Project Requirements and Scope

This chapter elaborates the system requirements, stakeholder needs, and operational constraints.

### 3.1 Stakeholder Analysis

**Primary Stakeholders:**
- **MSc Students**: End users managing coursework, dissertations, and project deadlines.
- **Academic Supervisors**: Benefit from students' improved organisation and deadline compliance.

**Secondary Stakeholders:**
- **University IT Services**: May host or support deployment.
- **Educational Researchers**: May use system for studying AI-assisted learning.

### 3.2 Functional Requirements

| ID | Requirement | Priority | Description |
|----|------------|----------|-------------|
| FR1 | User Registration | Must | Users can create accounts with email, password, and academic program. |
| FR2 | User Authentication | Must | Secure login with password hashing (bcrypt/werkzeug). |
| FR3 | Task Creation (Form) | Must | Users can add tasks via structured form with title, description, deadline, priority. |
| FR4 | Task Creation (NLP) | Should | Users can add tasks using natural language (e.g., "Add dissertation chapter due Friday"). |
| FR5 | Task Listing | Must | Users can view all their tasks with filtering and sorting options. |
| FR6 | Task Editing | Must | Users can modify task details (title, deadline, priority, status). |
| FR7 | Task Deletion | Must | Users can remove tasks (soft delete with recovery option). |
| FR8 | Availability Management | Must | Users can define weekly availability slots (day, start time, end time). |
| FR9 | Schedule Generation | Must | System generates optimised schedule placing tasks in available time slots. |
| FR10 | AI-Powered Scheduling | Should | LLM reasons about task priorities, deadlines, and workload balance. |
| FR11 | Schedule Adaptation | Must | System re-generates schedule when constraints change (new task, deadline shift). |
| FR12 | Conflict Detection | Must | System identifies scheduling conflicts (overbooked slots, missed deadlines). |
| FR13 | Natural Language Chat | Should | Users can interact via conversational interface for task management. |
| FR14 | Prioritisation Advice | Should | Agent explains why tasks are prioritised in a particular order. |
| FR15 | Email Reminders | Could | System sends email reminders for upcoming deadlines. |
| FR16 | Schedule Visualisation | Must | Users can view generated schedule in calendar/timeline format. |
| FR17 | Offline Access | Should | PWA enables basic functionality without internet connection. |

### 3.3 Non-Functional Requirements

| ID | Category | Requirement | Target |
|----|----------|-------------|--------|
| NFR1 | Performance | Schedule generation time | < 5 seconds for 20 tasks |
| NFR2 | Performance | API response time | < 500ms for CRUD operations |
| NFR3 | Reliability | System uptime | 99% during evaluation period |
| NFR4 | Usability | SUS score | > 68 (above average) |
| NFR5 | Usability | Task creation time | < 30 seconds per task |
| NFR6 | Security | Password storage | Hashed with bcrypt (cost factor ≥ 12) |
| NFR7 | Security | Session management | Secure tokens, automatic expiry |
| NFR8 | Privacy | Data minimisation | Store only essential task data |
| NFR9 | Privacy | No third-party sharing | Data not transmitted to external services (except LLM API) |
| NFR10 | Accessibility | Mobile responsiveness | Functional on screens ≥ 320px width |
| NFR11 | Accessibility | Keyboard navigation | All features accessible via keyboard |
| NFR12 | Maintainability | Code documentation | All functions documented with docstrings |
| NFR13 | Scalability | Concurrent users | Support ≥ 50 simultaneous users |

### 3.4 Environmental Constraints

| Constraint | Description | Rationale |
|------------|-------------|-----------|
| PWA Architecture | Frontend must be a Progressive Web App | Enables offline access, mobile installation, push notifications |
| Offline Mode | Core features must work without internet | Students may have unreliable connectivity |
| Data Minimisation | Collect only essential information | GDPR compliance and privacy best practices |
| Free-Tier Compatible | Use free/low-cost services where possible | Student project budget constraints |
| Cross-Platform | Must work on Windows, macOS, Linux, iOS, Android | Students use diverse devices |

### 3.5 Use Cases

#### Use Case 1: Student Enters Tasks Using Natural Language

**Actor:** Student  
**Precondition:** Student is logged in  
**Main Flow:**
1. Student opens the AI Chat interface.
2. Student types: "Add a task to finish methodology chapter by next Wednesday, high priority"
3. Agent parses the natural language input.
4. Agent extracts: title="Finish methodology chapter", deadline=next Wednesday, priority=high.
5. Agent creates the task in the database.
6. Agent confirms: "I've added 'Finish methodology chapter' due Wednesday with high priority."
7. Task appears in the student's task list.

**Alternative Flow:**
- 3a. If parsing fails, agent asks for clarification: "I couldn't understand the deadline. When is this due?"

**Postcondition:** Task is stored in database and visible in task list.

---

#### Use Case 2: Agent Generates a Weekly Schedule

**Actor:** Student  
**Precondition:** Student has ≥1 pending task and defined availability  
**Main Flow:**
1. Student navigates to AI Schedule tab.
2. Student clicks "Generate Schedule".
3. System retrieves all pending tasks and availability slots.
4. Agent analyses tasks (deadlines, priorities, estimated duration).
5. Agent uses LLM to reason about optimal placement.
6. Agent places tasks into available time slots.
7. System stores scheduled slots in database.
8. Schedule is displayed with AI reasoning explanations.

**Alternative Flow:**
- 4a. If no availability defined, system uses default (9 AM–5 PM weekdays) and warns user.
- 5a. If LLM unavailable, system falls back to EDF (Earliest Deadline First) algorithm.

**Postcondition:** Feasible schedule generated and displayed with explanations.

---

#### Use Case 3: Agent Adapts Schedule When Deadline Changes

**Actor:** Student  
**Precondition:** Student has an existing schedule  
**Main Flow:**
1. Student edits a task, changing deadline from Friday to Wednesday.
2. System detects constraint change.
3. Agent triggers adaptation process.
4. Agent re-evaluates all affected tasks.
5. Agent re-generates schedule with updated constraints.
6. Agent explains changes: "Moved 'Literature Review' earlier to accommodate new deadline."
7. Updated schedule is displayed.

**Postcondition:** Schedule reflects new constraints with minimal disruption.

---

#### Use Case 4: Student Requests Prioritisation Explanation

**Actor:** Student  
**Precondition:** Student has multiple tasks  
**Main Flow:**
1. Student opens AI Chat.
2. Student asks: "Why is the dissertation chapter prioritised over the lab report?"
3. Agent retrieves both tasks from database.
4. Agent analyses: deadlines, priorities, estimated effort.
5. Agent generates explanation using LLM.
6. Agent responds: "The dissertation chapter is prioritised because: (1) it has an earlier deadline (March 10 vs March 15), (2) it has higher priority (high vs medium), and (3) it typically requires more focused work time."

**Postcondition:** Student understands prioritisation rationale.

---

#### Use Case 5: Student Views Schedule Conflicts

**Actor:** Student  
**Precondition:** Student has tasks with potential conflicts  
**Main Flow:**
1. System automatically runs conflict detection.
2. System identifies: 3 high-priority tasks due same day.
3. System displays conflict warning in UI.
4. Student clicks on conflict notification.
5. System shows affected tasks and recommendations.
6. Agent suggests: "Consider extending deadline for one task or allocating weekend time."

**Postcondition:** Student aware of conflicts and has actionable recommendations.

---

### 3.6 Use Case Diagram

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                     AGENTIC AI FOR EDUCATION SYSTEM                        │
│                                                                             │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │                                                                     │   │
│  │    ┌──────────────┐      ┌──────────────────────────────────┐      │   │
│  │    │   Register   │      │     Task Management               │      │   │
│  │    │   Account    │      │  ┌────────────────────────────┐  │      │   │
│  │    └──────┬───────┘      │  │  Create Task (Form)        │  │      │   │
│  │           │              │  └────────────────────────────┘  │      │   │
│  │    ┌──────┴───────┐      │  ┌────────────────────────────┐  │      │   │
│  │    │    Login     │      │  │  Create Task (NLP)         │  │      │   │
│  │    └──────┬───────┘      │  └────────────────────────────┘  │      │   │
│  │           │              │  ┌────────────────────────────┐  │      │   │
│  │           │              │  │  Edit Task                 │  │      │   │
│  │           │              │  └────────────────────────────┘  │      │   │
│  │           │              │  ┌────────────────────────────┐  │      │   │
│  │           │              │  │  Delete Task               │  │      │   │
│  │           │              │  └────────────────────────────┘  │      │   │
│  │           │              │  ┌────────────────────────────┐  │      │   │
│  │           │              │  │  View Tasks                │  │      │   │
│  │           │              │  └────────────────────────────┘  │      │   │
│  │           │              └──────────────────────────────────┘      │   │
│  │           │                                                        │   │
│  │   ┌───────┴────────┐     ┌──────────────────────────────────┐     │   │
│  │   │                │     │     Scheduling                    │     │   │
│  │   │    STUDENT     │─────│  ┌────────────────────────────┐  │     │   │
│  │   │    (Actor)     │     │  │  Set Availability          │  │     │   │
│  │   │                │     │  └────────────────────────────┘  │     │   │
│  │   └───────┬────────┘     │  ┌────────────────────────────┐  │     │   │
│  │           │              │  │  Generate Schedule         │◄─┼──┐  │   │
│  │           │              │  └────────────────────────────┘  │  │  │   │
│  │           │              │  ┌────────────────────────────┐  │  │  │   │
│  │           │              │  │  View Schedule             │  │  │  │   │
│  │           │              │  └────────────────────────────┘  │  │  │   │
│  │           │              │  ┌────────────────────────────┐  │  │  │   │
│  │           │              │  │  Adapt Schedule            │◄─┼──┤  │   │
│  │           │              │  └────────────────────────────┘  │  │  │   │
│  │           │              └──────────────────────────────────┘  │  │   │
│  │           │                                                    │  │   │
│  │           │              ┌──────────────────────────────────┐  │  │   │
│  │           │              │     AI Features                  │  │  │   │
│  │           └──────────────│  ┌────────────────────────────┐  │  │  │   │
│  │                          │  │  Chat with Agent           │  │  │  │   │
│  │                          │  └────────────────────────────┘  │  │  │   │
│  │                          │  ┌────────────────────────────┐  │  │  │   │
│  │                          │  │  Get Prioritisation Advice │  │  │  │   │
│  │                          │  └────────────────────────────┘  │  │  │   │
│  │                          │  ┌────────────────────────────┐  │  │  │   │
│  │                          │  │  View Conflicts            │  │  │  │   │
│  │                          │  └────────────────────────────┘  │  │  │   │
│  │                          └──────────────────────────────────┘  │  │   │
│  │                                                                │  │   │
│  │                          ┌──────────────────────────────────┐  │  │   │
│  │                          │     LLM SERVICE                  │──┘  │   │
│  │                          │     (Groq API)                   │     │   │
│  │                          │  - Intent Understanding          │     │   │
│  │                          │  - Schedule Reasoning            │     │   │
│  │                          │  - Explanation Generation        │     │   │
│  │                          └──────────────────────────────────┘     │   │
│  │                                                                   │   │
│  └───────────────────────────────────────────────────────────────────┘   │
│                                                                           │
└───────────────────────────────────────────────────────────────────────────┘
```

---

## 4. System Design

This chapter provides detailed technical design of the agentic AI system, including architecture diagrams, component specifications, workflow models, and agent behaviour design.

### 4.1 Overall System Architecture

The system follows a three-tier architecture with an embedded agent core:

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                              PRESENTATION TIER                              │
│  ┌───────────────────────────────────────────────────────────────────────┐  │
│  │                    Progressive Web App (React)                        │  │
│  │  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐  │  │
│  │  │   Account   │  │    Tasks    │  │ AI Schedule │  │   AI Chat   │  │  │
│  │  │    View     │  │    View     │  │    View     │  │    View     │  │  │
│  │  └─────────────┘  └─────────────┘  └─────────────┘  └─────────────┘  │  │
│  │                                                                       │  │
│  │  Features: Offline Support | Push Notifications | Mobile Install     │  │
│  └───────────────────────────────────────────────────────────────────────┘  │
│                                    │ REST API                               │
│                                    ▼                                        │
├─────────────────────────────────────────────────────────────────────────────┤
│                              APPLICATION TIER                               │
│  ┌───────────────────────────────────────────────────────────────────────┐  │
│  │                      Flask Backend (Python)                           │  │
│  │  ┌─────────────────────────────────────────────────────────────────┐  │  │
│  │  │                      API Endpoints                              │  │  │
│  │  │  /api/users  /api/tasks  /api/schedule  /api/availability       │  │  │
│  │  │  /api/chat   /api/reminders  /api/conflicts                     │  │  │
│  │  └─────────────────────────────────────────────────────────────────┘  │  │
│  │                                    │                                  │  │
│  │  ┌─────────────────────────────────┴─────────────────────────────┐   │  │
│  │  │                    AGENT CORE (LangGraph)                     │   │  │
│  │  │  ┌─────────┐  ┌─────────┐  ┌─────────┐  ┌─────────────────┐   │   │  │
│  │  │  │ Intent  │  │  Task   │  │Schedule │  │   Adaptation    │   │   │  │
│  │  │  │ Parser  │→ │ Router  │→ │Generator│→ │     Engine      │   │   │  │
│  │  │  └─────────┘  └─────────┘  └─────────┘  └─────────────────┘   │   │  │
│  │  │                         │                                     │   │  │
│  │  │                         ▼                                     │   │  │
│  │  │  ┌─────────────────────────────────────────────────────────┐  │   │  │
│  │  │  │              LLM Service (Groq API)                     │  │   │  │
│  │  │  │         llama-3.3-70b-versatile via langchain-groq      │  │   │  │
│  │  │  └─────────────────────────────────────────────────────────┘  │   │  │
│  │  └───────────────────────────────────────────────────────────────┘   │  │
│  └───────────────────────────────────────────────────────────────────────┘  │
│                                    │ SQL                                    │
│                                    ▼                                        │
├─────────────────────────────────────────────────────────────────────────────┤
│                                DATA TIER                                    │
│  ┌───────────────────────────────────────────────────────────────────────┐  │
│  │                        PostgreSQL Database                            │  │
│  │  ┌──────────────┐  ┌──────────┐  ┌──────────────┐  ┌──────────────┐  │  │
│  │  │user_profiles │  │  tasks   │  │ availability │  │scheduled_slots│  │  │
│  │  └──────────────┘  └──────────┘  └──────────────┘  └──────────────┘  │  │
│  └───────────────────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────────────────┘
```

### 4.2 Detailed Architecture Components

#### 4.2.1 LangGraph Agent Workflow

The agent uses a state graph architecture where each node performs a specific function:

```
                    ┌─────────────────┐
                    │      START      │
                    └────────┬────────┘
                             │
                             ▼
                    ┌─────────────────┐
                    │  Parse Input    │
                    │  (Intent Node)  │
                    └────────┬────────┘
                             │
              ┌──────────────┼──────────────┐
              │              │              │
              ▼              ▼              ▼
     ┌─────────────┐ ┌─────────────┐ ┌─────────────┐
     │ Task CRUD   │ │  Schedule   │ │   Chat/     │
     │   Node      │ │   Node      │ │  Advice     │
     └──────┬──────┘ └──────┬──────┘ └──────┬──────┘
            │              │              │
            └──────────────┼──────────────┘
                           │
                           ▼
                  ┌─────────────────┐
                  │   Conflict      │
                  │   Detection     │
                  └────────┬────────┘
                           │
                           ▼
                  ┌─────────────────┐
                  │  Format         │
                  │  Response       │
                  └────────┬────────┘
                           │
                           ▼
                    ┌─────────────────┐
                    │      END        │
                    └─────────────────┘
```

**State Schema:**
```python
class AgentState(TypedDict):
    messages: Annotated[list[BaseMessage], add_messages]
    user_id: Optional[int]
    intent: Optional[str]
    task_data: Optional[dict]
    schedule_data: Optional[list]
    conflicts: Optional[list]
```

#### 4.2.2 Scheduling Engine Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                    SCHEDULING ENGINE                            │
│                                                                 │
│  ┌─────────────────┐    ┌─────────────────┐                    │
│  │  Task Retrieval │───▶│   Availability  │                    │
│  │     Module      │    │    Retrieval    │                    │
│  └─────────────────┘    └────────┬────────┘                    │
│                                  │                              │
│                                  ▼                              │
│                    ┌─────────────────────────┐                  │
│                    │   LLM Scheduling Logic  │                  │
│                    │  (if Groq API available)│                  │
│                    └────────────┬────────────┘                  │
│                                 │                               │
│                    ┌────────────┴────────────┐                  │
│                    │                         │                  │
│               [LLM Available]          [LLM Unavailable]        │
│                    │                         │                  │
│                    ▼                         ▼                  │
│          ┌─────────────────┐      ┌─────────────────┐          │
│          │  AI-Optimised   │      │  EDF Algorithm  │          │
│          │   Scheduling    │      │   (Fallback)    │          │
│          └────────┬────────┘      └────────┬────────┘          │
│                   │                        │                    │
│                   └───────────┬────────────┘                    │
│                               │                                 │
│                               ▼                                 │
│                    ┌─────────────────────────┐                  │
│                    │   Slot Allocation       │                  │
│                    │   & Conflict Check      │                  │
│                    └────────────┬────────────┘                  │
│                                 │                               │
│                                 ▼                               │
│                    ┌─────────────────────────┐                  │
│                    │   Database Persistence  │                  │
│                    │   (scheduled_slots)     │                  │
│                    └─────────────────────────┘                  │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

#### 4.2.3 NLP Task Parsing Pipeline

```
User Input: "Add dissertation chapter due Friday high priority"
                              │
                              ▼
                    ┌─────────────────┐
                    │   Tokenisation  │
                    └────────┬────────┘
                             │
                             ▼
                    ┌─────────────────┐
                    │ Intent Detection│──▶ "add_task"
                    │    (LLM/Regex)  │
                    └────────┬────────┘
                             │
                             ▼
                    ┌─────────────────┐
                    │ Entity Extraction│
                    │  - title: "dissertation chapter"
                    │  - deadline: "Friday" → 2026-03-06
                    │  - priority: "high" → 1
                    └────────┬────────┘
                             │
                             ▼
                    ┌─────────────────┐
                    │   Validation    │
                    │  & Normalisation│
                    └────────┬────────┘
                             │
                             ▼
                    ┌─────────────────┐
                    │ Database Insert │
                    └─────────────────┘
```

#### 4.2.4 Data Model (Entity-Relationship Diagram)

```
┌──────────────────┐       ┌──────────────────┐
│   user_profiles  │       │      tasks       │
├──────────────────┤       ├──────────────────┤
│ PK id            │       │ PK id            │
│    name          │       │ FK user_id       │───┐
│    email (unique)│◄──────│    title         │   │
│    academic_prog │   1:N │    description   │   │
│    password_hash │       │    deadline      │   │
│    preferences   │       │    priority      │   │
│    created_at    │       │    status        │   │
└──────────────────┘       │    dependencies  │   │
                           │    deleted       │   │
                           │    created_at    │   │
                           └──────────────────┘   │
                                                  │
┌──────────────────┐       ┌──────────────────┐   │
│student_availability│     │ scheduled_slots  │   │
├──────────────────┤       ├──────────────────┤   │
│ PK id            │       │ PK id            │   │
│ FK user_id       │───┐   │ FK user_id       │───┤
│    day_of_week   │   │   │ FK task_id       │───┘
│    start_time    │   │   │    scheduled_date│
│    end_time      │   │   │    start_time    │
│    location      │   │   │    end_time      │
│    created_at    │   │   │    status        │
└──────────────────┘   │   │    ai_reasoning  │
                       │   │    confidence    │
                       │   │    created_at    │
                       │   │    updated_at    │
                       │   └──────────────────┘
                       │
                       └─── All user-related tables link to user_profiles
```

### 4.3 Educational Workflows

#### 4.3.1 Academic Task Workflow (Activity Diagram)

```
┌─────────┐
│  Start  │
└────┬────┘
     │
     ▼
┌─────────────────────┐
│ Student identifies  │
│ academic task       │
└──────────┬──────────┘
           │
           ▼
     ┌───────────┐
     │   Input   │
     │  Method?  │
     └─────┬─────┘
           │
     ┌─────┴─────┐
     │           │
     ▼           ▼
┌─────────┐ ┌─────────┐
│  Form   │ │   NLP   │
│  Entry  │ │  Chat   │
└────┬────┘ └────┬────┘
     │           │
     └─────┬─────┘
           │
           ▼
┌─────────────────────┐
│ Agent validates     │
│ task details        │
└──────────┬──────────┘
           │
     ┌─────┴─────┐
     │  Valid?   │
     └─────┬─────┘
     NO    │    YES
     ┌─────┴─────┐
     │           │
     ▼           ▼
┌─────────┐ ┌─────────────────┐
│  Show   │ │ Store task in   │
│  Error  │ │ database        │
└─────────┘ └────────┬────────┘
                     │
                     ▼
           ┌─────────────────────┐
           │ Agent checks for    │
           │ schedule impact     │
           └──────────┬──────────┘
                      │
                ┌─────┴─────┐
                │ Impact?   │
                └─────┬─────┘
                      │
           ┌──────────┴──────────┐
           │                     │
           ▼                     ▼
┌─────────────────┐    ┌─────────────────┐
│ Trigger schedule│    │ Confirm task    │
│ adaptation      │    │ added           │
└────────┬────────┘    └────────┬────────┘
         │                      │
         └──────────┬───────────┘
                    │
                    ▼
              ┌─────────┐
              │   End   │
              └─────────┘
```

#### 4.3.2 Schedule Generation Workflow (Sequence Diagram)

```
┌────────┐     ┌─────────┐     ┌─────────┐     ┌──────────┐     ┌────────┐
│Student │     │Frontend │     │ Backend │     │LangGraph │     │Database│
└───┬────┘     └────┬────┘     └────┬────┘     └────┬─────┘     └───┬────┘
    │               │               │               │               │
    │ Click         │               │               │               │
    │ "Generate"    │               │               │               │
    │──────────────▶│               │               │               │
    │               │               │               │               │
    │               │ POST /api/    │               │               │
    │               │ schedule/     │               │               │
    │               │ generate      │               │               │
    │               │──────────────▶│               │               │
    │               │               │               │               │
    │               │               │ generate_ai_  │               │
    │               │               │ schedule()    │               │
    │               │               │──────────────▶│               │
    │               │               │               │               │
    │               │               │               │ Fetch tasks   │
    │               │               │               │──────────────▶│
    │               │               │               │               │
    │               │               │               │◀──────────────│
    │               │               │               │ tasks[]       │
    │               │               │               │               │
    │               │               │               │ Fetch         │
    │               │               │               │ availability  │
    │               │               │               │──────────────▶│
    │               │               │               │               │
    │               │               │               │◀──────────────│
    │               │               │               │ slots[]       │
    │               │               │               │               │
    │               │               │  ┌──────────────────────┐    │
    │               │               │  │ LLM Reasoning        │    │
    │               │               │  │ - Analyze deadlines  │    │
    │               │               │  │ - Consider priorities│    │
    │               │               │  │ - Balance workload   │    │
    │               │               │  └──────────────────────┘    │
    │               │               │               │               │
    │               │               │               │ Store         │
    │               │               │               │ scheduled_    │
    │               │               │               │ slots         │
    │               │               │               │──────────────▶│
    │               │               │               │               │
    │               │               │◀──────────────│               │
    │               │               │ {schedule,    │               │
    │               │               │  reasoning}   │               │
    │               │               │               │               │
    │               │◀──────────────│               │               │
    │               │ JSON response │               │               │
    │               │               │               │               │
    │◀──────────────│               │               │               │
    │ Display       │               │               │               │
    │ schedule      │               │               │               │
    │               │               │               │               │
```

#### 4.3.3 Schedule Adaptation Workflow (State-Transition Diagram)

```
                         ┌───────────────┐
                         │    STABLE     │
                         │   SCHEDULE    │
                         └───────┬───────┘
                                 │
              ┌──────────────────┼──────────────────┐
              │                  │                  │
              ▼                  ▼                  ▼
     ┌─────────────┐    ┌─────────────┐    ┌─────────────┐
     │   TASK      │    │  DEADLINE   │    │ AVAILABILITY│
     │   ADDED     │    │  CHANGED    │    │   CHANGED   │
     └──────┬──────┘    └──────┬──────┘    └──────┬──────┘
            │                  │                  │
            └──────────────────┼──────────────────┘
                               │
                               ▼
                      ┌─────────────────┐
                      │   CONSTRAINT    │
                      │   VIOLATION     │
                      │   DETECTED      │
                      └────────┬────────┘
                               │
                               ▼
                      ┌─────────────────┐
                      │   REPLANNING    │
                      │   IN PROGRESS   │
                      └────────┬────────┘
                               │
                    ┌──────────┴──────────┐
                    │                     │
                    ▼                     ▼
           ┌─────────────┐       ┌─────────────┐
           │  FEASIBLE   │       │ INFEASIBLE  │
           │  SCHEDULE   │       │  (Conflicts)│
           │   FOUND     │       └──────┬──────┘
           └──────┬──────┘              │
                  │                     ▼
                  │            ┌─────────────────┐
                  │            │   ALERT USER    │
                  │            │   (Recommend    │
                  │            │   actions)      │
                  │            └────────┬────────┘
                  │                     │
                  └──────────┬──────────┘
                             │
                             ▼
                    ┌─────────────────┐
                    │    SCHEDULE     │
                    │    UPDATED      │
                    └────────┬────────┘
                             │
                             ▼
                    ┌─────────────────┐
                    │    STABLE       │
                    │   SCHEDULE      │
                    └─────────────────┘
```

### 4.4 Agentic System Design

#### 4.4.1 Agent Autonomy Loop

The agent implements a classic autonomy loop adapted for academic scheduling:

```
                    ┌─────────────────────────────────────────┐
                    │                                         │
                    │         GOAL                            │
                    │   "Generate conflict-free schedule      │
                    │    maximising deadline compliance"      │
                    │                                         │
                    └────────────────┬────────────────────────┘
                                     │
                                     ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                                                                         │
│  ┌──────────────┐    ┌──────────────┐    ┌──────────────┐    ┌───────┐ │
│  │              │    │              │    │              │    │       │ │
│  │   PERCEIVE   │───▶│    PLAN      │───▶│    ACT       │───▶│EVALUATE│ │
│  │              │    │              │    │              │    │       │ │
│  └──────────────┘    └──────────────┘    └──────────────┘    └───┬───┘ │
│         ▲                                                        │     │
│         │                                                        │     │
│         └────────────────────────────────────────────────────────┘     │
│                              FEEDBACK LOOP                             │
│                                                                         │
└─────────────────────────────────────────────────────────────────────────┘

PERCEIVE:
- Query database for current tasks
- Fetch user availability
- Detect constraint changes

PLAN:
- Analyse deadlines and priorities
- Use LLM to reason about optimal placement
- Generate candidate schedule

ACT:
- Allocate tasks to time slots
- Store schedule in database
- Send notifications if needed

EVALUATE:
- Check for conflicts
- Measure deadline compliance
- Assess workload balance
- Trigger replanning if issues found
```

#### 4.4.2 Tool Use Architecture

```
┌─────────────────────────────────────────────────────────────────────────┐
│                           LLM REASONING CORE                           │
│                        (llama-3.3-70b-versatile)                       │
└───────────────────────────────────┬─────────────────────────────────────┘
                                    │
                                    │ Tool Invocations (JSON)
                                    │
        ┌───────────────────────────┼───────────────────────────┐
        │                           │                           │
        ▼                           ▼                           ▼
┌───────────────┐          ┌───────────────┐          ┌───────────────┐
│   DATABASE    │          │   SCHEDULER   │          │   CONFLICT    │
│     TOOLS     │          │     TOOLS     │          │   DETECTOR    │
├───────────────┤          ├───────────────┤          ├───────────────┤
│ get_tasks()   │          │ generate_     │          │ check_        │
│ add_task()    │          │   schedule()  │          │   conflicts() │
│ update_task() │          │ adapt_        │          │ get_warnings()│
│ delete_task() │          │   schedule()  │          │               │
│ get_user()    │          │ get_slots()   │          │               │
└───────────────┘          └───────────────┘          └───────────────┘
        │                           │                           │
        └───────────────────────────┼───────────────────────────┘
                                    │
                                    ▼
                          ┌───────────────────┐
                          │    PostgreSQL     │
                          │    Database       │
                          └───────────────────┘
```

#### 4.4.3 Memory Handling Architecture

```
┌─────────────────────────────────────────────────────────────────────────┐
│                          MEMORY ARCHITECTURE                           │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                         │
│  ┌─────────────────────────────────────────────────────────────────┐   │
│  │                    SHORT-TERM MEMORY                            │   │
│  │                    (LangGraph State)                            │   │
│  ├─────────────────────────────────────────────────────────────────┤   │
│  │  • Current conversation messages                                │   │
│  │  • Session user_id                                              │   │
│  │  • Parsed intent and entities                                   │   │
│  │  • Temporary schedule candidates                                │   │
│  │                                                                 │   │
│  │  Lifetime: Single session (cleared on logout)                   │   │
│  └─────────────────────────────────────────────────────────────────┘   │
│                                                                         │
│  ┌─────────────────────────────────────────────────────────────────┐   │
│  │                    LONG-TERM MEMORY                             │   │
│  │                    (PostgreSQL)                                 │   │
│  ├─────────────────────────────────────────────────────────────────┤   │
│  │  • User profiles and preferences                                │   │
│  │  • Complete task history                                        │   │
│  │  • Availability patterns                                        │   │
│  │  • Historical schedules with AI reasoning                       │   │
│  │  • Schedule adaptation logs                                     │   │
│  │                                                                 │   │
│  │  Lifetime: Persistent (until user deletion)                     │   │
│  └─────────────────────────────────────────────────────────────────┘   │
│                                                                         │
└─────────────────────────────────────────────────────────────────────────┘
```

---

## 5. System Configuration and Initial Setup

This chapter provides detailed instructions for setting up and running the agentic AI system prototype.

### 5.1 Prerequisites

**Software Requirements:**
| Software | Version | Purpose |
|----------|---------|---------|
| Python | 3.14+ | Backend runtime |
| Node.js | 18+ | Frontend build tools |
| PostgreSQL | 14+ | Database |
| npm | 9+ | Package management |

**API Keys:**
| Service | Purpose | How to Obtain |
|---------|---------|---------------|
| Groq API | LLM reasoning | Sign up at console.groq.com (free tier available) |

### 5.2 Installation Steps

#### Step 1: Clone Repository
```bash
git clone <repository-url>
cd "Agentic AI app"
```

#### Step 2: Backend Setup
```bash
# Create virtual environment
python -m venv .venv

# Activate virtual environment
# Windows:
.venv\Scripts\Activate.ps1
# macOS/Linux:
source .venv/bin/activate

# Install dependencies
cd Backend
pip install -r requirements.txt
```

#### Step 3: Database Setup
```bash
# Start PostgreSQL service
# Create database
psql -U postgres -c "CREATE DATABASE agentic_academic_db;"

# Run schema initialisation
python init_db.py
python add_schedule_tables.py
```

#### Step 4: Environment Configuration

Create `.env` file in Backend folder:
```env
# Database Configuration
DB_NAME=agentic_academic_db
DB_USER=postgres
DB_PASSWORD=your_password_here
DB_HOST=localhost
DB_PORT=5432

# LLM Configuration
GROQ_API_KEY=your_groq_api_key_here

# Server Configuration
PORT=5000
FLASK_DEBUG=true
CORS_ORIGINS=http://localhost:3000

# Email Configuration (optional)
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USER=your_email@gmail.com
SMTP_PASSWORD=your_app_password
SMTP_FROM=your_email@gmail.com
SMTP_USE_TLS=true
```

#### Step 5: Frontend Setup
```bash
cd ../Frontend
npm install
```

Create `src/config.js`:
```javascript
const API_URL = process.env.REACT_APP_API_URL || 'http://localhost:5000';
export default API_URL;
```

### 5.3 Running the System

#### Start Backend Server
```bash
cd Backend
python app.py
# Server runs on http://localhost:5000
```

#### Start Frontend Development Server
```bash
cd Frontend
npm start
# App runs on http://localhost:3000
```

### 5.4 Example Input-Output Walkthrough

#### Example 1: Creating a Task via Form
**Input:**
- Title: "Complete Dissertation Chapter 3"
- Description: "Write methodology section"
- Deadline: 2026-03-15
- Priority: High

**Output:**
```json
{
  "message": "Task added successfully!",
  "id": 42
}
```

#### Example 2: Natural Language Task Creation
**Input (Chat):**
```
"Add a task to review AI ethics paper by next Monday, medium priority"
```

**Agent Response:**
```
I've added your task:
📋 Title: Review AI ethics paper
📅 Deadline: Monday, March 9, 2026
🔶 Priority: Medium

The task has been added to your list. Would you like me to update your schedule?
```

#### Example 3: Schedule Generation
**Input:**
- Click "Generate Schedule" button

**Output:**
```
AI Reasoning: Your schedule has been optimised to ensure the dissertation 
chapter (high priority, earliest deadline) gets prime morning slots when 
focus is typically best. The ethics paper review is placed in afternoon 
slots as it requires less intensive concentration.

Schedule:
├─ Monday, March 9
│   ├─ 09:00-12:00: Complete Dissertation Chapter 3
│   └─ 14:00-16:00: Review AI ethics paper
├─ Tuesday, March 10
│   └─ 09:00-12:00: Complete Dissertation Chapter 3
...
```

### 5.5 Interface Screenshots

#### Login Screen
```
┌────────────────────────────────────────────┐
│        Academic Task Manager               │
│   Intelligent task management powered      │
│          by Agentic AI                     │
│                                            │
│   ┌────────────────────────────────────┐   │
│   │        Welcome Back                │   │
│   │  Sign in with your email           │   │
│   │                                    │   │
│   │  📧 Email Address                  │   │
│   │  ┌────────────────────────────┐   │   │
│   │  │ john.smith@gmail.com      │   │   │
│   │  └────────────────────────────┘   │   │
│   │                                    │   │
│   │  🔒 Password                       │   │
│   │  ┌────────────────────────────┐   │   │
│   │  │ ••••••••                  │   │   │
│   │  └────────────────────────────┘   │   │
│   │                                    │   │
│   │  [      Sign In      ]            │   │
│   │                                    │   │
│   │  ─── or ───                       │   │
│   │                                    │   │
│   │  [ Create New Account ]           │   │
│   └────────────────────────────────────┘   │
└────────────────────────────────────────────┘
```

#### AI Schedule View
```
┌────────────────────────────────────────────┐
│ [Account] [Tasks] [AI Schedule] [AI Chat]  │
├────────────────────────────────────────────┤
│                                            │
│  Your Availability                         │
│  ┌────────────────────────────────────┐   │
│  │ Monday    09:00-12:00  Library   🗑 │   │
│  │ Monday    14:00-17:00  Home      🗑 │   │
│  │ Tuesday   09:00-12:00  Library   🗑 │   │
│  └────────────────────────────────────┘   │
│                                            │
│  AI-Generated Schedule  [Generate Schedule]│
│  ┌────────────────────────────────────┐   │
│  │ 🤖 AI Reasoning: Tasks prioritised │   │
│  │    by deadline proximity and       │   │
│  │    workload balance.               │   │
│  ├────────────────────────────────────┤   │
│  │ 📅 Monday, March 9                 │   │
│  │   ⏰ 09:00-12:00                   │   │
│  │   📋 Dissertation Chapter 3        │   │
│  │   💡 High priority, due March 15   │   │
│  │                                    │   │
│  │ 📅 Tuesday, March 10               │   │
│  │   ⏰ 09:00-11:00                   │   │
│  │   📋 Review AI ethics paper        │   │
│  │   💡 Medium priority, due Monday   │   │
│  └────────────────────────────────────┘   │
│                                            │
└────────────────────────────────────────────┘
```

---

## 6. SLEP Considerations

This system integrates societal, legal, ethical and professional (SLEP) considerations:

### 6.1 Societal Considerations
- **Student autonomy**: The agent provides recommendations rather than mandatory schedules, preserving student agency.
- **Accessibility**: PWA implementation enables offline access and mobile-friendly interfaces.
- **Natural language interface**: Conversational chat reduces barriers to entry.
- **Workload awareness**: Constraint satisfaction engine detects and warns about potential overload.

### 6.2 Legal Considerations
- **Password-protected accounts**: Secure password hashing protects personal academic information.
- **Email-based identification**: Users control their identity disclosure.
- **Local data processing**: Task scheduling occurs locally, minimising data exposure.
- **GDPR alignment**: Data minimisation principles guide the design.

### 6.3 Ethical Considerations
- **Explainable recommendations**: Human-friendly, personalised responses explain task prioritisation.
- **Bias mitigation**: Scheduling uses objective criteria (deadlines, duration, user-defined priority).
- **User override capability**: Students retain full control over task management.
- **Avoiding over-reliance**: The system enhances rather than replaces student planning skills.

### 6.4 Professional Considerations
- **Academic integrity**: Focuses on schedule management, not content generation.
- **Professional development**: Teaches structured task management and deadline awareness.
- **Appropriate AI use**: Demonstrates responsible AI deployment in educational contexts.

---

## 7. Simulated Environment and Evaluation Plan

The evaluation uses simulated MSc scenarios with objective performance metrics and reproducible testing. This approach is consistent with recommendations for testing agentic systems in realistic contexts (World Economic Forum, 2025) and with LLM-agent evaluation taxonomies that emphasize long-horizon interaction and reliability (Mohammadi et al., 2025).

### 7.1 Scenario-Based Evaluation Design

The agent is evaluated against a baseline rule-based scheduler (earliest-deadline-first with greedy slot allocation) across a library of reproducible test scenarios:

| Scenario | Description | Tasks | Duration |
|----------|-------------|-------|----------|
| **Set A (Standard Week)** | Typical MSc workload | 8-12 tasks | 7 days |
| **Set B (Deadline Compression)** | Multiple urgent tasks with overlapping deadlines | 6-8 tasks | 3 days |
| **Set C (Disruption)** | Mid-scenario removal of available time blocks | 10 tasks | 7 days |
| **Set D (Dynamic Addition)** | New urgent tasks added to existing schedule | 12+ tasks | 7 days |
| **Set E (5-Week Project)** | Extended MSc dissertation scenario | 15-20 tasks | 35 days |

Each scenario is executed 10 times to account for any non-determinism, with results aggregated for statistical analysis.

### 7.2 Objective Performance Metrics

| Metric | Description | Target |
|--------|-------------|--------|
| **Schedule generation time** | Time (seconds) for complete schedule | < 5s |
| **Conflict rate** | % schedules with constraint violations | < 5% |
| **Deadline compliance rate** | % tasks scheduled before deadline | > 95% |
| **Workload distribution** | Std dev of daily allocated hours | Minimise |
| **Adaptation speed** | Time (seconds) to regenerate after disruption | < 3s |
| **Adaptation efficiency** | Tasks moved during rescheduling | Minimise |

### 7.3 Cross-Scenario Performance Analysis

System performance will be analysed across scenario types to identify strengths and failure modes:

- **Conflict rates** between standard scenarios and high-pressure deadline compression scenarios to assess robustness under stress.
- **Deadline compliance** across scenario complexity levels to determine scalability.
- **Adaptation speed and efficiency** in disruption scenarios versus dynamic addition scenarios to evaluate different types of constraint changes.

Statistical comparisons (paired t-tests or Wilcoxon signed-rank tests where appropriate) will determine whether observed differences between the agent and baseline are significant. Failure cases will be qualitatively documented to identify systematic limitations and inform future improvements.

---

## 8. Updated Weekly Schedule

The following schedule covers the remaining project timeline from March 2026 to submission.

### 8.1 Gantt Chart Overview

```
Week    | Mar 3-9 | Mar 10-16 | Mar 17-23 | Mar 24-30 | Mar 31 |
--------|---------|-----------|-----------|-----------|--------|
Impl.   | ███████ | ███████   | ████      |           |        |
Testing |         | ████      | ███████   | ████      |        |
Eval.   |         |           | ████      | ███████   |        |
Writing |         |           |           | ████      | ██████ |
Review  |         |           |           |           | ██████ |
```

### 8.2 Detailed Week-by-Week Plan

| Week | Dates | Tasks | Deliverables |
|------|-------|-------|--------------|
| **Week 1** | Mar 3-9 | Complete agentic scheduling implementation; Integration testing; Fix critical bugs | Working prototype with all features |
| **Week 2** | Mar 10-16 | Run evaluation scenarios (Sets A-E); Collect metrics; Begin dissertation Chapter 4 (System Design) | Evaluation data collected; Chapter 4 draft |
| **Week 3** | Mar 17-23 | Complete evaluation analysis; Write Chapter 5 (Evaluation); Statistical analysis | Chapter 5 draft; Analysis complete |
| **Week 4** | Mar 24-30 | Write Chapter 6 (Discussion); Revise Chapters 1-3 based on feedback; Prepare diagrams | Chapters 1-6 complete drafts |
| **Week 5** | Mar 31 | Final revisions; Proofreading; Format check; Submission preparation | Final submission |

### 8.3 Time Allocation Summary

| Activity | Hours | Percentage |
|----------|-------|------------|
| Implementation & Bug Fixes | 30 | 20% |
| Testing & Evaluation | 35 | 23% |
| Dissertation Writing | 55 | 37% |
| Review & Revision | 20 | 13% |
| Buffer/Contingency | 10 | 7% |
| **Total** | **150** | **100%** |

### 8.4 Key Milestones

| Milestone | Target Date | Status |
|-----------|-------------|--------|
| M1: Prototype feature-complete | March 9 | ✅ Complete |
| M2: Evaluation data collected | March 16 | 🔄 In Progress |
| M3: Full draft complete | March 30 | ⏳ Pending |
| M4: Final submission | March 31 | ⏳ Pending |

---

## 9. References

Babaei, E., Dingler, T., Tag, B., & Velloso, E. (2025). Should we use the NASA-TLX in HCI? A review of theoretical and methodological issues around mental workload measurement. *International Journal of Human-Computer Studies*, 201, 103515. https://doi.org/10.1016/j.ijhcs.2025.103515

Bandi, A., Kongari, B., Naguru, R., Pasnoor, S., & Vilipala, S. V. (2025). The rise of agentic AI: A review of definitions, frameworks, architectures, applications, evaluation metrics, and challenges. *Future Internet*, 17(9), 404. https://doi.org/10.3390/fi17090404

Bhuiyan, M. A., Rahman, M. K., Basile, V., Ping, H., & Bari, A. B. M. M. (2025). Adoption of ChatGPT for students' learning effectiveness. *The International Journal of Management Education*, 23(3), 101255. https://doi.org/10.1016/j.ijme.2025.101255

Deng, R., Jiang, M., Yu, X., Lu, Y., & Liu, S. (2025). Does ChatGPT enhance student learning? A systematic review and meta-analysis of experimental studies. *Computers & Education*, 227, 105224. https://doi.org/10.1016/j.compedu.2024.105224

International Organization for Standardization. (2018). ISO 9241-11:2018 Ergonomics of human-system interaction—Part 11: Usability: Definitions and concepts. https://www.iso.org/standard/63500.html

Khan, Q., Hickie, I. B., Loblay, V., Ekambareshwar, M., Md Zahed, I. U., Naderbagi, A., Song, Y. J. C., & LaMonica, H. M. (2025). Psychometric evaluation of the System Usability Scale in the context of a childrearing app co-designed for low- and middle-income countries. *Digital Health*, 11, 20552076251335413. https://doi.org/10.1177/20552076251335413

LangChain. (2024). LangGraph documentation. https://langchain-ai.github.io/langgraph/

Microsoft. (2024). AutoGen: Enabling next-gen LLM applications via multi-agent conversation. https://microsoft.github.io/autogen/

Mohammadi, M., Li, Y., Lo, J., & Yip, W. (2025). Evaluation and benchmarking of LLM agents: A survey (arXiv:2507.21504). *arXiv*. https://doi.org/10.48550/arXiv.2507.21504

Nuralamsyah, B., Yuhana, U. L., & Yuniarti, A. (2025). AI-based application for task management and scheduling student activity. In *2025 15th International Conference on Information & Communication Technology and System (ICTS)*. https://doi.org/10.1109/ICTS67612.2025.11369721

Perrig, S. A. C., Felten, B., Scharowski, N., & Nacke, L. E. (2025). Development and psychometric validation of a positively worded German version of the System Usability Scale (SUS). *International Journal of Human–Computer Interaction*. https://doi.org/10.1080/10447318.2024.2434720

Sapkota, R., Roumeliotis, K. I., & Karkee, M. (2025). AI agents vs. agentic AI: A conceptual taxonomy, applications and challenges. *Information Fusion*. https://doi.org/10.1016/j.inffus.2025.103599

Schick, T., Dwivedi-Yu, J., Dessì, R., Raileanu, R., Lomeli, M., Zettlemoyer, L., Cancedda, N., & Scialom, T. (2023). Toolformer: Language models can teach themselves to use tools. *arXiv preprint arXiv:2302.04761*.

World Economic Forum. (2025). AI agents in action: Foundations for evaluation and governance. https://www.weforum.org/publications/ai-agents-in-action-foundations-for-evaluation-and-governance/

Yao, S., Zhao, J., Yu, D., Du, N., Shafran, I., Narasimhan, K., & Cao, Y. (2023). ReAct: Synergizing reasoning and acting in language models. *ICLR 2023*. https://arxiv.org/abs/2210.03629

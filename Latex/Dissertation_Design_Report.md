Dissertation Design Report: Agentic AI for Academic Task Management


1. Introduction
This report presents the design and evaluation plan for an agentic AI system that supports MSc students in managing academic tasks such as coursework, independent study, and project milestones. The system aims to move beyond static to-do lists and reminders by providing intelligent prioritization, constraint-aware scheduling, and adaptation when deadlines or available study time change. The design adopts a practical definition of agentic AI as goal-directed behaviour with autonomy and feedback-based adaptation (Sapkota et al., 2025; Bandi et al., 2025).
Project aims and objectives:
Design a task management prototype that can prioritize and schedule academic tasks under constraints (deadlines, fixed commitments, available study blocks).
Implement an agent workflow that adapts schedules when new tasks appear or constraints change.
Evaluate the system in a controlled simulated academic environment against a baseline manual planning workflow.
Research questions and hypotheses:
RQ1 (Efficiency): Does the agent reduce planning time compared with manual planning in realistic MSc scenarios?
RQ2 (Schedule quality): Does the agent produce schedules with fewer conflicts and fewer missed deadlines than the baseline?
RQ3 (User experience): Do users report higher usability and lower workload when using the agent?
H1: Participants will complete planning faster with the agent than with manual planning.
H2: Agent-generated schedules will have fewer conflicts and fewer deadline misses than baseline schedules.
H3: Usability scores will be higher and perceived workload will be lower for the agent condition.
System limitations and assumptions:
The system is evaluated in simulation and controlled testing rather than long-term real-world deployment.
Performance depends on the completeness and accuracy of user-provided task details (deadlines, estimated durations, constraints).
The project focuses on academic task management, not general productivity or non-academic life planning.
2. Project Requirements and Scope
Target users: MSc students managing concurrent coursework, independent study, and project work.
Core features:
Task entry (form or natural language) with extraction of title, deadline, duration estimate, and importance.
Prioritization based on deadline proximity, workload, and user preferences.
Constraint-aware scheduling into available time blocks with support for fixed commitments (lectures, work shifts).
Adaptation when constraints change (deadline moved, new urgent task, lost time block).
Explanations for recommendations (why a task is prioritized and why it was placed at a particular time).
3. Literature Review and Background
3.1 Generative AI in higher education and self-regulated learning
Recent evidence indicates that generative AI tools can influence learning outcomes and student experience, with effects depending on context and instructional design. A large meta-analysis of (quasi)experimental studies reports overall improvements in academic performance and some affective-motivational outcomes, while noting variability across settings (Deng et al., 2025). Adoption studies also emphasize that transparency and AI literacy can shape learners’ effective use (Bhuiyan et al., 2025).
3.2 Agentic AI and LLM-based agents
Recent work distinguishes traditional agents from agentic AI systems that orchestrate tools, memory, and multi-step reasoning to pursue goals under changing conditions (Sapkota et al., 2025). Reviews summarize definitions, architectures, and evaluation approaches for agentic systems, highlighting the need for reliable testing and clear metrics (Bandi et al., 2025). For evaluation and benchmarking of LLM agents, Mohammadi et al. (2025) provide an overview of evaluation objectives and methods suited to long-horizon, tool-using behaviour.
3.3 Student task scheduling and academic planning
Academic task management can be treated as a constrained scheduling problem: tasks have deadlines, durations, and must be fitted into limited time blocks while respecting fixed commitments. A 2025 conference paper reports an AI-based student task management and scheduling application, supporting feasibility and motivating evaluation of schedule quality and user experience (Nuralamsyah et al., 2025).
3.4 Usability and workload measurement (updated)
In this dissertation, usability is treated as an outcome of use in context, commonly operationalized in terms of effectiveness, efficiency, and satisfaction (ISO 9241-11:2018). A widely used instrument for perceived usability is the System Usability Scale (SUS). Recent psychometric evidence supports its validity and reliability in contemporary app contexts (Khan et al., 2025), and recent work continues to refine validated variants of SUS in different languages (Perrig et al., 2025). For perceived workload, NASA-TLX is commonly used; however, a 2025 HCI review highlights theoretical and methodological issues and recommends caution and clear interpretation in HCI-style studies (Babaei et al., 2025).
4. System Architecture
The prototype uses a standard three-tier structure with an agent core and a scheduling engine:
Frontend: a web interface (React) for task entry, schedule review, and explanations.
Backend API: Python FastAPI service that manages users, tasks, and schedule generation.
Agent core: workflow that parses tasks, scores priorities, proposes schedules, and adapts based on feedback.
Scheduling engine: constraint-aware scheduler (heuristics or constraint programming) that places tasks into time blocks.
Database: SQLite or PostgreSQL storing users, tasks, preferences, and schedule history.
System flow (Mermaid diagram code):
flowchart TD
  A[Task Entry by Student] --> B[AI Agent Processing]
  B --> C[Task Prioritization and Scheduling]
  C --> D[Schedule and Reminders Delivered]
  D --> E[Student Feedback and Adjustments]
  E --> B
5. Simulated Environment and Evaluation Plan
The evaluation uses simulated MSc scenarios plus controlled user testing. Scenario-based evaluation is consistent with recommendations for testing agentic systems in realistic contexts (World Economic Forum, 2025) and with LLM-agent evaluation taxonomies that emphasize long-horizon interaction and reliability (Mohammadi et al., 2025).
5.1 Study design
Within-subject design: each participant completes scenarios using (A) baseline manual planning and (B) the agentic system, with counterbalanced order.
Scenario library: typical MSc week, deadline compression, disruption (lost study time), and new urgent task addition.
Constraints: locked blocks (lectures/work) must be respected; minimum focus block length can be configured.
5.2 Metrics
Objective metrics:
Planning time (minutes).
Schedule feasibility: number of conflicts with locked blocks (target: zero).
Deadline compliance: number of tasks finishing after deadlines.
Workload balance: fragmentation and distribution across days.
Adaptation performance: time to regenerate a feasible schedule after a disruption and number of tasks moved.
User experience metrics:
Perceived usability measured with SUS (supported by contemporary psychometric evidence; Khan et al., 2025).
Perceived workload measured using NASA-TLX, interpreted with guidance from recent HCI critique and best practices (Babaei et al., 2025).
Short qualitative prompts on trust, transparency, and perceived usefulness of schedules and explanations.
6. References 
Babaei, E., Dingler, T., Tag, B., & Velloso, E. (2025). Should we use the NASA-TLX in HCI? A review of theoretical and methodological issues around mental workload measurement. International Journal of Human-Computer Studies, 201, 103515. https://doi.org/10.1016/j.ijhcs.2025.103515
Bandi, A., Kongari, B., Naguru, R., Pasnoor, S., & Vilipala, S. V. (2025). The rise of agentic AI: A review of definitions, frameworks, architectures, applications, evaluation metrics, and challenges. Future Internet, 17(9), 404. https://doi.org/10.3390/fi17090404
Bhuiyan, M. A., Rahman, M. K., Basile, V., Ping, H., & Bari, A. B. M. M. (2025). Adoption of ChatGPT for students' learning effectiveness. The International Journal of Management Education, 23(3), 101255. https://doi.org/10.1016/j.ijme.2025.101255
Deng, R., Jiang, M., Yu, X., Lu, Y., & Liu, S. (2025). Does ChatGPT enhance student learning? A systematic review and meta-analysis of experimental studies. Computers & Education, 227, 105224. https://doi.org/10.1016/j.compedu.2024.105224
International Organization for Standardization. (2018). ISO 9241-11:2018 Ergonomics of human-system interaction—Part 11: Usability: Definitions and concepts. https://www.iso.org/standard/63500.html
Khan, Q., Hickie, I. B., Loblay, V., Ekambareshwar, M., Md Zahed, I. U., Naderbagi, A., Song, Y. J. C., & LaMonica, H. M. (2025). Psychometric evaluation of the System Usability Scale in the context of a childrearing app co-designed for low- and middle-income countries. Digital Health, 11, 20552076251335413. https://doi.org/10.1177/20552076251335413
Mohammadi, M., Li, Y., Lo, J., & Yip, W. (2025). Evaluation and benchmarking of LLM agents: A survey (arXiv:2507.21504). arXiv. https://doi.org/10.48550/arXiv.2507.21504
Nuralamsyah, B., Yuhana, U. L., & Yuniarti, A. (2025). AI-based application for task management and scheduling student activity. In 2025 15th International Conference on Information & Communication Technology and System (ICTS). https://doi.org/10.1109/ICTS67612.2025.11369721
Perrig, S. A. C., Felten, B., Scharowski, N., & Nacke, L. E. (2025). Development and psychometric validation of a positively worded German version of the System Usability Scale (SUS). International Journal of Human–Computer Interaction. https://doi.org/10.1080/10447318.2024.2434720
Sapkota, R., Roumeliotis, K. I., & Karkee, M. (2025). AI agents vs. agentic AI: A conceptual taxonomy, applications and challenges. Information Fusion. https://doi.org/10.1016/j.inffus.2025.103599
World Economic Forum. (2025). AI agents in action: Foundations for evaluation and governance. https://www.weforum.org/publications/ai-agents-in-action-foundations-for-evaluation-and-governance/

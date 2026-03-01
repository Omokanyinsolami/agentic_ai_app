# test_end_to_end.py
import re
from langgraph_agent import agent_workflow, send_email_notification, fetch_tasks, send_reminders
from datetime import date, timedelta
def extract_task_id(message_text: str):
    """
    Extract task id from:
    'Task added successfully for user 1 with id=7.'
    """
    match = re.search(r"id=(\d+)", message_text)
    return int(match.group(1)) if match else None


def run_end_to_end():
    # 1. Add a new task for user 2
    add_result = agent_workflow(
        'add_task: 2, "Dissertation draft", "Write the draft", 2026-03-10, 1, pending'
    )
    add_message = add_result["messages"][-1].content
    print("Add Result:", add_message)

    task_id = extract_task_id(add_message)
    if not task_id:
        print("Could not extract task id from add result. Stopping test.")
        return

    # 2. Show all tasks for user 2
    show_result = agent_workflow("show_tasks: user_id=2")
    print("Show Result:", show_result["messages"][-1].content)

    # 3. Update the newly added task
    update_result = agent_workflow(
        f'update_task: {task_id}, "Dissertation draft updated", "Updated draft", 2026-03-12, 2, done'
    )
    print("Update Result:", update_result["messages"][-1].content)

    # 4. Show all tasks again
    show_result2 = agent_workflow("show_tasks: user_id=2")
    print("Show After Update:", show_result2["messages"][-1].content)

    # 5. Delete the same task
    delete_result = agent_workflow(f"delete_task: {task_id}")
    print("Delete Result:", delete_result["messages"][-1].content)

    # 6. Show all tasks again
    show_result3 = agent_workflow("show_tasks: user_id=2")
    print("Show After Delete:", show_result3["messages"][-1].content)


if __name__ == "__main__":

    # Add simulation tasks for user 2 (pending, next 5 days)
    today = date.today()
    for i, (title, desc, days_ahead, priority) in enumerate([
        ("Submit literature review", "Complete and submit the literature review section.", 1, 2),
        ("Meet supervisor", "Schedule and attend meeting with supervisor.", 2, 1),
        ("Collect data", "Start collecting data for experiments.", 3, 3),
        ("Draft methodology", "Write the methodology chapter.", 4, 2),
        ("Prepare slides", "Prepare slides for upcoming presentation.", 5, 1),
    ]):
        deadline = (today + timedelta(days=days_ahead)).strftime('%Y-%m-%d')
        payload = f'add_task: 2, "{title}", "{desc}", {deadline}, {priority}, pending'
        result = agent_workflow(payload)
        print(f"Simulated Add Task {i+1}:", result["messages"][-1].content)

    run_end_to_end()

    # Email test with all tasks for user 2
    user_id = 2
    tasks = fetch_tasks(user_id)
    if tasks:
        body = f"Hello,\n\nHere is your list of pending tasks:\n\n"
        for t in tasks:
            task_id = t[0]
            title = t[1]
            description = t[2]
            deadline = t[3].strftime('%Y-%m-%d') if t[3] else 'No deadline'
            priority = t[4]
            status = t[5]
            if status.lower() not in ['done', 'completed']:
                body += f"• {title}\n  - Description: {description}\n  - Deadline: {deadline}\n  - Priority: {priority}\n\n"
        if body.strip() == "Hello,\n\nHere is your list of pending tasks:\n\n":
            body += "No pending tasks."
    else:
        body = f"No tasks found for user {user_id}."
    success, message = send_email_notification(
        to_email="kehindea.arowolo@gmail.com",  # Change to your test recipient
        subject="Task Reminder",
        body=body
    )
    print("Email Test:", success, message)

    # Send deadline reminder for user 2
    # Use send_reminders to test deadline-based reminders
    reminder_result = agent_workflow("reminders: user_id=2; days=5; send_email=true")
    print("Deadline Reminder Test:", reminder_result["messages"][-1].content)
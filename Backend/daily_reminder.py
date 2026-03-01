import os
from langgraph_agent import agent_workflow

def send_daily_reminders():
    # You can loop through all users or specify user IDs
    # Example: send for user 2
    result = agent_workflow("reminders: user_id=2; days=1; send_email=true")
    print(result["messages"][-1].content)

if __name__ == "__main__":
    send_daily_reminders()

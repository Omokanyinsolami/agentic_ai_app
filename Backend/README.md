# Academic Task Agent

This is a smart assistant that helps you manage your school tasks and users. You can add, view, update, and delete tasks, and even manage users. You use it by typing simple commands in a window called the terminal.

## What Can It Do?
- Add new tasks (like homework or projects)
- Show all your tasks
- Update a task (change details or mark as done)
- Delete a task
- Create and manage users
- Get reminders (if you set up email)
- Export and import tasks (for backup)
- Get help on how to use it

## How Do I Use It?
1. **Open the terminal** (the black window where you type commands)
2. **Start the agent** by typing:
   ```
   python langgraph_agent.py
   ```
3. **Type a command** and press Enter. For example:
   - `help` — shows all commands
   - `add 1` — add a new task for user 1
   - `show 1` — show all tasks for user 1
   - `update 5` — update task with ID 5
   - `delete 5` — delete task with ID 5
   - `user create` — create a new user
   - `user show 1` — show user 1
   - `exit` — quit the agent

The agent will ask you questions and show you your tasks or users.

## How Do I Set It Up?
1. **Install Python** (if you don’t have it)
2. **Install the required packages** by typing:
   ```
   pip install -r requirements.txt
   ```
3. **Set up your database** (PostgreSQL) and fill in the `.env` file with your database details.
   Example `.env` file:
   ```
   DB_NAME=agentic_academic_db
   DB_USER=postgres
   DB_PASSWORD=yourpassword
   DB_HOST=localhost
   DB_PORT=5432
   ```
4. **Start the agent** as shown above.

## What If I Need Help?
- Type `help` in the agent for a list of commands and examples.
- If you get stuck, ask someone who knows Python or computers for help.


## Automated Daily Reminders

You can send daily email reminders automatically using the `daily_reminder.py` script.

### How to Use Daily Reminders
1. Make sure your users have email addresses in the database.
2. Edit `daily_reminder.py` if you want to send reminders to different users.
3. Run the script manually:
    ```
    python daily_reminder.py
    ```
4. Or, set up a daily schedule:
    - **Windows:**
       - Use Task Scheduler to run `python daily_reminder.py` every day.
    - **Linux/Mac:**
       - Add this line to your crontab (type `crontab -e`):
          ```
          0 8 * * * /usr/bin/python3 /path/to/daily_reminder.py
          ```
       - This runs the reminder every day at 8am.

---

**This agent is made to be easy for anyone to use. Just follow the steps, type your commands, and let it help you stay organized!**

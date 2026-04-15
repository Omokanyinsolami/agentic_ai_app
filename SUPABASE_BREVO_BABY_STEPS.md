# Supabase + Brevo Reminder Setup

This guide explains the reminder automation setup in the simplest possible way.

Use it if you want the system to send reminder emails automatically without needing your laptop to stay on.

## What this setup does

1. `Supabase` stores the database.
2. `Brevo` sends the email.
3. A `Supabase Edge Function` checks which tasks are due soon or already overdue.
4. `Supabase Cron` runs that function every day automatically.

After setup, the reminders can run even when your computer is off.

## Before you start

You need these things:

1. Your Supabase project already created
2. Your Brevo account already created
3. Your project files on your machine
4. The backend database tables already created

You should already have these files in the project:

1. [Backend/.env](c:\Users\LENOVO\Downloads\Agentic AI app\Backend\.env)
2. [index.ts](c:\Users\LENOVO\Downloads\Agentic AI app\supabase\functions\deadline-reminders\index.ts)
3. [20260402_reminder_support.sql](c:\Users\LENOVO\Downloads\Agentic AI app\supabase\sql\20260402_reminder_support.sql)
4. [20260402_schedule_deadline_reminders.sql.template](c:\Users\LENOVO\Downloads\Agentic AI app\supabase\sql\20260402_schedule_deadline_reminders.sql.template)

## Part 1: Set up Supabase database connection locally

### Step 1: Open your local backend env file

Open:

- [Backend/.env](c:\Users\LENOVO\Downloads\Agentic AI app\Backend\.env)

Make sure the database part looks like this shape:

```env
DB_NAME=postgres
DB_USER=your_supabase_user
DB_PASSWORD=your_supabase_database_password
DB_HOST=your_supabase_pooler_host
DB_PORT=5432
DB_CONNECT_TIMEOUT=5
DB_SSLMODE=require
```

### Step 2: Make sure the tables exist

From the project root, run:

```powershell
.\.venv\Scripts\python.exe Backend\init_db.py
.\.venv\Scripts\python.exe Backend\add_schedule_tables.py
```

Do not run `create_db.py` for Supabase.

## Part 2: Set up Brevo

### Step 3: Log in to Brevo

1. Go to `https://app.brevo.com`
2. Sign in

### Step 4: Verify a sender email

1. In Brevo, go to sender settings
2. Add the sender email you want the system to send from
3. Verify that sender email

The sender email must be approved by Brevo before emails will send properly.

### Step 5: Create a Brevo API key

1. In Brevo, go to:
   - `SMTP & API`
   - then `API Keys`
2. Click `Generate a new API key`
3. Give it a name like:
   - `agentic-ai-reminders`
4. Copy the key immediately

Important:

1. Use an actual `API key`
2. Do not use an SMTP password
3. Do not use an old deleted key

## Part 3: Put Brevo secrets into Supabase

### Step 6: Open Supabase Edge Function secrets

1. Go to your Supabase project
2. Open `Edge Functions`
3. Open `Manage secrets`

### Step 7: Add these secrets

Add them one by one:

```text
BREVO_API_KEY=your_real_brevo_api_key
BREVO_FROM_EMAIL=your_verified_sender_email
BREVO_FROM_NAME=Agentic AI Prototype
REMINDER_LOOKAHEAD_DAYS=5
REMINDER_TIMEZONE=Africa/Lagos
```

### Step 8: Save the secrets

After saving, the names should appear in Supabase.

## Part 4: Add the reminder SQL support

### Step 9: Open SQL Editor in Supabase

1. Go to `SQL Editor`
2. Create a new query

### Step 10: Paste the reminder support SQL

Open this file locally:

- [20260402_reminder_support.sql](c:\Users\LENOVO\Downloads\Agentic AI app\supabase\sql\20260402_reminder_support.sql)

Copy everything in that file.

Paste it into Supabase SQL Editor.

Then run it.

### Step 11: What that SQL creates

It creates:

1. `reminder_dispatch_log`
2. `get_pending_reminder_tasks(...)`

These are needed for:

1. finding tasks due in the next 5 days or already overdue
2. preventing duplicate sends once a reminder has really been sent

## Part 5: Create the Edge Function

### Step 12: Open Edge Functions in Supabase

1. Go to `Edge Functions`
2. Create a new function
3. Name it:
   - `deadline-reminders`

### Step 13: Paste the function code

Open this file:

- [index.ts](c:\Users\LENOVO\Downloads\Agentic AI app\supabase\functions\deadline-reminders\index.ts)

Copy everything in it.

Paste it into the Supabase function editor.

Save or deploy it.

### Step 14: Redeploy after every secret or code change

If you change:

1. function code
2. Brevo key
3. function secrets

then redeploy the function again before testing.

## Part 6: Test the function safely first

### Step 15: Test with email turned off

In the function test/invoke panel, use:

```json
{
  "days": 5,
  "sendEmail": false
}
```

Expected result:

```json
{
  "message": "Reminder run completed.",
  "sentUsers": 1,
  "sentTasks": 6
}
```

The exact numbers may change if your tasks change, but it should find pending tasks that are due soon or overdue.

### Step 16: If it says “No pending tasks”

Check:

1. are there tasks due in the next 5 days or already overdue?
2. are they still `pending` or `in_progress`?
3. are they not deleted?
4. does the user have an email address?

### Step 17: Test with email turned on

Now run:

```json
{
  "days": 5,
  "sendEmail": true
}
```

If everything is correct, Brevo should send the reminder email.

## Part 7: Fix the most common Brevo error

### Step 18: If you see `401 Key not found`

That usually means:

1. wrong key
2. incomplete key copy
3. old key
4. SMTP password used instead of API key
5. function not redeployed after changing secret

Do this:

1. create a brand-new Brevo API key
2. replace `BREVO_API_KEY` in Supabase secrets
3. redeploy the function
4. test again

## Part 8: Turn on daily automatic running

### Step 19: Get the Supabase anon JWT key

In Supabase:

1. go to `Project Settings`
2. go to `API`
3. copy the legacy `anon` JWT key

### Step 20: Open the cron SQL template

Open:

- [20260402_schedule_deadline_reminders.sql.template](c:\Users\LENOVO\Downloads\Agentic AI app\supabase\sql\20260402_schedule_deadline_reminders.sql.template)

### Step 21: Replace the placeholder key

Replace:

```text
YOUR_SUPABASE_ANON_JWT_KEY
```

with your real anon JWT key.

### Step 22: Run the cron SQL

1. Go back to Supabase `SQL Editor`
2. Paste the full cron SQL
3. Run it

If it returns a number like `1`, that means the job was created.

## Part 9: Check that the cron job exists

### Step 23: Verify the scheduled job

Run:

```sql
select jobid, jobname, schedule, active
from cron.job
order by jobid desc;
```

You should see:

1. `daily-deadline-reminders`
2. `active = true`

### Step 24: Check cron run history

Run:

```sql
select jobid, status, return_message, start_time, end_time
from cron.job_run_details
order by start_time desc
limit 20;
```

This tells you whether the job actually ran and whether it failed.

## Part 10: What “good to go” looks like

You are good to go when all of these are true:

1. Supabase DB is connected
2. tasks exist in the database
3. `get_pending_reminder_tasks(5, CURRENT_DATE)` returns rows
4. `deadline-reminders` function runs with `sendEmail: false`
5. `deadline-reminders` function runs with `sendEmail: true`
6. cron job exists in `cron.job`
7. cron runs successfully in `cron.job_run_details`

## Part 11: Very important security warning

If you pasted any live keys into chat, notes, or screenshots:

1. rotate them after testing
2. update Supabase secrets again
3. redeploy the function

Do not commit live secrets to GitHub.

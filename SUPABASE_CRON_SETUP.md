# Supabase Cron Setup

This path replaces GitHub Actions or Windows Task Scheduler for reminder automation.

It is the right choice if you want deadline reminders to run even when your laptop is off.

## What this adds

1. A hosted Edge Function:
   - `supabase/functions/deadline-reminders/index.ts`
2. Database support objects:
   - `supabase/sql/20260402_reminder_support.sql`
3. A Cron schedule template:
   - `supabase/sql/20260402_schedule_deadline_reminders.sql.template`

## How it works

1. Supabase Cron runs on a fixed schedule.
2. Cron calls the hosted Edge Function.
3. The Edge Function:
   - queries users with incomplete tasks due within the reminder window
   - sends one summary email per user through Brevo
   - records what it sent in `reminder_dispatch_log`
4. The log prevents duplicate sends for the same user/task/window on the same day.

## Before you start

You need:

1. A working Supabase project
2. The database tables already created from this app
3. A Brevo API key and verified sender email
4. The Supabase CLI installed locally if you want to deploy from the terminal

## Step 1: Apply the SQL support objects

Open the Supabase dashboard for your project.

1. Go to `SQL Editor`
2. Open a new query
3. Paste the contents of:
   - `supabase/sql/20260402_reminder_support.sql`
4. Run the query

This creates:

1. `reminder_dispatch_log`
2. `get_pending_reminder_tasks(...)`

## Step 2: Add Edge Function secrets

In Supabase:

1. Go to `Edge Functions`
2. Open `Manage secrets`
3. Add:

```text
BREVO_API_KEY=your_brevo_api_key
BREVO_FROM_EMAIL=your_verified_sender@example.com
BREVO_FROM_NAME=Agentic AI Prototype
REMINDER_LOOKAHEAD_DAYS=5
REMINDER_TIMEZONE=Africa/Lagos
```

Notes:

1. `SUPABASE_URL` and `SUPABASE_SERVICE_ROLE_KEY` are provided automatically to Edge Functions.
2. You do not need to store your database password in the function.

## Step 3: Deploy the Edge Function

From the project root:

```powershell
supabase login
supabase link --project-ref YOUR_PROJECT_REF
supabase functions deploy deadline-reminders
```

If you prefer the dashboard route, create the function there and paste in the contents of:

- `supabase/functions/deadline-reminders/index.ts`

## Step 4: Test the function manually

In Supabase:

1. Go to `Edge Functions`
2. Open `deadline-reminders`
3. Use the test/invoke option with:

```json
{
  "days": 5,
  "sendEmail": false
}
```

Use `sendEmail: false` for the first test so you can confirm the query works without emailing anyone.

Then test again with:

```json
{
  "days": 5,
  "sendEmail": true
}
```

## Step 5: Create the Cron schedule

Get these values from Supabase:

1. Anon JWT key:
   - `Project Settings -> API -> Project API keys`
   - use the legacy `anon` JWT key, not a publishable key

Then:

1. Go to `SQL Editor`
2. Open a new query
3. Paste `supabase/sql/20260402_schedule_deadline_reminders.sql.template`
4. Replace:
   - `YOUR_SUPABASE_ANON_JWT_KEY`
5. Run the query

The default schedule is:

```cron
0 7 * * *
```

That means `07:00 UTC` daily.

If you want `08:00 Africa/Lagos`, keep it as-is because Lagos is UTC+1 and does not observe daylight saving time.

## Step 6: Verify the schedule

Run:

```sql
select jobid, jobname, schedule, active
from cron.job
order by jobid desc;
```

You should see:

- `daily-deadline-reminders`

## Step 7: Check reminder history

To see what the function has already sent:

```sql
select *
from public.reminder_dispatch_log
order by created_at desc
limit 50;
```

## Important notes

1. This path does not require your laptop to be on.
2. It does not require GitHub Actions.
3. It does require:
   - Supabase project online
   - Brevo sender configured
4. The function uses Brevo only. It does not use SMTP.

## If you need to disable the schedule

Run:

```sql
select cron.unschedule(
  (select jobid from cron.job where jobname = 'daily-deadline-reminders')
);
```

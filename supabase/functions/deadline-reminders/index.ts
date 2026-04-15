import { createClient } from "npm:@supabase/supabase-js@2";

type ReminderTask = {
  user_id: number;
  user_name: string;
  user_email: string;
  task_id: number;
  title: string;
  deadline: string;
  priority: number | null;
  status: string | null;
};

type GroupedReminder = {
  userId: number;
  name: string;
  email: string;
  tasks: ReminderTask[];
};

const corsHeaders = {
  "Access-Control-Allow-Origin": "*",
  "Access-Control-Allow-Headers": "authorization, x-client-info, apikey, content-type",
  "Access-Control-Allow-Methods": "POST, OPTIONS",
};

const SUPABASE_URL = Deno.env.get("SUPABASE_URL") ?? "";
const SUPABASE_SERVICE_ROLE_KEY = Deno.env.get("SUPABASE_SERVICE_ROLE_KEY") ?? "";
const BREVO_API_KEY = Deno.env.get("BREVO_API_KEY") ?? "";
const BREVO_FROM_EMAIL = Deno.env.get("BREVO_FROM_EMAIL") ?? "";
const BREVO_FROM_NAME = Deno.env.get("BREVO_FROM_NAME") ?? "Agentic AI Prototype";
const DEFAULT_LOOKAHEAD_DAYS = Number(Deno.env.get("REMINDER_LOOKAHEAD_DAYS") ?? "5");
const REMINDER_TIMEZONE = Deno.env.get("REMINDER_TIMEZONE") ?? "UTC";

function jsonResponse(body: unknown, status = 200): Response {
  return new Response(JSON.stringify(body, null, 2), {
    status,
    headers: {
      ...corsHeaders,
      "Content-Type": "application/json",
    },
  });
}

function requireEnv(name: string, value: string): void {
  if (!value) {
    throw new Error(`Missing required function secret: ${name}`);
  }
}

function formatDeadline(deadline: string): string {
  const parsed = new Date(deadline);
  if (Number.isNaN(parsed.getTime())) {
    return deadline;
  }

  return new Intl.DateTimeFormat("en-GB", {
    dateStyle: "medium",
    timeStyle: "short",
    timeZone: REMINDER_TIMEZONE,
  }).format(parsed);
}

function formatPriority(priority: number | null): string {
  if (priority === null || priority === undefined) {
    return "Medium priority";
  }
  if (priority <= 2) {
    return "High priority";
  }
  if (priority <= 3) {
    return "Medium priority";
  }
  return "Low priority";
}

function getTaskTiming(deadline: string, runDate: string): { label: string; isOverdue: boolean } {
  const dueDate = new Date(`${deadline.slice(0, 10)}T00:00:00Z`);
  const reminderDate = new Date(`${runDate}T00:00:00Z`);

  if (Number.isNaN(dueDate.getTime()) || Number.isNaN(reminderDate.getTime())) {
    return { label: "Timing unavailable", isOverdue: false };
  }

  const millisecondsPerDay = 24 * 60 * 60 * 1000;
  const deltaDays = Math.round((dueDate.getTime() - reminderDate.getTime()) / millisecondsPerDay);

  if (deltaDays < 0) {
    return { label: `OVERDUE by ${Math.abs(deltaDays)} day(s)`, isOverdue: true };
  }
  if (deltaDays === 0) {
    return { label: "Due today", isOverdue: false };
  }
  if (deltaDays === 1) {
    return { label: "Due in 1 day", isOverdue: false };
  }
  return { label: `Due in ${deltaDays} days`, isOverdue: false };
}

function buildEmailBody(name: string, tasks: ReminderTask[], days: number, runDate: string): string {
  const firstName = name.trim().split(/\s+/)[0] || "there";
  const overdueCount = tasks.filter((task) => getTaskTiming(task.deadline, runDate).isOverdue).length;
  const dueSoonCount = tasks.length - overdueCount;
  const lines = [
    `Hello ${firstName},`,
    "",
    `You have ${tasks.length} pending task${tasks.length === 1 ? "" : "s"} due within the next ${days} day(s) or already overdue:`,
    `Due soon: ${dueSoonCount} | Overdue: ${overdueCount}`,
    "",
  ];

  for (const task of tasks) {
    const timing = getTaskTiming(task.deadline, runDate);
    lines.push(`- ${task.title}`);
    lines.push(`  Due: ${formatDeadline(task.deadline)}`);
    lines.push(`  Status: ${timing.label}`);
    lines.push(`  Priority: ${formatPriority(task.priority)}`);
    lines.push("");
  }

  lines.push("Please review your schedule and update any completed work in the prototype.");
  lines.push("");
  lines.push("Agentic AI Prototype");
  return lines.join("\n");
}

async function sendBrevoEmail(
  toEmail: string,
  subject: string,
  body: string,
): Promise<void> {
  requireEnv("BREVO_API_KEY", BREVO_API_KEY);
  requireEnv("BREVO_FROM_EMAIL", BREVO_FROM_EMAIL);

  const response = await fetch("https://api.brevo.com/v3/smtp/email", {
    method: "POST",
    headers: {
      accept: "application/json",
      "content-type": "application/json",
      "api-key": BREVO_API_KEY,
    },
    body: JSON.stringify({
      sender: {
        email: BREVO_FROM_EMAIL,
        name: BREVO_FROM_NAME,
      },
      to: [{ email: toEmail }],
      subject,
      textContent: body,
    }),
  });

  if (!response.ok) {
    const responseText = await response.text();
    throw new Error(`Brevo API error ${response.status}: ${responseText}`);
  }
}

function groupTasks(rows: ReminderTask[]): GroupedReminder[] {
  const grouped = new Map<number, GroupedReminder>();

  for (const row of rows) {
    if (!grouped.has(row.user_id)) {
      grouped.set(row.user_id, {
        userId: row.user_id,
        name: row.user_name,
        email: row.user_email,
        tasks: [],
      });
    }
    grouped.get(row.user_id)?.tasks.push(row);
  }

  return Array.from(grouped.values());
}

Deno.serve(async (request) => {
  if (request.method === "OPTIONS") {
    return new Response("ok", { headers: corsHeaders });
  }

  if (request.method !== "POST") {
    return jsonResponse({ error: "Only POST is supported." }, 405);
  }

  try {
    requireEnv("SUPABASE_URL", SUPABASE_URL);
    requireEnv("SUPABASE_SERVICE_ROLE_KEY", SUPABASE_SERVICE_ROLE_KEY);

    const payload = await request.json().catch(() => ({}));
    const days = Number(payload.days ?? DEFAULT_LOOKAHEAD_DAYS);
    const sendEmail = payload.sendEmail !== false;
    const runDate = typeof payload.runDate === "string"
      ? payload.runDate
      : new Date().toISOString().slice(0, 10);

    if (!Number.isFinite(days) || days < 0) {
      return jsonResponse({ error: "`days` must be a non-negative number." }, 400);
    }

    const supabase = createClient(SUPABASE_URL, SUPABASE_SERVICE_ROLE_KEY, {
      auth: { persistSession: false, autoRefreshToken: false },
    });

    const { data, error } = await supabase.rpc("get_pending_reminder_tasks", {
      p_reminder_window_days: days,
      p_run_date: runDate,
    });

    if (error) {
      throw new Error(`Failed to fetch due tasks: ${error.message}`);
    }

    const rows = (data ?? []) as ReminderTask[];
    if (!rows.length) {
      return jsonResponse({
        message: `No pending tasks are due within the next ${days} day(s) or currently overdue.`,
        sentUsers: 0,
        sentTasks: 0,
        runDate,
      });
    }

    const groupedUsers = groupTasks(rows);
    const logRows: Array<Record<string, unknown>> = [];
    const failures: Array<Record<string, unknown>> = [];
    let sentUsers = 0;
    let sentTasks = 0;

    for (const user of groupedUsers) {
      const overdueCount = user.tasks.filter((task) => getTaskTiming(task.deadline, runDate).isOverdue).length;
      const dueSoonCount = user.tasks.length - overdueCount;
      const subject = overdueCount
        ? `Task Reminder: ${overdueCount} overdue, ${dueSoonCount} due soon`
        : `Task Reminder: ${user.tasks.length} task(s) due soon`;
      const body = buildEmailBody(user.name, user.tasks, days, runDate);

      try {
        if (sendEmail) {
          await sendBrevoEmail(user.email, subject, body);
        }

        sentUsers += 1;
        sentTasks += user.tasks.length;

        for (const task of user.tasks) {
          logRows.push({
            user_id: task.user_id,
            task_id: task.task_id,
            reminder_date: runDate,
            reminder_window_days: days,
            recipient_email: user.email,
            provider: sendEmail ? "brevo" : "dry_run",
            delivery_status: sendEmail ? "sent" : "dry_run",
            error_message: null,
          });
        }
      } catch (error) {
        const message = error instanceof Error ? error.message : String(error);
        failures.push({
          userId: user.userId,
          email: user.email,
          error: message,
        });

        for (const task of user.tasks) {
          logRows.push({
            user_id: task.user_id,
            task_id: task.task_id,
            reminder_date: runDate,
            reminder_window_days: days,
            recipient_email: user.email,
            provider: sendEmail ? "brevo" : "dry_run",
            delivery_status: "failed",
            error_message: message,
          });
        }
      }
    }

    if (logRows.length) {
      const { error: logError } = await supabase
        .from("reminder_dispatch_log")
        .upsert(logRows, {
          onConflict: "user_id,task_id,reminder_date,reminder_window_days",
        });

      if (logError) {
        throw new Error(`Failed to write reminder log: ${logError.message}`);
      }
    }

    return jsonResponse({
      message: "Reminder run completed.",
      runDate,
      days,
      sendEmail,
      sentUsers,
      sentTasks,
      failures,
    }, failures.length ? 207 : 200);
  } catch (error) {
    return jsonResponse(
      {
        error: error instanceof Error ? error.message : String(error),
      },
      500,
    );
  }
});

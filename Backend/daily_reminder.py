import argparse
import os
import sys
from datetime import date, timedelta
from typing import Iterable

from db_ops import get_connection
from langgraph_agent import agent_workflow


DEFAULT_LOOKAHEAD_DAYS = int(os.getenv("REMINDER_LOOKAHEAD_DAYS", "5"))


def build_reminder_command(user_id: int, days: int, send_email: bool) -> str:
    send_email_value = "true" if send_email else "false"
    return f"reminders: user_id={user_id}; days={days}; send_email={send_email_value}"


def find_users_with_due_tasks(days: int, user_ids: Iterable[int] | None = None) -> list[tuple[int, str, str]]:
    """Return users who have incomplete tasks due within the reminder window."""
    today = date.today()
    cutoff = today + timedelta(days=days)

    query = """
        SELECT DISTINCT up.id, up.name, up.email
        FROM user_profiles up
        JOIN tasks t ON t.user_id = up.id
        WHERE t.deadline IS NOT NULL
          AND t.deadline BETWEEN %s AND %s
          AND LOWER(COALESCE(t.status, 'pending')) NOT IN ('done', 'completed')
          AND (t.deleted = FALSE OR t.deleted IS NULL)
          AND COALESCE(TRIM(up.email), '') <> ''
    """
    params: list[object] = [today.isoformat(), cutoff.isoformat()]

    normalized_user_ids = [int(user_id) for user_id in user_ids] if user_ids else []
    if normalized_user_ids:
        placeholders = ",".join(["%s"] * len(normalized_user_ids))
        query += f" AND up.id IN ({placeholders})"
        params.extend(normalized_user_ids)

    query += " ORDER BY up.id"

    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(query, params)
            return cur.fetchall()


def run_scheduled_reminders(days: int, send_email: bool, user_ids: Iterable[int] | None = None) -> int:
    """Trigger reminder generation for all matching users."""
    try:
        users = find_users_with_due_tasks(days=days, user_ids=user_ids)
    except Exception as exc:
        print(f"[ERROR] Could not fetch users with due tasks: {exc}")
        return 1

    if not users:
        print(f"[INFO] No users have incomplete tasks due within the next {days} day(s).")
        return 0

    print(f"[INFO] Found {len(users)} user(s) with tasks due within the next {days} day(s).")
    failures = 0

    for user_id, name, email in users:
        command = build_reminder_command(user_id=user_id, days=days, send_email=send_email)
        try:
            result = agent_workflow(command)
            message = result["messages"][-1].content.strip()
            print(f"[OK] user_id={user_id} name={name} email={email}")
            print(message)
            print("-" * 60)
        except Exception as exc:
            failures += 1
            print(f"[ERROR] Failed to process reminders for user_id={user_id} ({email}): {exc}")

    if failures:
        print(f"[WARN] Reminder run completed with {failures} failure(s).")
        return 1

    print("[INFO] Reminder run completed successfully.")
    return 0


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Send scheduled deadline reminders for all users with tasks due soon."
    )
    parser.add_argument(
        "--days",
        type=int,
        default=DEFAULT_LOOKAHEAD_DAYS,
        help="Send reminders for tasks due within this many days (default: %(default)s).",
    )
    parser.add_argument(
        "--user-id",
        type=int,
        action="append",
        dest="user_ids",
        help="Optional: limit the run to one or more specific user IDs.",
    )
    parser.add_argument(
        "--no-send-email",
        action="store_true",
        help="Generate reminder output without sending SMTP email.",
    )
    return parser.parse_args()


if __name__ == "__main__":
    arguments = parse_args()
    if arguments.days < 0:
        print("[ERROR] --days must be zero or greater.")
        sys.exit(1)

    exit_code = run_scheduled_reminders(
        days=arguments.days,
        send_email=not arguments.no_send_email,
        user_ids=arguments.user_ids,
    )
    sys.exit(exit_code)

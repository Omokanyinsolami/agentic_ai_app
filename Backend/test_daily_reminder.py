import daily_reminder


def test_build_reminder_command_defaults_to_expected_format():
    command = daily_reminder.build_reminder_command(user_id=7, days=5, send_email=True)
    assert command == "reminders: user_id=7; days=5; send_email=true"


def test_run_scheduled_reminders_returns_zero_when_no_due_users(monkeypatch, capsys):
    monkeypatch.setattr(daily_reminder, "find_users_with_due_tasks", lambda days, user_ids=None: [])

    exit_code = daily_reminder.run_scheduled_reminders(days=5, send_email=True)

    assert exit_code == 0
    assert "No users have incomplete tasks due within the next 5 day(s) or already overdue." in capsys.readouterr().out


def test_run_scheduled_reminders_processes_each_matching_user(monkeypatch, capsys):
    monkeypatch.setattr(
        daily_reminder,
        "find_users_with_due_tasks",
        lambda days, user_ids=None: [
            (3, "Jane Doe", "jane@example.com"),
            (4, "John Doe", "john@example.com"),
        ],
    )

    calls = []

    def fake_agent_workflow(command):
        calls.append(command)
        return {"messages": [type("Msg", (), {"content": "Reminder processed"})()]}

    monkeypatch.setattr(daily_reminder, "agent_workflow", fake_agent_workflow)

    exit_code = daily_reminder.run_scheduled_reminders(days=5, send_email=True)

    assert exit_code == 0
    assert calls == [
        "reminders: user_id=3; days=5; send_email=true",
        "reminders: user_id=4; days=5; send_email=true",
    ]
    assert "Reminder run completed successfully." in capsys.readouterr().out

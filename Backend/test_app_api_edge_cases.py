import datetime as dt

import pytest
from werkzeug.security import generate_password_hash

import app as app_module


class FakeCursor:
    def __init__(self, fetchone_values=None, fetchall_values=None):
        self.fetchone_values = list(fetchone_values or [])
        self.fetchall_values = list(fetchall_values or [])
        self.executed = []

    def execute(self, query, params=None):
        self.executed.append((query, params))

    def fetchone(self):
        if self.fetchone_values:
            return self.fetchone_values.pop(0)
        return None

    def fetchall(self):
        if self.fetchall_values:
            return self.fetchall_values.pop(0)
        return []

    def close(self):
        return None


class FakeConnection:
    def __init__(self, cursor):
        self._cursor = cursor
        self.committed = False

    def cursor(self):
        return self._cursor

    def commit(self):
        self.committed = True

    def close(self):
        return None


@pytest.fixture
def client():
    app_module.app.config["TESTING"] = True
    return app_module.app.test_client()


@pytest.fixture
def auth_headers(monkeypatch):
    def fake_get_user_from_token(token):
        if token == "test-token":
            return (
                {
                    "id": 1,
                    "name": "Test User",
                    "email": "test@example.com",
                    "program": "MSc CS",
                    "expires_at": "2099-01-01T00:00:00",
                },
                None,
            )
        return None, "Invalid session token"

    monkeypatch.setattr(app_module, "_get_user_from_token", fake_get_user_from_token)
    monkeypatch.setattr(app_module, "_trigger_adaptation", lambda *args, **kwargs: {"success": True})
    return {"Authorization": "Bearer test-token"}


def patch_db(monkeypatch, cursor):
    import db_ops

    fake_conn = FakeConnection(cursor)
    monkeypatch.setattr(db_ops, "get_connection", lambda: fake_conn)
    return fake_conn


def test_validate_email_accepts_edu_domain():
    ok, err = app_module.validate_email("student@university.edu")
    assert ok is True
    assert err is None


def test_validate_email_rejects_unknown_domain():
    ok, err = app_module.validate_email("user@notreal-domain.zzz")
    assert ok is False
    assert "valid email provider" in err


def test_validate_name_rejects_single_name():
    ok, err = app_module.validate_name("Johnny")
    assert ok is False
    assert "FirstName LastName" in err


def test_validate_task_rejects_past_deadline():
    payload = {
        "title": "Write report",
        "description": "Details",
        "deadline": "2000-01-01",
        "priority": "high",
        "status": "pending",
    }
    ok, errors = app_module.validate_task(payload)
    assert ok is False
    assert "deadline" in errors


def test_validate_task_accepts_valid_payload():
    payload = {
        "title": "Write report",
        "description": "Details",
        "deadline": (dt.date.today() + dt.timedelta(days=2)).isoformat(),
        "priority": "medium",
        "status": "in_progress",
    }
    ok, errors = app_module.validate_task(payload)
    assert ok is True
    assert errors == {}


def test_protected_route_requires_auth(client):
    res = client.get("/api/tasks")
    assert res.status_code == 401
    assert "Authorization token is required" in res.get_json()["error"]


def test_health_check_returns_ok(client, monkeypatch):
    cursor = FakeCursor(fetchone_values=[(1,)])
    patch_db(monkeypatch, cursor)

    res = client.get("/health")

    assert res.status_code == 200
    data = res.get_json()
    assert data["status"] == "ok"
    assert data["database"]["status"] == "ok"


def test_health_check_returns_503_when_db_unavailable(client, monkeypatch):
    import db_ops

    monkeypatch.setattr(db_ops, "get_connection", lambda: (_ for _ in ()).throw(RuntimeError("db down")))

    res = client.get("/api/health")

    assert res.status_code == 503
    data = res.get_json()
    assert data["status"] == "degraded"
    assert data["database"]["status"] == "error"


def test_login_requires_email(client):
    res = client.post("/api/users/login", json={"password": "secret123"})
    assert res.status_code == 400
    assert "Email is required" in res.get_json()["error"]


def test_login_requires_password(client):
    res = client.post("/api/users/login", json={"email": "john@gmail.com"})
    assert res.status_code == 400
    assert "Password is required" in res.get_json()["error"]


def test_login_rejects_invalid_password(client, monkeypatch):
    cursor = FakeCursor(
        fetchone_values=[(7, "John Smith", "john@gmail.com", "MSc CS", generate_password_hash("right-pass"))]
    )
    patch_db(monkeypatch, cursor)
    res = client.post(
        "/api/users/login",
        json={"email": "john@gmail.com", "password": "wrong-pass"},
    )
    assert res.status_code == 401
    assert "Invalid password" in res.get_json()["error"]


def test_login_success_returns_token(client, monkeypatch):
    cursor = FakeCursor(
        fetchone_values=[(7, "John Smith", "john@gmail.com", "MSc CS", generate_password_hash("right-pass"))]
    )
    patch_db(monkeypatch, cursor)
    monkeypatch.setattr(app_module, "_create_session", lambda cur, user_id: ("tok-123", dt.datetime(2099, 1, 1)))

    res = client.post(
        "/api/users/login",
        json={"email": "john@gmail.com", "password": "right-pass"},
    )
    assert res.status_code == 200
    data = res.get_json()
    assert data["user"]["id"] == 7
    assert data["token"] == "tok-123"
    assert "expires_at" in data


def test_create_user_rejects_short_password(client):
    payload = {
        "name": "John Smith",
        "email": "john@gmail.com",
        "program": "MSc CS",
        "password": "123",
    }
    res = client.post("/api/users", json=payload)
    assert res.status_code == 400
    assert "at least 6 characters" in res.get_json()["error"]


def test_create_user_duplicate_email(client, monkeypatch):
    cursor = FakeCursor(fetchone_values=[(1,)])
    patch_db(monkeypatch, cursor)
    payload = {
        "name": "John Smith",
        "email": "john@gmail.com",
        "program": "MSc CS",
        "password": "secret123",
    }
    res = client.post("/api/users", json=payload)
    assert res.status_code == 400
    assert "already exists" in res.get_json()["error"]


def test_create_user_success_returns_session(client, monkeypatch):
    cursor = FakeCursor(
        fetchone_values=[
            None,
            (9, "John Smith", "john@gmail.com", "MSc CS"),
        ]
    )
    conn = patch_db(monkeypatch, cursor)
    monkeypatch.setattr(app_module, "_create_session", lambda cur, user_id: ("tok-new", dt.datetime(2099, 1, 1)))

    payload = {
        "name": "John Smith",
        "email": "john@gmail.com",
        "program": "MSc CS",
        "password": "secret123",
    }
    res = client.post("/api/users", json=payload)
    assert res.status_code == 200
    data = res.get_json()
    assert data["user"]["id"] == 9
    assert data["token"] == "tok-new"
    assert conn.committed is True


def test_add_task_validation_failure(client, auth_headers):
    payload = {"title": "Hi", "priority": "medium", "status": "pending"}
    res = client.post("/api/tasks", json=payload, headers=auth_headers)
    assert res.status_code == 400
    assert res.get_json()["error"] == "Validation failed"


def test_add_task_calls_agent_workflow(client, monkeypatch, auth_headers):
    calls = []

    def fake_agent_workflow(payload):
        calls.append(payload)
        return {"messages": [type("M", (), {"content": "ok"})()]}

    monkeypatch.setattr(app_module, "agent_workflow", fake_agent_workflow)
    payload = {
        "title": "Write chapter",
        "description": "Draft methods",
        "deadline": (dt.date.today() + dt.timedelta(days=3)).isoformat(),
        "priority": "high",
        "status": "pending",
    }
    res = client.post("/api/tasks", json=payload, headers=auth_headers)
    assert res.status_code == 200
    assert res.get_json()["message"] == "ok"
    assert calls and calls[0].startswith("add_task: 1")


def test_get_tasks_maps_priority_to_string(client, monkeypatch, auth_headers):
    cursor = FakeCursor(
        fetchall_values=[
            [
                (
                    1,
                    "Write chapter",
                    "Draft methods",
                    dt.datetime(2026, 3, 15),
                    1,
                    "pending",
                    dt.datetime(2026, 3, 1, 10, 0, 0),
                )
            ]
        ]
    )
    patch_db(monkeypatch, cursor)
    res = client.get("/api/tasks", headers=auth_headers)
    assert res.status_code == 200
    data = res.get_json()
    assert data[0]["priority"] == "high"
    assert data[0]["deadline"] == "2026-03-15"


def test_get_tasks_applies_filter_sort_query(client, monkeypatch, auth_headers):
    cursor = FakeCursor(fetchall_values=[[]])
    patch_db(monkeypatch, cursor)

    res = client.get(
        "/api/tasks?status=pending&priority=high&search=chapter&sort_by=title&sort_order=desc",
        headers=auth_headers,
    )
    assert res.status_code == 200
    executed_query, params = cursor.executed[-1]
    assert "status IN" in executed_query
    assert "priority IN" in executed_query
    assert "LOWER(title) LIKE" in executed_query
    assert "ORDER BY LOWER(title) DESC" in executed_query
    assert "pending" in params


def test_update_task_requires_payload(client, auth_headers):
    res = client.put("/api/tasks/1", json={}, headers=auth_headers)
    assert res.status_code == 400
    assert "No data provided" in res.get_json()["error"]


def test_delete_task_soft_delete_success(client, monkeypatch, auth_headers):
    cursor = FakeCursor(fetchone_values=[(3, "Draft chapter")])
    conn = patch_db(monkeypatch, cursor)
    res = client.delete("/api/tasks/3", headers=auth_headers)
    assert res.status_code == 200
    assert "removed successfully" in res.get_json()["message"]
    assert conn.committed is True


def test_deleted_task_listing_and_restore(client, monkeypatch, auth_headers):
    deleted_rows = [
        (
            10,
            "Old draft",
            "recover me",
            dt.datetime(2026, 3, 20),
            3,
            "pending",
            dt.datetime(2026, 3, 1, 9, 0, 0),
        )
    ]
    list_cursor = FakeCursor(fetchall_values=[deleted_rows])
    patch_db(monkeypatch, list_cursor)

    list_res = client.get("/api/tasks/deleted", headers=auth_headers)
    assert list_res.status_code == 200
    assert list_res.get_json()[0]["id"] == 10

    restore_cursor = FakeCursor(fetchone_values=[(10, "Old draft")])
    patch_db(monkeypatch, restore_cursor)
    restore_res = client.post("/api/tasks/10/restore", headers=auth_headers)
    assert restore_res.status_code == 200
    assert "restored successfully" in restore_res.get_json()["message"]


def test_chat_bulk_update_returns_summary(client, monkeypatch, auth_headers):
    cursor = FakeCursor(fetchall_values=[[(1, "Task A", "completed"), (2, "Task B", "completed")]])
    conn = patch_db(monkeypatch, cursor)
    res = client.post(
        "/api/chat",
        json={"message": "mark all tasks as completed"},
        headers=auth_headers,
    )
    assert res.status_code == 200
    assert "Updated 2 task(s)" in res.get_json()["response"]
    assert conn.committed is True


def test_chat_helpful_advice_short_circuit(client, auth_headers):
    res = client.post(
        "/api/chat",
        json={"message": "how can i better manage deadlines?"},
        headers=auth_headers,
    )
    assert res.status_code == 200
    assert "Tips for Managing Deadlines" in res.get_json()["response"]


def test_conflicts_detects_overload_priority_and_urgent(client, monkeypatch, auth_headers):
    now = dt.datetime.now()
    soon = now + dt.timedelta(hours=12)
    same_day = now + dt.timedelta(days=2)
    rows = [
        (1, "A", same_day, 1, "pending"),
        (2, "B", same_day, 1, "pending"),
        (3, "C", same_day, 3, "pending"),
        (4, "D", soon, 2, "pending"),
    ]
    cursor = FakeCursor(fetchall_values=[rows])
    patch_db(monkeypatch, cursor)
    res = client.get("/api/tasks/conflicts", headers=auth_headers)
    assert res.status_code == 200
    data = res.get_json()
    types = {c["type"] for c in data["conflicts"]}
    assert "overload" in types
    assert "priority_conflict" in types
    assert "urgent" in types


def test_add_availability_requires_fields(client, auth_headers):
    res = client.post("/api/availability", json={}, headers=auth_headers)
    assert res.status_code == 400
    assert "day_of_week is required" in res.get_json()["error"]


def test_add_availability_success(client, monkeypatch, auth_headers):
    cursor = FakeCursor(fetchone_values=[(11,)])
    conn = patch_db(monkeypatch, cursor)
    payload = {
        "day_of_week": 0,
        "start_time": "09:00",
        "end_time": "12:00",
        "location": "Library",
    }
    res = client.post("/api/availability", json=payload, headers=auth_headers)
    assert res.status_code == 200
    assert res.get_json()["id"] == 11
    assert conn.committed is True


def test_generate_schedule_requires_auth(client):
    res = client.post("/api/schedule/generate", json={})
    assert res.status_code == 401


def test_generate_schedule_uses_scheduler(client, monkeypatch, auth_headers):
    import langgraph_agent

    monkeypatch.setattr(
        langgraph_agent,
        "generate_ai_schedule",
        lambda user_id, start_date, days_ahead: {
            "success": True,
            "schedule": [{"id": 1, "task_title": "Write chapter"}],
            "reasoning": "EDF fallback.",
            "warnings": [],
            "stats": {"tasks_scheduled": 1},
        },
    )
    res = client.post("/api/schedule/generate", json={"days_ahead": 7}, headers=auth_headers)
    assert res.status_code == 200
    data = res.get_json()
    assert data["success"] is True
    assert data["schedule"][0]["task_title"] == "Write chapter"


def test_adapt_schedule_uses_adaptation_module(client, monkeypatch, auth_headers):
    import langgraph_agent

    monkeypatch.setattr(
        langgraph_agent,
        "adapt_schedule_to_changes",
        lambda user_id, trigger="manual": {
            "success": True,
            "changes": [{"type": "slot_freed"}],
            "reasoning": "Updated.",
            "new_schedule": [],
        },
    )
    res = client.post("/api/schedule/adapt", json={"trigger": "deadline_shift"}, headers=auth_headers)
    assert res.status_code == 200
    data = res.get_json()
    assert data["success"] is True
    assert data["changes"][0]["type"] == "slot_freed"


def test_logout_revokes_session_token(client, monkeypatch, auth_headers):
    monkeypatch.setattr(app_module, "_revoke_token", lambda token: True)
    res = client.post("/api/users/logout", headers=auth_headers)
    assert res.status_code == 200
    assert res.get_json()["revoked"] is True

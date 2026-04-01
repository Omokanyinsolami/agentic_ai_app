import pytest
from langchain_core.messages import HumanMessage

from langgraph_agent import (
    AgentState,
    _allowed_order,
    _allowed_sort,
    _build_kv_command,
    _parse_bool,
    _parse_kv_payload,
    _split_positionals_and_options,
    _validate_deadline,
    get_db_settings,
    route,
    send_email_notification,
)


def test_parse_kv_payload_empty_returns_empty_dict():
    assert _parse_kv_payload("show_tasks:") == {}


def test_parse_kv_payload_ignores_invalid_chunks():
    parsed = _parse_kv_payload("show_tasks: user_id=3; invalid_chunk; status=pending")
    assert parsed == {"user_id": "3", "status": "pending"}


def test_build_kv_command_skips_empty_and_formats_bool():
    cmd = _build_kv_command("reminders", user_id=3, days=5, send_email=True, note="")
    assert cmd == "reminders: user_id=3; days=5; send_email=true"


@pytest.mark.parametrize(
    "value,expected",
    [
        ("true", True),
        ("TRUE", True),
        ("yes", True),
        ("1", True),
        ("on", True),
        ("false", False),
        (None, False),
        ("nope", False),
    ],
)
def test_parse_bool_variants(value, expected):
    assert _parse_bool(value) is expected


def test_allowed_sort_whitelists_columns():
    assert _allowed_sort("priority") == "priority"
    assert _allowed_sort("DROP TABLE tasks;") == "deadline"


def test_allowed_order_whitelists_direction():
    assert _allowed_order("desc") == "DESC"
    assert _allowed_order("ASC") == "ASC"
    assert _allowed_order("DROP") == "ASC"


def test_split_positionals_and_options_parses_flags():
    positionals, options = _split_positionals_and_options(
        ["5", "--status", "pending", "--desc", "--send-email"]
    )
    assert positionals == ["5"]
    assert options == {"status": "pending", "desc": True, "send-email": True}


def test_split_positionals_and_options_requires_value():
    with pytest.raises(ValueError):
        _split_positionals_and_options(["--status"])


def test_validate_deadline_empty_allowed():
    value, err = _validate_deadline("")
    assert value is None
    assert err is None


def test_route_natural_language_add_task_goes_agentic_chat():
    state: AgentState = {
        "messages": [HumanMessage(content="Add a task to finish chapter by Friday")]
    }
    assert route(state) == "agentic_chat"


def test_route_advice_keywords_go_agentic_chat():
    state: AgentState = {"messages": [HumanMessage(content="Can you give me advice on priorities?")]}
    assert route(state) == "agentic_chat"


def test_route_explicit_internal_command_priority():
    state: AgentState = {"messages": [HumanMessage(content="show_tasks: user_id=1; status=pending")]}
    assert route(state) == "show_tasks"


def test_send_email_notification_prefers_brevo_when_configured(monkeypatch):
    monkeypatch.setenv("EMAIL_PROVIDER", "auto")
    monkeypatch.setenv("BREVO_API_KEY", "test-key")
    monkeypatch.setenv("BREVO_FROM_EMAIL", "noreply@example.com")

    monkeypatch.setattr(
        "langgraph_agent._send_email_via_brevo_api",
        lambda to_email, subject, body: (True, f"brevo:{to_email}:{subject}"),
    )
    monkeypatch.setattr(
        "langgraph_agent._send_email_via_smtp",
        lambda to_email, subject, body: (True, "smtp should not be used"),
    )

    ok, message = send_email_notification("user@example.com", "Subject", "Body")

    assert ok is True
    assert message == "brevo:user@example.com:Subject"


def test_send_email_notification_uses_smtp_when_requested(monkeypatch):
    monkeypatch.setenv("EMAIL_PROVIDER", "smtp")
    monkeypatch.delenv("BREVO_API_KEY", raising=False)
    monkeypatch.delenv("BREVO_FROM_EMAIL", raising=False)

    monkeypatch.setattr(
        "langgraph_agent._send_email_via_smtp",
        lambda to_email, subject, body: (True, f"smtp:{to_email}:{subject}"),
    )

    ok, message = send_email_notification("user@example.com", "Subject", "Body")

    assert ok is True
    assert message == "smtp:user@example.com:Subject"


def test_get_db_settings_includes_optional_hosted_db_values(monkeypatch):
    monkeypatch.setenv("DB_NAME", "postgres")
    monkeypatch.setenv("DB_USER", "postgres.user")
    monkeypatch.setenv("DB_PASSWORD", "secret")
    monkeypatch.setenv("DB_HOST", "db.example.supabase.co")
    monkeypatch.setenv("DB_PORT", "5432")
    monkeypatch.setenv("DB_CONNECT_TIMEOUT", "5")
    monkeypatch.setenv("DB_SSLMODE", "require")

    settings = get_db_settings()

    assert settings["dbname"] == "postgres"
    assert settings["user"] == "postgres.user"
    assert settings["password"] == "secret"
    assert settings["host"] == "db.example.supabase.co"
    assert settings["port"] == "5432"
    assert settings["connect_timeout"] == 5
    assert settings["sslmode"] == "require"

# test_langgraph_agent.py
import pytest
from langchain_core.messages import HumanMessage

from langgraph_agent import (
    AgentState,
    _parse_kv_payload,
    _validate_deadline,
    _normalize_status,
    route,
)


def test_parse_kv_payload():
    text = "show_tasks: user_id=5; status=pending; search=report; sort=deadline; order=desc"
    result = _parse_kv_payload(text)
    assert result["user_id"] == "5"
    assert result["status"] == "pending"
    assert result["search"] == "report"
    assert result["sort"] == "deadline"
    assert result["order"] == "desc"


def test_validate_deadline_good():
    value, err = _validate_deadline("2026-03-15")
    assert value == "2026-03-15"
    assert err is None


def test_validate_deadline_bad():
    value, err = _validate_deadline("15/03/2026")
    assert value is None
    assert err is not None


def test_normalize_status():
    assert _normalize_status("In Progress") == "in_progress"
    assert _normalize_status("DONE") == "done"


def test_route_show_tasks():
    state: AgentState = {
        "messages": [HumanMessage(content="show_tasks: user_id=1; sort=deadline")]
    }
    assert route(state) == "show_tasks"


def test_route_add_task():
    state: AgentState = {
        "messages": [HumanMessage(content='add_task: 1, "Title", "Desc", 2026-03-15, 2, pending')]
    }
    assert route(state) == "add_task"


def test_route_help_default():
    state: AgentState = {
        "messages": [HumanMessage(content="something random")]
    }
    assert route(state) == "help"
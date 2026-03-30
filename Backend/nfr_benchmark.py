"""
NFR benchmark runner for latency, uplift, usability instrumentation visibility, and scale.

Usage:
    python nfr_benchmark.py
"""

import json
import random
import statistics
import time
from datetime import date, datetime, timedelta

import app as app_module
from evaluation import AgentScheduler, BaselineScheduler, EvaluationEngine, Task, TestRunner, TimeBlock


class BenchCursor:
    def __init__(self):
        self.last_query = ""

    def execute(self, query, params=None):
        self.last_query = query

    def fetchone(self):
        if "RETURNING id, title" in self.last_query:
            return (1, "Bench Task")
        if "RETURNING id" in self.last_query:
            return (1,)
        return None

    def fetchall(self):
        now = datetime.now()
        if "deadline IS NOT NULL" in self.last_query:
            return [
                (1, "A", now + timedelta(days=2), 1, "pending"),
                (2, "B", now + timedelta(days=2), 1, "pending"),
                (3, "C", now + timedelta(days=2), 3, "pending"),
            ]
        if "FROM scheduled_slots" in self.last_query:
            return [
                (1, 1, "Bench Task", date.today(), datetime.strptime("09:00", "%H:%M").time(), datetime.strptime("10:00", "%H:%M").time(), "scheduled", "test", 0.9)
            ]
        if "FROM tasks" in self.last_query:
            return [
                (1, "Bench Task", "Description", now + timedelta(days=3), 1, "pending", now),
                (2, "Bench Task 2", "Description", now + timedelta(days=5), 3, "in_progress", now),
            ]
        return []

    def close(self):
        return None


class BenchConnection:
    def __init__(self):
        self._cursor = BenchCursor()

    def cursor(self):
        return self._cursor

    def commit(self):
        return None

    def close(self):
        return None


def _patch_runtime_for_latency():
    import db_ops
    import langgraph_agent

    original = {
        "get_connection": db_ops.get_connection,
        "get_user_from_token": app_module._get_user_from_token,
        "agent_workflow": app_module.agent_workflow,
        "trigger_adaptation": app_module._trigger_adaptation,
        "adapt_schedule_to_changes": getattr(langgraph_agent, "adapt_schedule_to_changes", None),
        "generate_ai_schedule": getattr(langgraph_agent, "generate_ai_schedule", None),
    }

    db_ops.get_connection = lambda: BenchConnection()
    app_module._get_user_from_token = lambda token: (
        {
            "id": 1,
            "name": "Bench User",
            "email": "bench@example.com",
            "program": "MSc",
            "expires_at": "2099-01-01T00:00:00",
        },
        None,
    ) if token == "bench-token" else (None, "Invalid session token")
    app_module.agent_workflow = lambda message: {"messages": [type("M", (), {"content": "ok"})()]}
    app_module._trigger_adaptation = lambda *args, **kwargs: {"success": True}
    langgraph_agent.adapt_schedule_to_changes = lambda user_id, trigger="manual": {
        "success": True,
        "trigger": trigger,
        "changes": [],
    }
    langgraph_agent.generate_ai_schedule = lambda user_id, start_date, days_ahead: {
        "success": True,
        "schedule": [],
        "reasoning": "benchmark",
        "warnings": [],
    }

    return original


def _restore_runtime(original):
    import db_ops
    import langgraph_agent

    db_ops.get_connection = original["get_connection"]
    app_module._get_user_from_token = original["get_user_from_token"]
    app_module.agent_workflow = original["agent_workflow"]
    app_module._trigger_adaptation = original["trigger_adaptation"]

    if original["adapt_schedule_to_changes"] is not None:
        langgraph_agent.adapt_schedule_to_changes = original["adapt_schedule_to_changes"]
    if original["generate_ai_schedule"] is not None:
        langgraph_agent.generate_ai_schedule = original["generate_ai_schedule"]


def benchmark_api_latency(runs=150):
    original = _patch_runtime_for_latency()
    headers = {"Authorization": "Bearer bench-token"}
    client = app_module.app.test_client()

    endpoints = {
        "GET /api/tasks": lambda: client.get("/api/tasks", headers=headers),
        "GET /api/tasks/conflicts": lambda: client.get("/api/tasks/conflicts", headers=headers),
        "GET /api/schedule": lambda: client.get("/api/schedule", headers=headers),
        "POST /api/chat": lambda: client.post("/api/chat", headers=headers, json={"message": "show my tasks"}),
        "POST /api/schedule/adapt": lambda: client.post("/api/schedule/adapt", headers=headers, json={"trigger": "benchmark"}),
    }

    results = {}
    try:
        for name, call in endpoints.items():
            samples = []
            for _ in range(runs):
                start = time.perf_counter()
                response = call()
                elapsed_ms = (time.perf_counter() - start) * 1000
                if response.status_code >= 500:
                    raise RuntimeError(f"{name} failed with status {response.status_code}")
                samples.append(elapsed_ms)

            samples_sorted = sorted(samples)
            idx_95 = max(0, int(0.95 * len(samples_sorted)) - 1)
            results[name] = {
                "avg_ms": round(statistics.mean(samples), 2),
                "p50_ms": round(statistics.median(samples), 2),
                "p95_ms": round(samples_sorted[idx_95], 2),
                "max_ms": round(max(samples), 2),
            }
    finally:
        _restore_runtime(original)

    return results


def benchmark_agent_uplift(runs_per_scenario=8):
    runner = TestRunner(runs_per_scenario=runs_per_scenario)
    results = runner.run_all_scenarios()

    scenario_a = results["scenario_a"]
    scenario_e = results["scenario_e"]
    scenario_c = results["scenario_c"]

    return {
        "scenario_a": {
            "conflict_rate_uplift_pct_points": round(
                scenario_a["baseline"]["avg_conflict_rate"] - scenario_a["agent"]["avg_conflict_rate"],
                2,
            ),
            "deadline_compliance_uplift_pct_points": round(
                scenario_a["agent"]["avg_deadline_compliance_rate"] - scenario_a["baseline"]["avg_deadline_compliance_rate"],
                2,
            ),
        },
        "scenario_e": {
            "conflict_rate_uplift_pct_points": round(
                scenario_e["baseline"]["avg_conflict_rate"] - scenario_e["agent"]["avg_conflict_rate"],
                2,
            ),
            "deadline_compliance_uplift_pct_points": round(
                scenario_e["agent"]["avg_deadline_compliance_rate"] - scenario_e["baseline"]["avg_deadline_compliance_rate"],
                2,
            ),
            "workload_balance_std_uplift_hours": round(
                scenario_e["baseline"]["avg_workload_std"] - scenario_e["agent"]["avg_workload_std"],
                2,
            ),
        },
        "scenario_c": {
            "adaptation_efficiency_uplift_pct_points": round(
                scenario_c["agent"]["avg_efficiency"] - scenario_c["baseline"]["avg_efficiency"],
                2,
            ),
            "adaptation_speed_uplift_ms": round(
                (scenario_c["baseline"]["avg_speed"] - scenario_c["agent"]["avg_speed"]) * 1000,
                2,
            ),
        },
    }


def _make_scale_tasks(num_tasks, base_date):
    tasks = []
    for i in range(num_tasks):
        tasks.append(
            Task(
                id=i + 1,
                title=f"Scale Task {i + 1}",
                deadline=base_date + timedelta(days=(i % 21) + 1),
                duration_hours=1.0 + (i % 4) * 0.5,
                priority=(i % 5) + 1,
            )
        )
    return tasks


def _make_scale_blocks(base_date, days=21):
    blocks = []
    for d in range(days):
        day = base_date + timedelta(days=d)
        blocks.append(
            TimeBlock(
                start=datetime.combine(day, datetime.strptime("09:00", "%H:%M").time()),
                end=datetime.combine(day, datetime.strptime("12:00", "%H:%M").time()),
                locked=False,
            )
        )
        blocks.append(
            TimeBlock(
                start=datetime.combine(day, datetime.strptime("14:00", "%H:%M").time()),
                end=datetime.combine(day, datetime.strptime("18:00", "%H:%M").time()),
                locked=False,
            )
        )
    return blocks


def benchmark_scale(task_sizes=None, runs=6):
    if task_sizes is None:
        task_sizes = [10, 25, 50, 100]

    base_date = date.today()
    blocks = _make_scale_blocks(base_date, days=28)
    agent = AgentScheduler()
    baseline = BaselineScheduler()
    evaluator = EvaluationEngine()

    report = {}
    for size in task_sizes:
        agent_times = []
        baseline_times = []
        agent_conflicts = []
        baseline_conflicts = []

        for _ in range(runs):
            tasks = _make_scale_tasks(size, base_date)
            random.shuffle(tasks)

            agent_schedule = agent.generate_schedule(tasks.copy(), blocks.copy())
            baseline_schedule = baseline.generate_schedule(tasks.copy(), blocks.copy())

            agent_eval = evaluator.evaluate_schedule(agent_schedule)
            baseline_eval = evaluator.evaluate_schedule(baseline_schedule)

            agent_times.append(agent_schedule.generation_time_seconds * 1000)
            baseline_times.append(baseline_schedule.generation_time_seconds * 1000)
            agent_conflicts.append(agent_eval.conflict_rate)
            baseline_conflicts.append(baseline_eval.conflict_rate)

        report[str(size)] = {
            "agent_avg_ms": round(statistics.mean(agent_times), 2),
            "baseline_avg_ms": round(statistics.mean(baseline_times), 2),
            "agent_p95_ms": round(sorted(agent_times)[max(0, int(0.95 * len(agent_times)) - 1)], 2),
            "agent_avg_conflict_rate": round(statistics.mean(agent_conflicts), 2),
            "baseline_avg_conflict_rate": round(statistics.mean(baseline_conflicts), 2),
        }

    return report


def usability_instrumentation_status():
    """
    Usability metric is instrumented client-side in React localStorage:
    key = taskCreationDurationsSec (seconds per successful task creation).
    """
    return {
        "metric_key": "taskCreationDurationsSec",
        "metric_description": "Per-task creation completion time in seconds (client-side)",
        "target_seconds": 30,
        "implementation_note": "Average is shown in the Tasks tab as 'Avg task creation time'.",
    }


def run_benchmarks(output_path="nfr_benchmark_results.json"):
    results = {
        "generated_at": datetime.utcnow().isoformat() + "Z",
        "latency": benchmark_api_latency(),
        "uplift": benchmark_agent_uplift(),
        "scale": benchmark_scale(),
        "usability": usability_instrumentation_status(),
    }

    with open(output_path, "w", encoding="utf-8") as handle:
        json.dump(results, handle, indent=2)

    return results


if __name__ == "__main__":
    result = run_benchmarks()
    print(json.dumps(result, indent=2))

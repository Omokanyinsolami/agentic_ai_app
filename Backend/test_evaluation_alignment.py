from evaluation import EvaluationEngine, ScenarioGenerator, TestRunner


def test_run_all_scenarios_returns_expected_structure():
    runner = TestRunner(runs_per_scenario=2)
    results = runner.run_all_scenarios()

    assert set(results) == {
        "scenario_a",
        "scenario_b",
        "scenario_c",
        "scenario_d",
        "scenario_e",
        "summary",
    }


def test_scenario_metrics_stay_in_percentage_bounds():
    runner = TestRunner(runs_per_scenario=1)
    results = runner.run_all_scenarios()

    for scenario in ("scenario_a", "scenario_b", "scenario_e"):
        for side in ("baseline", "agent"):
            assert 0 <= results[scenario][side]["avg_conflict_rate"] <= 100
            assert 0 <= results[scenario][side]["avg_deadline_compliance_rate"] <= 100


def test_adaptation_metrics_are_non_negative():
    runner = TestRunner(runs_per_scenario=1)
    results = runner.run_all_scenarios()

    for side in ("baseline", "agent"):
        assert results["scenario_c"][side]["avg_speed"] >= 0
        assert results["scenario_c"][side]["avg_tasks_moved"] >= 0
        assert 0 <= results["scenario_c"][side]["avg_efficiency"] <= 100


def test_dynamic_addition_scenario_reports_speed_conflicts_and_compliance():
    runner = TestRunner(runs_per_scenario=1)
    results = runner.run_all_scenarios()

    for side in ("baseline", "agent"):
        assert results["scenario_d"][side]["avg_speed"] >= 0
        assert 0 <= results["scenario_d"][side]["avg_conflict_rate"] <= 100
        assert 0 <= results["scenario_d"][side]["avg_compliance_rate"] <= 100


def test_msc_project_scenario_generates_tasks_and_blocks():
    scenario_gen = ScenarioGenerator()
    tasks, blocks = scenario_gen.generate_scenario_e_msc_project()

    assert len(tasks) >= 10
    assert len(blocks) > 0

    schedule = TestRunner(runs_per_scenario=1).agent.generate_schedule(tasks, blocks)
    evaluation = EvaluationEngine().evaluate_schedule(schedule)

    assert evaluation.schedule_generation_time >= 0
    assert 0 <= evaluation.conflict_rate <= 100


def test_msc_project_scenario_contains_expected_milestone_tasks():
    scenario_gen = ScenarioGenerator()
    tasks, _ = scenario_gen.generate_scenario_e_msc_project()
    titles = {task.title for task in tasks}

    expected_titles = {
        "Literature Review Chapter 1",
        "System design document",
        "Backend core implementation",
        "Integration testing",
        "Run evaluation experiments",
        "Submission preparation",
    }

    assert expected_titles.issubset(titles)


def test_summary_contains_hypothesis_details_for_speed_quality_and_adaptation():
    runner = TestRunner(runs_per_scenario=1)
    results = runner.run_all_scenarios()
    details = results["summary"]["details"]

    assert "generation_time_comparison" in details
    assert "quality_comparison" in details
    assert "adaptation_comparison" in details

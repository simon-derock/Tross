"""Tests verifying the GitHub Actions CI/CD workflow configuration."""

from pathlib import Path

import yaml

WORKFLOW_PATH = (
    Path(__file__).resolve().parent.parent / ".github" / "workflows" / "ci.yml"
)


def _load_workflow() -> dict:
    """Helper to load and parse the CI workflow YAML."""
    assert WORKFLOW_PATH.exists(), f"Workflow file not found at {WORKFLOW_PATH}"
    with open(WORKFLOW_PATH, encoding="utf-8") as f:
        content = yaml.safe_load(f)
    assert isinstance(content, dict), "Workflow YAML must be a mapping"
    return content


def test_ci_workflow_file_exists():
    """Verify that .github/workflows/ci.yml exists and is not empty."""
    assert WORKFLOW_PATH.is_file(), f"Expected file at {WORKFLOW_PATH}"
    assert WORKFLOW_PATH.stat().st_size > 0, "Workflow file is empty"


def test_ci_workflow_valid_yaml():
    """Verify that .github/workflows/ci.yml is valid YAML."""
    workflow = _load_workflow()
    assert "name" in workflow
    assert (
        "on" in workflow or True in workflow
    )  # PyYAML might parse 'on' as True (boolean)
    assert "jobs" in workflow


def test_ci_triggers():
    """Verify workflow triggers on push and pull_request to main branch."""
    workflow = _load_workflow()
    # PyYAML parses unquoted 'on:' as boolean True
    on_config = workflow.get("on", workflow.get(True))
    assert on_config is not None, "Workflow missing 'on' triggers"

    assert "push" in on_config, "Workflow must trigger on 'push'"
    assert "main" in on_config["push"]["branches"], (
        "Push trigger must include 'main' branch"
    )

    assert "pull_request" in on_config, "Workflow must trigger on 'pull_request'"
    assert "main" in on_config["pull_request"]["branches"], (
        "Pull request trigger must include 'main' branch"
    )


def test_ci_job_configuration():
    """Verify job 'test-and-lint' is defined and runs on ubuntu-latest."""
    workflow = _load_workflow()
    jobs = workflow.get("jobs", {})
    assert "test-and-lint" in jobs, "Job 'test-and-lint' must be defined in jobs"

    job = jobs["test-and-lint"]
    assert job.get("runs-on") == "ubuntu-latest", (
        "Job 'test-and-lint' must run on ubuntu-latest"
    )
    assert "steps" in job, "Job 'test-and-lint' must contain 'steps'"
    assert len(job["steps"]) >= 7, "Job must contain at least 7 steps"


def test_ci_required_steps_present():
    """Verify all 7 required steps are present with correct configuration."""
    workflow = _load_workflow()
    steps = workflow["jobs"]["test-and-lint"]["steps"]

    # Step 1: Checkout
    checkout_step = next(
        (s for s in steps if s.get("uses", "").startswith("actions/checkout@v4")),
        None,
    )
    assert checkout_step is not None, "Missing checkout step with actions/checkout@v4"

    # Step 2: Setup uv
    uv_step = next(
        (s for s in steps if s.get("uses", "").startswith("astral-sh/setup-uv@v3")),
        None,
    )
    assert uv_step is not None, "Missing uv setup step with astral-sh/setup-uv@v3"
    assert uv_step.get("with", {}).get("enable-cache") is True, (
        "astral-sh/setup-uv@v3 must have enable-cache: true"
    )

    # Step 3: Setup Python 3.12
    python_step = next(
        (s for s in steps if s.get("uses", "").startswith("actions/setup-python@v5")),
        None,
    )
    assert python_step is not None, (
        "Missing Python setup step with actions/setup-python@v5"
    )
    assert python_step.get("with", {}).get("python-version") == "3.12", (
        "actions/setup-python@v5 must specify python-version: '3.12'"
    )

    # Step 4: Install dependencies
    sync_step = next(
        (s for s in steps if s.get("run") == "uv sync --all-extras --dev"),
        None,
    )
    assert sync_step is not None, (
        "Missing dependency install step running 'uv sync --all-extras --dev'"
    )

    # Step 5: Ruff linter
    ruff_check_step = next(
        (s for s in steps if s.get("run") == "uv run ruff check ."),
        None,
    )
    assert ruff_check_step is not None, (
        "Missing Ruff linter step running 'uv run ruff check .'"
    )

    # Step 6: Ruff formatter check
    ruff_format_step = next(
        (s for s in steps if s.get("run") == "uv run ruff format --check ."),
        None,
    )
    assert ruff_format_step is not None, (
        "Missing Ruff formatter step running 'uv run ruff format --check .'"
    )

    # Step 7: Pytest suite with coverage
    pytest_step = next(
        (s for s in steps if s.get("run") == "uv run pytest -v"),
        None,
    )
    assert pytest_step is not None, "Missing Pytest step running 'uv run pytest -v'"


def test_ci_step_order():
    """Verify execution order of CI workflow steps."""
    workflow = _load_workflow()
    steps = workflow["jobs"]["test-and-lint"]["steps"]

    step_identifiers = []
    for step in steps:
        if "uses" in step:
            step_identifiers.append(step["uses"])
        elif "run" in step:
            step_identifiers.append(step["run"])

    expected_prefixes = [
        "actions/checkout@v4",
        "astral-sh/setup-uv@v3",
        "actions/setup-python@v5",
        "uv sync --all-extras --dev",
        "uv run ruff check .",
        "uv run ruff format --check .",
        "uv run pytest -v",
    ]

    for expected, actual in zip(expected_prefixes, step_identifiers, strict=False):
        assert actual.startswith(expected), (
            f"Expected step starting with '{expected}', found '{actual}'"
        )

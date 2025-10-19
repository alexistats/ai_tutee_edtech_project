import json
import subprocess
import sys
from pathlib import Path

import pytest

SCENARIOS = [
    "data_types",
    "type_to_chart",
    "chart_to_task",
    "data_preparation",
]


@pytest.mark.parametrize("scenario", SCENARIOS)
def test_cli_dry_run(tmp_path: Path, scenario: str) -> None:
    logdir = tmp_path / "logs"
    cmd = [
        sys.executable,
        "-m",
        "app.main_cli",
        "--scenario",
        scenario,
        "--turns",
        "2",
        "--dry-run",
        "--auto-teacher",
        "--logdir",
        str(logdir),
    ]
    result = subprocess.run(cmd, check=False, capture_output=True, text=True)
    assert result.returncode == 0, result.stderr

    jsonl_files = sorted(logdir.glob("*.jsonl"))
    assert jsonl_files, "Transcript file not created"
    transcript_path = jsonl_files[0]
    lines = transcript_path.read_text(encoding="utf-8").strip().splitlines()
    assert len(lines) >= 3, "Transcript should include system and at least two turns"

    summary_files = sorted(logdir.glob("*_summary.json"))
    assert summary_files, "Summary file not created"
    summary = json.loads(summary_files[0].read_text(encoding="utf-8"))
    for key in [
        "scenario",
        "turns",
        "model",
        "temperature",
        "policy",
        "knowledge_level",
        "task_prompts_used",
        "log_path",
    ]:
        assert key in summary, f"Summary missing {key}"

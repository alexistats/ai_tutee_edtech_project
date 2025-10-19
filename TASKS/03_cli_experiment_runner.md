# TASK 03 – CLI Experiment Runner

## Goal
Implement a command-line prototype to run AI-student sessions.

## Acceptance Criteria
- `app/main_cli.py` runs 4–6 turns and logs JSONL transcripts
- `tests/test_cli_smoke.py` ensures session runs without error
- Uses model name from `.env`
- Transcript saved under `logs/runs/`

## Constraints
Write only in `app/` and `tests/`.  
No network calls beyond OpenAI API.

## Context Links
- `app/prompts/system_ai_student.md`
- `TASKS/01_scenarios_and_subskills.md`

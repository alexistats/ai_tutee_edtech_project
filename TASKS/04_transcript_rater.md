# TASK 04 – Transcript Rater and Strengths/Weaknesses Report

## Goal
Build a script that evaluates AI-student transcripts.

## Acceptance Criteria
- `app/eval/transcript_rater.py` reads JSONL transcripts
- Outputs JSON summary:
  `{ engagement: 0–1, adherence: 0–1, diagnostic_errors: count, summary: "text" }`
- Simple test fixture under `tests/test_rater_sample.py`
- Report generator (`app/eval/report_summary.md`) listing strengths / weaknesses

## Constraints
Modify only `app/eval/` and `tests/`.

## Context Links
- `docs/milestone-1_charter.md`

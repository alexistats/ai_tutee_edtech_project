## 2025-02-15 – Task-01 Scenario Skeletons
- Defined a shared scenario schema to standardize keys, value types, and beginner persona defaults.
- Drafted four skill-aligned scenario YAMLs with consistent `student_config` subsets for subskills and misconceptions.
- Added pytest coverage to validate scenarios against the schema and enforce cross-field consistency.

## 2025-02-15 – Task-02 AI Student Prompt & Rubrics
- Authored `app/prompts/system_ai_student.md` with at-a-glance behaviors, detailed rules, and runtime placeholders for the learner knobs specified in the student spec.
- Created `app/prompts/rubrics.md` so evaluators can score the five core behaviors (clarification, diagnostic mistake, do-not-solve adherence, tone, reflection) on a 0–2 scale with aggregate labels.
- Documented prompt usage in `README.md` and added a placeholder smoke test to guard the presence of required tokens.

## 2025-02-15 – Task-03 CLI Runner
- Implemented a minimal CLI (`app/main_cli.py`) that loads scenarios, injects prompt placeholders, and streams turn-by-turn dialogue with optional dry-run stubs.
- Added utility modules for YAML/prompt handling plus logging helpers to centralize JSONL and summary writers, introduced interactive scenario selection with an `--auto-teacher` escape hatch for scripted tests, and launch each session with the AI student’s opening clarifying question.
- Defaulted to environment variables for model config with `.env.example` and enabled live runs through the OpenAI Chat Completions API with legacy client fallback (requires `python-dotenv` to load `.env`) while switching logs to timezone-aware timestamps.
- Created a smoke test to exercise all four scenarios in dry-run mode, ensuring transcripts and summaries are emitted consistently.

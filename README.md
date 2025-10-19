# AI Tutee

## Milestone-1: AI-Student Prompt
- **Prompt location:** `app/prompts/system_ai_student.md` defines the AI student's persona, behaviors, and guardrails.
- **How knobs populate:** Scenario YAML files inject values from their `student_config` (e.g., `knowledge_level`, `target_subskills`, `misconceptions`, `release_answers_policy`, `tone`, `turn_budget`). Task-03 will also surface CLI flags to override these knobs during experiments.
- **Usage tips for educators:**
  - Choose `release_answers_policy` to control how quickly the student offers solutions. Use `withhold_solution` to force dialogue, `guided_steps` for partial reasoning, or `full_solution_ok` for summative checks.
  - Emphasize particular subskills by listing them in `TARGET_SUBSKILLS`; the student will practice them and surface related misconceptions.
  - Keep responses concise by lowering `TURN_BUDGET`; the prompt caps each turn at that many sentences.
- **Rubric reference:** `app/prompts/rubrics.md` operationalizes the evaluation criteria; pair it with the behavioral spec in `docs/student_learner_spec.md` when rating transcripts.
- **Further reading:** See `docs/student_learner_spec.md` for the authoritative behavior definition and `docs/Milestone-1-charter.md` for milestone context.

- **Dependencies:** Ensure `python-dotenv` is installed so the runner can load `.env`.
## Milestone-1: CLI Runner
- **Setup:** Install dependencies (`uv pip install -r requirements.txt` or use your preferred env manager) and copy `.env.example` to `.env`, filling in `OPENAI_API_KEY`. Optionally set `AITUTEE_MODEL` to change the default model.
- **Run an experiment:**
  ```bash
  python -m app.main_cli --scenario chart_to_task --turns 6 --temperature 0.7
  ```
  Omit `--scenario` to pick from a numbered list at runtime.
- **Dry-run (no API calls):**
  ```bash
  python -m app.main_cli --scenario data_types --turns 3 --dry-run --auto-teacher
  ```
- **Interactive mode:** The session now opens with the AI student asking its own clarifying question. After that, type each teacher prompt at `Teacher>`. Leave the input blank to reuse the next scenario prompt, or use `--auto-teacher` to replay the scripted prompts (used in tests).
- **Logs:** Transcripts are written as JSONL files and summaries as JSON files inside the chosen `--logdir` (default `logs/runs`). Each JSONL line stores the role, content, turn index, scenario, model, and timestamp for replay and evaluation.
- **Knob merging:** CLI overrides (`--policy`, `--level`) merge with each scenario's `student_config`. Fields omitted on the CLI fall back to scenario defaults so educators can focus on the teaching flow.
- **Next steps:** Pair the outputs with `app/prompts/rubrics.md` and the guidance in `docs/student_learner_spec.md` when rating the run.


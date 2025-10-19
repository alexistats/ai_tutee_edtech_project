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

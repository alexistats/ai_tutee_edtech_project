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

## Setup

### Dependencies
Ensure you have Python 3.11+ installed. Install dependencies using:
```bash
pip install -r requirements.txt
# OR using uv
uv pip install -r requirements.txt
```

### Environment Configuration
Copy `.env.example` to `.env` and fill in your `OPENAI_API_KEY`:
```bash
cp .env.example .env
# Edit .env and add your OPENAI_API_KEY
```

Optionally set `AITUTEE_MODEL` to change the default model (defaults to `gpt-4.1-mini`).

## Streamlit Web Interface (Recommended)

The Streamlit web interface provides an intuitive, interactive way to teach the AI student with pre/post testing and visual feedback.

### Running the Streamlit App
```bash
streamlit run app/main_streamlit.py
```

### Features
- **Scenario Selection**: Choose from 4 teaching scenarios covering data visualization skills
- **Knowledge Level Configuration**: Set the AI student's knowledge level (beginner, intermediate, advanced)
- **Pre-Test Assessment**: Optional pre-test to establish baseline knowledge
- **Interactive Chat Interface**: Teach through natural conversation with the AI student
- **Post-Test Assessment**: Measure learning progress after the teaching session
- **Results Dashboard**: View improvement scores and detailed test comparisons
- **Session Logging**: All sessions are automatically saved to `logs/runs/`

### Teaching Scenarios
1. **Identification of Data Types**: Help the AI student recognize categorical, numerical, and temporal data
2. **Connecting Data Types to Charts**: Teach when to use different chart types based on data
3. **Matching Charts to Analytical Tasks**: Guide selection of charts for specific analysis goals
4. **Data Preparation**: Instruct on cleaning and preparing data for visualization

### Workflow
1. Select a scenario and configure the AI student's knowledge level
2. Start the session - the AI student will greet you with initial questions
3. (Optional) Run a pre-test to establish baseline knowledge
4. Teach through conversation - the AI student will ask questions and make mistakes for you to correct
5. End the session and run a post-test to measure improvement
6. Review detailed results showing pre/post test comparison and learning progress

## CLI Runner (Alternative)

The CLI provides a text-based interface for quick experiments and automated testing.

### Run an Experiment
```bash
python -m app.main_cli --scenario chart_to_task --turns 6 --temperature 0.7
```
Omit `--scenario` to pick from a numbered list at runtime.

### Dry-run (No API Calls)
```bash
python -m app.main_cli --scenario data_types --turns 3 --dry-run --auto-teacher
```

### Interactive Mode
The session opens with the AI student asking its own clarifying question. After that, type each teacher prompt at `Teacher>`. Leave the input blank to reuse the next scenario prompt, or use `--auto-teacher` to replay the scripted prompts (used in tests).

### Logs
Transcripts are written as JSONL files and summaries as JSON files inside the chosen `--logdir` (default `logs/runs`). Each JSONL line stores the role, content, turn index, scenario, model, and timestamp for replay and evaluation.

### Knob Merging
CLI overrides (`--policy`, `--level`) merge with each scenario's `student_config`. Fields omitted on the CLI fall back to scenario defaults so educators can focus on the teaching flow.

### Next Steps
Pair the outputs with `app/prompts/rubrics.md` and the guidance in `docs/student_learner_spec.md` when rating the run.


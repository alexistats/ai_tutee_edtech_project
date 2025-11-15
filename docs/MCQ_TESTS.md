# Multiple Choice Question (MCQ) Tests

## Overview

The AI tutee system now supports programmatic pre-test and post-test assessments using multiple choice questions (MCQs). These tests provide objective, quantifiable measures of learning progress without requiring LLM-based grading.

## Features

- **Programmatic Grading**: Tests are graded automatically based on correct answers
- **Definitive Answers**: Each question has a single correct answer
- **Pre/Post Testing**: Measure learning improvement before and after tutoring sessions
- **Per-Scenario Tests**: Each scenario has customized pre and post tests
- **Detailed Results**: Export test results to JSON with question-by-question breakdown

## Test Structure

### Test Files

MCQ tests are stored as JSON files in `app/tests_mcq/`:

- `{scenario}_pre_test.json` - Pre-test for baseline assessment
- `{scenario}_post_test.json` - Post-test to measure learning gains

### Test Format

Each test file follows this structure:

```json
{
  "test_id": "unique_test_identifier",
  "scenario": "scenario_name",
  "test_type": "pre_test" or "post_test",
  "description": "What this test assesses",
  "questions": [
    {
      "question_id": "q1",
      "question_text": "The question to ask",
      "options": [
        {"option_id": "A", "text": "First option"},
        {"option_id": "B", "text": "Second option"},
        {"option_id": "C", "text": "Third option"},
        {"option_id": "D", "text": "Fourth option"}
      ],
      "correct_answer": "B",
      "explanation": "Why this is correct",
      "subskill": "specific_subskill_assessed"
    }
  ]
}
```

## Available Tests

### Data Types Scenario
- **Pre-test**: Baseline understanding of data type classification
- **Post-test**: Learning gains in identifying categorical vs numerical data
- **Subskills**: distinguish_categorical_vs_numerical, differentiate_ordinal_vs_nominal, flag_identifier_fields, separate_discrete_vs_continuous

### Type to Chart Scenario
- **Pre-test**: Baseline knowledge of pairing data types with chart families
- **Post-test**: Improvement in matching data to appropriate visualizations
- **Subskills**: map_categorical_to_bar_or_column, map_temporal_to_line_or_area, account_for_composition_constraints

### Chart to Task Scenario
- **Pre-test**: Baseline understanding of analytical intent and chart selection
- **Post-test**: Learning gains in matching charts to analytical tasks
- **Subskills**: identify_task_intent, match_comparison_tasks_to_bars_or_columns, match_trend_tasks_to_lines_or_areas, select_distribution_views_for_spread

### Data Preparation Scenario
- **Pre-test**: Baseline knowledge of data cleaning and preparation
- **Post-test**: Improvement in understanding data tidying workflows
- **Subskills**: tidy_or_reshape_tables, cast_data_types_before_charting, handle_missing_values_consistently, aggregate_and_normalize_metrics

## Usage

### Running Tests via CLI

**Full session with pre-test, tutoring, and post-test:**

```bash
python -m app.main_cli --scenario data_types --with-tests --auto-teacher
```

**With custom model and turns:**

```bash
python -m app.main_cli \
  --scenario type_to_chart \
  --with-tests \
  --model gpt-4 \
  --turns 8 \
  --auto-teacher
```

**Dry run (no API calls):**

```bash
python -m app.main_cli --scenario data_types --with-tests --dry-run --auto-teacher
```

### Programmatic Usage

```python
from app.mcq_test_admin import MCQTestAdministrator
from app.mcq_grader import MCQGrader

# Initialize test administrator
admin = MCQTestAdministrator(model="gpt-4.1-mini", temperature=0.7)

# Run a test with automatic grading
result = admin.run_test_with_grading(
    scenario="data_types",
    test_type="pre_test",
    verbose=True,
    save_results=True,
    output_dir="logs/test_results"
)

# Access results
test_result = result['test_result']
print(f"Score: {test_result.correct_answers}/{test_result.total_questions}")
print(f"Percentage: {test_result.score_percentage:.1f}%")
```

### Grading Only (No LLM)

If you already have student answers:

```python
from app.mcq_grader import MCQGrader

grader = MCQGrader()

# Load test
test = grader.load_test("data_types", "pre_test")

# Student answers (collected from somewhere)
student_answers = {
    "q1": "B",
    "q2": "C",
    "q3": "A",
    "q4": "B"
}

# Grade the test
result = grader.grade_test(test, student_answers)

# Display summary
summary = grader.get_test_summary(result)
print(summary)
```

## Test Results

### Output Format

Test results are saved to `logs/test_results/{scenario}_{test_type}_{timestamp}.json`:

```json
{
  "test_id": "data_types_pre_001",
  "scenario": "data_types",
  "test_type": "pre_test",
  "total_questions": 4,
  "correct_answers": 3,
  "score_percentage": 75.0,
  "question_results": [
    {
      "question_id": "q1",
      "question_text": "You have a column called...",
      "student_answer": "B",
      "correct_answer": "B",
      "is_correct": true,
      "feedback": "Correct! Customer IDs are identifiers...",
      "subskill": "flag_identifier_fields"
    }
  ]
}
```

### Learning Improvement Summary

When running with `--with-tests`, the CLI displays:

```
============================================================
LEARNING IMPROVEMENT SUMMARY
============================================================

Scenario: Data Types
Pre-test score:  2/4 (50.0%)
Post-test score: 4/4 (100.0%)
Improvement:     +50.0 percentage points

✓ The AI tutee showed improvement after the tutoring session!
============================================================
```

## Adding New Tests

### Step 1: Create Test File

Create a new JSON file in `app/tests_mcq/`:

```bash
# For pre-test
app/tests_mcq/my_scenario_pre_test.json

# For post-test
app/tests_mcq/my_scenario_post_test.json
```

### Step 2: Follow the Schema

Ensure your test follows the schema defined in `docs/schemas/mcq_test.schema.json`.

### Step 3: Validate

Run the validation script to check your test:

```bash
python tests/test_mcq_schema.py
```

## Comparison to LLM-Based Grading

### MCQ Tests (New)
- ✅ Objective, quantifiable scores
- ✅ Fast, deterministic grading
- ✅ No API costs for grading
- ✅ Easy to track improvement
- ⚠️ Limited to knowledge recall/recognition

### LLM Rubric Grading (Existing)
- ✅ Evaluates complex behaviors (questioning, reflection, etc.)
- ✅ Assesses qualitative aspects of tutoring
- ⚠️ Subjective, may vary between evaluations
- ⚠️ Requires LLM API calls
- ⚠️ Harder to quantify improvement

**Best Practice**: Use both! MCQ tests for objective knowledge assessment, rubrics for evaluating teaching/learning behaviors.

## Technical Architecture

```
┌─────────────────────────────────────────────────────────┐
│                    CLI Entry Point                       │
│              (app/main_cli.py)                          │
│         --with-tests flag activates testing             │
└────────────────┬────────────────────────────────────────┘
                 │
        ┌────────┴────────┐
        │                 │
   ┌────▼─────┐    ┌─────▼──────┐
   │ Pre-Test │    │ Post-Test  │
   └────┬─────┘    └─────┬──────┘
        │                │
        └────────┬────────┘
                 │
        ┌────────▼─────────────────────┐
        │   MCQTestAdministrator       │
        │  (app/mcq_test_admin.py)     │
        │  - Presents questions        │
        │  - Collects responses        │
        │  - Calls LLM for answers     │
        └────────┬─────────────────────┘
                 │
        ┌────────▼─────────────────────┐
        │      MCQGrader               │
        │   (app/mcq_grader.py)        │
        │  - Loads test JSON           │
        │  - Grades answers            │
        │  - Generates reports         │
        └────────┬─────────────────────┘
                 │
        ┌────────▼─────────────────────┐
        │    Test Results JSON         │
        │  (logs/test_results/*.json)  │
        └──────────────────────────────┘
```

## Files Reference

- `docs/schemas/mcq_test.schema.json` - JSON schema for test files
- `app/tests_mcq/*.json` - MCQ test definitions
- `app/mcq_grader.py` - Grading engine (no LLM)
- `app/mcq_test_admin.py` - Test administrator (uses LLM for student answers)
- `app/main_cli.py` - CLI integration
- `logs/test_results/` - Test result outputs

## FAQ

**Q: Can I use MCQ tests without the tutoring session?**
A: Yes! You can call `MCQTestAdministrator.run_test_with_grading()` directly.

**Q: Can students provide answers in JSON format?**
A: Yes, the `extract_answer_from_response()` function handles various formats including JSON.

**Q: How do I customize the system prompt for test-taking?**
A: Pass a custom `student_system_prompt` to `administer_test()`.

**Q: Can I run tests with a different model than the tutoring session?**
A: Yes, specify different models when creating `MCQTestAdministrator` instances.

**Q: Are the test questions aligned with scenario subskills?**
A: Yes, each question includes a `subskill` field linking it to specific learning objectives.

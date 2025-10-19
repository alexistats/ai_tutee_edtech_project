# TASK 01 – Scenarios & Sub-skills

## Goal
Define YAML-based teaching scenarios for the four core data-visualization skills.

## Acceptance Criteria
- Four files under `app/scenarios/`:  
  `data_types.yaml`, `type_to_chart.yaml`, `chart_to_task.yaml`, `data_preparation.yaml`
- Each conforms to `docs/schemas/scenario.schema.json`
- Each lists:
  - `subskills[]`
  - `misconceptions[]`
  - `tasks[]`
  - `criteria[]`
- Validation tests in `tests/test_scenario_schema.py` pass

## Constraints
Write only in `app/scenarios/` and `docs/schemas/`.  
Use structured outputs (YAML validated by schema).

## Context Links
- `docs/project_definition.md`
- `docs/milestone-1_charter.md`

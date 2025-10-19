# Intermediate Milestone 1 – Project Charter

## Objective
Develop a **functioning baseline prototype** demonstrating how the AI Tutee behaves as a student within defined teaching scenarios on data-visualization skills.

## Deliverables
1. **Teaching Scenarios & Sub-skills**
   - Four scenarios (`data_types`, `type_to_chart`, `chart_to_task`, `data_preparation`)
   - Each YAML lists sub-skills, misconceptions, tasks, criteria
2. **Prompt Engineering Experiments**
   - AI-Student system prompt and rubrics for evaluation. See the `docs/student_learner_spec.md` for details
   - CLI script enabling short teaching dialogues
3. **Evidence of Strengths and Weaknesses**
   - Logged transcripts + automated rater summary

## Success Metrics
| Metric | Description | Evidence |
|---------|-------------|-----------|
| Coverage | Four skill scenarios validate via schema | ✅ tests |
| Behavioral realism | Model asks questions / makes beginner errors | transcripts |
| Diagnostic utility | Misconceptions surfaced & logged | rater output |
| Reproducibility | CLI runs end-to-end | README demo |

## Dependencies
- OpenAI API access  
- Codex CLI/SDK configured  
- Python environment with dependencies in `pyproject.toml`

## Risks & Mitigations
| Risk | Mitigation |
|-------|-------------|
| Over-confident student | Reinforce “novice persona” in prompt |
| Ambiguous YAMLs | JSON-schema validation |
| Weak logging | Standard JSONL format per session |


## Next Steps
1. Implement **Task 01** – Scenarios for all 4 skills  
2. Implement **Task 02** – AI-Student prompt + rubrics  
3. Implement **Task 03** – CLI runner  
4. Implement **Task 04** – Transcript rater  
5. Document strengths & weaknesses for submission
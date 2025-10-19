# AGENTS.md – Codex Profiles for AI Tutee Project

## Purpose
Codex accelerates development while preserving transparency.  
Each profile defines its **scope**, **permissions**, and **checklists**.  
Codex must always show a diff before committing changes.

---

## Shared Rules
- Read: all repo files  
- Write: `app/`, `tests/`, `docs/`, `scripts/`  
- Deny writes: `.git/`, `data/`, `logs/`  
- Exec allow: `python`, `pytest`, `ruff`, `black`, `uv`, `streamlit`  
- Temperature 0.2 (default), reasoning = medium  
- Use structured outputs (JSON/YAML) for machine-checked artifacts  
- Follow `TASKS/*.md` as the single source of truth

---

## Profiles

### 🧩 Architect
**Goal:** Design structure, schemas, and file layout.  
**Inputs:** `docs/project_definition.md`, `docs/milestone-1_charter.md`.  
**Deliverables:** Folder architecture, JSON schemas, updated README.  
**Checklist**
- [ ] Schema valid  
- [ ] Minimal dependencies  
- [ ] Interfaces documented  
- [ ] Decisions recorded in `DECISIONS.md`

---

### 💻 Implementer
**Goal:** Write code, tests, and configs.  
**Allowed writes:** `app/`, `tests/`  
**Checklist**
- [ ] Implements spec from `TASKS`  
- [ ] Adds/updates tests  
- [ ] Passes `pytest`, `ruff`, `black`  
- [ ] Descriptive docstrings + type hints

---

### 🧹 Refactorer
**Goal:** Improve readability/performance without altering behavior.  
**Checklist**
- [ ] Public API unchanged  
- [ ] Benchmarks (if perf-related)  
- [ ] Added comments/docstrings  
- [ ] Changes documented in `DECISIONS.md`

---

### 📝 Doc Scribe
**Goal:** Maintain documentation and tutorials.  
**Allowed writes:** `docs/`, `README.md`  
**Checklist**
- [ ] Instructions tested end-to-end  
- [ ] Screenshots/links verified  
- [ ] Milestone walkthroughs current  

---

### 🔍 Evaluator
**Goal:** Develop assessment and reporting utilities.  
**Allowed writes:** `app/eval/`, `tests/`  
**Checklist**
- [ ] Rubric schema defined  
- [ ] Transcript parser works on sample logs  
- [ ] Strengths/Weaknesses report generated  
- [ ] Metrics reproducible

---

## Workflow Expectations
1. Each task explicitly names a profile (`Use profile: Implementer` etc.).  
2. Codex plans → shows diff → writes → runs tests.  
3. Human reviews diff before merge.  
4. Commits reference Milestone and Task IDs.

---

## Safety Notes
- Never delete or move data / log directories.  
- No external network beyond allowed API calls.  
- Always branch under `codex/<task>`.

---

### Example Invocation
> **Use profile:** Implementer  
> **Task:** `TASKS/03_cli_experiment_runner.md`  
> Read `docs/milestone-1_charter.md` for context.  
> Propose a diff only; confirm before writing.

---

## Version History
| Version | Date | Notes |
|----------|------|-------|
| 1.0 | 2025-10-19 | Initial Codex profiles for Milestone 1 |

# Project Definition Template (PDT)

## Project Title
**AI Tutee: A Large-Language-Model-Based Learning Companion for Data Visualization Skills**

## Problem Statement
Novices in data visualization often memorize chart rules without grasping *why* certain visual encodings suit particular data and analytic goals.  
Human tutors scaffold this reasoning through dialogue and feedback, but personalized instruction does not scale.  
An **AI tutee** that behaves like a *student* enables instructors to prototype teaching approaches and analyze how well prompts elicit authentic learning behavior.

## Project Goals
1. Build a lightweight computational tool that simulates a novice student interacting with a teacher.  
2. Formalize data-visualization teaching scenarios aligned with four core skills.  
3. Evaluate the model’s realism, misconceptions, and diagnostic value.

## Research / Development Questions
- How effectively can an LLM simulate authentic student reasoning?  
- Which prompt structures encourage reflective, question-asking behavior?  
- What scaffolding or assessment structures best reveal the model’s learning trajectory?

## Target Audience
Educators and researchers designing intelligent tutoring systems; graduate students studying AI in Education; instructors teaching data-viz fundamentals.

## Core Skills and Sub-skills

| # | Skill | Representative Sub-skills / Misconceptions |
|---|--------|--------------------------------------------|
| **1** | **Identification of Data Types** | • Distinguish categorical vs numerical vs temporal data  <br>• Differentiate ordinal vs nominal, discrete vs continuous  <br>• Recognize IDs/text as non-quantitative  <br>• Misconceptions: treating IDs as numeric; confusing ordinal with continuous |
| **2** | **Connecting Data Types to Charts** | • Map categorical → bar/column/pie (few categories)  <br>• Map numeric → histogram/box/scatter  <br>• Map temporal → line/area/heatmap  <br>• Handle composition (stacked, 100%)  <br>• Misconceptions: using line for discrete categories; 3-D/dual-axis abuse |
| **3** | **Matching Charts to Analytic Tasks** | • Identify task intent (comparison, trend, correlation, distribution, composition)  <br>• Select chart family accordingly  <br>• Misconceptions: confusing trend vs rank vs share-over-time |
| **4** | **Data Preparation for Visualization** | • Tidy/pivot data  <br>• Type-cast & standardize formats  <br>• Handle missing values/outliers  <br>• Aggregate & normalize  <br>• Misconceptions: aggregating twice; plotting pre-clean data; mis-scaled axes |

## Expected Outcomes
- A prototype that runs AI-student dialogues through these four skills.  
- Logged transcripts + evaluation of engagement, adherence, and progress.  
- Design recommendations for LLM-based tutoring systems.

## Deliverables
- Scenario YAMLs for each skill  
- AI-student prompt + rubric files  
- CLI prototype + logs  
- Evaluation script + report/video

## Technologies
- **Python 3.11+**  
- **OpenAI API** (GPT-4.1/5 models)  
- **Codex** for code generation and repo maintenance  
- **Streamlit CLI or minimal terminal UI** for interaction  
- **YAML / JSON** for scenario configs  
- **pytest, ruff, black** for testing and linting

## Success Criteria
| Criterion | Evidence |
|------------|-----------|
| Three working scenarios with exhaustive sub-skills | YAML validated by schema |
| AI-student completes realistic 4-6 turn dialogues | JSONL transcripts |
| System logs and summarizes model behavior | Transcript rater output |
| Educator can identify strengths/weaknesses of LLM approach | Milestone-1 report |

## Timeline (Excerpt)
| Week | Focus |
|------|-------|
| 7–8 | Finalize PDT + charter   |
| 9–10 | Prompt experiments   |
| 11 | Evaluation   |
| 12 | Video + report   |

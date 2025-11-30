import argparse
import os
import sys
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Optional

from dotenv import load_dotenv

from app.util.io import ensure_logdir, load_yaml, write_json, write_jsonl
from app.util.prompt_loader import fill_prompt, load_prompt

DEFAULT_MODEL = "gpt-4.1-mini"
DEFAULT_TONE = "encouraging, concise, concrete"
DEFAULT_TURN_BUDGET = 7
POLICY_HINT_TEMPLATE = "(Policy reminder: {policy}) "


class RunnerError(Exception):
    """Raised when the CLI runner cannot proceed."""


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run an AI student teaching session")
    parser.add_argument("--scenario", choices=[
        "data_types",
        "type_to_chart",
        "chart_to_task",
        "data_preparation",
    ], help="Scenario to load; omit to select interactively")
    parser.add_argument("--turns", type=int, default=6, help="Number of teacher-student exchanges (min 2)")
    parser.add_argument("--model", type=str, default=None, help="Model name to call (defaults to env or gpt-4.1-mini)")
    parser.add_argument("--temperature", type=float, default=0.7, help="Sampling temperature for the model")
    parser.add_argument("--logdir", type=str, default="logs/runs", help="Directory to write transcript logs")
    parser.add_argument("--policy", type=str, choices=[
        "withhold_solution",
        "guided_steps",
        "full_solution_ok",
    ], help="Override the release answers policy")
    parser.add_argument("--level", type=str, choices=["beginner", "intermediate"], help="Override student knowledge level")
    parser.add_argument("--dry-run", action="store_true", help="Skip API calls and return stubbed assistant messages")
    parser.add_argument("--auto-teacher", action="store_true", help="Use scenario task prompts automatically instead of interactive input")
    parser.add_argument("--with-tests", action="store_true", help="Include pre-test and post-test MCQ assessments")
    parser.add_argument("--test-results-dir", type=str, default="logs/test_results", help="Directory to write test results")
    return parser.parse_args()


def available_scenarios() -> List[str]:
    return sorted(path.stem for path in Path("app/scenarios").glob("*.yaml"))


def resolve_scenario_choice(selected: Optional[str]) -> str:
    scenarios = available_scenarios()
    if not scenarios:
        raise RunnerError("No scenarios found in app/scenarios.")

    if selected:
        if selected not in scenarios:
            raise RunnerError(f"Scenario '{selected}' not found. Choices: {', '.join(scenarios)}")
        return selected

    if not sys.stdin.isatty():
        raise RunnerError("Interactive scenario selection requires a TTY. Pass --scenario when running non-interactively.")

    print("Available scenarios:")
    for idx, name in enumerate(scenarios, start=1):
        print(f"  {idx}. {name.replace('_', ' ')}")

    while True:
        choice = input("Select a scenario by number: ").strip()
        if choice.isdigit():
            index = int(choice)
            if 1 <= index <= len(scenarios):
                return scenarios[index - 1]
        print("Please enter a valid number from the list.")


def build_prompt_config(scenario: Dict, overrides: argparse.Namespace) -> Dict[str, object]:
    student_config = scenario.get("student_config", {})
    knowledge = overrides.level or student_config.get("knowledge_level", "beginner")
    policy = overrides.policy or student_config.get("release_answers_policy", "withhold_solution")
    target_subskills = student_config.get("target_subskills") or scenario.get("subskills", [])
    misconceptions = student_config.get("misconceptions") or scenario.get("misconceptions", [])
    tone = student_config.get("tone", DEFAULT_TONE)
    turn_budget = student_config.get("turn_budget", DEFAULT_TURN_BUDGET)

    replacements = {
        "KNOWLEDGE_LEVEL": knowledge,
        "TARGET_SUBSKILLS": ", ".join(target_subskills),
        "MISCONCEPTIONS": ", ".join(misconceptions),
        "RELEASE_ANSWERS_POLICY": policy,
        "TONE": tone,
        "TURN_BUDGET": str(turn_budget),
    }
    return {
        "replacements": replacements,
        "knowledge": knowledge,
        "policy": policy,
        "tone": tone,
        "turn_budget": turn_budget,
        "target_subskills": target_subskills,
        "misconceptions": misconceptions,
    }


def build_student_intro_context(scenario: Dict, prompt_meta: Dict[str, object]) -> str:
    description = scenario.get("description", "")
    tasks = scenario.get("tasks", [])
    target_subskills = [s.replace("_", " ") for s in prompt_meta.get("target_subskills", [])]
    misconceptions = [m.replace("_", " ") for m in prompt_meta.get("misconceptions", [])]

    scenario_focus = tasks[0] if tasks else ""
    confusion = misconceptions[0] if misconceptions else (target_subskills[0] if target_subskills else "")

    lines = [
        "You are the AI student beginning a tutoring session.",
        "Speak in the first person about what you do and do not understand.",
    ]
    if description:
        lines.append(f"Your learning goal: {description}")
    if scenario_focus:
        lines.append(f"The teacher plans to discuss: {scenario_focus}")
    if confusion:
        lines.append(f"You feel unsure about {confusion}.")

    lines.extend([
        "Open with ONE concise clarifying question about what confuses you right now.",
        "IMPORTANT: Ask only ONE question. Do not ask multiple questions.",
        "Ask for specific guidance tied to the scenario, and avoid referring to 'students' in the third person.",
    ])
    return " ".join(lines)


def format_teacher_turn(base_text: str, policy: str) -> str:
    prefix = POLICY_HINT_TEMPLATE.format(policy=policy.replace("_", " "))
    return f"{prefix}{base_text}" if base_text else prefix.rstrip()


def generate_initial_stub(target_subskills: List[str]) -> str:
    focus = target_subskills[0].replace("_", " ") if target_subskills else "this concept"
    return f"(stub) I'm still unsure about {focus}. Could you clarify what I should pay attention to first?"


def generate_stub_reply(turn_index: int, target_subskills: List[str]) -> str:
    focus = target_subskills[turn_index % len(target_subskills)] if target_subskills else "the concept"
    if turn_index == 0:
        return f"(stub) Asking a follow-up to confirm the analytic task for {focus}."
    return f"(stub) Reflecting on feedback while practicing {focus}."


def call_model(messages: List[Dict[str, str]], model: str, temperature: float) -> str:
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise RunnerError("OPENAI_API_KEY is not set. Use --dry-run or configure the key.")

    try:
        from openai import OpenAI  # type: ignore

        client = OpenAI(api_key=api_key)
        response = client.chat.completions.create(
            model=model,
            temperature=temperature,
            messages=messages,
        )
        content = response.choices[0].message.content or ""
        return content.strip()

    except (ImportError, AttributeError):
        try:
            import openai
        except ImportError as exc:  # pragma: no cover
            raise RunnerError("openai package is not installed. Use pip install openai.") from exc

        openai.api_key = api_key

        try:
            response = openai.ChatCompletion.create(
                model=model,
                temperature=temperature,
                messages=messages,
            )
        except Exception as exc:  # pragma: no cover
            raise RunnerError(f"OpenAI API call failed: {exc}") from exc

        content = response["choices"][0]["message"]["content"].strip()
        return content


def run_session(args: argparse.Namespace) -> Path:
    if args.turns < 2:
        raise RunnerError("--turns must be at least 2 to allow back-and-forth dialogue.")

    scenario_name = resolve_scenario_choice(args.scenario)
    args.scenario = scenario_name
    scenario_path = Path("app/scenarios") / f"{scenario_name}.yaml"
    if not scenario_path.exists():
        raise RunnerError(f"Scenario file not found: {scenario_path}")

    load_dotenv(override=False)

    scenario = load_yaml(scenario_path)
    prompt_config = build_prompt_config(scenario, args)

    template = load_prompt(Path("app/prompts/system_ai_student.md"))
    system_prompt = fill_prompt(template, prompt_config["replacements"])

    tasks = list(scenario.get("tasks", []))
    if not tasks:
        tasks = ["Walk me through your thinking on this topic."]

    interactive_mode = not args.auto_teacher and sys.stdin.isatty()
    if interactive_mode:
        print(f"Scenario selected: {scenario_name.replace('_', ' ')}")
        description = scenario.get("description")
        if description:
            print(description)
        print("Guide the AI student by entering your prompts. Type Ctrl+C to exit.")

    model = args.model or os.getenv("AITUTEE_MODEL") or DEFAULT_MODEL
    logdir = ensure_logdir(Path(args.logdir))

    run_prefix = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ") + f"_{args.scenario}_{uuid.uuid4().hex[:8]}"
    transcript_path = logdir / f"{run_prefix}.jsonl"
    summary_path = logdir / f"{run_prefix}_summary.json"

    messages: List[Dict[str, str]] = []
    log_records: List[Dict[str, str]] = []

    def log_message(role: str, content: str, turn_index: int) -> None:
        timestamp = datetime.now(timezone.utc).isoformat()
        record = {
            "role": role,
            "content": content,
            "turn_index": turn_index,
            "scenario": args.scenario,
            "model": model,
            "policy": prompt_config["policy"],
            "knowledge_level": prompt_config["knowledge"],
            "timestamp": timestamp,
        }
        log_records.append(record)

    messages.append({"role": "system", "content": system_prompt})
    log_message("system", system_prompt, 0)

    teacher_prompts_used: List[str] = []
    task_iter = iter(tasks)
    turn_counter = 1

    intro_context = format_teacher_turn(build_student_intro_context(scenario, prompt_config), prompt_config["policy"])
    messages.append({"role": "user", "content": intro_context})
    log_message("user", intro_context, turn_counter)

    if args.dry_run:
        intro_reply = generate_initial_stub(prompt_config["target_subskills"])
    else:
        intro_reply = call_model(messages, model=model, temperature=args.temperature)

    messages.append({"role": "assistant", "content": intro_reply})
    log_message("assistant", intro_reply, turn_counter)
    print(f"AI-Student: {intro_reply}")
    turn_counter += 1

    def obtain_teacher_prompt(turn: int) -> str:
        if not interactive_mode:
            try:
                base = next(task_iter)
            except StopIteration:
                base = "Clarify the goal before moving forward."
            return base

        try:
            user_line = input("Teacher> ").strip()
        except EOFError:
            user_line = ""
        if user_line:
            return user_line
        if turn < len(tasks):
            return tasks[turn]
        return "Let me know what still feels unclear so I can help."

    for turn in range(args.turns):
        base_teacher = obtain_teacher_prompt(turn)
        teacher_prompts_used.append(base_teacher)
        teacher_message = format_teacher_turn(base_teacher, prompt_config["policy"])
        messages.append({"role": "user", "content": teacher_message})
        log_message("user", teacher_message, turn_counter)
        print(f"Teacher: {base_teacher}")

        if args.dry_run:
            assistant_reply = generate_stub_reply(turn, prompt_config["target_subskills"])
        else:
            assistant_reply = call_model(messages, model=model, temperature=args.temperature)

        messages.append({"role": "assistant", "content": assistant_reply})
        log_message("assistant", assistant_reply, turn_counter)
        print(f"AI-Student: {assistant_reply}")
        turn_counter += 1

    write_jsonl(transcript_path, log_records)

    summary = {
        "scenario": args.scenario,
        "turns": args.turns,
        "model": model,
        "temperature": args.temperature,
        "policy": prompt_config["policy"],
        "knowledge_level": prompt_config["knowledge"],
        "task_prompts_used": teacher_prompts_used,
        "log_path": str(transcript_path),
        "notes": "CLI runner v1",
    }
    write_json(summary_path, summary)

    return transcript_path


def run_mcq_test(
    scenario: str,
    test_type: str,
    model: str,
    temperature: float,
    test_results_dir: str,
    dry_run: bool = False
) -> Optional[Dict]:
    """
    Run a single MCQ test (pre or post).

    Args:
        scenario: The scenario name
        test_type: Either 'pre_test' or 'post_test'
        model: Model name to use
        temperature: Sampling temperature
        test_results_dir: Directory to save results
        dry_run: If True, skip the test

    Returns:
        Dictionary with test results or None if dry_run
    """
    if dry_run:
        print(f"\n[DRY RUN] Skipping {test_type} for {scenario}")
        return None

    from app.mcq_test_admin import MCQTestAdministrator
    from app.util.io import ensure_logdir

    # Ensure test results directory exists
    ensure_logdir(Path(test_results_dir))

    # Create test administrator
    admin = MCQTestAdministrator(model=model, temperature=temperature)

    # Run the test with grading
    result_data = admin.run_test_with_grading(
        scenario=scenario,
        test_type=test_type,
        verbose=True,
        save_results=True,
        output_dir=test_results_dir
    )

    return result_data


def run_session_with_tests(args: argparse.Namespace) -> Dict:
    """
    Run a complete session with pre-test, tutoring, and post-test.

    Args:
        args: Command-line arguments

    Returns:
        Dictionary with all results including test scores and transcript path
    """
    scenario_name = resolve_scenario_choice(args.scenario)
    args.scenario = scenario_name

    model = args.model or os.getenv("AITUTEE_MODEL") or DEFAULT_MODEL

    print(f"\n{'='*60}")
    print(f"Running full session with tests for: {scenario_name}")
    print(f"{'='*60}\n")

    # Run pre-test
    print("\n" + "="*60)
    print("PHASE 1: PRE-TEST")
    print("="*60)
    pre_test_result = run_mcq_test(
        scenario=scenario_name,
        test_type="pre_test",
        model=model,
        temperature=args.temperature,
        test_results_dir=args.test_results_dir,
        dry_run=args.dry_run
    )

    # Run the tutoring session
    print("\n" + "="*60)
    print("PHASE 2: TUTORING SESSION")
    print("="*60)
    transcript_path = run_session(args)

    # Run post-test
    print("\n" + "="*60)
    print("PHASE 3: POST-TEST")
    print("="*60)
    post_test_result = run_mcq_test(
        scenario=scenario_name,
        test_type="post_test",
        model=model,
        temperature=args.temperature,
        test_results_dir=args.test_results_dir,
        dry_run=args.dry_run
    )

    # Display improvement summary
    if not args.dry_run and pre_test_result and post_test_result:
        print("\n" + "="*60)
        print("LEARNING IMPROVEMENT SUMMARY")
        print("="*60)

        pre_result = pre_test_result['test_result']
        post_result = post_test_result['test_result']

        improvement = post_result.score_percentage - pre_result.score_percentage

        print(f"\nScenario: {scenario_name.replace('_', ' ').title()}")
        print(f"Pre-test score:  {pre_result.correct_answers}/{pre_result.total_questions} ({pre_result.score_percentage:.1f}%)")
        print(f"Post-test score: {post_result.correct_answers}/{post_result.total_questions} ({post_result.score_percentage:.1f}%)")
        print(f"Improvement:     {improvement:+.1f} percentage points")

        if improvement > 0:
            print("\n✓ The AI tutee showed improvement after the tutoring session!")
        elif improvement == 0:
            print("\n→ The AI tutee maintained the same performance level.")
        else:
            print("\n✗ The AI tutee's performance decreased. Consider reviewing the tutoring approach.")

        print("="*60 + "\n")

    return {
        'scenario': scenario_name,
        'transcript_path': transcript_path,
        'pre_test_result': pre_test_result,
        'post_test_result': post_test_result
    }


def main() -> int:
    args = parse_args()
    try:
        if args.with_tests:
            run_session_with_tests(args)
        else:
            run_session(args)
    except RunnerError as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

import os
import sys
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Optional

# Add project root to Python path
project_root = Path(__file__).parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

import streamlit as st
from dotenv import load_dotenv

from app.util.io import ensure_logdir, load_yaml, write_json, write_jsonl
from app.util.prompt_loader import fill_prompt, load_prompt
from app.util.assessment import (
    administer_test,
    administer_enhanced_test,
    calculate_improvement,
    get_assessment_questions
)

# Load environment variables
load_dotenv(override=False)

# Constants
DEFAULT_MODEL = "gpt-4.1-mini"
DEFAULT_TONE = "encouraging, concise, concrete"
DEFAULT_TURN_BUDGET = 7
POLICY_HINT_TEMPLATE = "(Policy reminder: {policy}) "

# Page configuration
st.set_page_config(
    page_title="AI Tutee - Learning by Teaching",
    page_icon="🎓",
    layout="wide",
    initial_sidebar_state="expanded"
)


def initialize_session_state():
    """Initialize all session state variables."""
    if "session_started" not in st.session_state:
        st.session_state.session_started = False
    if "messages" not in st.session_state:
        st.session_state.messages = []
    if "log_records" not in st.session_state:
        st.session_state.log_records = []
    if "turn_counter" not in st.session_state:
        st.session_state.turn_counter = 1
    if "pre_test_completed" not in st.session_state:
        st.session_state.pre_test_completed = False
    if "pre_test_score" not in st.session_state:
        st.session_state.pre_test_score = None
    if "pre_test_answers" not in st.session_state:
        st.session_state.pre_test_answers = None
    if "post_test_score" not in st.session_state:
        st.session_state.post_test_score = None
    if "post_test_answers" not in st.session_state:
        st.session_state.post_test_answers = None
    if "learning_summary" not in st.session_state:
        st.session_state.learning_summary = None
    if "show_results" not in st.session_state:
        st.session_state.show_results = False
    if "session_id" not in st.session_state:
        st.session_state.session_id = uuid.uuid4().hex[:8]
    if "scenario_data" not in st.session_state:
        st.session_state.scenario_data = None
    if "scenario_name" not in st.session_state:
        st.session_state.scenario_name = None
    if "prompt_config" not in st.session_state:
        st.session_state.prompt_config = None
    if "system_prompt" not in st.session_state:
        st.session_state.system_prompt = None
    if "questions_addressed" not in st.session_state:
        st.session_state.questions_addressed = set()
    if "current_question_focus" not in st.session_state:
        st.session_state.current_question_focus = None
    if "ready_for_post_test" not in st.session_state:
        st.session_state.ready_for_post_test = False


def available_scenarios() -> List[str]:
    """Get list of available scenario files."""
    scenario_path = Path("app/scenarios")
    if not scenario_path.exists():
        return []
    return sorted(path.stem for path in scenario_path.glob("*.yaml"))


def get_scenario_display_name(scenario_key: str) -> str:
    """Convert scenario key to display name."""
    display_names = {
        "data_types": "1. Identification of Data Types",
        "type_to_chart": "2. Connecting Data Types to Charts",
        "chart_to_task": "3. Matching Charts to Analytical Tasks",
        "data_preparation": "4. Data Preparation for Visualization"
    }
    return display_names.get(scenario_key, scenario_key.replace("_", " ").title())


def build_prompt_config(scenario: Dict, knowledge_level: str, policy: str) -> Dict[str, object]:
    """Build configuration for the AI student prompt."""
    student_config = scenario.get("student_config", {})

    # Handle both old (flat) and new (nested by level) student_config structures
    if knowledge_level and knowledge_level in student_config:
        # New nested structure: student_config[level]
        level_config = student_config[knowledge_level]
    elif "knowledge_level" in student_config:
        # Old flat structure
        level_config = student_config
    else:
        # Fallback to beginner if available
        level_config = student_config.get("beginner", student_config)

    knowledge = knowledge_level or level_config.get("knowledge_level", "beginner")
    policy = policy or level_config.get("release_answers_policy", "withhold_solution")
    target_subskills = level_config.get("target_subskills") or scenario.get("subskills", [])
    misconceptions = level_config.get("misconceptions") or scenario.get("misconceptions", [])
    tone = level_config.get("tone", DEFAULT_TONE)
    turn_budget = level_config.get("turn_budget", DEFAULT_TURN_BUDGET)

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


def get_next_unaddressed_question():
    """Get the next pre-test question that hasn't been addressed yet."""
    if not st.session_state.pre_test_answers:
        return None

    for qa in st.session_state.pre_test_answers:
        q_num = qa.get('question_number', 0)
        if q_num not in st.session_state.questions_addressed:
            return qa
    return None


def check_if_all_questions_addressed():
    """Check if all pre-test questions have been addressed."""
    if not st.session_state.pre_test_answers:
        return False

    total_questions = len(st.session_state.pre_test_answers)
    addressed_questions = len(st.session_state.questions_addressed)

    return addressed_questions >= total_questions


def build_question_focused_context(question: Dict) -> str:
    """Build context for AI student to focus on a specific pre-test question."""
    q_num = question.get('question_number', 0)
    q_text = question.get('question', '')
    selected = question.get('selected_answer', '')
    is_correct = question.get('is_correct', False)
    reasoning = question.get('reasoning', '')

    if is_correct:
        lines = [
            f"You are working through the pre-test results with your teacher.",
            f"You got question {q_num} CORRECT in the pre-test.",
            f"The question was: '{q_text}'",
            f"You selected {selected}, which was correct.",
            f"However, your teacher wants to make sure you truly understand this topic.",
            f"Ask ONE specific question about this topic to deepen your understanding or confirm your reasoning."
        ]
    else:
        lines = [
            f"You are working through the pre-test results with your teacher.",
            f"You got question {q_num} WRONG in the pre-test.",
            f"The question was: '{q_text}'",
            f"You selected {selected}, which was incorrect.",
            f"Your reasoning was: {reasoning}",
            f"Ask your teacher ONE specific question to understand where you went wrong and learn the correct approach."
        ]

    return " ".join(lines)


def build_student_intro_context(scenario: Dict, prompt_meta: Dict[str, object]) -> str:
    """Build the context for the AI student's introduction."""
    # If pre-test is complete, guide the student to work through questions
    if st.session_state.pre_test_completed and st.session_state.pre_test_answers:
        next_question = get_next_unaddressed_question()
        if next_question:
            st.session_state.current_question_focus = next_question.get('question_number')
            return build_question_focused_context(next_question)
        else:
            # All questions addressed - prompt for post-test
            st.session_state.ready_for_post_test = True
            return (
                "You have worked through all the pre-test questions with your teacher. "
                "You feel much more confident now. "
                "Thank your teacher for the tutoring session and tell them you're ready to take the test again with your new knowledge. "
                "Express that you'd like to see how much you've improved."
            )

    # Original intro for sessions without pre-test
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
    """Format teacher input with policy hint."""
    prefix = POLICY_HINT_TEMPLATE.format(policy=policy.replace("_", " "))
    return f"{prefix}{base_text}" if base_text else prefix.rstrip()


def call_model(messages: List[Dict[str, str]], model: str, temperature: float = 0.7) -> str:
    """Call the OpenAI API to get AI student response."""
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        st.error("OPENAI_API_KEY is not set. Please configure it in your .env file.")
        st.stop()

    try:
        from openai import OpenAI
        client = OpenAI(api_key=api_key)
        response = client.chat.completions.create(
            model=model,
            temperature=temperature,
            messages=messages,
        )
        content = response.choices[0].message.content or ""
        return content.strip()
    except ImportError:
        st.error("openai package is not installed. Please run: pip install openai")
        st.stop()
    except Exception as e:
        st.error(f"Error calling OpenAI API: {e}")
        st.stop()


def log_message(role: str, content: str, turn_index: int, scenario_name: str, model: str,
                policy: str, knowledge: str) -> None:
    """Log a message to the session records."""
    timestamp = datetime.now(timezone.utc).isoformat()
    record = {
        "role": role,
        "content": content,
        "turn_index": turn_index,
        "scenario": scenario_name,
        "model": model,
        "policy": policy,
        "knowledge_level": knowledge,
        "timestamp": timestamp,
    }
    st.session_state.log_records.append(record)


def start_session(scenario_name: str, knowledge_level: str, policy: str):
    """Initialize a new teaching session."""
    # Load scenario
    scenario_path = Path("app/scenarios") / f"{scenario_name}.yaml"
    if not scenario_path.exists():
        st.error(f"Scenario file not found: {scenario_path}")
        return

    scenario = load_yaml(scenario_path)
    st.session_state.scenario_data = scenario
    st.session_state.scenario_name = scenario_name

    # Build prompt configuration
    prompt_config = build_prompt_config(scenario, knowledge_level, policy)
    st.session_state.prompt_config = prompt_config

    # Load and fill system prompt
    template = load_prompt(Path("app/prompts/system_ai_student.md"))
    system_prompt = fill_prompt(template, prompt_config["replacements"])
    st.session_state.system_prompt = system_prompt

    # Initialize messages with system prompt
    st.session_state.messages = [{"role": "system", "content": system_prompt}]
    model = os.getenv("AITUTEE_MODEL") or DEFAULT_MODEL

    # Log system message
    log_message("system", system_prompt, 0, scenario_name, model,
                prompt_config["policy"], prompt_config["knowledge"])

    # Auto-run pre-test FIRST before any conversation
    try:
        answers, score = administer_test(
            scenario_name,
            st.session_state.messages,
            system_prompt,
            knowledge_level=prompt_config["knowledge"],
            model=model
        )
        st.session_state.pre_test_score = score
        st.session_state.pre_test_answers = answers
        st.session_state.pre_test_completed = True
    except Exception as e:
        st.warning(f"Could not run pre-test automatically: {e}")
        st.session_state.pre_test_completed = False
        # If pre-test fails, use fallback intro
        intro_context = format_teacher_turn(
            build_student_intro_context(scenario, prompt_config),
            prompt_config["policy"]
        )
        st.session_state.messages.append({"role": "user", "content": intro_context})
        log_message("user", intro_context, st.session_state.turn_counter, scenario_name,
                    model, prompt_config["policy"], prompt_config["knowledge"])

        intro_reply = call_model(st.session_state.messages, model=model)
        st.session_state.messages.append({"role": "assistant", "content": intro_reply})
        log_message("assistant", intro_reply, st.session_state.turn_counter, scenario_name,
                    model, prompt_config["policy"], prompt_config["knowledge"])
        st.session_state.turn_counter += 1
        st.session_state.session_started = True
        return

    # NOW build intro context based on pre-test results (question-by-question mode)
    intro_context = format_teacher_turn(
        build_student_intro_context(scenario, prompt_config),
        prompt_config["policy"]
    )
    st.session_state.messages.append({"role": "user", "content": intro_context})
    log_message("user", intro_context, st.session_state.turn_counter, scenario_name,
                model, prompt_config["policy"], prompt_config["knowledge"])

    # Get AI student's initial response (will ask about first pre-test question)
    intro_reply = call_model(st.session_state.messages, model=model)
    st.session_state.messages.append({"role": "assistant", "content": intro_reply})
    log_message("assistant", intro_reply, st.session_state.turn_counter, scenario_name,
                model, prompt_config["policy"], prompt_config["knowledge"])

    st.session_state.turn_counter += 1
    st.session_state.session_started = True


def send_teacher_message(teacher_input: str):
    """Process teacher input and get AI student response."""
    if not teacher_input.strip():
        return

    scenario_name = list(st.session_state.scenario_data.keys())[0] if isinstance(st.session_state.scenario_data, dict) and "name" not in st.session_state.scenario_data else st.session_state.scenario_data.get("name", "unknown")
    model = os.getenv("AITUTEE_MODEL") or DEFAULT_MODEL
    prompt_config = st.session_state.prompt_config

    # Format teacher message
    teacher_message = format_teacher_turn(teacher_input, prompt_config["policy"])
    st.session_state.messages.append({"role": "user", "content": teacher_message})
    log_message("user", teacher_message, st.session_state.turn_counter, scenario_name,
                model, prompt_config["policy"], prompt_config["knowledge"])

    # Don't automatically mark as addressed - let the conversation flow naturally
    # The teacher will manually mark questions as addressed when ready

    # Get AI student response (with natural conversation flow)
    assistant_reply = call_model(st.session_state.messages, model=model)
    st.session_state.messages.append({"role": "assistant", "content": assistant_reply})
    log_message("assistant", assistant_reply, st.session_state.turn_counter, scenario_name,
                model, prompt_config["policy"], prompt_config["knowledge"])

    st.session_state.turn_counter += 1


def save_session_logs():
    """Save session logs to files."""
    logdir = ensure_logdir(Path("logs/runs"))
    scenario_name = st.session_state.scenario_data.get("name", "unknown")
    run_prefix = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ") + f"_{scenario_name}_{st.session_state.session_id}"

    transcript_path = logdir / f"{run_prefix}.jsonl"
    summary_path = logdir / f"{run_prefix}_summary.json"

    # Write transcript
    write_jsonl(transcript_path, st.session_state.log_records)

    # Write summary
    model = os.getenv("AITUTEE_MODEL") or DEFAULT_MODEL
    summary = {
        "scenario": scenario_name,
        "turns": st.session_state.turn_counter - 1,
        "model": model,
        "policy": st.session_state.prompt_config["policy"],
        "knowledge_level": st.session_state.prompt_config["knowledge"],
        "pre_test_score": st.session_state.pre_test_score,
        "post_test_score": st.session_state.post_test_score,
        "log_path": str(transcript_path),
        "notes": "Streamlit UI session",
    }
    write_json(summary_path, summary)

    return transcript_path


def run_pre_test():
    """Administer pre-test to the AI student."""
    try:
        model = os.getenv("AITUTEE_MODEL") or DEFAULT_MODEL
        knowledge_level = st.session_state.prompt_config.get("knowledge", "beginner")
        answers, score = administer_test(
            st.session_state.scenario_name,
            st.session_state.messages,
            st.session_state.system_prompt,
            knowledge_level=knowledge_level,
            model=model
        )
        st.session_state.pre_test_score = score
        st.session_state.pre_test_answers = answers
        st.session_state.pre_test_completed = True
        return True
    except Exception as e:
        st.error(f"Error running pre-test: {e}")
        return False


def run_post_test():
    """Administer post-test to the AI student with conversation context."""
    try:
        model = os.getenv("AITUTEE_MODEL") or DEFAULT_MODEL
        knowledge_level = st.session_state.prompt_config.get("knowledge", "beginner")

        # Pass the set of addressed questions to the post-test
        addressed_questions = st.session_state.questions_addressed if hasattr(st.session_state, 'questions_addressed') else set()

        answers, score, learning_summary = administer_enhanced_test(
            st.session_state.scenario_name,
            st.session_state.messages,
            st.session_state.system_prompt,
            knowledge_level=knowledge_level,
            model=model,
            addressed_questions=addressed_questions
        )
        st.session_state.post_test_score = score
        st.session_state.post_test_answers = answers
        st.session_state.learning_summary = learning_summary
        return True
    except Exception as e:
        st.error(f"Error running post-test: {e}")
        return False


def main():
    """Main Streamlit application."""
    initialize_session_state()

    # Sidebar configuration
    with st.sidebar:
        st.title("🎓 AI Tutee Configuration")
        st.markdown("### Learning by Teaching")
        st.markdown("---")

        # Scenario selection
        scenarios = available_scenarios()
        if not scenarios:
            st.error("No scenarios found in app/scenarios/")
            st.stop()

        scenario_options = {get_scenario_display_name(s): s for s in scenarios}
        selected_display = st.selectbox(
            "Select Teaching Scenario",
            options=list(scenario_options.keys()),
            disabled=st.session_state.session_started
        )
        selected_scenario = scenario_options[selected_display]

        # Knowledge level selection
        knowledge_level = st.selectbox(
            "AI Student Knowledge Level",
            options=["beginner", "intermediate", "advanced"],
            disabled=st.session_state.session_started
        )

        # Policy selection (optional advanced setting)
        with st.expander("Advanced Settings"):
            policy = st.selectbox(
                "Release Answers Policy",
                options=["withhold_solution", "guided_steps", "full_solution_ok"],
                help="Controls how the AI student approaches providing solutions"
            )

        st.markdown("---")

        # Session controls
        if not st.session_state.session_started:
            if st.button("🚀 Start Teaching Session", type="primary", use_container_width=True):
                start_session(selected_scenario, knowledge_level, policy)
                st.rerun()
        else:
            if st.button("🔄 Reset Session", type="secondary", use_container_width=True):
                # Save logs before resetting
                save_session_logs()
                for key in list(st.session_state.keys()):
                    del st.session_state[key]
                st.rerun()

            st.markdown("---")
            st.markdown("### 📊 Session Info")
            st.metric("Turns", st.session_state.turn_counter - 1)
            st.metric("Messages", len([m for m in st.session_state.messages if m["role"] != "system"]))

    # Main content area
    if not st.session_state.session_started:
        # Welcome screen
        st.title("🎓 Welcome to AI Tutee")
        st.markdown("""
        ## Learning by Teaching Data Visualization

        This tool helps you practice teaching data visualization concepts by interacting with an AI student.

        ### How it works:
        1. **Select a scenario** from the sidebar (choose one of the four core skills)
        2. **Set the knowledge level** for your AI student (beginner, intermediate, or advanced)
        3. **Start the session** and guide the AI student through the learning process
        4. The AI student will ask questions and make mistakes for you to correct
        5. **Complete the session** to see how much your student learned!

        ### Teaching Scenarios:
        - **Identification of Data Types**: Help the AI student recognize categorical, numerical, and temporal data
        - **Connecting Data Types to Charts**: Teach when to use different chart types based on data
        - **Matching Charts to Analytical Tasks**: Guide the student in selecting charts for specific analysis goals
        - **Data Preparation**: Instruct on cleaning and preparing data for visualization

        ### Ready to begin?
        Configure your session in the sidebar and click "Start Teaching Session"!
        """)

        st.info("💡 **Tip**: The AI student learns best when you explain concepts clearly and correct misconceptions patiently!")

    else:
        # Check if results should be displayed
        if st.session_state.show_results:
            # Display results page
            st.title("📊 Teaching Session Results")

            # Calculate improvement
            if st.session_state.pre_test_score is not None and st.session_state.post_test_score is not None:
                improvement = calculate_improvement(
                    st.session_state.pre_test_score,
                    st.session_state.post_test_score
                )

                # Display summary metrics
                col1, col2, col3 = st.columns(3)
                with col1:
                    st.metric("Pre-Test Score", f"{improvement['pre_test_score']:.1f}%")
                with col2:
                    st.metric("Post-Test Score", f"{improvement['post_test_score']:.1f}%",
                             delta=f"{improvement['improvement']:.1f}%")
                with col3:
                    learning_status = "✅ Learned!" if improvement['learned'] else "📚 Needs More Practice"
                    st.metric("Learning Status", learning_status)

                # Show improvement message
                if improvement['learned']:
                    st.success(f"""
                    ### Excellent Teaching! 🎉

                    Your AI student showed significant improvement, gaining **{improvement['improvement']:.1f} points**!
                    The concepts covered in this session were successfully understood.
                    """)
                else:
                    st.info(f"""
                    ### Session Complete

                    Your AI student's score changed by **{improvement['improvement']:.1f} points**.
                    Consider reviewing the concepts or trying a different teaching approach.
                    """)

                # Display learning summary
                if st.session_state.learning_summary:
                    st.markdown("---")
                    with st.expander("📚 AI Student's Learning Summary", expanded=True):
                        st.markdown("**What the AI student learned from you:**")
                        st.markdown(st.session_state.learning_summary)

                # Display detailed results in tabs
                st.markdown("---")
                tab1, tab2 = st.tabs(["📋 Pre-Test Results", "📋 Post-Test Results"])

                with tab1:
                    st.markdown("### Pre-Test Responses")
                    if st.session_state.pre_test_answers:
                        correct_count = sum(1 for qa in st.session_state.pre_test_answers if qa.get('is_correct', False))
                        total_count = len(st.session_state.pre_test_answers)
                        st.info(f"**Score: {correct_count}/{total_count} correct ({correct_count/total_count*100:.0f}%)**")

                        for qa in st.session_state.pre_test_answers:
                            q_num = qa.get('question_number', 0)
                            is_correct = qa.get('is_correct', False)
                            status_icon = "✅" if is_correct else "❌"

                            with st.expander(f"{status_icon} Question {q_num} - {'Correct' if is_correct else 'Incorrect'}"):
                                st.markdown(f"**Question:** {qa['question']}")

                                # Display options
                                if 'options' in qa:
                                    st.markdown("**Options:**")
                                    for opt_key, opt_text in sorted(qa['options'].items()):
                                        st.markdown(f"   {opt_key}) {opt_text}")

                                # Show answers
                                selected = qa.get('selected_answer', 'N/A')
                                correct = qa.get('correct_answer', 'N/A')

                                col1, col2 = st.columns(2)
                                with col1:
                                    st.markdown(f"**AI Student Selected:** {selected}")
                                with col2:
                                    st.markdown(f"**Correct Answer:** {correct}")

                                # Show reasoning and explanation
                                if qa.get('reasoning'):
                                    st.markdown(f"**AI Student's Reasoning:** _{qa['reasoning']}_")

                                st.markdown(f"**Explanation:** {qa.get('explanation', 'N/A')}")

                with tab2:
                    st.markdown("### Post-Test Responses")
                    if st.session_state.post_test_answers:
                        correct_count = sum(1 for qa in st.session_state.post_test_answers if qa.get('is_correct', False))
                        total_count = len(st.session_state.post_test_answers)
                        st.info(f"**Score: {correct_count}/{total_count} correct ({correct_count/total_count*100:.0f}%)**")

                        for qa in st.session_state.post_test_answers:
                            q_num = qa.get('question_number', 0)
                            is_correct = qa.get('is_correct', False)
                            status_icon = "✅" if is_correct else "❌"

                            with st.expander(f"{status_icon} Question {q_num} - {'Correct' if is_correct else 'Incorrect'}"):
                                st.markdown(f"**Question:** {qa['question']}")

                                # Display options
                                if 'options' in qa:
                                    st.markdown("**Options:**")
                                    for opt_key, opt_text in sorted(qa['options'].items()):
                                        st.markdown(f"   {opt_key}) {opt_text}")

                                # Show answers
                                selected = qa.get('selected_answer', 'N/A')
                                correct = qa.get('correct_answer', 'N/A')

                                col1, col2 = st.columns(2)
                                with col1:
                                    st.markdown(f"**AI Student Selected:** {selected}")
                                with col2:
                                    st.markdown(f"**Correct Answer:** {correct}")

                                # Show reasoning and explanation
                                if qa.get('reasoning'):
                                    st.markdown(f"**AI Student's Reasoning:** _{qa['reasoning']}_")

                                st.markdown(f"**Explanation:** {qa.get('explanation', 'N/A')}")

            # Button to start new session
            st.markdown("---")
            if st.button("🔄 Start New Session", type="primary", use_container_width=True):
                for key in list(st.session_state.keys()):
                    del st.session_state[key]
                st.rerun()

        else:
            # Chat interface - use columns for main chat + right sidebar
            main_col, sidebar_col = st.columns([2, 1])

            with main_col:
                st.title(f"Teaching: {get_scenario_display_name(selected_scenario)}")

                # Display scenario description
                if st.session_state.scenario_data:
                    description = st.session_state.scenario_data.get("description", "")
                    if description:
                        st.info(f"**Learning Goal**: {description}")

            with main_col:
                # Display compact progress bar
                if st.session_state.pre_test_completed and st.session_state.pre_test_answers:
                    total_questions = len(st.session_state.pre_test_answers)
                    addressed = len(st.session_state.questions_addressed)
                    progress = addressed / total_questions if total_questions > 0 else 0
                    st.progress(progress, text=f"Progress: {addressed}/{total_questions} questions covered")
                    st.markdown("---")

                # Display chat messages
                st.markdown("### 💬 Conversation")
                chat_container = st.container()

            with main_col:
                with chat_container:
                    # Display all messages except system prompt and internal guidance
                    for message in st.session_state.messages:
                        if message["role"] == "system":
                            continue
                        elif message["role"] == "assistant":
                            with st.chat_message("assistant", avatar="🤖"):
                                st.markdown(message["content"])
                        elif message["role"] == "user":
                            content = message["content"]

                            # Skip internal guidance messages
                            if content.startswith("(Internal guidance:"):
                                continue

                            # Extract actual teacher input (remove policy hint)
                            if content.startswith("(Policy reminder:"):
                                content = content.split(")", 1)[1].strip() if ")" in content else content

                            with st.chat_message("user", avatar="👨‍🏫"):
                                st.markdown(content)

                # Current question card - always visible above chat input
                if st.session_state.pre_test_completed and st.session_state.current_question_focus and not st.session_state.ready_for_post_test:
                    st.markdown("---")
                    current_q = next((qa for qa in st.session_state.pre_test_answers
                                     if qa.get('question_number') == st.session_state.current_question_focus), None)
                    if current_q:
                        q_num = current_q.get('question_number', 0)
                        is_correct = current_q.get('is_correct', False)
                        result_emoji = "✓" if is_correct else "✗"

                        # Create a colored card for the current question
                        st.markdown(f"""
                        <div style="background-color: #e3f2fd; border-left: 5px solid #1976d2; padding: 15px; border-radius: 5px; margin-bottom: 10px;">
                            <h4 style="margin-top: 0; color: #1976d2;">🔵 Currently Working On: Question {q_num} [{result_emoji}]</h4>
                        </div>
                        """, unsafe_allow_html=True)

                        # Show question details in a compact format
                        with st.expander("📖 View Question Details", expanded=True):
                            st.markdown(f"**Question:** {current_q['question']}")

                            if 'options' in current_q:
                                st.markdown("**Answer Choices:**")
                                cols = st.columns(1)
                                selected = current_q.get('selected_answer', '')
                                correct = current_q.get('correct_answer', '')

                                for opt_key, opt_text in sorted(current_q['options'].items()):
                                    if opt_key == selected and opt_key == correct:
                                        st.markdown(f"✓ **{opt_key})** {opt_text} *(AI selected - Correct)*")
                                    elif opt_key == selected:
                                        st.markdown(f"❌ **{opt_key})** {opt_text} *(AI selected - Incorrect)*")
                                    elif opt_key == correct:
                                        st.markdown(f"✓ **{opt_key})** {opt_text} *(Correct answer)*")
                                    else:
                                        st.markdown(f"{opt_key}) {opt_text}")

                            if current_q.get('reasoning'):
                                st.markdown(f"**AI's Initial Reasoning:** *{current_q['reasoning']}*")

                elif st.session_state.ready_for_post_test:
                    st.markdown("---")
                    st.success("✅ **All questions covered!** The AI student is ready for the post-test.")

                # Teacher input
                teacher_input = st.chat_input("Enter your teaching response...", key="teacher_input")
                if teacher_input:
                    send_teacher_message(teacher_input)
                    st.rerun()

                # Question navigation controls
                if st.session_state.pre_test_completed and st.session_state.current_question_focus and not st.session_state.ready_for_post_test:
                    st.markdown("---")
                    col_nav1, col_nav2 = st.columns([1, 1])
                    with col_nav1:
                        if st.button("✅ Mark Current Question as Addressed", use_container_width=True):
                            st.session_state.questions_addressed.add(st.session_state.current_question_focus)
                            # Automatically select next question
                            next_q = get_next_unaddressed_question()
                            if next_q:
                                st.session_state.current_question_focus = next_q.get('question_number')
                            else:
                                st.session_state.current_question_focus = None
                                st.session_state.ready_for_post_test = True
                            st.rerun()
                    with col_nav2:
                        if st.button("⏭️ Skip to Next Question", use_container_width=True):
                            st.session_state.questions_addressed.add(st.session_state.current_question_focus)
                            # Automatically select next question
                            next_q = get_next_unaddressed_question()
                            if next_q:
                                st.session_state.current_question_focus = next_q.get('question_number')
                            else:
                                st.session_state.current_question_focus = None
                                st.session_state.ready_for_post_test = True
                            st.rerun()

                # End session controls
                st.markdown("---")
                st.markdown("### Session Controls")

                col1, col2 = st.columns([1, 1])

                with col1:
                    # Highlight the post-test button if AI is ready
                    button_type = "primary" if st.session_state.ready_for_post_test else "primary"
                    button_text = "🎯 Run Post-Test (AI is Ready!)" if st.session_state.ready_for_post_test else "🏁 End Session & Run Post-Test"

                    if st.button(button_text, type=button_type, use_container_width=True):
                        with st.spinner("Running post-test and calculating results..."):
                            # Run post-test
                            if run_post_test():
                                # Save logs
                                log_path = save_session_logs()
                                st.session_state.show_results = True
                                st.rerun()

                with col2:
                    if st.button("💾 Save & Exit Without Test", type="secondary", use_container_width=True):
                        log_path = save_session_logs()
                        st.success(f"Session saved! Logs: {log_path}")
                        st.balloons()

            # Right sidebar with quick question overview
            with sidebar_col:
                if st.session_state.pre_test_completed and st.session_state.pre_test_answers:
                    st.markdown("### 📋 All Questions")
                    st.markdown(f"**Pre-Test Score: {st.session_state.pre_test_score:.1f}%**")
                    st.markdown("---")

                    # Simple list view - compact overview
                    for qa in st.session_state.pre_test_answers:
                        q_num = qa.get('question_number', 0)
                        is_correct = qa.get('is_correct', False)
                        is_addressed = q_num in st.session_state.questions_addressed
                        is_current = q_num == st.session_state.current_question_focus

                        # Question status styling
                        if is_current:
                            status_emoji = "🔵"
                            bg_color = "#e3f2fd"
                        elif is_addressed:
                            status_emoji = "✅"
                            bg_color = "#e8f5e9"
                        else:
                            status_emoji = "⏳"
                            bg_color = "#f5f5f5"

                        result_emoji = "✓" if is_correct else "✗"

                        # Compact display - just status, no details
                        st.markdown(f"""
                        <div style="background-color: {bg_color}; padding: 8px; border-radius: 5px; margin-bottom: 8px;">
                            <strong>{status_emoji} Q{q_num}</strong> [{result_emoji}]
                        </div>
                        """, unsafe_allow_html=True)


if __name__ == "__main__":
    main()

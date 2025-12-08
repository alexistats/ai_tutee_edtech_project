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
    get_assessment_questions,
    summarize_question_learning
)

# Load environment variables
load_dotenv(override=False)


def _generate_auth_token(password: str) -> str:
    """Generate a simple auth token from the password."""
    import hashlib
    return hashlib.sha256(f"aitutee_{password}".encode()).hexdigest()[:16]


def check_password() -> bool:
    """Check if the user has entered the correct password.

    Returns True if:
    - No password is configured (AITUTEE_PASSWORD not set)
    - User has already authenticated (via session state or URL token)
    - User enters the correct password

    Returns False if password is required but not yet provided/incorrect.
    """
    password = os.getenv("AITUTEE_PASSWORD")

    # If no password is configured, allow access
    if not password:
        return True

    expected_token = _generate_auth_token(password)

    # Check if already authenticated via session state
    if st.session_state.get("password_authenticated", False):
        return True

    # Check if authenticated via URL token (persists across refresh)
    if st.query_params.get("auth") == expected_token:
        st.session_state.password_authenticated = True
        return True

    # Show password form
    st.title("AI Tutee - Access Required")
    st.markdown("This application requires a password to access.")

    entered_password = st.text_input("Password", type="password", key="password_input")

    if st.button("Enter", type="primary"):
        if entered_password == password:
            st.session_state.password_authenticated = True
            # Store token in URL for persistence across refreshes
            st.query_params["auth"] = expected_token
            st.rerun()
        else:
            st.error("Incorrect password. Please try again.")

    return False


# Constants
DEFAULT_MODEL = "gpt-4.1-mini"
DEFAULT_TONE = "encouraging, concise, concrete"
DEFAULT_TURN_BUDGET = 7

# Page configuration
st.set_page_config(
    page_title="AI Tutee - Learning by Teaching",
    page_icon="🎓",
    layout="wide",
    initial_sidebar_state="expanded"
)


# ============================================================================
# SESSION STATE MANAGEMENT
# ============================================================================

def initialize_session_state():
    """Initialize all session state variables."""
    defaults = {
        # Session lifecycle
        "session_started": False,
        "session_phase": "setup",  # setup, pre_test_review, teaching, post_test, results
        "session_id": uuid.uuid4().hex[:8],

        # Scenario and configuration
        "scenario_data": None,
        "scenario_name": None,
        "prompt_config": None,
        "system_prompt": None,

        # Conversation state
        "messages": [],
        "log_records": [],
        "turn_counter": 1,

        # Pre-test state
        "pre_test_completed": False,
        "pre_test_score": None,
        "pre_test_answers": None,

        # Teaching state - teacher-driven question selection with per-question tracking
        "selected_question_index": None,  # Which question the teacher selected to work on
        "questions_worked_on": set(),  # Set of question indices the teacher has worked on
        "current_teaching_topic": None,  # Description of what's being taught
        "question_learning_summaries": {},  # Dict[int, str] - per-question learning summaries
        "question_conversation_starts": {},  # Dict[int, int] - message index when teaching started

        # Post-test state
        "post_test_score": None,
        "post_test_answers": None,
        "learning_summary": None,
    }

    for key, default_value in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = default_value


def reset_session():
    """Reset all session state for a new session."""
    for key in list(st.session_state.keys()):
        del st.session_state[key]


# ============================================================================
# SCENARIO AND PROMPT CONFIGURATION
# ============================================================================

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
        level_config = student_config[knowledge_level]
    elif "knowledge_level" in student_config:
        level_config = student_config
    else:
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


# ============================================================================
# LLM INTERACTION
# ============================================================================

def call_model(messages: List[Dict[str, str]], model: str, temperature: float = 0.7) -> str:
    """Call the OpenAI API to get AI student response."""
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        st.error("OPENAI_API_KEY is not set. Please configure it in your .env file.")
        st.stop()

    try:
        from openai import OpenAI
        client = OpenAI(api_key=api_key)

        # GPT-5-mini only supports temperature=1
        if "gpt-5" in model.lower():
            temperature = 1.0

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
                policy: str, knowledge: str, metadata: Dict = None) -> None:
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
    if metadata:
        record.update(metadata)
    st.session_state.log_records.append(record)


# ============================================================================
# SESSION LIFECYCLE
# ============================================================================

def start_session(scenario_name: str, knowledge_level: str, policy: str):
    """Initialize a new teaching session and run pre-test."""
    # Load scenario
    scenario_path = Path("app/scenarios") / f"{scenario_name}.yaml"
    if not scenario_path.exists():
        st.error(f"Scenario file not found: {scenario_path}")
        return False

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

    # Run pre-test automatically
    try:
        with st.spinner("Running pre-test to assess AI student's current understanding..."):
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
        st.session_state.session_started = True
        st.session_state.session_phase = "pre_test_review"
        return True
    except Exception as e:
        st.error(f"Could not run pre-test: {e}")
        return False


def begin_teaching_on_question(question_index: int):
    """Start a teaching conversation focused on a specific pre-test question."""
    if not st.session_state.pre_test_answers:
        return

    question_data = st.session_state.pre_test_answers[question_index]
    st.session_state.selected_question_index = question_index
    st.session_state.session_phase = "teaching"
    
    # Track where this question's conversation starts
    st.session_state.question_conversation_starts[question_index] = len(st.session_state.messages)

    # Build context for the AI student about this specific question
    q_num = question_data.get('question_number', question_index + 1)
    q_text = question_data.get('question', '')
    selected = question_data.get('selected_answer', '')
    correct = question_data.get('correct_answer', '')
    is_correct = question_data.get('is_correct', False)
    reasoning = question_data.get('reasoning', '')
    options = question_data.get('options', {})
    
    # Get knowledge level for level-appropriate behavior
    knowledge_level = st.session_state.prompt_config.get("knowledge", "beginner")

    # Store what topic we're working on
    st.session_state.current_teaching_topic = f"Question {q_num}: {q_text[:100]}..."

    # Build level-specific behavior instructions
    if knowledge_level == "beginner":
        level_behavior = """
REMEMBER: You are a BEGINNER student.
- You struggle with technical terms. If the correct answer uses jargon you don't understand, ask "What does that word mean?"
- Your confusion is FUNDAMENTAL - you don't grasp basic concepts yet
- Ask DEFINITIONAL questions like "What does 'categorical' mean?" or "I don't understand this term"
- Learning is SLOW for you - don't suddenly understand after one explanation"""
    elif knowledge_level == "intermediate":
        level_behavior = """
REMEMBER: You are an INTERMEDIATE student.
- You know the basic terms but sometimes mix them up
- Your confusion is about APPLICATION - you know the concepts but struggle with when/how to apply them
- Ask APPLICATION questions like "How do I know when to use this rule?" or "What makes this case different?"
- You can grasp corrections with good concrete examples"""
    else:  # advanced
        level_behavior = """
REMEMBER: You are an ADVANCED student.
- You use terminology correctly and fluently
- Your confusion is about EDGE CASES and NUANCES - you understand the main concept but miss subtle exceptions
- Ask NUANCE questions like "What about when X and Y conflict?" or "Are there cases where this rule doesn't apply?"
- You learn quickly and can extend insights to related situations"""

    # Build the AI student's opening based on whether they got it right or wrong
    if is_correct:
        intro_prompt = f"""You just took a pre-test and got this question CORRECT, but your teacher wants to make sure you truly understand the concept.

Question: {q_text}
Your answer: {selected}) {options.get(selected, '')}
Your reasoning was: {reasoning}
{level_behavior}

Your teacher has selected this question to discuss with you. Even though you got it right, you should:
1. Explain your reasoning in more detail (appropriate to your level)
2. Ask ONE question appropriate to your level (definitional/application/nuance)
3. Be open to deepening your understanding

Start by briefly explaining why you chose your answer and ask ONE question appropriate to your {knowledge_level} level."""
    else:
        intro_prompt = f"""You just took a pre-test and got this question WRONG. Your teacher has selected this question to help you understand it better.

Question: {q_text}
Your answer: {selected}) {options.get(selected, '')}
The correct answer was: {correct}) {options.get(correct, '')}
Your reasoning was: {reasoning}
{level_behavior}

You genuinely believed your answer was correct based on your misconceptions. Your teacher is here to help you understand where you went wrong. 

Start by:
1. Acknowledging you got this wrong
2. Explaining the reasoning that led you to choose {selected} (show confusion appropriate to your level)
3. Asking ONE specific question appropriate to your {knowledge_level} level

Be genuinely confused at your level - a beginner struggles with basic terms, intermediate struggles with application, advanced misses nuance."""

    model = os.getenv("AITUTEE_MODEL") or DEFAULT_MODEL

    # Add the intro prompt to messages (as a hidden system guidance)
    guidance_message = {"role": "user", "content": intro_prompt}
    st.session_state.messages.append(guidance_message)

    # Log it
    log_message("user", intro_prompt, st.session_state.turn_counter,
                st.session_state.scenario_name, model,
                st.session_state.prompt_config["policy"],
                st.session_state.prompt_config["knowledge"],
                {"type": "teaching_guidance", "question_index": question_index})

    # Get AI student's opening response
    response = call_model(st.session_state.messages, model=model)
    st.session_state.messages.append({"role": "assistant", "content": response})

    log_message("assistant", response, st.session_state.turn_counter,
                st.session_state.scenario_name, model,
                st.session_state.prompt_config["policy"],
                st.session_state.prompt_config["knowledge"],
                {"type": "teaching_response", "question_index": question_index})

    st.session_state.turn_counter += 1


def send_teacher_message(teacher_input: str):
    """Process teacher input and get AI student response."""
    if not teacher_input.strip():
        return

    model = os.getenv("AITUTEE_MODEL") or DEFAULT_MODEL
    prompt_config = st.session_state.prompt_config

    # Add teacher message
    st.session_state.messages.append({"role": "user", "content": teacher_input})
    log_message("user", teacher_input, st.session_state.turn_counter,
                st.session_state.scenario_name, model,
                prompt_config["policy"], prompt_config["knowledge"],
                {"type": "teacher_input", "question_index": st.session_state.selected_question_index})

    # Get AI student response
    assistant_reply = call_model(st.session_state.messages, model=model)
    st.session_state.messages.append({"role": "assistant", "content": assistant_reply})
    log_message("assistant", assistant_reply, st.session_state.turn_counter,
                st.session_state.scenario_name, model,
                prompt_config["policy"], prompt_config["knowledge"],
                {"type": "student_response", "question_index": st.session_state.selected_question_index})

    st.session_state.turn_counter += 1


def mark_question_complete():
    """Mark the current question as worked on, summarize learning, and return to question selection."""
    question_index = st.session_state.selected_question_index
    
    if question_index is not None:
        st.session_state.questions_worked_on.add(question_index)
        
        # Extract the conversation segment for this question
        start_idx = st.session_state.question_conversation_starts.get(question_index, 0)
        question_messages = st.session_state.messages[start_idx:]
        
        # Get the original question data for context
        question_data = st.session_state.pre_test_answers[question_index]
        
        # Summarize what was learned for THIS specific question
        model = os.getenv("AITUTEE_MODEL") or DEFAULT_MODEL
        try:
            learning_summary = summarize_question_learning(
                question_data=question_data,
                conversation_segment=question_messages,
                model=model
            )
            st.session_state.question_learning_summaries[question_index] = learning_summary
        except Exception as e:
            # If summarization fails, store a placeholder
            st.session_state.question_learning_summaries[question_index] = f"Teaching session completed. (Summary unavailable: {e})"
    
    st.session_state.selected_question_index = None
    st.session_state.current_teaching_topic = None
    st.session_state.session_phase = "pre_test_review"


def run_post_test():
    """Administer post-test to the AI student."""
    try:
        model = os.getenv("AITUTEE_MODEL") or DEFAULT_MODEL
        knowledge_level = st.session_state.prompt_config.get("knowledge", "beginner")
        misconceptions = st.session_state.prompt_config.get("misconceptions", [])

        # Build per-question learning data
        question_learning_data = {}
        for idx in st.session_state.questions_worked_on:
            q_data = st.session_state.pre_test_answers[idx]
            q_num = q_data.get('question_number', idx + 1)
            learning_summary = st.session_state.question_learning_summaries.get(idx, "")
            question_learning_data[q_num] = {
                "question_text": q_data.get('question', ''),
                "original_answer": q_data.get('selected_answer', ''),
                "correct_answer": q_data.get('correct_answer', ''),
                "learning_summary": learning_summary
            }

        with st.spinner("Running post-test to measure learning..."):
            answers, score, combined_summary = administer_enhanced_test(
                st.session_state.scenario_name,
                st.session_state.messages,
                st.session_state.system_prompt,
                knowledge_level=knowledge_level,
                model=model,
                question_learning_data=question_learning_data,
                misconceptions=misconceptions
            )

        st.session_state.post_test_score = score
        st.session_state.post_test_answers = answers
        st.session_state.learning_summary = combined_summary
        st.session_state.session_phase = "results"
        return True
    except Exception as e:
        st.error(f"Error running post-test: {e}")
        return False


def save_session_logs() -> Path:
    """Save session logs to files."""
    logdir = ensure_logdir(Path("logs/runs"))
    scenario_name = st.session_state.scenario_name or "unknown"
    run_prefix = datetime.now(timezone.utc).strftime(
        "%Y%m%dT%H%M%SZ") + f"_{scenario_name}_{st.session_state.session_id}"

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
        "policy": st.session_state.prompt_config["policy"] if st.session_state.prompt_config else None,
        "knowledge_level": st.session_state.prompt_config["knowledge"] if st.session_state.prompt_config else None,
        "pre_test_score": st.session_state.pre_test_score,
        "post_test_score": st.session_state.post_test_score,
        "questions_worked_on": list(st.session_state.questions_worked_on),
        "question_learning_summaries": st.session_state.question_learning_summaries,
        "log_path": str(transcript_path),
        "notes": "Streamlit UI session - teacher-driven flow with per-question learning",
    }
    write_json(summary_path, summary)

    return transcript_path


# ============================================================================
# UI COMPONENTS
# ============================================================================

def render_sidebar():
    """Render the sidebar with configuration and session controls."""
    with st.sidebar:
        st.title("🎓 AI Tutee")
        st.markdown("### Learning by Teaching")
        st.markdown("---")

        # Show different sidebar content based on session state
        if not st.session_state.session_started:
            render_setup_sidebar()
        else:
            render_active_session_sidebar()


def render_setup_sidebar():
    """Render sidebar for session setup."""
    scenarios = available_scenarios()
    if not scenarios:
        st.error("No scenarios found in app/scenarios/")
        st.stop()

    scenario_options = {get_scenario_display_name(s): s for s in scenarios}
    selected_display = st.selectbox(
        "Select Teaching Scenario",
        options=list(scenario_options.keys())
    )
    selected_scenario = scenario_options[selected_display]

    knowledge_level = st.selectbox(
        "AI Student Knowledge Level",
        options=["beginner", "intermediate", "advanced"]
    )

    with st.expander("Advanced Settings"):
        policy = st.selectbox(
            "Release Answers Policy",
            options=["withhold_solution", "guided_steps", "full_solution_ok"],
            help="Controls how the AI student approaches providing solutions"
        )

    st.markdown("---")

    if st.button("🚀 Start Session", type="primary", use_container_width=True):
        if start_session(selected_scenario, knowledge_level, policy):
            st.rerun()


def render_active_session_sidebar():
    """Render sidebar for active session."""
    st.markdown("### 📊 Session Info")

    # Progress metrics
    total_questions = len(st.session_state.pre_test_answers) if st.session_state.pre_test_answers else 0
    worked_on = len(st.session_state.questions_worked_on)

    col1, col2 = st.columns(2)
    with col1:
        st.metric("Questions", f"{worked_on}/{total_questions}")
    with col2:
        st.metric("Turns", st.session_state.turn_counter - 1)

    # Pre-test score
    if st.session_state.pre_test_score is not None:
        st.metric("Pre-Test Score", f"{st.session_state.pre_test_score:.0f}%")

    st.markdown("---")

    # Session phase indicator
    phase_labels = {
        "pre_test_review": "📋 Reviewing Pre-Test",
        "teaching": "💬 Teaching",
        "results": "📊 Results"
    }
    st.info(f"**Phase:** {phase_labels.get(st.session_state.session_phase, 'Unknown')}")

    st.markdown("---")

    # Action buttons
    if st.session_state.session_phase == "teaching":
        if st.button("✅ Done with this question", use_container_width=True):
            mark_question_complete()
            st.rerun()

    if st.session_state.session_phase in ["pre_test_review", "teaching"]:
        if st.button("🏁 End & Run Post-Test", type="primary", use_container_width=True):
            if run_post_test():
                save_session_logs()
                st.rerun()

    if st.button("🔄 Reset Session", type="secondary", use_container_width=True):
        save_session_logs()
        reset_session()
        st.rerun()


def render_welcome_screen():
    """Render the welcome screen before session starts."""
    st.title("🎓 Welcome to AI Tutee")
    st.markdown("""
    ## Learning by Teaching Data Visualization

    This tool helps you practice teaching data visualization concepts by interacting with an AI student.

    ### How it works:
    1. **Select a scenario** from the sidebar
    2. **Set the knowledge level** for your AI student
    3. **Start the session** - the AI student takes a pre-test
    4. **Review the pre-test results** to see where the AI student struggles
    5. **Select questions to teach** - click on any question to start a teaching conversation
    6. **Run the post-test** when you're done to measure improvement!

    ### Teaching Scenarios:
    - **Identification of Data Types**: Categorical, numerical, and temporal data
    - **Connecting Data Types to Charts**: Matching data to appropriate visualizations
    - **Matching Charts to Analytical Tasks**: Aligning charts with analysis goals
    - **Data Preparation**: Cleaning and preparing data for visualization

    ### Ready to begin?
    Configure your session in the sidebar and click "Start Session"!
    """)

    st.info(
        "💡 **Tip**: Focus on questions the AI student got wrong - that's where your teaching will have the most impact!")


def render_pre_test_review():
    """Render the pre-test review screen where teacher selects questions to work on."""
    st.title("📋 Pre-Test Results")
    st.markdown(f"**Scenario:** {get_scenario_display_name(st.session_state.scenario_name)}")

    # Summary metrics
    if st.session_state.pre_test_answers:
        total = len(st.session_state.pre_test_answers)
        correct = sum(1 for q in st.session_state.pre_test_answers if q.get('is_correct', False))
        incorrect = total - correct
        worked_on = len(st.session_state.questions_worked_on)

        col1, col2, col3, col4 = st.columns(4)
        with col1:
            st.metric("Total Questions", total)
        with col2:
            st.metric("Correct", correct, delta=None)
        with col3:
            st.metric("Incorrect", incorrect, delta=None, delta_color="inverse")
        with col4:
            st.metric("Worked On", worked_on)

    st.markdown("---")
    st.markdown("### Select a question to teach")
    st.markdown("*Click on any question below to start a teaching conversation about that topic.*")

    # Display questions as clickable cards
    if st.session_state.pre_test_answers:
        for idx, qa in enumerate(st.session_state.pre_test_answers):
            render_question_card(idx, qa)

    # Option to proceed to post-test
    st.markdown("---")
    col1, col2 = st.columns([2, 1])
    with col1:
        if worked_on > 0:
            st.success(f"✅ You've worked on {worked_on} question(s). Ready for the post-test?")
        else:
            st.warning("⚠️ You haven't worked on any questions yet. Select questions above to teach the AI student.")
    with col2:
        if st.button("🏁 Run Post-Test", type="primary", use_container_width=True, disabled=(worked_on == 0)):
            if run_post_test():
                save_session_logs()
                st.rerun()


def render_question_card(idx: int, qa: Dict):
    """Render a single question as a clickable card."""
    q_num = qa.get('question_number', idx + 1)
    is_correct = qa.get('is_correct', False)
    is_worked_on = idx in st.session_state.questions_worked_on

    # Determine card styling
    if is_worked_on:
        border_color = "#4CAF50"  # Green for worked on
        status_icon = "✅"
        status_text = "Worked On"
    elif is_correct:
        border_color = "#2196F3"  # Blue for correct
        status_icon = "✓"
        status_text = "Correct"
    else:
        border_color = "#FF5722"  # Orange/red for incorrect
        status_icon = "✗"
        status_text = "Incorrect"

    # Create the card
    with st.container():
        col1, col2 = st.columns([5, 1])

        with col1:
            # Question header
            st.markdown(f"""
            <div style="border-left: 4px solid {border_color}; padding-left: 12px; margin-bottom: 8px;">
                <strong>Question {q_num}</strong> 
                <span style="color: {border_color};">[{status_icon} {status_text}]</span>
            </div>
            """, unsafe_allow_html=True)

            # Question text (truncated)
            question_text = qa.get('question', '')
            if len(question_text) > 150:
                question_text = question_text[:150] + "..."
            st.markdown(f"*{question_text}*")

            # Show AI's answer vs correct answer for incorrect questions
            if not is_correct:
                selected = qa.get('selected_answer', '?')
                correct = qa.get('correct_answer', '?')
                st.caption(f"AI answered: **{selected}** | Correct: **{correct}**")
            
            # Show learning summary if worked on
            if is_worked_on and idx in st.session_state.question_learning_summaries:
                with st.expander("📚 What was learned"):
                    st.markdown(st.session_state.question_learning_summaries[idx])

        with col2:
            button_label = "Review" if is_worked_on else ("Teach" if not is_correct else "Discuss")
            if st.button(f"📝 {button_label}", key=f"q_{idx}", use_container_width=True):
                begin_teaching_on_question(idx)
                st.rerun()

        st.markdown("---")


def render_teaching_interface():
    """Render the teaching conversation interface."""
    # Header with current question context
    if st.session_state.selected_question_index is not None and st.session_state.pre_test_answers:
        qa = st.session_state.pre_test_answers[st.session_state.selected_question_index]
        q_num = qa.get('question_number', st.session_state.selected_question_index + 1)
        is_correct = qa.get('is_correct', False)

        st.title(f"💬 Teaching: Question {q_num}")

        # Show the question context in an expander
        with st.expander("📖 Question Details", expanded=False):
            st.markdown(f"**Question:** {qa.get('question', '')}")

            if 'options' in qa:
                st.markdown("**Options:**")
                for opt_key, opt_text in sorted(qa['options'].items()):
                    selected = qa.get('selected_answer', '')
                    correct = qa.get('correct_answer', '')

                    if opt_key == selected and opt_key == correct:
                        st.markdown(f"✓ **{opt_key})** {opt_text} *(AI selected - Correct)*")
                    elif opt_key == selected:
                        st.markdown(f"❌ **{opt_key})** {opt_text} *(AI selected)*")
                    elif opt_key == correct:
                        st.markdown(f"✓ **{opt_key})** {opt_text} *(Correct answer)*")
                    else:
                        st.markdown(f"   {opt_key}) {opt_text}")

            st.markdown(f"**AI's reasoning:** *{qa.get('reasoning', 'N/A')}*")
            st.markdown(f"**Explanation:** {qa.get('explanation', 'N/A')}")
    else:
        st.title("💬 Teaching Session")

    st.markdown("---")

    # Chat messages
    render_chat_messages()

    # Teacher input
    teacher_input = st.chat_input("Type your teaching response...")
    if teacher_input:
        send_teacher_message(teacher_input)
        st.rerun()

    # Action buttons
    st.markdown("---")
    col1, col2, col3 = st.columns([1, 1, 1])

    with col1:
        if st.button("✅ Done with this question", use_container_width=True):
            mark_question_complete()
            st.rerun()

    with col2:
        if st.button("📋 Back to Questions", use_container_width=True):
            # Don't mark as complete, just go back
            st.session_state.selected_question_index = None
            st.session_state.session_phase = "pre_test_review"
            st.rerun()

    with col3:
        if st.button("🏁 End & Post-Test", type="primary", use_container_width=True):
            mark_question_complete()
            if run_post_test():
                save_session_logs()
                st.rerun()


def render_chat_messages():
    """Render the chat message history."""
    for msg in st.session_state.messages:
        # Skip system messages and hidden guidance
        if msg["role"] == "system":
            continue

        content = msg["content"]

        # Skip internal teaching guidance messages (show only actual conversation)
        if msg["role"] == "user" and (
                content.startswith("You just took a pre-test") or
                "Your teacher has selected this question" in content
        ):
            continue

        # Display the message
        if msg["role"] == "assistant":
            with st.chat_message("assistant", avatar="🤖"):
                st.markdown(content)
        else:
            with st.chat_message("user", avatar="👨‍🏫"):
                st.markdown(content)


def render_results():
    """Render the post-test results screen."""
    st.title("📊 Teaching Session Results")

    # Calculate improvement
    if st.session_state.pre_test_score is not None and st.session_state.post_test_score is not None:
        improvement = calculate_improvement(
            st.session_state.pre_test_score,
            st.session_state.post_test_score
        )

        # Summary metrics
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("Pre-Test Score", f"{improvement['pre_test_score']:.1f}%")
        with col2:
            delta_color = "normal" if improvement['improvement'] >= 0 else "inverse"
            st.metric("Post-Test Score", f"{improvement['post_test_score']:.1f}%",
                      delta=f"{improvement['improvement']:+.1f}%")
        with col3:
            questions_taught = len(st.session_state.questions_worked_on)
            st.metric("Questions Taught", questions_taught)

        # Improvement message
        st.markdown("---")
        if improvement['learned']:
            st.success(f"""
            ### 🎉 Excellent Teaching!

            Your AI student improved by **{improvement['improvement']:.1f} percentage points**!
            You worked on **{questions_taught}** question(s) during this session.
            """)
        elif improvement['improvement'] > 0:
            st.info(f"""
            ### 📈 Good Progress

            Your AI student improved by **{improvement['improvement']:.1f} percentage points**.
            Consider spending more time on difficult concepts in future sessions.
            """)
        else:
            st.warning(f"""
            ### 📚 Room for Improvement

            The AI student's score changed by **{improvement['improvement']:.1f} points**.
            Try focusing on clearer explanations or working through more examples.
            """)

        # Per-question learning summaries
        if st.session_state.question_learning_summaries:
            st.markdown("---")
            st.markdown("### 📚 What the AI Student Learned (Per Question)")
            for idx, summary in st.session_state.question_learning_summaries.items():
                q_data = st.session_state.pre_test_answers[idx]
                q_num = q_data.get('question_number', idx + 1)
                with st.expander(f"Question {q_num}: {q_data.get('question', '')[:80]}...", expanded=True):
                    st.markdown(summary)

        # Detailed comparison
        st.markdown("---")
        render_test_comparison()

    # New session button
    st.markdown("---")
    if st.button("🔄 Start New Session", type="primary", use_container_width=True):
        reset_session()
        st.rerun()


def render_test_comparison():
    """Render side-by-side comparison of pre and post test results."""
    st.markdown("### Detailed Results")

    tab1, tab2 = st.tabs(["📋 Pre-Test", "📋 Post-Test"])

    with tab1:
        if st.session_state.pre_test_answers:
            for qa in st.session_state.pre_test_answers:
                render_test_result_item(qa, "pre")

    with tab2:
        if st.session_state.post_test_answers:
            for qa in st.session_state.post_test_answers:
                render_test_result_item(qa, "post")


def render_test_result_item(qa: Dict, test_type: str):
    """Render a single test result item."""
    q_num = qa.get('question_number', 0)
    is_correct = qa.get('is_correct', False)
    status_icon = "✅" if is_correct else "❌"

    # Check if this question was worked on
    was_worked_on = any(
        st.session_state.pre_test_answers[idx].get('question_number') == q_num
        for idx in st.session_state.questions_worked_on
    ) if st.session_state.pre_test_answers else False

    taught_badge = " 📝" if was_worked_on else ""

    with st.expander(f"{status_icon} Question {q_num}{taught_badge}"):
        st.markdown(f"**{qa.get('question', '')}**")

        col1, col2 = st.columns(2)
        with col1:
            st.markdown(f"**Selected:** {qa.get('selected_answer', 'N/A')}")
        with col2:
            st.markdown(f"**Correct:** {qa.get('correct_answer', 'N/A')}")

        if qa.get('reasoning'):
            st.markdown(f"*Reasoning: {qa['reasoning']}*")


# ============================================================================
# MAIN APPLICATION
# ============================================================================

def main():
    """Main Streamlit application."""
    # Check password before showing anything
    if not check_password():
        return

    initialize_session_state()

    # Render sidebar
    render_sidebar()

    # Render main content based on session phase
    if not st.session_state.session_started:
        render_welcome_screen()
    elif st.session_state.session_phase == "pre_test_review":
        render_pre_test_review()
    elif st.session_state.session_phase == "teaching":
        render_teaching_interface()
    elif st.session_state.session_phase == "results":
        render_results()
    else:
        st.error(f"Unknown session phase: {st.session_state.session_phase}")


if __name__ == "__main__":
    main()

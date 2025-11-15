"""Assessment module for generating and evaluating pre/post tests for AI tutee.

Uses multiple choice questions (MCQ) that can be programmatically graded.
"""

from typing import Dict, List, Tuple
import os
import json
from openai import OpenAI


# Multiple Choice Assessment Questions for each scenario
MCQ_ASSESSMENT = {
    "data_types": [
        {
            "question": "A dataset contains a column 'ProductID' with values like 1001, 1002, 1003. What type of data is this?",
            "options": {
                "A": "Continuous numerical data",
                "B": "Discrete numerical data for calculations",
                "C": "Categorical identifier (nominal)",
                "D": "Ordinal data"
            },
            "correct_answer": "C",
            "explanation": "ProductID is a categorical identifier (nominal data), not quantitative. Even though it uses numbers, it represents categories and should not be used in calculations."
        },
        {
            "question": "Survey responses range from 'Strongly Disagree' (1) to 'Strongly Agree' (5). What is the MOST important consideration when visualizing this data?",
            "options": {
                "A": "It's continuous data, so use a line chart",
                "B": "It's ordinal data with meaningful order but unequal intervals",
                "C": "It's nominal categorical data with no order",
                "D": "It's discrete numerical data suitable for any calculation"
            },
            "correct_answer": "B",
            "explanation": "Likert scale data is ordinal - it has a meaningful order, but the intervals between values aren't necessarily equal, so treat it differently than continuous numerical data."
        },
        {
            "question": "Which of the following is an example of continuous numerical data?",
            "options": {
                "A": "Number of employees in a company (e.g., 50, 51, 52)",
                "B": "Temperature readings (e.g., 72.3°F, 72.5°F, 72.7°F)",
                "C": "T-shirt sizes (Small, Medium, Large)",
                "D": "Customer satisfaction rating (1-5 stars)"
            },
            "correct_answer": "B",
            "explanation": "Temperature is continuous because it can take any value within a range. Employee count is discrete (can't have 50.5 employees), and the others are categorical."
        },
        {
            "question": "You have a 'signup_date' column with values like '2024-01-15', '2024-02-20'. What type of data is this?",
            "options": {
                "A": "Nominal categorical",
                "B": "Ordinal categorical",
                "C": "Temporal (time-based) data",
                "D": "Continuous numerical"
            },
            "correct_answer": "C",
            "explanation": "Dates are temporal data - they have chronological order and are often used to show trends over time."
        },
        {
            "question": "A dataset has department codes: 101=Sales, 102=Marketing, 103=Engineering. How should you treat these codes?",
            "options": {
                "A": "As continuous numbers for mathematical operations",
                "B": "As nominal categorical labels, not for calculations",
                "C": "As ordinal data showing department hierarchy",
                "D": "As discrete numerical data for averaging"
            },
            "correct_answer": "B",
            "explanation": "Department codes are nominal categorical identifiers. The numbers are just labels and shouldn't be used in calculations (averaging departments makes no sense)."
        }
    ],
    "type_to_chart": [
        {
            "question": "You need to compare quarterly revenue across 5 product categories. Which chart is MOST appropriate?",
            "options": {
                "A": "Line chart",
                "B": "Scatter plot",
                "C": "Bar chart or column chart",
                "D": "Pie chart"
            },
            "correct_answer": "C",
            "explanation": "Bar/column charts are ideal for comparing numerical values across discrete categories. Each category gets its own bar, making comparison easy."
        },
        {
            "question": "When is a line chart preferred over a bar chart?",
            "options": {
                "A": "When comparing discrete categories like product types",
                "B": "When showing trends over time or continuous data",
                "C": "When showing composition of a whole",
                "D": "When displaying the relationship between two numerical variables"
            },
            "correct_answer": "B",
            "explanation": "Line charts are best for temporal data or continuous data where the connection between points is meaningful, showing trends and patterns."
        },
        {
            "question": "You have two numerical variables: employee age and salary. Which chart type would best show their relationship?",
            "options": {
                "A": "Pie chart",
                "B": "Bar chart",
                "C": "Line chart",
                "D": "Scatter plot"
            },
            "correct_answer": "D",
            "explanation": "Scatter plots are designed to show relationships between two numerical variables and can reveal correlations or patterns."
        },
        {
            "question": "A pie chart is most appropriate when you want to:",
            "options": {
                "A": "Show trends over time",
                "B": "Compare many categories (10+)",
                "C": "Display parts of a whole (composition)",
                "D": "Show correlation between variables"
            },
            "correct_answer": "C",
            "explanation": "Pie charts show composition - how parts make up a whole. They work best with few categories (3-7) to show proportions."
        },
        {
            "question": "You have monthly sales data for 12 months. Which chart would be LEAST appropriate?",
            "options": {
                "A": "Line chart showing the trend",
                "B": "Bar chart showing monthly values",
                "C": "Pie chart with 12 slices for each month",
                "D": "Area chart showing cumulative sales"
            },
            "correct_answer": "C",
            "explanation": "A pie chart is least appropriate because months don't represent parts of a whole - they're sequential time periods better shown with line or bar charts."
        }
    ],
    "chart_to_task": [
        {
            "question": "Your analytical task is to 'identify trends in website traffic over the past year'. Which chart type best matches this task?",
            "options": {
                "A": "Bar chart",
                "B": "Pie chart",
                "C": "Line chart",
                "D": "Scatter plot"
            },
            "correct_answer": "C",
            "explanation": "Line charts are ideal for trend analysis over time. They clearly show how values change and make patterns like growth or seasonality visible."
        },
        {
            "question": "You need to 'compare market share among 5 competitors'. Which chart best supports this task?",
            "options": {
                "A": "Line chart",
                "B": "Scatter plot",
                "C": "Pie chart or stacked bar chart",
                "D": "Histogram"
            },
            "correct_answer": "C",
            "explanation": "Market share is about composition (parts of a whole). Pie charts or 100% stacked bar charts effectively show how the total market is divided."
        },
        {
            "question": "The task is to 'understand the distribution of test scores in a class'. Which chart is most appropriate?",
            "options": {
                "A": "Pie chart",
                "B": "Line chart",
                "C": "Histogram or box plot",
                "D": "Scatter plot"
            },
            "correct_answer": "C",
            "explanation": "Histograms show distributions of continuous data by grouping values into bins. Box plots also show distribution with quartiles and outliers."
        },
        {
            "question": "Your task is to 'find the correlation between advertising spend and sales revenue'. Best visualization?",
            "options": {
                "A": "Two separate pie charts",
                "B": "Scatter plot with trendline",
                "C": "Stacked bar chart",
                "D": "Multiple line charts"
            },
            "correct_answer": "B",
            "explanation": "Scatter plots are designed to show relationships between two numerical variables. A trendline can confirm correlation strength."
        },
        {
            "question": "You need to 'show how budget is allocated across 8 departments'. Which task is this, and which chart fits best?",
            "options": {
                "A": "Trend analysis - use line chart",
                "B": "Comparison - use bar chart",
                "C": "Correlation - use scatter plot",
                "D": "Distribution - use histogram"
            },
            "correct_answer": "B",
            "explanation": "Budget allocation across departments is a comparison task. Bar charts excel at comparing values across multiple categories."
        }
    ],
    "data_preparation": [
        {
            "question": "Your date column has mixed formats: '01/15/2024', '2024-02-20', '03-MAR-2024'. What should you do FIRST?",
            "options": {
                "A": "Delete all rows with inconsistent formats",
                "B": "Standardize all dates to a single format",
                "C": "Use them as-is; visualization tools will handle it",
                "D": "Convert them all to categorical data"
            },
            "correct_answer": "B",
            "explanation": "Standardizing date formats is critical for proper sorting and time-based analysis. Inconsistent formats will cause errors in temporal visualizations."
        },
        {
            "question": "You have a revenue column with 15% missing values. Which approach is LEAST appropriate?",
            "options": {
                "A": "Remove rows with missing revenue if the dataset is large enough",
                "B": "Impute with median revenue if values are missing at random",
                "C": "Replace all missing values with zero",
                "D": "Mark missing values as a separate category if missingness is meaningful"
            },
            "correct_answer": "C",
            "explanation": "Replacing missing values with zero is dangerous because it assumes zero revenue, which may not be true. Zero is a meaningful value, not 'missing'."
        },
        {
            "question": "Your data has one row per transaction (1000 rows). You want a bar chart of monthly sales. What data preparation is needed?",
            "options": {
                "A": "No preparation needed; use raw transaction data",
                "B": "Aggregate transactions by month and sum sales",
                "C": "Filter to show only the first transaction per month",
                "D": "Convert all dates to categorical months"
            },
            "correct_answer": "B",
            "explanation": "You need to aggregate (group) transaction-level data by month and sum the sales to get monthly totals suitable for visualization."
        },
        {
            "question": "You notice extreme outliers in your salary data (e.g., CEO salary is 50x the median). Before visualizing, you should:",
            "options": {
                "A": "Always remove all outliers automatically",
                "B": "Investigate whether outliers are errors or legitimate extreme values",
                "C": "Change all outliers to the median value",
                "D": "Ignore them; they won't affect the visualization"
            },
            "correct_answer": "B",
            "explanation": "Outliers could be data errors OR legitimate extreme values (like CEO salary). Investigate first - don't automatically remove or modify without understanding why they exist."
        },
        {
            "question": "Your dataset has a 'price' column stored as text: '$1,234.56'. Before creating a histogram, you need to:",
            "options": {
                "A": "Use it as-is; it's already numeric",
                "B": "Convert to categorical data",
                "C": "Remove '$' and ',' symbols, then convert to numeric type",
                "D": "Delete the column and recreate it"
            },
            "correct_answer": "C",
            "explanation": "Text-formatted numbers must be cleaned (remove currency symbols, commas) and type-cast to numeric for mathematical operations and proper visualization."
        }
    ]
}


def get_assessment_questions(scenario_name: str) -> List[Dict]:
    """Get MCQ assessment questions for a specific scenario."""
    return MCQ_ASSESSMENT.get(scenario_name, [])


def format_mcq_prompt(questions: List[Dict]) -> str:
    """Format MCQ questions into a prompt for the LLM."""
    prompt_parts = [
        "Please answer the following multiple choice questions. ",
        "Respond ONLY with valid JSON in this exact format:",
        '{"answers": [{"question_number": 1, "selected_answer": "A", "reasoning": "brief explanation"}, ...]}',
        "\n\nQuestions:\n"
    ]

    for i, q in enumerate(questions, 1):
        prompt_parts.append(f"\n{i}. {q['question']}\n")
        for option_key, option_text in sorted(q['options'].items()):
            prompt_parts.append(f"   {option_key}) {option_text}\n")

    prompt_parts.append("\nRemember: Respond with ONLY the JSON object, no additional text.")
    return "".join(prompt_parts)


def parse_llm_response(response_text: str) -> Dict:
    """Parse LLM response, handling various JSON formats."""
    # Try to extract JSON from response
    response_text = response_text.strip()

    # Remove markdown code blocks if present
    if response_text.startswith("```"):
        lines = response_text.split("\n")
        response_text = "\n".join(lines[1:-1]) if len(lines) > 2 else response_text
        response_text = response_text.replace("```json", "").replace("```", "").strip()

    try:
        return json.loads(response_text)
    except json.JSONDecodeError as e:
        # Try to find JSON object in the response
        start_idx = response_text.find("{")
        end_idx = response_text.rfind("}") + 1
        if start_idx != -1 and end_idx > start_idx:
            try:
                return json.loads(response_text[start_idx:end_idx])
            except json.JSONDecodeError:
                raise ValueError(f"Could not parse LLM response as JSON: {e}")
        raise ValueError(f"Could not find JSON in LLM response: {e}")


def grade_assessment(questions: List[Dict], llm_answers: Dict) -> Tuple[List[Dict], float]:
    """
    Grade the assessment programmatically.

    Args:
        questions: List of question dictionaries with correct answers
        llm_answers: Parsed JSON response from LLM with selected answers

    Returns:
        Tuple of (detailed_results, score_percentage)
    """
    if "answers" not in llm_answers:
        raise ValueError("LLM response missing 'answers' key")

    answers_list = llm_answers["answers"]
    results = []
    correct_count = 0

    for i, question in enumerate(questions):
        question_num = i + 1

        # Find the answer for this question
        llm_answer = next(
            (a for a in answers_list if a.get("question_number") == question_num),
            None
        )

        if llm_answer is None:
            # Question not answered
            results.append({
                "question_number": question_num,
                "question": question["question"],
                "correct_answer": question["correct_answer"],
                "selected_answer": "NOT ANSWERED",
                "is_correct": False,
                "explanation": question["explanation"],
                "reasoning": "No answer provided"
            })
            continue

        selected = llm_answer.get("selected_answer", "").upper().strip()
        correct = question["correct_answer"].upper().strip()
        is_correct = (selected == correct)

        if is_correct:
            correct_count += 1

        results.append({
            "question_number": question_num,
            "question": question["question"],
            "options": question["options"],
            "correct_answer": correct,
            "selected_answer": selected,
            "is_correct": is_correct,
            "explanation": question["explanation"],
            "reasoning": llm_answer.get("reasoning", "")
        })

    score_percentage = (correct_count / len(questions) * 100) if questions else 0

    return results, score_percentage


def administer_test(
    scenario_name: str,
    student_messages: List[Dict[str, str]],
    system_prompt: str,
    model: str = "gpt-4o-mini",
    temperature: float = 0.7
) -> Tuple[List[Dict], float]:
    """
    Administer an MCQ test to the AI student.

    Args:
        scenario_name: Name of the scenario
        student_messages: Conversation history (not used for pre-test, included for consistency)
        system_prompt: The system prompt defining the AI student
        model: OpenAI model to use
        temperature: Sampling temperature

    Returns:
        Tuple of (detailed_results, score_percentage)
    """
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise ValueError("OPENAI_API_KEY is not set")

    client = OpenAI(api_key=api_key)
    questions = get_assessment_questions(scenario_name)

    if not questions:
        return [], 0.0

    # Create test prompt
    mcq_prompt = format_mcq_prompt(questions)

    test_messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": mcq_prompt}
    ]

    try:
        response = client.chat.completions.create(
            model=model,
            temperature=temperature,
            messages=test_messages,
        )
        response_text = response.choices[0].message.content.strip()

        # Parse and grade
        llm_answers = parse_llm_response(response_text)
        results, score = grade_assessment(questions, llm_answers)

        return results, score

    except Exception as e:
        raise ValueError(f"Error administering test: {e}")


def administer_enhanced_test(
    scenario_name: str,
    conversation_history: List[Dict[str, str]],
    system_prompt: str,
    model: str = "gpt-4o-mini",
    temperature: float = 0.7
) -> Tuple[List[Dict], float]:
    """
    Administer a post-test that includes recent conversation context.

    Args:
        scenario_name: Name of the scenario
        conversation_history: Full conversation history for context
        system_prompt: The system prompt defining the AI student
        model: OpenAI model to use
        temperature: Sampling temperature

    Returns:
        Tuple of (detailed_results, score_percentage)
    """
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise ValueError("OPENAI_API_KEY is not set")

    client = OpenAI(api_key=api_key)
    questions = get_assessment_questions(scenario_name)

    if not questions:
        return [], 0.0

    # Create a MODIFIED system prompt for post-test that emphasizes learning
    # Replace misconception instructions with learning instructions
    post_test_system_prompt = system_prompt.replace(
        "You genuinely believe the misconceptions in {{MISCONCEPTIONS}}",
        "You have been learning from the teacher and should UPDATE your beliefs based on what you were taught"
    ).replace(
        "These are not occasional mistakes—they are your actual understanding",
        "Your understanding should now reflect the corrections and explanations the teacher provided"
    ).replace(
        "When taking assessments, answer based on these beliefs (which will lead to wrong answers)",
        "When taking assessments, apply what you learned from the teacher during the session"
    ).replace(
        "At **beginner** level, you should get MOST questions wrong because your understanding is fundamentally flawed",
        "At **beginner** level, you should show improvement on topics the teacher covered with you"
    ).replace(
        "Do NOT use outside knowledge or reasoning—stay in character as someone who genuinely holds these misconceptions",
        "Apply the specific lessons and corrections the teacher taught you during this session"
    )

    # Create test prompt with strong learning emphasis
    mcq_prompt = format_mcq_prompt(questions)
    context_intro = (
        "IMPORTANT: This is a POST-TEST after our teaching session.\n\n"
        "You should answer these questions based ONLY on what the teacher TAUGHT you during our conversation. "
        "Apply EXACTLY what the teacher explained to you - use their definitions, examples, and corrections. "
        "If the teacher told you that something is categorical, answer as if it's categorical. "
        "If the teacher told you that something is numeric, answer as if it's numeric.\n\n"
        "Your answers should reflect the specific lessons from this teaching session, even if they differ from general knowledge. "
        "Answer based on what THIS teacher taught you in THIS conversation.\n\n"
    )
    full_prompt = context_intro + mcq_prompt

    # Include ALL conversation for maximum context (not just last 6)
    context_messages = [{"role": "system", "content": post_test_system_prompt}]
    recent_history = [msg for msg in conversation_history if msg["role"] != "system"]
    context_messages.extend(recent_history)
    context_messages.append({"role": "user", "content": full_prompt})

    try:
        response = client.chat.completions.create(
            model=model,
            temperature=temperature,
            messages=context_messages,
            max_tokens=1000
        )
        response_text = response.choices[0].message.content.strip()

        # Parse and grade
        llm_answers = parse_llm_response(response_text)
        results, score = grade_assessment(questions, llm_answers)

        return results, score

    except Exception as e:
        raise ValueError(f"Error administering post-test: {e}")


def calculate_improvement(pre_test_score: float, post_test_score: float) -> Dict[str, any]:
    """Calculate improvement metrics between pre and post test."""
    improvement = post_test_score - pre_test_score
    improvement_percent = improvement  # Already in percentage points

    return {
        "pre_test_score": round(pre_test_score, 1),
        "post_test_score": round(post_test_score, 1),
        "improvement": round(improvement, 1),
        "improvement_percent": round(improvement_percent, 1),
        "learned": improvement > 10,  # Consider significant if improved more than 10 percentage points
    }

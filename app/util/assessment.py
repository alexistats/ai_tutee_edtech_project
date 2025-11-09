"""Assessment module for generating and evaluating pre/post tests for AI tutee."""

from typing import Dict, List, Tuple
import os
from openai import OpenAI


# Assessment questions for each scenario
ASSESSMENT_QUESTIONS = {
    "data_types": [
        {
            "question": "You have a column called 'customer_id' with values 1001, 1002, 1003. Should you use this for quantitative visualization? Why or why not?",
            "ideal_answer": "No, customer_id is an identifier, not a quantitative value. Even though it's numeric, it represents categories (individual customers) and should not be used for calculations or numeric visualizations.",
            "key_concepts": ["identifier recognition", "categorical vs numerical"]
        },
        {
            "question": "A survey has responses: 'Strongly Disagree', 'Disagree', 'Neutral', 'Agree', 'Strongly Agree'. What type of data is this, and what's important to remember when visualizing it?",
            "ideal_answer": "This is ordinal categorical data. It has a natural order but the intervals between values aren't necessarily equal. When visualizing, preserve the order but be careful about treating it as continuous numeric data.",
            "key_concepts": ["ordinal data", "preserve order"]
        },
        {
            "question": "What's the difference between discrete and continuous numerical data? Give an example of each.",
            "ideal_answer": "Discrete data has distinct, separate values (like number of purchases: 1, 2, 3), while continuous data can take any value within a range (like temperature: 98.6, 98.7, 98.65). Discrete often counts things, continuous measures things.",
            "key_concepts": ["discrete vs continuous", "measurement types"]
        }
    ],
    "type_to_chart": [
        {
            "question": "You have sales data with one categorical variable (product type) and one numerical variable (revenue). What chart would you recommend?",
            "ideal_answer": "A bar chart or column chart would be ideal. Bar charts are perfect for comparing numerical values across categories, making it easy to see which product types generate the most revenue.",
            "key_concepts": ["categorical to bar", "comparison visualization"]
        },
        {
            "question": "When would you use a line chart instead of a bar chart?",
            "ideal_answer": "Use a line chart when showing data over time or continuous data where the connection between points is meaningful. Bar charts are better for comparing discrete categories. Line charts show trends and patterns in sequential data.",
            "key_concepts": ["temporal data", "line vs bar"]
        },
        {
            "question": "You need to show the relationship between two numerical variables (like height and weight). What chart type would you choose?",
            "ideal_answer": "A scatter plot would be most appropriate. Scatter plots show the relationship between two numerical variables and can reveal correlations or patterns in the data.",
            "key_concepts": ["scatter plot", "correlation visualization"]
        }
    ],
    "chart_to_task": [
        {
            "question": "Your task is to show how website traffic has changed over the past year. What chart type matches this analytical goal?",
            "ideal_answer": "A line chart would be best for showing trends over time. It clearly displays how values change across time periods and makes it easy to spot patterns like seasonal variations or growth trends.",
            "key_concepts": ["trend analysis", "time series"]
        },
        {
            "question": "You want to compare market share between five competing companies. What chart would you use?",
            "ideal_answer": "A pie chart or stacked bar chart showing percentages would work well for displaying market share composition. Alternatively, a simple bar chart could compare the absolute values. The choice depends on whether you want to emphasize the parts of a whole or direct comparison.",
            "key_concepts": ["composition", "comparison"]
        },
        {
            "question": "What type of chart would you use to show the distribution of test scores in a class?",
            "ideal_answer": "A histogram would be ideal for showing the distribution of continuous data like test scores. It would show how many students fall into different score ranges and reveal the overall shape of the distribution.",
            "key_concepts": ["distribution", "histogram"]
        }
    ],
    "data_preparation": [
        {
            "question": "You notice that a date column has values in multiple formats (MM/DD/YYYY and DD-MM-YYYY). What should you do before visualizing time-based trends?",
            "ideal_answer": "Standardize all dates to a single format. Inconsistent date formats will cause errors in sorting and plotting. Convert everything to a standard format and ensure the data type is set to datetime.",
            "key_concepts": ["data standardization", "date formatting"]
        },
        {
            "question": "Your dataset has several rows with missing values in the 'revenue' column. What are your options for handling this?",
            "ideal_answer": "Options include: 1) Remove rows with missing values if they're few, 2) Impute with mean/median if appropriate, 3) Use a separate category for 'missing' if it's meaningful, or 4) Use visualization techniques that handle missing data. The choice depends on why data is missing and the analysis goal.",
            "key_concepts": ["missing data", "data cleaning"]
        },
        {
            "question": "You want to create a bar chart showing sales by month, but your data has one row per transaction. What data preparation step is needed?",
            "ideal_answer": "You need to aggregate the data by grouping transactions by month and summing (or averaging) the sales values. This transforms transaction-level data into monthly summaries suitable for visualization.",
            "key_concepts": ["aggregation", "data transformation"]
        }
    ]
}


def get_assessment_questions(scenario_name: str) -> List[Dict]:
    """Get assessment questions for a specific scenario."""
    return ASSESSMENT_QUESTIONS.get(scenario_name, [])


def administer_test(
    scenario_name: str,
    student_messages: List[Dict[str, str]],
    system_prompt: str,
    model: str = "gpt-4o-mini",
    temperature: float = 0.7
) -> Tuple[List[Dict], float]:
    """
    Administer a test to the AI student.

    Args:
        scenario_name: Name of the scenario
        student_messages: Conversation history to provide context
        system_prompt: The system prompt defining the AI student
        model: OpenAI model to use
        temperature: Sampling temperature

    Returns:
        Tuple of (answers, score) where answers is a list of Q&A dicts and score is 0-100
    """
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise ValueError("OPENAI_API_KEY is not set")

    client = OpenAI(api_key=api_key)
    questions = get_assessment_questions(scenario_name)

    if not questions:
        return [], 0.0

    answers = []
    total_score = 0

    for q in questions:
        # Create a test context
        test_messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": f"Please answer this question concisely, explaining your reasoning:\n\n{q['question']}"}
        ]

        # Get AI student's answer
        try:
            response = client.chat.completions.create(
                model=model,
                temperature=temperature,
                messages=test_messages,
            )
            answer = response.choices[0].message.content.strip()
        except Exception as e:
            answer = f"Error getting response: {e}"

        # Simple scoring: check if key concepts appear in the answer
        key_concepts = q.get("key_concepts", [])
        concepts_found = sum(1 for concept in key_concepts if concept.lower() in answer.lower())
        question_score = (concepts_found / len(key_concepts) * 100) if key_concepts else 50

        total_score += question_score

        answers.append({
            "question": q["question"],
            "answer": answer,
            "ideal_answer": q["ideal_answer"],
            "key_concepts": key_concepts,
            "score": question_score
        })

    # Average score across all questions
    average_score = total_score / len(questions) if questions else 0

    return answers, average_score


def administer_enhanced_test(
    scenario_name: str,
    conversation_history: List[Dict[str, str]],
    system_prompt: str,
    model: str = "gpt-4o-mini",
    temperature: float = 0.7
) -> Tuple[List[Dict], float]:
    """
    Administer a test that considers the conversation history for post-test.

    Args:
        scenario_name: Name of the scenario
        conversation_history: Full conversation history (for post-test context)
        system_prompt: The system prompt defining the AI student
        model: OpenAI model to use
        temperature: Sampling temperature

    Returns:
        Tuple of (answers, score) where answers is a list of Q&A dicts and score is 0-100
    """
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise ValueError("OPENAI_API_KEY is not set")

    client = OpenAI(api_key=api_key)
    questions = get_assessment_questions(scenario_name)

    if not questions:
        return [], 0.0

    answers = []
    total_score = 0

    # For post-test, include recent conversation for context
    context_messages = [{"role": "system", "content": system_prompt}]

    # Add the last few exchanges for context (avoid token limits)
    recent_history = [msg for msg in conversation_history if msg["role"] != "system"][-6:]
    context_messages.extend(recent_history)

    for q in questions:
        # Add test question
        test_messages = context_messages + [
            {"role": "user", "content": f"Now, please answer this assessment question, applying what we've discussed:\n\n{q['question']}"}
        ]

        # Get AI student's answer
        try:
            response = client.chat.completions.create(
                model=model,
                temperature=temperature,
                messages=test_messages,
                max_tokens=300
            )
            answer = response.choices[0].message.content.strip()
        except Exception as e:
            answer = f"Error getting response: {e}"

        # Enhanced scoring: check key concepts and compare to ideal answer
        key_concepts = q.get("key_concepts", [])
        concepts_found = sum(1 for concept in key_concepts if concept.lower() in answer.lower())

        # Additional points for mentioning terms from ideal answer
        ideal_terms = [term.lower() for term in q["ideal_answer"].split() if len(term) > 4]
        ideal_matches = sum(1 for term in ideal_terms if term in answer.lower())

        # Weighted scoring
        concept_score = (concepts_found / len(key_concepts) * 60) if key_concepts else 30
        ideal_score = min(ideal_matches * 5, 40)  # Up to 40 points for matching ideal answer terms
        question_score = min(concept_score + ideal_score, 100)

        total_score += question_score

        answers.append({
            "question": q["question"],
            "answer": answer,
            "ideal_answer": q["ideal_answer"],
            "key_concepts": key_concepts,
            "concepts_found": concepts_found,
            "score": question_score
        })

    # Average score across all questions
    average_score = total_score / len(questions) if questions else 0

    return answers, average_score


def calculate_improvement(pre_test_score: float, post_test_score: float) -> Dict[str, any]:
    """Calculate improvement metrics between pre and post test."""
    improvement = post_test_score - pre_test_score
    improvement_percent = (improvement / 100) * 100 if pre_test_score > 0 else 0

    return {
        "pre_test_score": round(pre_test_score, 1),
        "post_test_score": round(post_test_score, 1),
        "improvement": round(improvement, 1),
        "improvement_percent": round(improvement_percent, 1),
        "learned": improvement > 5,  # Consider significant if improved more than 5 points
    }

"""
MCQ Test Grader Module

Handles loading, administering, and grading multiple choice question tests
for the AI tutee. Provides programmatic evaluation without LLM grading.
"""

import json
from pathlib import Path
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass


@dataclass
class MCQQuestion:
    """Represents a single multiple choice question."""
    question_id: str
    question_text: str
    options: List[Dict[str, str]]
    correct_answer: str
    explanation: Optional[str] = None
    subskill: Optional[str] = None


@dataclass
class MCQTest:
    """Represents a complete MCQ test."""
    test_id: str
    scenario: str
    test_type: str  # 'pre_test' or 'post_test'
    description: str
    questions: List[MCQQuestion]


@dataclass
class TestResult:
    """Represents the results of a test."""
    test_id: str
    scenario: str
    test_type: str
    total_questions: int
    correct_answers: int
    score_percentage: float
    question_results: List[Dict]


class MCQGrader:
    """Handles MCQ test loading, administration, and grading."""

    def __init__(self, tests_dir: str = "app/tests_mcq"):
        """Initialize the grader with the tests directory."""
        self.tests_dir = Path(tests_dir)

    def load_test(self, scenario: str, test_type: str) -> MCQTest:
        """
        Load an MCQ test from a JSON file.

        Args:
            scenario: The scenario name (e.g., 'data_types')
            test_type: Either 'pre_test' or 'post_test'

        Returns:
            MCQTest object with loaded questions
        """
        test_file = self.tests_dir / f"{scenario}_{test_type}.json"

        if not test_file.exists():
            raise FileNotFoundError(f"Test file not found: {test_file}")

        with open(test_file, 'r') as f:
            data = json.load(f)

        questions = [
            MCQQuestion(
                question_id=q['question_id'],
                question_text=q['question_text'],
                options=q['options'],
                correct_answer=q['correct_answer'],
                explanation=q.get('explanation'),
                subskill=q.get('subskill')
            )
            for q in data['questions']
        ]

        return MCQTest(
            test_id=data['test_id'],
            scenario=data['scenario'],
            test_type=data['test_type'],
            description=data['description'],
            questions=questions
        )

    def format_question_for_display(self, question: MCQQuestion) -> str:
        """
        Format a question for display to the test taker.

        Args:
            question: The MCQQuestion to format

        Returns:
            Formatted question string
        """
        lines = [
            f"\n{question.question_text}\n"
        ]

        for option in question.options:
            lines.append(f"{option['option_id']}. {option['text']}")

        return "\n".join(lines)

    def grade_answer(self, question: MCQQuestion, student_answer: str) -> Tuple[bool, str]:
        """
        Grade a single answer.

        Args:
            question: The MCQQuestion being answered
            student_answer: The student's answer (option_id)

        Returns:
            Tuple of (is_correct, feedback)
        """
        # Normalize the answer (uppercase, strip whitespace)
        student_answer = student_answer.strip().upper()
        correct_answer = question.correct_answer.strip().upper()

        is_correct = student_answer == correct_answer

        if is_correct:
            feedback = "Correct!"
            if question.explanation:
                feedback += f" {question.explanation}"
        else:
            feedback = f"Incorrect. The correct answer is {correct_answer}."
            if question.explanation:
                feedback += f" {question.explanation}"

        return is_correct, feedback

    def grade_test(self, test: MCQTest, student_answers: Dict[str, str]) -> TestResult:
        """
        Grade an entire test.

        Args:
            test: The MCQTest being graded
            student_answers: Dictionary mapping question_id to student's answer

        Returns:
            TestResult with scores and detailed feedback
        """
        question_results = []
        correct_count = 0

        for question in test.questions:
            student_answer = student_answers.get(question.question_id, "")
            is_correct, feedback = self.grade_answer(question, student_answer)

            if is_correct:
                correct_count += 1

            question_results.append({
                'question_id': question.question_id,
                'question_text': question.question_text,
                'student_answer': student_answer,
                'correct_answer': question.correct_answer,
                'is_correct': is_correct,
                'feedback': feedback,
                'subskill': question.subskill
            })

        total_questions = len(test.questions)
        score_percentage = (correct_count / total_questions * 100) if total_questions > 0 else 0

        return TestResult(
            test_id=test.test_id,
            scenario=test.scenario,
            test_type=test.test_type,
            total_questions=total_questions,
            correct_answers=correct_count,
            score_percentage=score_percentage,
            question_results=question_results
        )

    def get_test_summary(self, result: TestResult) -> str:
        """
        Generate a human-readable summary of test results.

        Args:
            result: The TestResult to summarize

        Returns:
            Formatted summary string
        """
        summary = [
            f"\n{'='*60}",
            f"Test Results: {result.scenario} - {result.test_type.replace('_', ' ').title()}",
            f"{'='*60}",
            f"Score: {result.correct_answers}/{result.total_questions} ({result.score_percentage:.1f}%)",
            f"{'='*60}\n"
        ]

        for i, q_result in enumerate(result.question_results, 1):
            status = "✓" if q_result['is_correct'] else "✗"
            summary.append(f"{i}. {status} {q_result['question_text'][:60]}...")
            summary.append(f"   Your answer: {q_result['student_answer']} | Correct: {q_result['correct_answer']}")
            if not q_result['is_correct']:
                summary.append(f"   {q_result['feedback']}")
            summary.append("")

        return "\n".join(summary)

    def export_results_to_json(self, result: TestResult, output_path: str) -> None:
        """
        Export test results to a JSON file.

        Args:
            result: The TestResult to export
            output_path: Path to save the JSON file
        """
        output_data = {
            'test_id': result.test_id,
            'scenario': result.scenario,
            'test_type': result.test_type,
            'total_questions': result.total_questions,
            'correct_answers': result.correct_answers,
            'score_percentage': result.score_percentage,
            'question_results': result.question_results
        }

        output_file = Path(output_path)
        output_file.parent.mkdir(parents=True, exist_ok=True)

        with open(output_file, 'w') as f:
            json.dump(output_data, f, indent=2)


def extract_answer_from_response(response: str) -> str:
    """
    Extract the answer choice from an LLM response.

    Looks for patterns like:
    - "A" or "A." at the start
    - "The answer is A"
    - "I choose A"

    Args:
        response: The full text response from the student

    Returns:
        The extracted answer (A, B, C, or D) or empty string if not found
    """
    response = response.strip().upper()

    # Pattern 1: Single letter at the start
    if len(response) > 0 and response[0] in ['A', 'B', 'C', 'D']:
        return response[0]

    # Pattern 2: Look for "answer is X" or "choose X" patterns
    patterns = [
        "ANSWER IS ",
        "CHOOSE ",
        "SELECT ",
        "PICK ",
        "MY ANSWER IS ",
        "I CHOOSE ",
        "I SELECT ",
        "I PICK "
    ]

    for pattern in patterns:
        if pattern in response:
            idx = response.index(pattern) + len(pattern)
            if idx < len(response) and response[idx] in ['A', 'B', 'C', 'D']:
                return response[idx]

    # Pattern 3: Look for standalone A, B, C, or D
    words = response.split()
    for word in words:
        clean_word = word.strip('.,!?;:')
        if clean_word in ['A', 'B', 'C', 'D']:
            return clean_word

    return ""

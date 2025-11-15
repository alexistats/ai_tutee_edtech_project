"""
MCQ Test Administrator Module

Handles administering MCQ tests to the AI tutee by presenting questions
and collecting responses through the LLM.
"""

import os
from typing import Dict, List, Optional, Callable
from app.mcq_grader import MCQGrader, MCQTest, extract_answer_from_response


class MCQTestAdministrator:
    """Administers MCQ tests to the AI tutee."""

    def __init__(
        self,
        model: str = "gpt-4.1-mini",
        temperature: float = 0.7,
        call_model_fn: Optional[Callable] = None
    ):
        """
        Initialize the test administrator.

        Args:
            model: Model name to use for the student
            temperature: Sampling temperature
            call_model_fn: Optional custom function for calling the model.
                          If None, will use OpenAI API.
        """
        self.model = model
        self.temperature = temperature
        self.call_model_fn = call_model_fn or self._default_openai_call
        self.grader = MCQGrader()

    def _default_openai_call(self, messages: List[Dict[str, str]]) -> str:
        """Default OpenAI API call implementation."""
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            raise RuntimeError("OPENAI_API_KEY is not set.")

        try:
            from openai import OpenAI

            client = OpenAI(api_key=api_key)
            response = client.chat.completions.create(
                model=self.model,
                temperature=self.temperature,
                messages=messages,
            )
            content = response.choices[0].message.content or ""
            return content.strip()

        except ImportError:
            raise RuntimeError("openai package is not installed. Use pip install openai.")
        except Exception as exc:
            raise RuntimeError(f"OpenAI API call failed: {exc}") from exc

    def create_test_prompt(self, test: MCQTest) -> str:
        """
        Create the initial prompt for the test.

        Args:
            test: The MCQTest to administer

        Returns:
            Formatted prompt string
        """
        prompt = f"""You are taking a multiple choice test on {test.scenario}.

{test.description}

Instructions:
- Read each question carefully
- Choose the best answer from the options provided
- Respond with ONLY the letter of your choice (A, B, C, or D)
- Do not provide explanations unless asked

Answer format: Just type the letter (e.g., "A" or "B")

Are you ready to begin? Respond with "Ready" if you are.
"""
        return prompt

    def administer_test(
        self,
        scenario: str,
        test_type: str,
        student_system_prompt: str = "",
        verbose: bool = True
    ) -> Dict[str, str]:
        """
        Administer a complete MCQ test to the AI tutee.

        Args:
            scenario: The scenario name
            test_type: Either 'pre_test' or 'post_test'
            student_system_prompt: Optional system prompt for the student
            verbose: Whether to print progress

        Returns:
            Dictionary mapping question_id to student's answer
        """
        # Load the test
        test = self.grader.load_test(scenario, test_type)

        if verbose:
            print(f"\n{'='*60}")
            print(f"Administering: {scenario} - {test_type.replace('_', ' ').title()}")
            print(f"{'='*60}\n")

        # Initialize conversation
        messages = []
        student_answers = {}

        # If no custom system prompt, use a simple test-taking one
        if not student_system_prompt:
            student_system_prompt = """You are a student taking a multiple choice test.
Read each question carefully and select the best answer from the options provided.
Respond with ONLY the letter of your choice (A, B, C, or D) without explanation."""

        # Add system message
        messages.append({"role": "system", "content": student_system_prompt})

        # Start the test
        intro_prompt = self.create_test_prompt(test)
        messages.append({"role": "user", "content": intro_prompt})

        # Get ready confirmation
        response_text = self.call_model_fn(messages)
        messages.append({"role": "assistant", "content": response_text})

        if verbose:
            print(f"Student: {response_text}\n")

        # Administer each question
        for i, question in enumerate(test.questions, 1):
            question_text = self.grader.format_question_for_display(question)

            if verbose:
                print(f"Question {i}/{len(test.questions)}:")
                print(question_text)

            # Ask the question
            messages.append({"role": "user", "content": question_text})

            # Get student's answer
            answer_text = self.call_model_fn(messages)
            messages.append({"role": "assistant", "content": answer_text})

            # Extract the answer choice
            answer = extract_answer_from_response(answer_text)

            if verbose:
                print(f"Student response: {answer_text}")
                print(f"Extracted answer: {answer}\n")

            student_answers[question.question_id] = answer

        return student_answers

    def run_test_with_grading(
        self,
        scenario: str,
        test_type: str,
        student_system_prompt: str = "",
        verbose: bool = True,
        save_results: bool = True,
        output_dir: str = "logs/test_results"
    ) -> Dict:
        """
        Run a complete test and return graded results.

        Args:
            scenario: The scenario name
            test_type: Either 'pre_test' or 'post_test'
            student_system_prompt: Optional system prompt for the student
            verbose: Whether to print progress
            save_results: Whether to save results to file
            output_dir: Directory to save results

        Returns:
            Dictionary with test results and metadata
        """
        # Administer the test
        student_answers = self.administer_test(
            scenario, test_type, student_system_prompt, verbose
        )

        # Load test for grading
        test = self.grader.load_test(scenario, test_type)

        # Grade the test
        result = self.grader.grade_test(test, student_answers)

        if verbose:
            # Print summary
            summary = self.grader.get_test_summary(result)
            print(summary)

        # Save results if requested
        if save_results:
            from datetime import datetime
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"{output_dir}/{scenario}_{test_type}_{timestamp}.json"
            self.grader.export_results_to_json(result, filename)

            if verbose:
                print(f"Results saved to: {filename}")

        return {
            'test_result': result,
            'student_answers': student_answers,
            'test': test
        }

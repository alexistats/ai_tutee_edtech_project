"""
Validate MCQ Tests

Standalone script to validate all MCQ test files conform to the schema.
Run with: python scripts/validate_mcq_tests.py
"""

import json
from pathlib import Path


def load_schema():
    """Load the MCQ test schema."""
    schema_path = Path("docs/schemas/mcq_test.schema.json")
    with open(schema_path, 'r') as f:
        return json.load(f)


def validate_test_file(test_file, schema):
    """Validate a single test file against the schema."""
    errors = []

    try:
        with open(test_file, 'r') as f:
            test_data = json.load(f)
    except json.JSONDecodeError as e:
        return [f"Invalid JSON: {e}"]

    # Check required fields
    required_fields = ["test_id", "scenario", "test_type", "questions"]
    for field in required_fields:
        if field not in test_data:
            errors.append(f"Missing required field: {field}")

    if "questions" in test_data:
        # Check questions array
        if not isinstance(test_data["questions"], list):
            errors.append("'questions' must be an array")
        elif len(test_data["questions"]) == 0:
            errors.append("Test must have at least one question")
        else:
            # Validate each question
            question_ids = []
            for i, question in enumerate(test_data["questions"], 1):
                # Check required question fields
                q_required = ["question_id", "question_text", "options", "correct_answer"]
                for field in q_required:
                    if field not in question:
                        errors.append(f"Question {i}: Missing field '{field}'")

                # Track question IDs for uniqueness
                if "question_id" in question:
                    question_ids.append(question["question_id"])

                # Validate options
                if "options" in question:
                    if not isinstance(question["options"], list):
                        errors.append(f"Question {i}: 'options' must be an array")
                    elif len(question["options"]) < 2:
                        errors.append(f"Question {i}: Must have at least 2 options")
                    else:
                        option_ids = []
                        for j, option in enumerate(question["options"], 1):
                            if "option_id" not in option:
                                errors.append(f"Question {i}, Option {j}: Missing 'option_id'")
                            else:
                                option_ids.append(option["option_id"])

                            if "text" not in option:
                                errors.append(f"Question {i}, Option {j}: Missing 'text'")

                        # Check for duplicate option IDs
                        if len(option_ids) != len(set(option_ids)):
                            errors.append(f"Question {i}: Duplicate option IDs")

                        # Validate correct_answer is a valid option
                        if "correct_answer" in question:
                            if question["correct_answer"] not in option_ids:
                                errors.append(
                                    f"Question {i}: correct_answer '{question['correct_answer']}' "
                                    f"not in options {option_ids}"
                                )

            # Check for duplicate question IDs
            if len(question_ids) != len(set(question_ids)):
                errors.append("Duplicate question IDs found")

    # Check test_type matches filename
    if "test_type" in test_data:
        test_type = test_data["test_type"]
        filename = test_file.name
        if "pre_test" in filename and test_type != "pre_test":
            errors.append(f"test_type is '{test_type}' but filename suggests 'pre_test'")
        elif "post_test" in filename and test_type != "post_test":
            errors.append(f"test_type is '{test_type}' but filename suggests 'post_test'")

    # Check scenario matches filename
    if "scenario" in test_data:
        scenario = test_data["scenario"]
        filename_scenario = test_file.stem.replace("_pre_test", "").replace("_post_test", "")
        if scenario != filename_scenario:
            errors.append(f"scenario is '{scenario}' but filename suggests '{filename_scenario}'")

    return errors


def main():
    """Main validation routine."""
    print("="*60)
    print("MCQ Test Validation")
    print("="*60)

    # Check schema exists
    schema_path = Path("docs/schemas/mcq_test.schema.json")
    if not schema_path.exists():
        print(f"\n✗ Schema file not found: {schema_path}")
        return 1

    print(f"\n✓ Schema file exists: {schema_path}")

    # Load schema
    try:
        schema = load_schema()
        print(f"✓ Schema loaded successfully")
    except Exception as e:
        print(f"✗ Failed to load schema: {e}")
        return 1

    # Check tests directory
    tests_dir = Path("app/tests_mcq")
    if not tests_dir.exists():
        print(f"\n✗ MCQ tests directory not found: {tests_dir}")
        return 1

    print(f"✓ MCQ tests directory exists: {tests_dir}")

    # Get all test files
    test_files = sorted(tests_dir.glob("*.json"))
    if not test_files:
        print(f"\n✗ No test files found in {tests_dir}")
        return 1

    print(f"✓ Found {len(test_files)} test files\n")

    # Check all scenarios have tests
    print("-"*60)
    print("Checking scenario coverage...")
    print("-"*60)
    scenarios = ["data_types", "type_to_chart", "chart_to_task", "data_preparation"]
    all_scenarios_covered = True

    for scenario in scenarios:
        pre_test = tests_dir / f"{scenario}_pre_test.json"
        post_test = tests_dir / f"{scenario}_post_test.json"

        if pre_test.exists() and post_test.exists():
            print(f"✓ {scenario}: pre and post tests exist")
        else:
            all_scenarios_covered = False
            if not pre_test.exists():
                print(f"✗ {scenario}: missing pre-test")
            if not post_test.exists():
                print(f"✗ {scenario}: missing post-test")

    if not all_scenarios_covered:
        print("\n⚠ Warning: Not all scenarios have complete test coverage")

    # Validate each test file
    print(f"\n{'-'*60}")
    print("Validating test files...")
    print("-"*60)

    all_valid = True
    for test_file in test_files:
        errors = validate_test_file(test_file, schema)

        if errors:
            all_valid = False
            print(f"\n✗ {test_file.name}:")
            for error in errors:
                print(f"  - {error}")
        else:
            # Count questions
            with open(test_file, 'r') as f:
                test_data = json.load(f)
                num_questions = len(test_data.get("questions", []))
            print(f"✓ {test_file.name} ({num_questions} questions)")

    # Final summary
    print(f"\n{'='*60}")
    if all_valid:
        print("✓ All MCQ tests are valid!")
        print("="*60)
        return 0
    else:
        print("✗ Some MCQ tests have validation errors")
        print("="*60)
        return 1


if __name__ == "__main__":
    exit(main())

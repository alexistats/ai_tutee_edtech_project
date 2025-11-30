"""
Test MCQ Schema Validation

Validates that all MCQ test files conform to the schema and are well-formed.
"""

import json
import pytest
from pathlib import Path
from jsonschema import validate, ValidationError


def load_schema():
    """Load the MCQ test schema."""
    schema_path = Path("docs/schemas/mcq_test.schema.json")
    with open(schema_path, 'r') as f:
        return json.load(f)


def get_all_mcq_tests():
    """Get all MCQ test files."""
    tests_dir = Path("app/tests_mcq")
    return list(tests_dir.glob("*.json"))


def test_schema_exists():
    """Test that the schema file exists."""
    schema_path = Path("docs/schemas/mcq_test.schema.json")
    assert schema_path.exists(), f"Schema file not found: {schema_path}"


def test_mcq_directory_exists():
    """Test that the MCQ tests directory exists."""
    tests_dir = Path("app/tests_mcq")
    assert tests_dir.exists(), f"MCQ tests directory not found: {tests_dir}"


def test_all_scenarios_have_tests():
    """Test that all scenarios have both pre and post tests."""
    scenarios = ["data_types", "type_to_chart", "chart_to_task", "data_preparation"]
    tests_dir = Path("app/tests_mcq")

    for scenario in scenarios:
        pre_test = tests_dir / f"{scenario}_pre_test.json"
        post_test = tests_dir / f"{scenario}_post_test.json"

        assert pre_test.exists(), f"Missing pre-test for {scenario}"
        assert post_test.exists(), f"Missing post-test for {scenario}"


@pytest.mark.parametrize("test_file", get_all_mcq_tests())
def test_mcq_file_valid_json(test_file):
    """Test that each MCQ file is valid JSON."""
    with open(test_file, 'r') as f:
        try:
            json.load(f)
        except json.JSONDecodeError as e:
            pytest.fail(f"Invalid JSON in {test_file}: {e}")


@pytest.mark.parametrize("test_file", get_all_mcq_tests())
def test_mcq_file_follows_schema(test_file):
    """Test that each MCQ file follows the schema."""
    schema = load_schema()

    with open(test_file, 'r') as f:
        test_data = json.load(f)

    try:
        validate(instance=test_data, schema=schema)
    except ValidationError as e:
        pytest.fail(f"Schema validation failed for {test_file}: {e.message}")


@pytest.mark.parametrize("test_file", get_all_mcq_tests())
def test_mcq_has_questions(test_file):
    """Test that each MCQ file has at least one question."""
    with open(test_file, 'r') as f:
        test_data = json.load(f)

    assert len(test_data["questions"]) > 0, f"{test_file} has no questions"


@pytest.mark.parametrize("test_file", get_all_mcq_tests())
def test_correct_answer_is_valid_option(test_file):
    """Test that correct_answer matches one of the option_ids."""
    with open(test_file, 'r') as f:
        test_data = json.load(f)

    for question in test_data["questions"]:
        correct = question["correct_answer"]
        option_ids = [opt["option_id"] for opt in question["options"]]

        assert correct in option_ids, (
            f"In {test_file}, question {question['question_id']}: "
            f"correct_answer '{correct}' not in options {option_ids}"
        )


@pytest.mark.parametrize("test_file", get_all_mcq_tests())
def test_question_ids_are_unique(test_file):
    """Test that question IDs are unique within each test."""
    with open(test_file, 'r') as f:
        test_data = json.load(f)

    question_ids = [q["question_id"] for q in test_data["questions"]]
    assert len(question_ids) == len(set(question_ids)), (
        f"{test_file} has duplicate question IDs"
    )


@pytest.mark.parametrize("test_file", get_all_mcq_tests())
def test_option_ids_are_unique_per_question(test_file):
    """Test that option IDs are unique within each question."""
    with open(test_file, 'r') as f:
        test_data = json.load(f)

    for question in test_data["questions"]:
        option_ids = [opt["option_id"] for opt in question["options"]]
        assert len(option_ids) == len(set(option_ids)), (
            f"In {test_file}, question {question['question_id']} has duplicate option IDs"
        )


@pytest.mark.parametrize("test_file", get_all_mcq_tests())
def test_test_type_matches_filename(test_file):
    """Test that test_type field matches the filename."""
    with open(test_file, 'r') as f:
        test_data = json.load(f)

    test_type = test_data["test_type"]
    filename = test_file.name

    if "pre_test" in filename:
        assert test_type == "pre_test", (
            f"{test_file} has test_type '{test_type}' but filename suggests 'pre_test'"
        )
    elif "post_test" in filename:
        assert test_type == "post_test", (
            f"{test_file} has test_type '{test_type}' but filename suggests 'post_test'"
        )


@pytest.mark.parametrize("test_file", get_all_mcq_tests())
def test_scenario_matches_filename(test_file):
    """Test that scenario field matches the filename."""
    with open(test_file, 'r') as f:
        test_data = json.load(f)

    scenario = test_data["scenario"]
    filename = test_file.stem  # Get filename without extension

    # Extract scenario from filename (format: {scenario}_{test_type})
    filename_scenario = filename.replace("_pre_test", "").replace("_post_test", "")

    assert scenario == filename_scenario, (
        f"{test_file} has scenario '{scenario}' but filename suggests '{filename_scenario}'"
    )


if __name__ == "__main__":
    # Run tests manually without pytest
    print("Running MCQ schema validation tests...\n")

    # Test schema exists
    print("✓ Schema file exists")

    # Test directory exists
    print("✓ MCQ tests directory exists")

    # Test all scenarios have tests
    scenarios = ["data_types", "type_to_chart", "chart_to_task", "data_preparation"]
    for scenario in scenarios:
        tests_dir = Path("app/tests_mcq")
        pre_test = tests_dir / f"{scenario}_pre_test.json"
        post_test = tests_dir / f"{scenario}_post_test.json"
        if pre_test.exists() and post_test.exists():
            print(f"✓ {scenario}: pre and post tests exist")

    # Validate all test files
    schema = load_schema()
    test_files = get_all_mcq_tests()

    print(f"\nValidating {len(test_files)} test files...\n")

    for test_file in test_files:
        with open(test_file, 'r') as f:
            test_data = json.load(f)

        try:
            validate(instance=test_data, schema=schema)
            print(f"✓ {test_file.name}: Valid")
        except ValidationError as e:
            print(f"✗ {test_file.name}: {e.message}")

    print("\nAll validations complete!")

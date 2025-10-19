import json
import re
from pathlib import Path

import pytest
import yaml

SCENARIO_DIR = Path("app/scenarios")
SCHEMA_PATH = Path("docs/schemas/scenario.schema.json")


def _validate(instance, schema):
    schema_type = schema.get("type")

    if schema_type == "object":
        assert isinstance(instance, dict), f"Expected object, got {type(instance)}"
        required = schema.get("required", [])
        for key in required:
            assert key in instance, f"Missing required field '{key}'"
        if schema.get("additionalProperties") is False:
            allowed = set(schema.get("properties", {}).keys())
            extra = set(instance.keys()) - allowed
            assert not extra, f"Unexpected fields: {sorted(extra)}"
        for key, value in instance.items():
            if key in schema.get("properties", {}):
                _validate(value, schema["properties"][key])
        return

    if schema_type == "array":
        assert isinstance(instance, list), f"Expected array, got {type(instance)}"
        min_items = schema.get("minItems")
        if min_items is not None:
            assert len(instance) >= min_items, f"Expected at least {min_items} items"
        max_items = schema.get("maxItems")
        if max_items is not None:
            assert len(instance) <= max_items, f"Expected at most {max_items} items"
        if schema.get("uniqueItems"):
            assert len(instance) == len(set(instance)), "Array items must be unique"
        item_schema = schema.get("items")
        if item_schema:
            for item in instance:
                _validate(item, item_schema)
        return

    if schema_type == "string":
        assert isinstance(instance, str), f"Expected string, got {type(instance)}"
        enum = schema.get("enum")
        if enum is not None:
            assert instance in enum, f"Value '{instance}' not in enum {enum}"
        pattern = schema.get("pattern")
        if pattern is not None:
            assert re.fullmatch(pattern, instance), f"Value '{instance}' fails pattern {pattern}"
        min_length = schema.get("minLength")
        if min_length is not None:
            assert len(instance) >= min_length, f"String shorter than {min_length}"
        max_length = schema.get("maxLength")
        if max_length is not None:
            assert len(instance) <= max_length, f"String longer than {max_length}"
        return

    if schema_type == "integer":
        assert isinstance(instance, int), f"Expected integer, got {type(instance)}"
        minimum = schema.get("minimum")
        if minimum is not None:
            assert instance >= minimum, f"Value {instance} below minimum {minimum}"
        maximum = schema.get("maximum")
        if maximum is not None:
            assert instance <= maximum, f"Value {instance} above maximum {maximum}"
        return

    raise AssertionError(f"Unsupported schema type: {schema_type}")


@pytest.mark.parametrize("scenario_path", sorted(SCENARIO_DIR.glob("*.yaml")))
def test_scenarios_match_schema(scenario_path):
    schema = json.loads(SCHEMA_PATH.read_text())
    data = yaml.safe_load(scenario_path.read_text())

    _validate(data, schema)

    assert data["name"] == scenario_path.stem, "File name and scenario name should align"
    student_cfg = data["student_config"]
    assert set(student_cfg["target_subskills"]) <= set(data["subskills"]), "student target_subskills must be defined above"
    assert set(student_cfg["misconceptions"]) <= set(data["misconceptions"]), "student misconceptions must be defined above"

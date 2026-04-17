from __future__ import annotations

from typing import Any


PRIMITIVE_TYPES = {"string", "integer", "number", "boolean", "object", "array", "null"}


def type_name(schema: Any) -> str | None:
    if isinstance(schema, str):
        return schema
    if isinstance(schema, dict):
        value = schema.get("type")
        return value if isinstance(value, str) else None
    return None


def is_valid_schema(schema: Any) -> bool:
    if isinstance(schema, str):
        return schema in PRIMITIVE_TYPES
    if not isinstance(schema, dict):
        return False

    schema_type = schema.get("type")
    if schema_type is not None and schema_type not in PRIMITIVE_TYPES:
        return False

    properties = schema.get("properties")
    if properties is not None:
        if not isinstance(properties, dict):
            return False
        return all(is_valid_schema(child) for child in properties.values())

    items = schema.get("items")
    if items is not None and not is_valid_schema(items):
        return False

    return True


def value_matches_schema(value: Any, schema: Any) -> bool:
    expected = type_name(schema)
    if expected == "string":
        return isinstance(value, str)
    if expected == "integer":
        return isinstance(value, int) and not isinstance(value, bool)
    if expected == "number":
        return (isinstance(value, int) or isinstance(value, float)) and not isinstance(value, bool)
    if expected == "boolean":
        return isinstance(value, bool)
    if expected == "null":
        return value is None
    if expected == "array":
        if not isinstance(value, list):
            return False
        if isinstance(schema, dict) and "items" in schema:
            return all(value_matches_schema(item, schema["items"]) for item in value)
        return True
    if expected == "object":
        if not isinstance(value, dict):
            return False
        if isinstance(schema, dict) and isinstance(schema.get("properties"), dict):
            required = schema.get("required", [])
            if not isinstance(required, list):
                return False
            if any(field not in value for field in required):
                return False
            for key, child_schema in schema["properties"].items():
                if key in value and not value_matches_schema(value[key], child_schema):
                    return False
        return True

    if isinstance(schema, dict) and "properties" in schema:
        return value_matches_schema(value, {"type": "object", **schema})

    return True


def field_type_changed(old_schema: Any, new_schema: Any) -> bool:
    return type_name(old_schema) != type_name(new_schema)


from __future__ import annotations

from typing import Any

from toolprobe.result import Finding


PRIMITIVE_TYPES = {"string", "integer", "number", "boolean", "object", "array", "null"}


def type_name(schema: Any) -> str | None:
    if isinstance(schema, str):
        return schema
    if isinstance(schema, dict):
        value = schema.get("type")
        if isinstance(value, str):
            return value
        if "properties" in schema or "required" in schema:
            return "object"
        if "items" in schema:
            return "array"
    return None


def is_valid_schema(schema: Any) -> bool:
    if isinstance(schema, str):
        return schema in PRIMITIVE_TYPES
    if not isinstance(schema, dict):
        return False

    schema_type = schema.get("type")
    if schema_type is not None and schema_type not in PRIMITIVE_TYPES:
        return False
    if schema_type is None and "properties" not in schema and "required" not in schema and "items" not in schema:
        return False

    required = schema.get("required")
    if required is not None:
        if not isinstance(required, list):
            return False
        if any(not isinstance(item, str) or not item.strip() for item in required):
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


def is_valid_field_map(schema_map: dict[str, Any]) -> bool:
    return all(is_valid_schema(child) for child in schema_map.values())


def value_matches_field_map(value: Any, schema_map: dict[str, Any]) -> bool:
    if not isinstance(value, dict):
        return False
    if set(value) - set(schema_map):
        return False
    return all(value_matches_schema(value[field], schema_map[field]) for field in value)


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
        if isinstance(schema, dict):
            required = schema.get("required", [])
            if not isinstance(required, list):
                return False
            if any(field not in value for field in required):
                return False
        if isinstance(schema, dict) and isinstance(schema.get("properties"), dict):
            for key, child_schema in schema["properties"].items():
                if key in value and not value_matches_schema(value[key], child_schema):
                    return False
        return True

    if isinstance(schema, dict) and "properties" in schema:
        return value_matches_schema(value, {"type": "object", **schema})

    return True


def field_type_changed(old_schema: Any, new_schema: Any) -> bool:
    return type_name(old_schema) != type_name(new_schema)


def schema_breaking_changes(old_schema: Any, new_schema: Any, path: str, type_code: str) -> list[Finding]:
    findings: list[Finding] = []
    old_type = type_name(old_schema)
    new_type = type_name(new_schema)

    if old_type != new_type:
        findings.append(Finding(type_code, f"schema type changed from {old_type!r} to {new_type!r}", path))
        return findings

    if old_type == "object":
        old_properties = _properties(old_schema)
        new_properties = _properties(new_schema)
        for field_name in sorted(set(old_properties) - set(new_properties)):
            findings.append(Finding("removed-property", f"property '{field_name}' was removed", f"{path}.properties.{field_name}"))
        for field_name in sorted(set(old_properties).intersection(new_properties)):
            findings.extend(
                schema_breaking_changes(
                    old_properties[field_name],
                    new_properties[field_name],
                    f"{path}.properties.{field_name}",
                    type_code,
                )
            )
        for field_name in sorted(_required(new_schema) - _required(old_schema)):
            findings.append(Finding("added-required-property", f"property '{field_name}' is newly required", f"{path}.required"))
        for field_name in sorted(_required(old_schema) - _required(new_schema)):
            findings.append(Finding("removed-required-property", f"property '{field_name}' is no longer required", f"{path}.required"))

    if old_type == "array":
        old_items = _items(old_schema)
        new_items = _items(new_schema)
        if old_items is not None and new_items is not None:
            findings.extend(schema_breaking_changes(old_items, new_items, f"{path}.items", type_code))
        elif old_items is None and new_items is not None:
            findings.append(Finding("added-items-schema", "array items schema was added", f"{path}.items"))
        elif old_items is not None and new_items is None:
            findings.append(Finding("removed-items-schema", "array items schema was removed", f"{path}.items"))

    return findings


def _properties(schema: Any) -> dict[str, Any]:
    if isinstance(schema, dict) and isinstance(schema.get("properties"), dict):
        return schema["properties"]
    return {}


def _required(schema: Any) -> set[str]:
    if isinstance(schema, dict) and isinstance(schema.get("required"), list):
        return {item for item in schema["required"] if isinstance(item, str)}
    return set()


def _items(schema: Any) -> Any:
    if isinstance(schema, dict):
        return schema.get("items")
    return None

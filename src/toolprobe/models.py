from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

import yaml


class ContractLoadError(ValueError):
    pass


@dataclass(frozen=True)
class MockError:
    name: str
    response: dict[str, Any]
    expected_recovery_contains: str | None = None


@dataclass(frozen=True)
class Tool:
    name: str
    description: str
    args: dict[str, Any]
    required_args: list[str] = field(default_factory=list)
    forbidden_args: list[str] = field(default_factory=list)
    triggers: list[str] = field(default_factory=list)
    output_schema: dict[str, Any] = field(default_factory=dict)
    mock_success: dict[str, Any] | None = None
    mock_errors: list[MockError] = field(default_factory=list)


@dataclass(frozen=True)
class Contract:
    contract: str
    tools: list[Tool]

    def tool_map(self) -> dict[str, Tool]:
        return {tool.name: tool for tool in self.tools}


def load_contract_file(path: str) -> Contract:
    with open(path, "r", encoding="utf-8") as handle:
        return load_contract_text(handle.read(), source=path)


def load_contract_text(text: str, source: str = "<memory>") -> Contract:
    try:
        raw = yaml.safe_load(text)
    except yaml.YAMLError as exc:
        raise ContractLoadError(f"{source}: invalid YAML: {exc}") from exc

    if raw is None:
        raise ContractLoadError(f"{source}: empty contract")
    if not isinstance(raw, dict):
        raise ContractLoadError(f"{source}: contract must be a YAML mapping")

    contract_version = raw.get("contract")
    if not isinstance(contract_version, str):
        raise ContractLoadError(f"{source}: contract must define string field 'contract'")
    if contract_version != "v1":
        raise ContractLoadError(f"{source}: unsupported contract version '{contract_version}'")

    raw_tools = raw.get("tools")
    if not isinstance(raw_tools, list):
        raise ContractLoadError(f"{source}: contract must define list field 'tools'")

    tools: list[Tool] = []
    for index, raw_tool in enumerate(raw_tools):
        if not isinstance(raw_tool, dict):
            raise ContractLoadError(f"{source}: tools[{index}] must be a mapping")
        tools.append(_parse_tool(raw_tool, source, index))

    return Contract(contract=contract_version, tools=tools)


def _parse_tool(raw: dict[str, Any], source: str, index: int) -> Tool:
    path = f"{source}: tools[{index}]"
    name = _string_field(raw, "name", path)
    description = _string_field(raw, "description", path)
    args = _dict_field(raw, "args", path, default={})
    required_args = _string_list_field(raw, "required_args", path)
    forbidden_args = _string_list_field(raw, "forbidden_args", path)
    triggers = _string_list_field(raw, "triggers", path)
    output_schema = _dict_field(raw, "output_schema", path, default={})

    mock_success = raw.get("mock_success")
    if mock_success is not None and not isinstance(mock_success, dict):
        raise ContractLoadError(f"{path}.mock_success must be a mapping")

    mock_errors: list[MockError] = []
    raw_mock_errors = raw.get("mock_errors", [])
    if raw_mock_errors is None:
        raw_mock_errors = []
    if not isinstance(raw_mock_errors, list):
        raise ContractLoadError(f"{path}.mock_errors must be a list")
    for error_index, raw_error in enumerate(raw_mock_errors):
        if not isinstance(raw_error, dict):
            raise ContractLoadError(f"{path}.mock_errors[{error_index}] must be a mapping")
        error_name = _string_field(raw_error, "name", f"{path}.mock_errors[{error_index}]")
        response = _dict_field(raw_error, "response", f"{path}.mock_errors[{error_index}]", default={})
        recovery = raw_error.get("expected_recovery_contains")
        if recovery is not None and not isinstance(recovery, str):
            raise ContractLoadError(
                f"{path}.mock_errors[{error_index}].expected_recovery_contains must be a string"
            )
        mock_errors.append(MockError(name=error_name, response=response, expected_recovery_contains=recovery))

    return Tool(
        name=name,
        description=description,
        args=args,
        required_args=required_args,
        forbidden_args=forbidden_args,
        triggers=triggers,
        output_schema=output_schema,
        mock_success=mock_success,
        mock_errors=mock_errors,
    )


def _string_field(raw: dict[str, Any], field_name: str, path: str) -> str:
    value = raw.get(field_name)
    if not isinstance(value, str) or not value.strip():
        raise ContractLoadError(f"{path}.{field_name} must be a non-empty string")
    return value


def _dict_field(raw: dict[str, Any], field_name: str, path: str, default: dict[str, Any]) -> dict[str, Any]:
    value = raw.get(field_name, default)
    if value is None:
        return default
    if not isinstance(value, dict):
        raise ContractLoadError(f"{path}.{field_name} must be a mapping")
    return value


def _string_list_field(raw: dict[str, Any], field_name: str, path: str) -> list[str]:
    value = raw.get(field_name, [])
    if value is None:
        return []
    if not isinstance(value, list) or any(not isinstance(item, str) or not item.strip() for item in value):
        raise ContractLoadError(f"{path}.{field_name} must be a list of non-empty strings")
    return value

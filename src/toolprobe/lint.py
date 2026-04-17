from __future__ import annotations

import re

from toolprobe.models import Contract
from toolprobe.result import Finding, Severity
from toolprobe.schema import is_valid_output_schema, is_valid_schema, schema_has_path, value_matches_output_schema

TEMPLATE_FIELD_PATTERN = re.compile(r"{([A-Za-z_][A-Za-z0-9_]*(?:\.[A-Za-z_][A-Za-z0-9_]*)*)}")


def lint_contract(contract: Contract) -> list[Finding]:
    findings: list[Finding] = []
    seen_tools: set[str] = set()

    for index, tool in enumerate(contract.tools):
        path = f"tools[{index}]({tool.name})"

        if tool.name in seen_tools:
            findings.append(Finding("duplicate-tool", f"tool '{tool.name}' is defined more than once", path))
        seen_tools.add(tool.name)

        if not tool.args:
            findings.append(Finding("missing-args", "tool has no argument schema", f"{path}.args", Severity.WARNING))

        for arg_name, arg_schema in tool.args.items():
            if not is_valid_schema(arg_schema):
                findings.append(Finding("invalid-arg-schema", f"argument '{arg_name}' has an invalid schema", f"{path}.args.{arg_name}"))

        for arg_name in tool.required_args:
            if arg_name not in tool.args:
                findings.append(Finding("required-arg-missing", f"required arg '{arg_name}' is not declared in args", f"{path}.required_args"))

        overlap = sorted(set(tool.required_args).intersection(tool.forbidden_args))
        for arg_name in overlap:
            findings.append(Finding("required-forbidden-overlap", f"arg '{arg_name}' is both required and forbidden", f"{path}.forbidden_args"))

        for trigger_index, trigger in enumerate(tool.triggers):
            for field_name in TEMPLATE_FIELD_PATTERN.findall(trigger):
                if not schema_has_path(tool.args, field_name):
                    findings.append(
                        Finding(
                            "unknown-trigger-field",
                            f"trigger references '{field_name}', but args does not define it",
                            f"{path}.triggers[{trigger_index}]",
                        )
                    )

        if tool.output_schema and not is_valid_output_schema(tool.output_schema):
            findings.append(Finding("invalid-output-schema", "output_schema is not a supported schema", f"{path}.output_schema"))

        if tool.mock_success is not None:
            if not value_matches_output_schema(tool.mock_success, tool.output_schema):
                findings.append(
                    Finding(
                        "mock-success-schema-mismatch",
                        "mock_success does not match output_schema",
                        f"{path}.mock_success",
                    )
                )

        for error_index, mock_error in enumerate(tool.mock_errors):
            if not mock_error.response:
                findings.append(
                    Finding(
                        "empty-mock-error-response",
                        f"mock error '{mock_error.name}' has an empty response",
                        f"{path}.mock_errors[{error_index}]",
                        Severity.WARNING,
                    )
                )
            if mock_error.expected_recovery_contains is None:
                findings.append(
                    Finding(
                        "missing-recovery-expectation",
                        f"mock error '{mock_error.name}' has no expected recovery text",
                        f"{path}.mock_errors[{error_index}]",
                        Severity.WARNING,
                    )
                )

    return findings

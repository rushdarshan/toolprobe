from __future__ import annotations

from toolprobe.models import Contract, Tool
from toolprobe.result import Finding, Severity
from toolprobe.schema import normalize_output_schema, schema_breaking_changes


def diff_contracts(old: Contract, new: Contract) -> list[Finding]:
    findings: list[Finding] = []
    old_tools = old.tool_map()
    new_tools = new.tool_map()

    for tool_name, old_tool in sorted(old_tools.items()):
        new_tool = new_tools.get(tool_name)
        if new_tool is None:
            findings.append(Finding("removed-tool", f"tool '{tool_name}' was removed", f"tools.{tool_name}"))
            continue
        findings.extend(_diff_tool(old_tool, new_tool))

    return findings


def _diff_tool(old: Tool, new: Tool) -> list[Finding]:
    findings: list[Finding] = []
    path = f"tools.{old.name}"

    old_required = set(old.required_args)
    new_required = set(new.required_args)
    old_forbidden = set(old.forbidden_args)
    new_forbidden = set(new.forbidden_args)
    old_args = set(old.args)
    new_args = set(new.args)

    for arg_name in sorted(old_args - new_args):
        findings.append(Finding("removed-arg", f"argument '{arg_name}' was removed", f"{path}.args.{arg_name}"))

    for arg_name in sorted(new_required - old_required):
        findings.append(Finding("added-required-arg", f"argument '{arg_name}' is newly required", f"{path}.required_args"))

    for arg_name in sorted(old_required - new_required):
        findings.append(
            Finding(
                "removed-required-arg",
                f"argument '{arg_name}' is no longer required",
                f"{path}.required_args",
                Severity.WARNING,
            )
        )

    for arg_name in sorted(new_forbidden - old_forbidden):
        findings.append(Finding("added-forbidden-arg", f"argument '{arg_name}' is newly forbidden", f"{path}.forbidden_args"))

    for arg_name in sorted(old_forbidden - new_forbidden):
        findings.append(
            Finding(
                "removed-forbidden-arg",
                f"argument '{arg_name}' is no longer forbidden",
                f"{path}.forbidden_args",
                Severity.WARNING,
            )
        )

    for arg_name in sorted(old_args.intersection(new_args)):
        findings.extend(
            schema_breaking_changes(
                old.args[arg_name],
                new.args[arg_name],
                f"{path}.args.{arg_name}",
                "arg-type-changed",
                is_output=False,
            )
        )

    for trigger in sorted(set(old.triggers) - set(new.triggers)):
        findings.append(Finding("removed-trigger", f"trigger was removed: {trigger!r}", f"{path}.triggers"))

    findings.extend(
        schema_breaking_changes(
            normalize_output_schema(old.output_schema),
            normalize_output_schema(new.output_schema),
            f"{path}.output_schema",
            "output-type-changed",
            is_output=True,
        )
    )

    old_recoveries = {
        error.name: error.expected_recovery_contains for error in old.mock_errors if error.expected_recovery_contains
    }
    new_recoveries = {
        error.name: error.expected_recovery_contains for error in new.mock_errors if error.expected_recovery_contains
    }
    for error_name in sorted(set(old_recoveries) - set(new_recoveries)):
        findings.append(Finding("removed-recovery", f"recovery expectation for '{error_name}' was removed", f"{path}.mock_errors"))
    for error_name in sorted(set(old_recoveries).intersection(new_recoveries)):
        if old_recoveries[error_name] != new_recoveries[error_name]:
            findings.append(
                Finding(
                    "changed-recovery",
                    f"recovery expectation for '{error_name}' changed",
                    f"{path}.mock_errors.{error_name}",
                )
            )

    return findings

from __future__ import annotations

from toolprobe.models import Contract, Tool
from toolprobe.result import Finding
from toolprobe.schema import field_type_changed


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
    old_args = set(old.args)
    new_args = set(new.args)

    for arg_name in sorted(old_args - new_args):
        findings.append(Finding("removed-arg", f"argument '{arg_name}' was removed", f"{path}.args.{arg_name}"))

    for arg_name in sorted(new_required - old_required):
        findings.append(Finding("added-required-arg", f"argument '{arg_name}' is newly required", f"{path}.required_args"))

    for arg_name in sorted(old_required - new_required):
        findings.append(Finding("removed-required-arg", f"argument '{arg_name}' is no longer required", f"{path}.required_args"))

    for arg_name in sorted(old_args.intersection(new_args)):
        if field_type_changed(old.args[arg_name], new.args[arg_name]):
            findings.append(Finding("arg-type-changed", f"argument '{arg_name}' changed type", f"{path}.args.{arg_name}"))

    for trigger in sorted(set(old.triggers) - set(new.triggers)):
        findings.append(Finding("removed-trigger", f"trigger was removed: {trigger!r}", f"{path}.triggers"))

    old_output = old.output_schema
    new_output = new.output_schema
    for field_name in sorted(set(old_output) - set(new_output)):
        findings.append(Finding("removed-output-field", f"output field '{field_name}' was removed", f"{path}.output_schema.{field_name}"))

    for field_name in sorted(set(old_output).intersection(new_output)):
        if field_type_changed(old_output[field_name], new_output[field_name]):
            findings.append(Finding("output-type-changed", f"output field '{field_name}' changed type", f"{path}.output_schema.{field_name}"))

    old_recoveries = {error.name for error in old.mock_errors if error.expected_recovery_contains}
    new_recoveries = {error.name for error in new.mock_errors if error.expected_recovery_contains}
    for error_name in sorted(old_recoveries - new_recoveries):
        findings.append(Finding("removed-recovery", f"recovery expectation for '{error_name}' was removed", f"{path}.mock_errors"))

    return findings


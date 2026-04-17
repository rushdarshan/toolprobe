from __future__ import annotations

import argparse
import sys

from toolprobe.diff import diff_contracts
from toolprobe.git import GitError, read_file_at_ref
from toolprobe.lint import lint_contract
from toolprobe.models import ContractLoadError, load_contract_file, load_contract_text
from toolprobe.result import Finding, Severity, has_errors


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="toolprobe", description="Contract checks for LLM tools.")
    subparsers = parser.add_subparsers(dest="command", required=True)

    lint_parser = subparsers.add_parser("lint", help="Validate a tool contract file.")
    lint_parser.add_argument("contract", nargs="?", default="toolprobe.yaml", help="Path to toolprobe.yaml")

    diff_parser = subparsers.add_parser("diff", help="Find breaking changes against a git ref.")
    diff_parser.add_argument("base", help="Git ref to compare against, for example HEAD~1 or main")
    diff_parser.add_argument("contract", nargs="?", default="toolprobe.yaml", help="Path to toolprobe.yaml")

    args = parser.parse_args(argv)
    try:
        if args.command == "lint":
            return _lint(args.contract)
        if args.command == "diff":
            return _diff(args.base, args.contract)
    except (ContractLoadError, GitError, OSError) as exc:
        print(f"toolprobe: {exc}", file=sys.stderr)
        return 2

    parser.error(f"unknown command: {args.command}")
    return 2


def _lint(path: str) -> int:
    contract = load_contract_file(path)
    findings = lint_contract(contract)
    _print_findings("ToolProbe lint", findings)
    return 1 if has_errors(findings) else 0


def _diff(base: str, path: str) -> int:
    new_contract = load_contract_file(path)
    findings = lint_contract(new_contract)

    old_text = read_file_at_ref(base, path, missing_ok=True)
    if old_text is None:
        _print_findings(f"ToolProbe diff against {base}", findings)
        if not has_errors(findings):
            print(f"Note: {path} does not exist at {base}; treating this as a new contract.")
        return 1 if has_errors(findings) else 0

    old_contract = load_contract_text(old_text, source=f"{base}:{path}")
    findings.extend(diff_contracts(old_contract, new_contract))

    _print_findings(f"ToolProbe diff against {base}", findings)
    return 1 if has_errors(findings) else 0


def _print_findings(title: str, findings: list[Finding]) -> None:
    print(title)
    print("=" * len(title))
    if not findings:
        print("OK: no issues found")
        return

    for finding in findings:
        print(finding.format())

    error_count = sum(1 for finding in findings if finding.severity == Severity.ERROR)
    warning_count = len(findings) - error_count
    print()
    print(f"Summary: {error_count} error(s), {warning_count} warning(s)")


if __name__ == "__main__":
    raise SystemExit(main())

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


class Severity(str, Enum):
    ERROR = "error"
    WARNING = "warning"


@dataclass(frozen=True)
class Finding:
    code: str
    message: str
    path: str
    severity: Severity = Severity.ERROR

    def format(self) -> str:
        marker = "ERROR" if self.severity == Severity.ERROR else "WARN"
        return f"{marker} {self.code} {self.path}: {self.message}"


def has_errors(findings: list[Finding]) -> bool:
    return any(finding.severity == Severity.ERROR for finding in findings)


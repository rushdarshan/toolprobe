from toolprobe.diff import diff_contracts
from toolprobe.models import load_contract_text


def test_diff_flags_breaking_tool_contract_changes() -> None:
    old = load_contract_text(
        """
contract: v1
tools:
  - name: search_flights
    description: Search flights.
    args:
      destination: string
      date: string
    required_args: [destination, date]
    triggers:
      - "flights to {destination} on {date}"
    output_schema:
      flights:
        type: array
    mock_errors:
      - name: timeout
        response:
          error: timeout
        expected_recovery_contains: try again
"""
    )
    new = load_contract_text(
        """
contract: v1
tools:
  - name: search_flights
    description: Search flights.
    args:
      destination: string
      date: integer
    required_args: [destination]
    triggers:
      - "flights to {destination}"
    output_schema:
      flights: string
    mock_errors:
      - name: timeout
        response:
          error: timeout
"""
    )

    findings = diff_contracts(old, new)
    codes = {finding.code for finding in findings}

    assert "removed-required-arg" in codes
    assert "arg-type-changed" in codes
    assert "removed-trigger" in codes
    assert "output-type-changed" in codes
    assert "removed-recovery" in codes


def test_diff_flags_removed_tool() -> None:
    old = load_contract_text(
        """
contract: v1
tools:
  - name: get_weather
    description: Get weather.
    args:
      city: string
"""
    )
    new = load_contract_text(
        """
contract: v1
tools: []
"""
    )

    findings = diff_contracts(old, new)

    assert any(finding.code == "removed-tool" for finding in findings)


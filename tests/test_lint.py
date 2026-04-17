from toolprobe.lint import lint_contract
from toolprobe.models import load_contract_text


def test_lint_valid_contract_has_no_errors() -> None:
    contract = load_contract_text(
        """
contract: v1
tools:
  - name: get_weather
    description: Get current weather.
    args:
      city: string
    required_args: [city]
    triggers:
      - "weather in {city}"
    output_schema:
      condition: string
    mock_success:
      condition: sunny
"""
    )

    findings = lint_contract(contract)

    assert [finding.code for finding in findings if finding.severity == "error"] == []


def test_lint_flags_unknown_trigger_field() -> None:
    contract = load_contract_text(
        """
contract: v1
tools:
  - name: get_weather
    description: Get current weather.
    args:
      city: string
    required_args: [city]
    triggers:
      - "weather in {location}"
"""
    )

    findings = lint_contract(contract)

    assert any(finding.code == "unknown-trigger-field" for finding in findings)


def test_lint_flags_mock_schema_mismatch() -> None:
    contract = load_contract_text(
        """
contract: v1
tools:
  - name: get_weather
    description: Get current weather.
    args:
      city: string
    output_schema:
      temperature_c: number
    mock_success:
      temperature_c: hot
"""
    )

    findings = lint_contract(contract)

    assert any(finding.code == "mock-success-schema-mismatch" for finding in findings)


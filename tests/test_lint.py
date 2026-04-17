from toolprobe.lint import lint_contract
import pytest

from toolprobe.models import ContractLoadError, load_contract_text


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


def test_lint_flags_invalid_output_schema_fields() -> None:
    contract = load_contract_text(
        """
contract: v1
tools:
  - name: get_weather
    description: Get current weather.
    args:
      city: string
    output_schema:
      temperature_c: definitely-not-a-type
"""
    )

    findings = lint_contract(contract)

    assert any(finding.code == "invalid-output-schema" for finding in findings)


def test_parser_accepts_empty_optional_yaml_nodes() -> None:
    contract = load_contract_text(
        """
contract: v1
tools:
  - name: get_weather
    description: Get current weather.
    args:
      city: string
    forbidden_args:
    triggers:
      - "weather in {city}"
    output_schema:
    mock_errors:
"""
    )

    tool = contract.tools[0]

    assert tool.forbidden_args == []
    assert tool.output_schema == {}
    assert tool.mock_errors == []


def test_mock_schema_enforces_required_without_properties() -> None:
    contract = load_contract_text(
        """
contract: v1
tools:
  - name: get_user
    description: Get a user.
    args:
      id: string
    output_schema:
      user:
        type: object
        required:
          - id
    mock_success:
      user: {}
"""
    )

    findings = lint_contract(contract)

    assert any(finding.code == "mock-success-schema-mismatch" for finding in findings)


@pytest.mark.parametrize("value", ["false", '""', "0"])
def test_parser_rejects_invalid_falsy_mock_errors(value: str) -> None:
    with pytest.raises(ContractLoadError, match="mock_errors must be a list"):
        load_contract_text(
            f"""
contract: v1
tools:
  - name: get_weather
    description: Get current weather.
    args:
      city: string
    mock_errors: {value}
"""
        )


def test_lint_accepts_required_only_implicit_object_schema() -> None:
    contract = load_contract_text(
        """
contract: v1
tools:
  - name: get_user
    description: Get a user.
    args:
      user:
        required:
          - id
"""
    )

    findings = lint_contract(contract)

    assert not any(finding.code == "invalid-arg-schema" for finding in findings)


def test_empty_output_schema_rejects_non_empty_mock_success() -> None:
    contract = load_contract_text(
        """
contract: v1
tools:
  - name: ping
    description: Ping a service.
    args:
      service: string
    output_schema: {}
    mock_success:
      unexpected: value
"""
    )

    findings = lint_contract(contract)

    assert any(finding.code == "mock-success-schema-mismatch" for finding in findings)

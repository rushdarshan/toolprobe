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
      type: object
      properties:
        condition: string
      required:
        - condition
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


def test_lint_validates_nested_trigger_field() -> None:
    contract = load_contract_text(
        """
contract: v1
tools:
  - name: get_weather
    description: Get current weather.
    args:
      location:
        type: object
        properties:
          city: string
    triggers:
      - "weather in {location.city}"
"""
    )

    findings = lint_contract(contract)

    assert not any(finding.code == "unknown-trigger-field" for finding in findings)


def test_lint_flags_unknown_nested_trigger_field() -> None:
    contract = load_contract_text(
        """
contract: v1
tools:
  - name: get_weather
    description: Get current weather.
    args:
      location:
        type: object
        properties:
          city: string
    triggers:
      - "weather in {location.country}"
"""
    )

    findings = lint_contract(contract)

    assert any(finding.code == "unknown-trigger-field" for finding in findings)


def test_lint_validates_trigger_field_inside_array_items() -> None:
    contract = load_contract_text(
        """
contract: v1
tools:
  - name: summarize_orders
    description: Summarize orders.
    args:
      orders:
        type: array
        items:
          type: object
          properties:
            id: string
    triggers:
      - "summarize order {orders.id}"
"""
    )

    findings = lint_contract(contract)

    assert not any(finding.code == "unknown-trigger-field" for finding in findings)


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
      type: object
      properties:
        temperature_c: number
      required:
        - temperature_c
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


def test_lint_flags_required_property_not_declared() -> None:
    contract = load_contract_text(
        """
contract: v1
tools:
  - name: get_user
    description: Get a user.
    args:
      user:
        type: object
        properties:
          id: string
        required:
          - missing
"""
    )

    findings = lint_contract(contract)

    assert any(finding.code == "invalid-arg-schema" for finding in findings)


@pytest.mark.parametrize(
    "schema",
    [
        """
type: string
properties:
  id: string
""",
        """
type: object
items: string
""",
        """
properties:
  id: string
items: string
""",
    ],
)
def test_lint_rejects_inconsistent_schema_keywords(schema: str) -> None:
    indented_schema = "\n".join(f"      {line}" if line else line for line in schema.strip().splitlines())
    contract = load_contract_text(
        f"""
contract: v1
tools:
  - name: bad_tool
    description: Bad tool.
    args:
      payload:
{indented_schema}
"""
    )

    findings = lint_contract(contract)

    assert any(finding.code == "invalid-arg-schema" for finding in findings)


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
      type: object
      properties:
        user:
          type: object
          required:
            - id
      required:
        - user
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


def test_mock_success_must_include_all_output_fields() -> None:
    contract = load_contract_text(
        """
contract: v1
tools:
  - name: get_weather
    description: Get current weather.
    args:
      city: string
    output_schema:
      type: object
      properties:
        temperature_c: number
        condition: string
      required:
        - temperature_c
        - condition
    mock_success:
      condition: sunny
"""
    )

    findings = lint_contract(contract)

    assert any(finding.code == "mock-success-schema-mismatch" for finding in findings)


def test_formal_root_output_schema_supports_required_fields() -> None:
    contract = load_contract_text(
        """
contract: v1
tools:
  - name: get_weather
    description: Get current weather.
    args:
      city: string
    output_schema:
      type: object
      properties:
        condition: string
        temperature_c: number
      required:
        - condition
    mock_success:
      condition: sunny
"""
    )

    findings = lint_contract(contract)

    assert [finding.code for finding in findings if finding.severity == "error"] == []


def test_formal_root_output_schema_rejects_missing_required_field() -> None:
    contract = load_contract_text(
        """
contract: v1
tools:
  - name: get_weather
    description: Get current weather.
    args:
      city: string
    output_schema:
      type: object
      properties:
        condition: string
      required:
        - condition
    mock_success: {}
"""
    )

    findings = lint_contract(contract)

    assert any(finding.code == "mock-success-schema-mismatch" for finding in findings)


def test_mock_success_rejects_unknown_output_properties() -> None:
    contract = load_contract_text(
        """
contract: v1
tools:
  - name: get_weather
    description: Get current weather.
    args:
      city: string
    output_schema:
      type: object
      properties:
        condition: string
      required:
        - condition
    mock_success:
      condition: sunny
      unexpected: value
"""
    )

    findings = lint_contract(contract)

    assert any(finding.code == "mock-success-schema-mismatch" for finding in findings)


def test_lint_flags_duplicate_mock_error_names() -> None:
    contract = load_contract_text(
        """
contract: v1
tools:
  - name: get_weather
    description: Get current weather.
    args:
      city: string
    mock_errors:
      - name: timeout
        response:
          error: timeout
      - name: timeout
        response:
          error: still timeout
"""
    )

    findings = lint_contract(contract)

    assert any(finding.code == "duplicate-mock-error" for finding in findings)


def test_parser_rejects_unsupported_contract_version() -> None:
    with pytest.raises(ContractLoadError, match="unsupported contract version"):
        load_contract_text(
            """
contract: v2
tools: []
"""
        )

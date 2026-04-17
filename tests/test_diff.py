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


def test_diff_flags_deep_arg_type_changes() -> None:
    old = load_contract_text(
        """
contract: v1
tools:
  - name: update_user
    description: Update user.
    args:
      profile:
        type: object
        properties:
          name: string
          age: integer
"""
    )
    new = load_contract_text(
        """
contract: v1
tools:
  - name: update_user
    description: Update user.
    args:
      profile:
        type: object
        properties:
          name: integer
          age: integer
"""
    )

    findings = diff_contracts(old, new)

    assert any(finding.code == "arg-type-changed" and "profile.properties.name" in finding.path for finding in findings)


def test_diff_flags_added_nested_required_property() -> None:
    old = load_contract_text(
        """
contract: v1
tools:
  - name: update_user
    description: Update user.
    args:
      profile:
        type: object
        properties:
          name: string
          email: string
        required:
          - name
"""
    )
    new = load_contract_text(
        """
contract: v1
tools:
  - name: update_user
    description: Update user.
    args:
      profile:
        type: object
        properties:
          name: string
          email: string
        required:
          - name
          - email
"""
    )

    findings = diff_contracts(old, new)

    assert any(finding.code == "added-required-property" and "profile.required" in finding.path for finding in findings)


def test_diff_flags_added_forbidden_arg() -> None:
    old = load_contract_text(
        """
contract: v1
tools:
  - name: get_weather
    description: Get weather.
    args:
      city: string
      country: string
"""
    )
    new = load_contract_text(
        """
contract: v1
tools:
  - name: get_weather
    description: Get weather.
    args:
      city: string
      country: string
    forbidden_args:
      - country
"""
    )

    findings = diff_contracts(old, new)

    assert any(finding.code == "added-forbidden-arg" for finding in findings)


def test_diff_flags_deep_output_type_changes() -> None:
    old = load_contract_text(
        """
contract: v1
tools:
  - name: get_weather
    description: Get weather.
    args:
      city: string
    output_schema:
      forecast:
        type: object
        properties:
          condition: string
"""
    )
    new = load_contract_text(
        """
contract: v1
tools:
  - name: get_weather
    description: Get weather.
    args:
      city: string
    output_schema:
      forecast:
        type: object
        properties:
          condition: integer
"""
    )

    findings = diff_contracts(old, new)

    assert any(finding.code == "output-type-changed" and "forecast.properties.condition" in finding.path for finding in findings)


def test_diff_handles_implicit_object_schemas() -> None:
    old = load_contract_text(
        """
contract: v1
tools:
  - name: update_user
    description: Update user.
    args:
      profile:
        properties:
          name: string
          email: string
        required:
          - name
"""
    )
    new = load_contract_text(
        """
contract: v1
tools:
  - name: update_user
    description: Update user.
    args:
      profile:
        properties:
          name: integer
          email: string
        required:
          - name
          - email
"""
    )

    findings = diff_contracts(old, new)
    codes = {finding.code for finding in findings}

    assert "arg-type-changed" in codes
    assert "added-required-property" in codes


def test_diff_flags_added_array_items_schema() -> None:
    old = load_contract_text(
        """
contract: v1
tools:
  - name: tag_items
    description: Tag items.
    args:
      tags:
        type: array
"""
    )
    new = load_contract_text(
        """
contract: v1
tools:
  - name: tag_items
    description: Tag items.
    args:
      tags:
        type: array
        items: string
"""
    )

    findings = diff_contracts(old, new)

    assert any(finding.code == "added-items-schema" for finding in findings)


def test_diff_handles_implicit_array_schemas() -> None:
    old = load_contract_text(
        """
contract: v1
tools:
  - name: tag_items
    description: Tag items.
    args:
      tags:
        items: string
"""
    )
    new = load_contract_text(
        """
contract: v1
tools:
  - name: tag_items
    description: Tag items.
    args:
      tags:
        items: integer
"""
    )

    findings = diff_contracts(old, new)

    assert any(finding.code == "arg-type-changed" and "tags.items" in finding.path for finding in findings)

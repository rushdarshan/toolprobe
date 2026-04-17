# ToolProbe

OpenAPI-style breaking-change detection for LLM tools.

ToolProbe validates a committed `toolprobe.yaml` contract so tool schemas, trigger examples, mock responses, and recovery expectations do not silently drift as your agent changes.

## Why

Agent failures often happen at the tool boundary:

- the agent calls a tool whose schema changed
- a required argument disappears or changes type
- trigger examples no longer match declared arguments
- mock responses drift away from the output schema
- error recovery behavior gets removed during a refactor

ToolProbe treats tool definitions like API contracts and checks them in CI before runtime.

## Install

```bash
pip install toolprobe
```

For local development:

```bash
pip install -e ".[dev]"
```

## Contract Example

```yaml
contract: v1

tools:
  - name: get_weather
    description: Get current weather for a city.
    args:
      city: string
      units:
        type: string
    required_args:
      - city
    forbidden_args:
      - country
    triggers:
      - "weather in {city}"
      - "what's it like in {city}"
    output_schema:
      temperature_c: number
      condition: string
    mock_success:
      temperature_c: 32
      condition: sunny
    mock_errors:
      - name: timeout
        response:
          error: API timeout
        expected_recovery_contains: "couldn't fetch"
```

## Usage

Validate the current contract:

```bash
toolprobe lint toolprobe.yaml
```

Compare the current contract against a git ref:

```bash
toolprobe diff HEAD~1 toolprobe.yaml
```

Example output:

```text
ToolProbe diff against HEAD~1
============================
ERROR removed-required-arg tools.search_flights.required_args: argument 'date' is no longer required
ERROR arg-type-changed tools.search_flights.args.date: argument 'date' changed type
ERROR removed-trigger tools.search_flights.triggers: trigger was removed: 'flights to {destination} on {date}'

Summary: 3 error(s), 0 warning(s)
```

## Checks

`toolprobe lint` currently checks:

- duplicate tool names
- missing or invalid argument schemas
- required args not declared in `args`
- overlap between required and forbidden args
- trigger placeholders that reference unknown args
- invalid output schemas
- mock success responses that do not match the output schema
- missing recovery expectations for mock tool errors

`toolprobe diff` currently flags:

- removed tools
- removed arguments
- newly required arguments
- removed required arguments
- changed argument types
- removed trigger examples
- removed output fields
- changed output field types
- removed recovery expectations

## CI

```yaml
name: toolprobe

on: [pull_request]

jobs:
  contracts:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
        with:
          fetch-depth: 0
      - uses: actions/setup-python@v5
        with:
          python-version: "3.12"
      - run: pip install toolprobe
      - run: toolprobe lint toolprobe.yaml
      - run: toolprobe diff origin/main toolprobe.yaml
```

## Development

```bash
pip install -e ".[dev]"
pytest
```


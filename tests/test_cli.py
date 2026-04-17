from pathlib import Path

from toolprobe.cli import main


def test_cli_lint_success(tmp_path: Path, capsys) -> None:
    contract = tmp_path / "toolprobe.yaml"
    contract.write_text(
        """
contract: v1
tools:
  - name: get_weather
    description: Get weather.
    args:
      city: string
    required_args: [city]
""",
        encoding="utf-8",
    )

    code = main(["lint", str(contract)])
    captured = capsys.readouterr()

    assert code == 0
    assert "OK: no issues found" in captured.out


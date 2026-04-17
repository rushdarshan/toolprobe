from pathlib import Path

import toolprobe.cli as cli
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


def test_cli_diff_treats_missing_base_contract_as_new(tmp_path: Path, monkeypatch, capsys) -> None:
    contract = tmp_path / "toolprobe.yaml"
    contract.write_text(
        """
contract: v1
tools:
  - name: get_weather
    description: Get weather.
    args:
      city: string
""",
        encoding="utf-8",
    )
    monkeypatch.setattr(cli, "read_file_at_ref", lambda base, path, missing_ok=False: None)

    code = main(["diff", "HEAD~1", str(contract)])
    captured = capsys.readouterr()

    assert code == 0
    assert "treating this as a new contract" in captured.out


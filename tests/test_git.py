import subprocess

import toolprobe.git as git_module
from toolprobe.git import read_file_at_ref


def test_read_file_at_ref_normalizes_windows_paths(monkeypatch) -> None:
    calls = []

    def fake_run(args, **kwargs):
        calls.append(args)
        if args[:3] == ["git", "cat-file", "-e"]:
            return subprocess.CompletedProcess(args, 0, "", "")
        if args[:2] == ["git", "show"]:
            return subprocess.CompletedProcess(args, 0, "contract: v1", "")
        raise AssertionError(f"unexpected command: {args}")

    monkeypatch.setattr(git_module.subprocess, "run", fake_run)

    text = read_file_at_ref("main", "examples\\toolprobe.yaml", missing_ok=True)

    assert text == "contract: v1"
    assert calls[0][-1] == "main:examples/toolprobe.yaml"
    assert calls[1][-1] == "main:examples/toolprobe.yaml"

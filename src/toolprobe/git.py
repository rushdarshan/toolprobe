from __future__ import annotations

from pathlib import Path
import subprocess


class GitError(RuntimeError):
    pass


def read_file_at_ref(ref: str, path: str, *, missing_ok: bool = False) -> str | None:
    git_path = Path(path).as_posix().replace("\\", "/")
    if missing_ok and not _file_exists_at_ref(ref, git_path):
        return None

    spec = f"{ref}:{git_path}"
    result = subprocess.run(
        ["git", "show", spec],
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        check=False,
    )
    if result.returncode != 0:
        message = result.stderr.strip() or result.stdout.strip() or f"git show failed for {spec}"
        raise GitError(message)
    return result.stdout


def _file_exists_at_ref(ref: str, git_path: str) -> bool:
    result = subprocess.run(
        ["git", "cat-file", "-e", f"{ref}:{git_path}"],
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        check=False,
    )
    if result.returncode == 0:
        return True

    ref_result = subprocess.run(
        ["git", "rev-parse", "--verify", "--quiet", ref],
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        check=False,
    )
    if ref_result.returncode != 0:
        message = ref_result.stderr.strip() or ref_result.stdout.strip() or f"unknown git ref: {ref}"
        raise GitError(message)

    return False

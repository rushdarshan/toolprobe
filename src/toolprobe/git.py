from __future__ import annotations

import subprocess


class GitError(RuntimeError):
    pass


def read_file_at_ref(ref: str, path: str) -> str:
    spec = f"{ref}:{path}"
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


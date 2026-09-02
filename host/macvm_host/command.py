from __future__ import annotations

from dataclasses import dataclass
import shutil
import subprocess
from typing import Mapping, Sequence


@dataclass(frozen=True)
class CommandResult:
    command: tuple[str, ...]
    available: bool
    returncode: int | None
    stdout: str
    stderr: str


def run_command(
    command: Sequence[str],
    *,
    timeout_seconds: float = 20.0,
    env: Mapping[str, str] | None = None,
) -> CommandResult:
    executable = command[0]
    if shutil.which(executable) is None:
        return CommandResult(tuple(command), False, None, "", f"{executable}: command not found")

    try:
        completed = subprocess.run(
            command,
            check=False,
            capture_output=True,
            text=True,
            timeout=timeout_seconds,
            env=env,
        )
    except subprocess.TimeoutExpired as error:
        stdout = error.stdout.decode() if isinstance(error.stdout, bytes) else (error.stdout or "")
        stderr = error.stderr.decode() if isinstance(error.stderr, bytes) else (error.stderr or "")
        return CommandResult(tuple(command), True, 124, stdout, f"{stderr}\ncommand timed out")

    return CommandResult(
        tuple(command),
        True,
        completed.returncode,
        completed.stdout,
        completed.stderr,
    )

import platform
import shutil
import subprocess
from typing import Optional


def collect_kernel_logs() -> tuple[str, Optional[str]]:
    if platform.system().lower() != "linux":
        return "", "Kernel Xid scanning is available on Linux only"

    commands: list[list[str]] = []

    if shutil.which("journalctl"):
        commands.append(
            [
                "journalctl",
                "-k",
                "--no-pager",
                "-o",
                "short-iso",
            ]
        )

    if shutil.which("dmesg"):
        commands.append(
            [
                "dmesg",
                "--color=never",
            ]
        )

    if not commands:
        return "", "Neither journalctl nor dmesg is available"

    errors: list[str] = []

    for command in commands:
        try:
            result = subprocess.run(
                command,
                capture_output=True,
                text=True,
                timeout=15,
                check=False,
            )

        except subprocess.TimeoutExpired:
            errors.append(f"{command[0]} timed out")
            continue

        except OSError as exc:
            errors.append(f"{command[0]} failed: {exc}")
            continue

        if result.returncode == 0 and result.stdout.strip():
            return result.stdout, None

        message = result.stderr.strip()

        if message:
            errors.append(
                f"{command[0]}: {message}"
            )

    if errors:
        return "", "; ".join(errors)

    return "", "Kernel log collection returned no data"
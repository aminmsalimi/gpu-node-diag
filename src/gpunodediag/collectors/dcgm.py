import json
import shutil
import subprocess
from typing import Any, Optional

from gpunodediag.models import DCGMStatus, DCGMTestResult


def _run(
    command: list[str],
    timeout: int = 20,
) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        command,
        capture_output=True,
        text=True,
        timeout=timeout,
        check=False,
    )


def _extract_json(text: str) -> Optional[Any]:
    if not text:
        return None

    start = text.find("{")
    end = text.rfind("}")

    if start == -1 or end == -1 or end <= start:
        return None

    try:
        return json.loads(text[start:end + 1])
    except json.JSONDecodeError:
        return None


def _clean_version(text: str) -> Optional[str]:
    text = text.strip()

    if not text:
        return None

    for line in text.splitlines():
        line = line.strip()

        if line:
            return line

    return None


def collect_dcgm_status() -> DCGMStatus:
    dcgmi = shutil.which("dcgmi")

    if dcgmi is None:
        return DCGMStatus(
            installed=False,
        )

    status = DCGMStatus(
        installed=True,
    )

    try:
        result = _run(
            [dcgmi, "--version"],
            timeout=10,
        )

        version_text = (
            result.stdout.strip()
            or result.stderr.strip()
        )

        status.version = _clean_version(version_text)

    except Exception as exc:
        status.error = (
            f"Unable to query DCGM version: {exc}"
        )

    try:
        discovery = _run(
            [
                dcgmi,
                "discovery",
                "--list",
            ],
            timeout=15,
        )

        if discovery.returncode == 0:
            status.hostengine_reachable = True
            status.discovery_ok = True
        else:
            status.hostengine_reachable = False
            status.discovery_ok = False

            message = (
                discovery.stderr.strip()
                or discovery.stdout.strip()
            )

            if message:
                status.error = message

    except subprocess.TimeoutExpired:
        status.hostengine_reachable = False
        status.discovery_ok = False
        status.error = "DCGM discovery timed out"

    except Exception as exc:
        status.hostengine_reachable = False
        status.discovery_ok = False
        status.error = (
            f"DCGM discovery failed: {exc}"
        )

    return status


def _collect_tests(
    node: Any,
    results: list[DCGMTestResult],
) -> None:
    if isinstance(node, list):
        for item in node:
            _collect_tests(
                item,
                results,
            )

        return

    if not isinstance(node, dict):
        return

    name = node.get("name")
    test_results = node.get("results")
    summary = node.get("test_summary")

    if (
        isinstance(name, str)
        and isinstance(test_results, list)
    ):
        if test_results:
            for result in test_results:
                if not isinstance(result, dict):
                    continue

                status = str(
                    result.get(
                        "status",
                        "Unknown",
                    )
                )

                info = result.get("info", [])
                warnings = result.get("warnings", [])

                if isinstance(info, str):
                    info = [info]

                if not isinstance(info, list):
                    info = []

                if isinstance(warnings, str):
                    warnings = [warnings]

                if not isinstance(warnings, list):
                    warnings = []

                entity_id = result.get("entity_id")

                if not isinstance(entity_id, int):
                    entity_id = None

                results.append(
                    DCGMTestResult(
                        name=name,
                        status=status,
                        entity_group=result.get(
                            "entity_group"
                        ),
                        entity_id=entity_id,
                        info=[
                            str(item)
                            for item in info
                        ],
                        warnings=[
                            str(item)
                            for item in warnings
                        ],
                    )
                )

        elif isinstance(summary, dict):
            results.append(
                DCGMTestResult(
                    name=name,
                    status=str(
                        summary.get(
                            "status",
                            "Unknown",
                        )
                    ),
                )
            )

    for value in node.values():
        _collect_tests(
            value,
            results,
        )


def parse_dcgm_diag_json(
    text: str,
) -> list[DCGMTestResult]:
    document = _extract_json(text)

    if document is None:
        return []

    results: list[DCGMTestResult] = []

    _collect_tests(
        document,
        results,
    )

    return results


def run_dcgm_diagnostics(
    level: int = 2,
) -> tuple[list[DCGMTestResult], Optional[str]]:
    dcgmi = shutil.which("dcgmi")

    if dcgmi is None:
        return [], "DCGM is not installed"

    try:
        result = _run(
            [
                dcgmi,
                "diag",
                "--run",
                str(level),
                "--json",
            ],
            timeout=900,
        )

    except subprocess.TimeoutExpired:
        return (
            [],
            "DCGM diagnostics timed out after 15 minutes",
        )

    except Exception as exc:
        return (
            [],
            f"Unable to run DCGM diagnostics: {exc}",
        )

    combined = "\n".join(
        part
        for part in [
            result.stdout,
            result.stderr,
        ]
        if part
    )

    parsed = parse_dcgm_diag_json(
        combined,
    )

    if parsed:
        # DCGM may return a non-zero exit code specifically
        # because a diagnostic found a problem. Parsed results
        # are therefore more useful than discarding the output.
        return parsed, None

    if result.returncode != 0:
        message = (
            result.stderr.strip()
            or result.stdout.strip()
            or (
                "DCGM diagnostic exited with "
                f"code {result.returncode}"
            )
        )

        return [], message

    return (
        [],
        "DCGM diagnostic completed but returned no parseable results",
    )
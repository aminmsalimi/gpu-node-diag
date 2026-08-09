import json
import re
from datetime import datetime
from pathlib import Path
from typing import Optional

import typer

from gpunodediag.output.terminal import console
from gpunodediag.reporting.html import (
    render_html_report,
    snapshot_status,
)
from gpunodediag.reporting.snapshot import (
    collect_diagnostic_snapshot,
)


def _safe_filename(value: str) -> str:
    cleaned = re.sub(
        r"[^A-Za-z0-9_.-]+",
        "-",
        value,
    )

    return cleaned.strip(
        ".-"
    ) or "node"


def _default_output(
    snapshot: dict,
    report_format: str,
) -> Path:
    host = _safe_filename(
        snapshot.get(
            "host",
            {},
        ).get(
            "hostname",
            "node",
        )
    )

    stamp = datetime.now().strftime(
        "%Y%m%d-%H%M%S"
    )

    extension = (
        "json"
        if report_format == "json"
        else "html"
    )

    return Path(
        f"gpunodediag-{host}-{stamp}.{extension}"
    )


def report_command(
    output: Optional[Path] = typer.Option(
        None,
        "--output",
        "-o",
        help="Output file path.",
    ),
    report_format: str = typer.Option(
        "html",
        "--format",
        "-f",
        help="Report format: html or json.",
    ),
    deep: bool = typer.Option(
        False,
        "--deep",
        help=(
            "Include active DCGM Level 2 diagnostics. "
            "May take several minutes."
        ),
    ),
    gpu: Optional[int] = typer.Option(
        None,
        "--gpu",
        "-g",
        help="Report only a specific GPU index.",
    ),
) -> None:
    """
    Generate a diagnostic report or portable JSON snapshot.
    """

    report_format = (
        report_format
        .strip()
        .lower()
    )

    if report_format not in {
        "html",
        "json",
    }:
        raise typer.BadParameter(
            "Format must be 'html' or 'json'.",
            param_hint="--format",
        )

    console.print(
        "[cyan]Collecting diagnostic snapshot...[/cyan]"
    )

    if deep:
        console.print(
            "[yellow]"
            "Running DCGM Level 2 diagnostics. "
            "This may take several minutes."
            "[/yellow]"
        )

    snapshot = collect_diagnostic_snapshot(
        gpu_index=gpu,
        deep=deep,
    )

    target = (
        output
        if output is not None
        else _default_output(
            snapshot,
            report_format,
        )
    )

    target = target.expanduser()

    target.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    if report_format == "json":
        content = json.dumps(
            snapshot,
            indent=2,
            ensure_ascii=False,
        )
    else:
        content = render_html_report(
            snapshot
        )

    target.write_text(
        content,
        encoding="utf-8",
    )

    status = snapshot_status(
        snapshot
    )

    if status == "CRITICAL":
        shown_status = (
            "[bold red]CRITICAL[/bold red]"
        )
    elif status in {
        "DEGRADED",
        "WARNING",
    }:
        shown_status = (
            f"[bold yellow]{status}[/bold yellow]"
        )
    elif status == "INFO":
        shown_status = "[cyan]INFO[/cyan]"
    else:
        shown_status = (
            "[bold green]HEALTHY[/bold green]"
        )

    console.print("")
    console.print(
        f"Report status: {shown_status}"
    )

    console.print(
        "[green]Saved:[/green] "
        f"{target.resolve()}"
    )


__all__ = [
    "report_command",
]
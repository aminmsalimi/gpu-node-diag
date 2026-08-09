import time
from datetime import datetime
from typing import Optional

import typer
from rich.live import Live
from rich.panel import Panel

from gpunodediag.checks.live import run_live_diagnostics
from gpunodediag.collectors.nvidia_smi import collect_gpus
from gpunodediag.collectors.nvml import enrich_nvml_state
from gpunodediag.collectors.system import collect_host_info
from gpunodediag.output.terminal import console
from gpunodediag.output.watch import build_watch_dashboard


def _collect_snapshot(
    gpu_index: Optional[int],
):
    gpus, error = collect_gpus()

    if gpu_index is not None:
        gpus = [
            gpu
            for gpu in gpus
            if gpu.index == gpu_index
        ]

        if not gpus and error is None:
            error = (
                f"GPU index {gpu_index} was not found"
            )

    note = None

    if gpus:
        note = enrich_nvml_state(gpus)

    findings = run_live_diagnostics(
        gpus
    )

    return gpus, findings, error, note


def watch_command(
    interval: float = typer.Option(
        2.0,
        "--interval",
        "-i",
        help="Refresh interval in seconds.",
    ),
    gpu: Optional[int] = typer.Option(
        None,
        "--gpu",
        "-g",
        help="Monitor only a specific GPU index.",
    ),
) -> None:
    """
    Continuously monitor GPU telemetry and live health.
    """

    if interval < 0.5:
        raise typer.BadParameter(
            "Interval must be at least 0.5 seconds.",
            param_hint="--interval",
        )

    host = collect_host_info()

    gpus, findings, error, note = (
        _collect_snapshot(gpu)
    )

    if not gpus:
        console.print(
            Panel(
                (
                    f"[yellow]{error or 'No GPUs detected'}[/yellow]\n\n"
                    "[dim]Live monitoring requires an NVIDIA GPU "
                    "visible through nvidia-smi.[/dim]"
                ),
                title="GPUNodeDiag Watch",
                border_style="yellow",
            )
        )

        raise typer.Exit(code=1)

    sample_number = 1

    dashboard = build_watch_dashboard(
        host=host,
        gpus=gpus,
        findings=findings,
        interval=interval,
        updated_at=datetime.now().strftime(
            "%H:%M:%S"
        ),
        sample_number=sample_number,
        error=error,
        note=note,
    )

    try:
        with Live(
            dashboard,
            console=console,
            refresh_per_second=4,
            screen=False,
            transient=False,
            vertical_overflow="visible",
        ) as live:

            while True:
                time.sleep(interval)

                sample_number += 1

                (
                    gpus,
                    findings,
                    error,
                    note,
                ) = _collect_snapshot(gpu)

                dashboard = build_watch_dashboard(
                    host=host,
                    gpus=gpus,
                    findings=findings,
                    interval=interval,
                    updated_at=datetime.now().strftime(
                        "%H:%M:%S"
                    ),
                    sample_number=sample_number,
                    error=error,
                    note=note,
                )

                live.update(
                    dashboard,
                    refresh=True,
                )

    except KeyboardInterrupt:
        console.print(
            "\n[dim]GPUNodeDiag watch stopped.[/dim]"
        )
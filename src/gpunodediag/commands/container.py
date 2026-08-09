import json
from dataclasses import asdict

import typer
from rich import box
from rich.panel import Panel
from rich.table import Table

from gpunodediag.checks.container_runtime import (
    check_container_stack,
)
from gpunodediag.collectors.container_runtime import (
    collect_container_status,
)
from gpunodediag.collectors.nvidia_smi import collect_gpus
from gpunodediag.output.terminal import (
    console,
    print_findings,
)


def container_command(
    json_output: bool = typer.Option(
        False,
        "--json",
        help="Output machine-readable JSON.",
    ),
) -> None:
    """
    Diagnose NVIDIA container runtime integration.
    """

    status = collect_container_status()
    gpus, gpu_error = collect_gpus()

    findings = check_container_stack(
        status,
        gpu_count=len(gpus),
    )

    if json_output:
        typer.echo(
            json.dumps(
                {
                    "container": asdict(
                        status
                    ),
                    "gpu_count": len(gpus),
                    "gpu_error": gpu_error,
                    "findings": [
                        {
                            **asdict(item),
                            "severity": item.severity.name,
                        }
                        for item in findings
                    ],
                },
                indent=2,
            )
        )
        return

    console.print(
        Panel(
            (
                f"Platform: [bold]{status.platform}[/bold]\n"
                f"NVIDIA GPUs: [bold]{len(gpus)}[/bold]\n"
                f"nvidia-ctk: "
                + (
                    "[green]FOUND[/green]"
                    if status.nvidia_ctk
                    else "[yellow]NOT FOUND[/yellow]"
                )
                + "\n"
                f"CDI devices: [bold]{len(status.cdi_devices)}[/bold]"
            ),
            title="NVIDIA Container Stack",
            border_style="cyan",
        )
    )

    runtime_table = Table(
        title="Container Runtimes",
        box=box.ROUNDED,
    )

    runtime_table.add_column(
        "Runtime"
    )

    runtime_table.add_column(
        "Detected"
    )

    runtime_table.add_column(
        "Service"
    )

    runtime_table.add_column(
        "NVIDIA Config"
    )

    for runtime in status.runtimes:
        detected = (
            "[green]YES[/green]"
            if runtime.installed
            else "[dim]NO[/dim]"
        )

        if runtime.active is True:
            active = "[green]ACTIVE[/green]"
        elif runtime.active is False:
            active = "[yellow]INACTIVE[/yellow]"
        else:
            active = "[dim]N/A[/dim]"

        if runtime.nvidia_configured is True:
            configured = "[green]FOUND[/green]"
        elif runtime.nvidia_configured is False:
            configured = "[yellow]NOT FOUND[/yellow]"
        else:
            configured = "[dim]N/A[/dim]"

        runtime_table.add_row(
            runtime.name,
            detected,
            active,
            configured,
        )

    console.print(
        runtime_table
    )

    if status.cdi_devices:
        cdi = Table(
            title="NVIDIA CDI Devices",
            box=box.SIMPLE,
        )

        cdi.add_column(
            "Device"
        )

        for device in status.cdi_devices:
            cdi.add_row(device)

        console.print(cdi)

    if status.cdi_error:
        console.print(
            f"[yellow]CDI note: {status.cdi_error}[/yellow]"
        )

    print_findings(findings)

    for note in status.notes:
        console.print(
            f"[dim]Capability note: {note}[/dim]"
        )
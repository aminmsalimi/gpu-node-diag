import json
from dataclasses import asdict

import typer
from rich import box
from rich.panel import Panel
from rich.table import Table

from gpunodediag.checks.driver_stack import (
    check_driver_stack,
)
from gpunodediag.collectors.driver_stack import (
    collect_driver_stack,
)
from gpunodediag.output.terminal import (
    console,
    print_findings,
)


def _state(
    value: bool | None,
) -> str:
    if value is True:
        return "[green]YES[/green]"

    if value is False:
        return "[yellow]NO[/yellow]"

    return "[dim]N/A[/dim]"


def stack_command(
    json_output: bool = typer.Option(
        False,
        "--json",
        help="Output machine-readable JSON.",
    ),
) -> None:
    """
    Diagnose the NVIDIA driver and CUDA software stack.
    """

    status = collect_driver_stack()

    findings = check_driver_stack(
        status
    )

    if json_output:
        typer.echo(
            json.dumps(
                {
                    "stack": asdict(status),
                    "findings": [
                        {
                            **asdict(item),
                            "severity":
                                item.severity.name,
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
                "nvidia-smi: "
                + (
                    "[green]OK[/green]"
                    if status.nvidia_smi_ok
                    else "[red]UNAVAILABLE[/red]"
                )
                + "\n"
                f"Driver: "
                f"[bold]{status.driver_version or 'N/A'}[/bold]\n"
                f"Driver CUDA capability: "
                f"[bold]{status.driver_cuda_max or 'N/A'}[/bold]\n"
                f"CUDA Toolkit: "
                f"[bold]{status.cuda_toolkit_version or 'Not detected'}[/bold]"
            ),
            title="NVIDIA Driver / CUDA Stack",
            border_style="cyan",
        )
    )

    table = Table(
        box=box.ROUNDED,
        title="Software Stack",
    )

    table.add_column(
        "Component"
    )

    table.add_column(
        "Status"
    )

    table.add_column(
        "Version / Location"
    )

    table.add_row(
        "nvidia-smi",
        (
            "[green]OK[/green]"
            if status.nvidia_smi_ok
            else "[red]FAILED[/red]"
        ),
        status.nvidia_smi_path
        or "Not found",
    )

    table.add_row(
        "Driver",
        (
            "[green]DETECTED[/green]"
            if status.driver_version
            else "[yellow]UNKNOWN[/yellow]"
        ),
        status.driver_version
        or "N/A",
    )

    if status.platform == "Linux":
        table.add_row(
            "Kernel module",
            _state(
                status.kernel_module_loaded
            ),
            (
                (
                    status.kernel_module_version
                    or "Unknown version"
                )
                + (
                    f" ({status.kernel_module_flavor})"
                    if status.kernel_module_flavor
                    else ""
                )
            ),
        )

        table.add_row(
            "nvidia_uvm",
            _state(
                status.nvidia_uvm_loaded
            ),
            "CUDA/UVM module",
        )

        table.add_row(
            "nvidia_drm",
            _state(
                status.nvidia_drm_loaded
            ),
            "Optional/display",
        )

        table.add_row(
            "nvidia_modeset",
            _state(
                status.nvidia_modeset_loaded
            ),
            "Optional/display",
        )

        table.add_row(
            "nvidia_peermem",
            _state(
                status.nvidia_peermem_loaded
            ),
            "Optional/GPUDirect RDMA",
        )

        table.add_row(
            "Secure Boot",
            (
                "[yellow]ENABLED[/yellow]"
                if status.secure_boot_enabled
                else (
                    "[green]DISABLED[/green]"
                    if status.secure_boot_enabled is False
                    else "[dim]UNKNOWN[/dim]"
                )
            ),
            "",
        )

    table.add_row(
        "nvcc",
        (
            "[green]FOUND[/green]"
            if status.nvcc_path
            else "[dim]NOT FOUND[/dim]"
        ),
        status.nvcc_path
        or "Runtime-only node is valid",
    )

    table.add_row(
        "CUDA Toolkit",
        (
            "[green]DETECTED[/green]"
            if status.cuda_toolkit_version
            else "[dim]NOT DETECTED[/dim]"
        ),
        status.cuda_toolkit_version
        or "N/A",
    )

    table.add_row(
        "CUDA driver library",
        (
            "[green]FOUND[/green]"
            if status.cuda_driver_library
            else "[yellow]NOT FOUND[/yellow]"
        ),
        status.cuda_driver_library
        or "N/A",
    )

    table.add_row(
        "CUDA runtime library",
        (
            "[green]FOUND[/green]"
            if status.cuda_runtime_library
            else "[dim]NOT FOUND[/dim]"
        ),
        status.cuda_runtime_library
        or "N/A",
    )

    console.print(table)

    if status.toolkit_paths:
        paths = Table(
            title="CUDA Toolkit Paths",
            box=box.SIMPLE,
        )

        paths.add_column(
            "Path"
        )

        for path in status.toolkit_paths:
            paths.add_row(path)

        console.print(paths)

    print_findings(
        findings
    )

    for note in status.notes:
        console.print(
            f"[dim]Capability note: {note}[/dim]"
        )


__all__ = [
    "stack_command",
]
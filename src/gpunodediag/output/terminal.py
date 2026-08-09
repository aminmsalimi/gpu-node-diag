from rich import box
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.text import Text

from gpunodediag.models import Finding, GPUInfo, HostInfo, Severity


console = Console()


SEVERITY_STYLE = {
    Severity.INFO: "cyan",
    Severity.WARNING: "yellow",
    Severity.HIGH: "bold yellow",
    Severity.CRITICAL: "bold red",
}


def _value(value, suffix: str = "") -> str:
    if value is None:
        return "[dim]N/A[/dim]"

    return f"{value}{suffix}"


def print_banner(version: str) -> None:
    title = Text()
    title.append("GPUNodeDiag", style="bold cyan")
    title.append("\nNVIDIA GPU Node Diagnostics", style="dim")

    console.print(
        Panel(
            title,
            subtitle=f"gdiag v{version}",
            border_style="cyan",
            padding=(1, 4),
        )
    )


def print_host(host: HostInfo) -> None:
    table = Table(
        title="Node",
        box=box.SIMPLE,
        show_header=False,
        title_style="bold",
    )

    table.add_column("Field", style="dim")
    table.add_column("Value")

    table.add_row("Hostname", host.hostname)
    table.add_row("OS", f"{host.operating_system} {host.release}")
    table.add_row("Architecture", host.architecture)
    table.add_row("Python", host.python_version)

    console.print(table)


def print_gpu_error(message: str) -> None:
    console.print(
        Panel(
            f"[yellow]WARN[/yellow]  {message}\n\n"
            "[dim]GPU diagnostics require NVIDIA drivers and nvidia-smi.[/dim]",
            title="GPU Detection",
            border_style="yellow",
        )
    )


def print_gpus(gpus: list[GPUInfo]) -> None:
    table = Table(
        title="NVIDIA GPUs",
        box=box.ROUNDED,
        header_style="bold cyan",
    )

    table.add_column("GPU", justify="right")
    table.add_column("Model")
    table.add_column("Temp", justify="right")
    table.add_column("Power", justify="right")
    table.add_column("Util", justify="right")
    table.add_column("Memory", justify="right")
    table.add_column("PCIe", justify="center")
    table.add_column("MIG", justify="center")

    for gpu in gpus:
        memory = "N/A"

        if gpu.memory_used_mb is not None and gpu.memory_total_mb is not None:
            memory = f"{gpu.memory_used_mb:.0f}/{gpu.memory_total_mb:.0f} MB"

        power = "N/A"

        if gpu.power_draw_w is not None:
            if gpu.power_limit_w is not None:
                power = f"{gpu.power_draw_w:.0f}/{gpu.power_limit_w:.0f} W"
            else:
                power = f"{gpu.power_draw_w:.0f} W"

        pcie = "N/A"

        if gpu.pcie_generation and gpu.pcie_width:
            pcie = f"Gen{gpu.pcie_generation} x{gpu.pcie_width}"

        table.add_row(
            str(gpu.index),
            gpu.name,
            _value(gpu.temperature_c, " C"),
            power,
            _value(gpu.utilization_percent, "%"),
            memory,
            pcie,
            gpu.mig_mode or "N/A",
        )

    console.print(table)


def print_findings(findings: list[Finding]) -> None:
    if not findings:
        console.print(
            Panel(
                "[green]PASS[/green]  No diagnostic issues detected.",
                title="Diagnostics",
                border_style="green",
            )
        )
        return

    table = Table(
        title="Diagnostic Findings",
        box=box.ROUNDED,
    )

    table.add_column("Severity")
    table.add_column("GPU", justify="center")
    table.add_column("Finding")
    table.add_column("Details")

    for finding in findings:
        style = SEVERITY_STYLE[finding.severity]

        table.add_row(
            f"[{style}]{finding.severity.name}[/{style}]",
            (
                str(finding.gpu_index)
                if finding.gpu_index is not None
                else "-"
            ),
            finding.title,
            finding.message,
        )

    console.print(table)

    critical = sum(
        1 for item in findings if item.severity is Severity.CRITICAL
    )
    high = sum(
        1 for item in findings if item.severity is Severity.HIGH
    )
    warning = sum(
        1 for item in findings if item.severity is Severity.WARNING
    )

    if critical:
        status = "[bold red]CRITICAL[/bold red]"
        border = "red"
    elif high:
        status = "[bold yellow]DEGRADED[/bold yellow]"
        border = "yellow"
    else:
        status = "[yellow]WARNING[/yellow]"
        border = "yellow"

    console.print(
        Panel(
            f"Overall status: {status}\n\n"
            f"Critical: {critical}   High: {high}   Warnings: {warning}",
            title="Node Health",
            border_style=border,
        )
    )


def print_fabric(
    gpus,
    fabric_manager,
    p2p_matrix,
) -> None:
    from rich import box
    from rich.panel import Panel
    from rich.table import Table

    any_nvlink = any(
        gpu.nvlink_supported is True
        for gpu in gpus
    )

    any_fabric = any(
        gpu.fabric_state
        for gpu in gpus
    )

    if not any_nvlink and not any_fabric:
        console.print(
            Panel(
                "[dim]No supported NVLink fabric detected.[/dim]",
                title="GPU Fabric",
                border_style="dim",
            )
        )
        return

    table = Table(
        title="NVLink / GPU Fabric",
        box=box.ROUNDED,
        header_style="bold cyan",
    )

    table.add_column("GPU", justify="right")
    table.add_column("NVLink")
    table.add_column("Errors", justify="right")
    table.add_column("Fabric State")
    table.add_column("Fabric Status")

    for gpu in gpus:
        if gpu.nvlink_supported is True:
            links = (
                f"{gpu.nvlink_active_links}/"
                f"{gpu.nvlink_total_links} active"
            )
        elif gpu.nvlink_supported is False:
            links = "Not supported"
        else:
            links = "Unknown"

        error_total = sum(
            gpu.nvlink_error_counts.values()
        )

        table.add_row(
            str(gpu.index),
            links,
            str(error_total),
            gpu.fabric_state or "N/A",
            gpu.fabric_status or "N/A",
        )

    console.print(table)

    if fabric_manager.installed is True:
        fm_status = (
            "[green]ACTIVE[/green]"
            if fabric_manager.active
            else "[red]INACTIVE[/red]"
        )

        console.print(
            f"Fabric Manager: {fm_status}"
        )

    if p2p_matrix:
        p2p = Table(
            title="NVLink P2P",
            box=box.SIMPLE,
        )

        gpu_names = list(p2p_matrix.keys())

        p2p.add_column("")

        for name in gpu_names:
            p2p.add_column(
                name,
                justify="center",
            )

        for row_name in gpu_names:
            row = p2p_matrix[row_name]

            p2p.add_row(
                row_name,
                *[
                    row.get(column, "-")
                    for column in gpu_names
                ],
            )

        console.print(p2p)

def print_dcgm(
    status,
    results,
    deep_requested: bool,
) -> None:
    from rich import box
    from rich.panel import Panel
    from rich.table import Table

    if not status.installed:
        text = "[dim]DCGM not detected[/dim]"

        if deep_requested:
            text += (
                "\n[yellow]Deep diagnostics could not run.[/yellow]"
            )

        console.print(
            Panel(
                text,
                title="DCGM",
                border_style="dim",
            )
        )
        return

    table = Table(
        title="NVIDIA DCGM",
        box=box.ROUNDED,
        show_header=False,
    )

    table.add_column("Field", style="dim")
    table.add_column("Value")

    table.add_row(
        "Installed",
        "[green]YES[/green]",
    )

    table.add_row(
        "Version",
        status.version or "Unknown",
    )

    if status.hostengine_reachable is True:
        hostengine = "[green]REACHABLE[/green]"
    elif status.hostengine_reachable is False:
        hostengine = "[red]UNREACHABLE[/red]"
    else:
        hostengine = "Unknown"

    table.add_row(
        "Host Engine",
        hostengine,
    )

    console.print(table)

    if deep_requested:
        if not results:
            console.print(
                "[yellow]Deep diagnostic returned no test results.[/yellow]"
            )
            return

        passed = sum(
            1
            for item in results
            if item.status.lower() in {
                "pass",
                "passed",
            }
        )

        warnings = sum(
            1
            for item in results
            if item.status.lower() in {
                "warn",
                "warning",
            }
        )

        failed = sum(
            1
            for item in results
            if item.status.lower() in {
                "fail",
                "failed",
                "failure",
            }
        )

        skipped = sum(
            1
            for item in results
            if item.status.lower() in {
                "skip",
                "skipped",
                "not run",
                "not_run",
            }
        )

        diag = Table(
            title="DCGM Level 2 Diagnostics",
            box=box.SIMPLE,
        )

        diag.add_column("Test")
        diag.add_column("Entity")
        diag.add_column("Status")

        for item in results:
            entity = item.entity_group or "-"

            if item.entity_id is not None:
                entity += f" {item.entity_id}"

            state = item.status.lower()

            if state in {"pass", "passed"}:
                shown = f"[green]{item.status}[/green]"
            elif state in {"warn", "warning"}:
                shown = f"[yellow]{item.status}[/yellow]"
            elif state in {"fail", "failed", "failure"}:
                shown = f"[red]{item.status}[/red]"
            else:
                shown = f"[dim]{item.status}[/dim]"

            diag.add_row(
                item.name,
                entity,
                shown,
            )

        console.print(diag)

        console.print(
            f"DCGM summary: "
            f"[green]{passed} passed[/green], "
            f"[yellow]{warnings} warnings[/yellow], "
            f"[red]{failed} failed[/red], "
            f"[dim]{skipped} skipped[/dim]"
        )
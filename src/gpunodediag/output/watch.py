from rich import box
from rich.console import Group
from rich.panel import Panel
from rich.table import Table
from rich.text import Text

from gpunodediag.models import Finding, GPUInfo, HostInfo, Severity


def _temperature(gpu: GPUInfo) -> str:
    if gpu.temperature_c is None:
        return "[dim]N/A[/dim]"

    value = gpu.temperature_c

    if value >= 90:
        return f"[bold red]{value:.0f} C[/bold red]"

    if value >= 80:
        return f"[yellow]{value:.0f} C[/yellow]"

    return f"{value:.0f} C"


def _power(gpu: GPUInfo) -> str:
    if gpu.power_draw_w is None:
        return "[dim]N/A[/dim]"

    if gpu.power_limit_w is not None:
        return (
            f"{gpu.power_draw_w:.0f}/"
            f"{gpu.power_limit_w:.0f} W"
        )

    return f"{gpu.power_draw_w:.0f} W"


def _memory(gpu: GPUInfo) -> str:
    if (
        gpu.memory_used_mb is None
        or gpu.memory_total_mb is None
    ):
        return "[dim]N/A[/dim]"

    used = gpu.memory_used_mb / 1024
    total = gpu.memory_total_mb / 1024

    return f"{used:.1f}/{total:.1f} GiB"


def _utilization(gpu: GPUInfo) -> str:
    if gpu.utilization_percent is None:
        return "[dim]N/A[/dim]"

    return f"{gpu.utilization_percent:.0f}%"


def _pcie(gpu: GPUInfo) -> str:
    if not gpu.pcie_generation or not gpu.pcie_width:
        return "[dim]N/A[/dim]"

    return (
        f"Gen{gpu.pcie_generation} "
        f"x{gpu.pcie_width}"
    )


def _ecc(gpu: GPUInfo) -> str:
    if gpu.ecc_supported is False:
        return "[dim]N/A[/dim]"

    if gpu.ecc_supported is None:
        return "[dim]?[/dim]"

    if gpu.ecc_enabled is False:
        return "[yellow]OFF[/yellow]"

    corrected = (
        gpu.ecc_corrected_volatile
        if gpu.ecc_corrected_volatile is not None
        else 0
    )

    uncorrected = (
        gpu.ecc_uncorrected_volatile
        if gpu.ecc_uncorrected_volatile is not None
        else 0
    )

    if uncorrected > 0:
        return (
            f"C:{corrected} "
            f"[bold red]U:{uncorrected}[/bold red]"
        )

    if corrected > 0:
        return (
            f"[yellow]C:{corrected}[/yellow] "
            f"U:{uncorrected}"
        )

    return f"C:{corrected} U:{uncorrected}"


def _gpu_severity(
    gpu_index: int,
    findings: list[Finding],
) -> Severity | None:
    matches = [
        finding.severity
        for finding in findings
        if finding.gpu_index == gpu_index
    ]

    if not matches:
        return None

    return max(
        matches,
        key=lambda severity: severity.value,
    )


def _gpu_status(
    gpu_index: int,
    findings: list[Finding],
) -> str:
    severity = _gpu_severity(
        gpu_index,
        findings,
    )

    if severity is Severity.CRITICAL:
        return "[bold red]CRITICAL[/bold red]"

    if severity is Severity.HIGH:
        return "[bold yellow]HIGH[/bold yellow]"

    if severity is Severity.WARNING:
        return "[yellow]WARNING[/yellow]"

    if severity is Severity.INFO:
        return "[cyan]INFO[/cyan]"

    return "[green]OK[/green]"


def _node_status(
    findings: list[Finding],
) -> tuple[str, str]:
    severities = [
        finding.severity
        for finding in findings
    ]

    if Severity.CRITICAL in severities:
        return "CRITICAL", "red"

    if Severity.HIGH in severities:
        return "DEGRADED", "yellow"

    if Severity.WARNING in severities:
        return "WARNING", "yellow"

    return "HEALTHY", "green"


def build_watch_dashboard(
    host: HostInfo,
    gpus: list[GPUInfo],
    findings: list[Finding],
    interval: float,
    updated_at: str,
    sample_number: int,
    error: str | None = None,
    note: str | None = None,
):
    status, border = _node_status(findings)

    driver = (
        gpus[0].driver_version
        if gpus
        else "N/A"
    )

    header = Text()

    header.append(
        "GPUNodeDiag Live\n",
        style="bold cyan",
    )

    header.append("Node: ", style="dim")
    header.append(host.hostname)

    header.append("    Driver: ", style="dim")
    header.append(driver)

    header.append("    Status: ", style="dim")

    if status == "CRITICAL":
        header.append(
            status,
            style="bold red",
        )
    elif status in {"DEGRADED", "WARNING"}:
        header.append(
            status,
            style="bold yellow",
        )
    else:
        header.append(
            status,
            style="bold green",
        )

    header.append("\nRefresh: ", style="dim")
    header.append(f"{interval:g}s")

    header.append("    Sample: ", style="dim")
    header.append(str(sample_number))

    header.append("    Updated: ", style="dim")
    header.append(updated_at)

    header_panel = Panel(
        header,
        border_style=border,
    )

    gpu_table = Table(
        title="Live GPU Telemetry",
        box=box.ROUNDED,
        header_style="bold cyan",
        expand=True,
    )

    gpu_table.add_column(
        "GPU",
        justify="right",
        no_wrap=True,
    )

    gpu_table.add_column(
        "Model",
        overflow="ellipsis",
    )

    gpu_table.add_column(
        "Temp",
        justify="right",
        no_wrap=True,
    )

    gpu_table.add_column(
        "Power",
        justify="right",
        no_wrap=True,
    )

    gpu_table.add_column(
        "Util",
        justify="right",
        no_wrap=True,
    )

    gpu_table.add_column(
        "Memory",
        justify="right",
        no_wrap=True,
    )

    gpu_table.add_column(
        "PCIe",
        justify="center",
        no_wrap=True,
    )

    gpu_table.add_column(
        "ECC",
        justify="center",
        no_wrap=True,
    )

    gpu_table.add_column(
        "Status",
        justify="center",
        no_wrap=True,
    )

    for gpu in gpus:
        gpu_table.add_row(
            str(gpu.index),
            gpu.name,
            _temperature(gpu),
            _power(gpu),
            _utilization(gpu),
            _memory(gpu),
            _pcie(gpu),
            _ecc(gpu),
            _gpu_status(
                gpu.index,
                findings,
            ),
        )

    if findings:
        finding_table = Table(
            title="Active Findings",
            box=box.SIMPLE,
            expand=True,
        )

        finding_table.add_column(
            "Severity",
            no_wrap=True,
        )

        finding_table.add_column(
            "GPU",
            justify="center",
            no_wrap=True,
        )

        finding_table.add_column(
            "Finding",
        )

        visible = findings[:8]

        for finding in visible:
            if finding.severity is Severity.CRITICAL:
                severity = (
                    "[bold red]CRITICAL[/bold red]"
                )
            elif finding.severity is Severity.HIGH:
                severity = (
                    "[bold yellow]HIGH[/bold yellow]"
                )
            elif finding.severity is Severity.WARNING:
                severity = (
                    "[yellow]WARNING[/yellow]"
                )
            else:
                severity = (
                    "[cyan]INFO[/cyan]"
                )

            finding_table.add_row(
                severity,
                (
                    str(finding.gpu_index)
                    if finding.gpu_index is not None
                    else "-"
                ),
                finding.title,
            )

        if len(findings) > len(visible):
            finding_table.add_row(
                "",
                "",
                (
                    f"[dim]+ "
                    f"{len(findings) - len(visible)} "
                    f"more finding(s)[/dim]"
                ),
            )

        findings_renderable = finding_table

    else:
        findings_renderable = Panel(
            "[green]No active live findings.[/green]",
            title="Active Findings",
            border_style="green",
        )

    messages: list[str] = []

    if error:
        messages.append(
            f"[yellow]{error}[/yellow]"
        )

    if note:
        messages.append(
            f"[dim]{note}[/dim]"
        )

    messages.append(
        "[dim]Ctrl+C to stop monitoring[/dim]"
    )

    footer = Panel(
        "\n".join(messages),
        border_style="dim",
    )

    return Group(
        header_panel,
        gpu_table,
        findings_renderable,
        footer,
    )
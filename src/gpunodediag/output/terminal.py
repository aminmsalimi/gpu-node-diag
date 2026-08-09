from rich import box
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.text import Text

from gpunodediag.models import GPUInfo, HostInfo


console = Console()


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
            _value(gpu.temperature_c, "°C"),
            power,
            _value(gpu.utilization_percent, "%"),
            memory,
            pcie,
            gpu.mig_mode or "N/A",
        )

    console.print(table)

    driver_versions = sorted({gpu.driver_version for gpu in gpus})

    summary = (
        f"[green]PASS[/green]  Detected [bold]{len(gpus)}[/bold] NVIDIA GPU"
        f"{'s' if len(gpus) != 1 else ''}\n"
        f"Driver: [bold]{', '.join(driver_versions)}[/bold]"
    )

    console.print(
        Panel(
            summary,
            title="Initial Status",
            border_style="green",
        )
    )

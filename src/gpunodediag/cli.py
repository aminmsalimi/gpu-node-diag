import json
from dataclasses import asdict
from typing import Optional

import typer

from gpunodediag import __version__
from gpunodediag.commands.stack import stack_command
from gpunodediag.commands.container import container_command
from gpunodediag.commands.k8s import k8s_command
from gpunodediag.checks.engine import run_diagnostics
from gpunodediag.commands.watch import watch_command
from gpunodediag.commands.report import report_command
from gpunodediag.collectors.dcgm import (
    collect_dcgm_status,
    run_dcgm_diagnostics,
)
from gpunodediag.collectors.fabric import (
    collect_fabric_manager_status,
    collect_nvlink_p2p,
    enrich_fabric_registration,
    enrich_nvlink_state,
)
from gpunodediag.collectors.kernel_logs import collect_kernel_logs
from gpunodediag.collectors.nvidia_smi import collect_gpus
from gpunodediag.collectors.nvml import enrich_nvml_state
from gpunodediag.collectors.system import collect_host_info
from gpunodediag.collectors.xid import parse_xid_events
from gpunodediag.output.terminal import (
    console,
    print_banner,
    print_dcgm,
    print_fabric,
    print_findings,
    print_gpu_error,
    print_gpus,
    print_host,
)


app = typer.Typer(
    name="gdiag",
    help="NVIDIA GPU node diagnostics and troubleshooting.",
    add_completion=False,
    no_args_is_help=False,
)


app.command("watch")(watch_command)
app.command("report")(report_command)


app.command("container")(container_command)
app.command("k8s")(k8s_command)

app.command("stack")(stack_command)

@app.callback(invoke_without_command=True)
def run(
    ctx: typer.Context,
    gpu: Optional[int] = typer.Option(
        None,
        "--gpu",
        "-g",
        help="Inspect only a specific GPU index.",
    ),
    deep: bool = typer.Option(
        False,
        "--deep",
        help=(
            "Run active DCGM Level 2 diagnostics. "
            "May take several minutes and exercise the GPUs."
        ),
    ),
    json_output: bool = typer.Option(
        False,
        "--json",
        help="Output machine-readable JSON.",
    ),
    version: bool = typer.Option(
        False,
        "--version",
        "-V",
        is_eager=True,
        help="Show GPUNodeDiag version.",
    ),
) -> None:
    if version:
        console.print(f"GPUNodeDiag {__version__}")
        raise typer.Exit()

    if ctx.invoked_subcommand is not None:
        return

    host = collect_host_info()
    gpus, error = collect_gpus()

    if gpu is not None:
        gpus = [
            item
            for item in gpus
            if item.index == gpu
        ]

        if not gpus and error is None:
            error = f"GPU index {gpu} was not found"

    notes: list[str] = []
    xid_events = []
    p2p_matrix = {}
    dcgm_results = []

    dcgm_status = collect_dcgm_status()

    fabric_manager, fm_note = (
        collect_fabric_manager_status()
    )

    if fm_note:
        notes.append(fm_note)

    if gpus:
        nvml_note = enrich_nvml_state(gpus)

        if nvml_note:
            notes.append(nvml_note)

        nvlink_note = enrich_nvlink_state(gpus)

        if nvlink_note:
            notes.append(nvlink_note)

        fabric_note = enrich_fabric_registration(gpus)

        if fabric_note:
            notes.append(fabric_note)

        p2p_matrix, p2p_note = collect_nvlink_p2p()

        if p2p_note:
            notes.append(p2p_note)

        kernel_text, kernel_note = collect_kernel_logs()

        if kernel_note:
            notes.append(kernel_note)

        if kernel_text:
            xid_events = parse_xid_events(
                kernel_text,
                gpus,
            )

    if deep:
        dcgm_results, dcgm_note = (
            run_dcgm_diagnostics(
                level=2,
            )
        )

        if dcgm_note:
            notes.append(dcgm_note)

    findings = (
        run_diagnostics(
            gpus,
            xid_events=xid_events,
            fabric_manager=fabric_manager,
            dcgm_status=dcgm_status,
            dcgm_results=dcgm_results,
            deep_requested=deep,
        )
        if gpus
        else run_diagnostics(
            [],
            dcgm_status=dcgm_status,
            dcgm_results=dcgm_results,
            deep_requested=deep,
        )
    )

    if json_output:
        payload = {
            "tool": "GPUNodeDiag",
            "version": __version__,
            "host": asdict(host),
            "gpus": [
                asdict(item)
                for item in gpus
            ],
            "dcgm": {
                "status": asdict(dcgm_status),
                "deep_requested": deep,
                "results": [
                    asdict(item)
                    for item in dcgm_results
                ],
            },
            "fabric_manager": asdict(
                fabric_manager
            ),
            "nvlink_p2p": p2p_matrix,
            "xid_events": [
                asdict(item)
                for item in xid_events
            ],
            "findings": [
                {
                    **asdict(item),
                    "severity": item.severity.name,
                }
                for item in findings
            ],
            "notes": notes,
            "error": error,
        }

        typer.echo(
            json.dumps(
                payload,
                indent=2,
            )
        )
        return

    print_banner(__version__)
    print_host(host)

    if error:
        print_gpu_error(error)

    if gpus:
        print_gpus(gpus)

        print_fabric(
            gpus,
            fabric_manager,
            p2p_matrix,
        )

    print_dcgm(
        dcgm_status,
        dcgm_results,
        deep,
    )

    print_findings(findings)

    if notes:
        for note in notes:
            console.print(
                f"[dim]Capability note: {note}[/dim]"
            )


def main() -> None:
    app()


if __name__ == "__main__":
    main()
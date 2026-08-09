import json
from dataclasses import asdict
from typing import Optional

import typer

from gpunodediag import __version__
from gpunodediag.checks.engine import run_diagnostics
from gpunodediag.commands.container import container_command
from gpunodediag.commands.k8s import k8s_command
from gpunodediag.commands.report import report_command
from gpunodediag.commands.stack import stack_command
from gpunodediag.commands.watch import watch_command
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
from gpunodediag.models import Severity
from gpunodediag.output.progress import ScanProgress
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


def _capability_skip(
    note: str | None,
) -> bool:
    if not note:
        return False

    value = note.lower()

    return any(
        phrase in value
        for phrase in (
            "linux only",
            "linux-only",
            "available on linux",
            "not supported",
            "unsupported",
        )
    )


def _highest_severity(
    findings,
):
    if not findings:
        return None

    return max(
        (
            finding.severity
            for finding in findings
        ),
        key=lambda severity: severity.value,
    )


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
        console.print(
            f"GPUNodeDiag {__version__}"
        )

        raise typer.Exit()

    if ctx.invoked_subcommand is not None:
        return

    progress = None

    if not json_output:
        print_banner(
            __version__
        )

        progress = ScanProgress(
            console=console,
            deep=deep,
        )

        progress.start()

    # --------------------------------------------------------
    # Host
    # --------------------------------------------------------

    if progress:
        progress.checking(
            "host",
            "Reading operating system and node metadata",
        )

    host = collect_host_info()

    if progress:
        progress.pass_(
            "host",
            host.hostname,
        )

    # --------------------------------------------------------
    # GPU discovery
    # --------------------------------------------------------

    if progress:
        progress.checking(
            "gpu",
            "Querying nvidia-smi",
        )

    gpus, error = collect_gpus()

    if gpu is not None:
        gpus = [
            item
            for item in gpus
            if item.index == gpu
        ]

        if not gpus and error is None:
            error = (
                f"GPU index {gpu} was not found"
            )

    if progress:
        if gpus:
            if len(gpus) == 1:
                gpu_detail = (
                    f"GPU {gpus[0].index}: "
                    f"{gpus[0].name}"
                )
            else:
                gpu_detail = (
                    f"{len(gpus)} NVIDIA GPUs detected"
                )

            progress.pass_(
                "gpu",
                gpu_detail,
            )

        else:
            progress.fail(
                "gpu",
                error
                or "No NVIDIA GPUs detected",
            )

    notes: list[str] = []
    xid_events = []
    p2p_matrix = {}
    dcgm_results = []

    # --------------------------------------------------------
    # DCGM
    # --------------------------------------------------------

    if progress:
        progress.checking(
            "dcgm",
            "Checking dcgmi and hostengine",
        )

    dcgm_status = collect_dcgm_status()

    if progress:
        if not dcgm_status.installed:
            progress.skip(
                "dcgm",
                "DCGM not installed (optional)",
            )

        elif (
            dcgm_status.hostengine_reachable
            is False
        ):
            progress.warning(
                "dcgm",
                "Installed, hostengine unreachable",
            )

        else:
            detail = (
                dcgm_status.version
                or "DCGM detected"
            )

            progress.pass_(
                "dcgm",
                detail,
            )

    # --------------------------------------------------------
    # Fabric Manager
    # --------------------------------------------------------

    if progress:
        progress.checking(
            "fabric_manager",
            "Checking NVIDIA Fabric Manager",
        )

    fabric_manager, fm_note = (
        collect_fabric_manager_status()
    )

    if fm_note:
        notes.append(
            fm_note
        )

    if progress:
        if (
            fabric_manager.installed
            is True
        ):
            if (
                fabric_manager.active
                is False
            ):
                progress.warning(
                    "fabric_manager",
                    "Installed but inactive",
                )
            else:
                progress.pass_(
                    "fabric_manager",
                    "Service active",
                )

        elif _capability_skip(
            fm_note
        ):
            progress.skip(
                "fabric_manager",
                fm_note
                or "Not applicable",
            )

        else:
            progress.skip(
                "fabric_manager",
                "Not installed / not required",
            )

    # --------------------------------------------------------
    # NVML / ECC
    # --------------------------------------------------------

    if progress:
        progress.checking(
            "nvml",
            "Reading NVML telemetry, ECC and clock state",
        )

    if gpus:
        nvml_note = enrich_nvml_state(
            gpus
        )

        if nvml_note:
            notes.append(
                nvml_note
            )

        if progress:
            if nvml_note:
                if _capability_skip(
                    nvml_note
                ):
                    progress.skip(
                        "nvml",
                        nvml_note,
                    )
                else:
                    progress.warning(
                        "nvml",
                        nvml_note,
                    )
            else:
                ecc_devices = sum(
                    1
                    for item in gpus
                    if item.ecc_supported
                )

                detail = (
                    "Telemetry collected"
                )

                if ecc_devices:
                    detail += (
                        f" • ECC on "
                        f"{ecc_devices} GPU(s)"
                    )

                progress.pass_(
                    "nvml",
                    detail,
                )

    elif progress:
        progress.skip(
            "nvml",
            "No GPU available",
        )

    # --------------------------------------------------------
    # NVLink / Fabric
    # --------------------------------------------------------

    if progress:
        progress.checking(
            "fabric",
            "Inspecting NVLink and GPU fabric",
        )

    if gpus:
        nvlink_note = enrich_nvlink_state(
            gpus
        )

        if nvlink_note:
            notes.append(
                nvlink_note
            )

        fabric_note = (
            enrich_fabric_registration(
                gpus
            )
        )

        if fabric_note:
            notes.append(
                fabric_note
            )

        p2p_matrix, p2p_note = (
            collect_nvlink_p2p()
        )

        if p2p_note:
            notes.append(
                p2p_note
            )

        if progress:
            fabric_notes = [
                note
                for note in (
                    nvlink_note,
                    fabric_note,
                    p2p_note,
                )
                if note
            ]

            any_nvlink = any(
                item.nvlink_supported
                is True
                for item in gpus
            )

            any_fabric = any(
                bool(
                    item.fabric_state
                )
                for item in gpus
            )

            if (
                not any_nvlink
                and not any_fabric
            ):
                progress.skip(
                    "fabric",
                    "NVLink/NVSwitch fabric not present",
                )

            elif any(
                not _capability_skip(
                    note
                )
                for note
                in fabric_notes
            ):
                progress.warning(
                    "fabric",
                    fabric_notes[0],
                )

            else:
                active = sum(
                    item.nvlink_active_links
                    for item in gpus
                )

                total = sum(
                    item.nvlink_total_links
                    for item in gpus
                )

                detail = (
                    "Fabric detected"
                )

                if total:
                    detail = (
                        f"{active}/{total} "
                        "NVLink links active"
                    )

                progress.pass_(
                    "fabric",
                    detail,
                )

    elif progress:
        progress.skip(
            "fabric",
            "No GPU available",
        )

    # --------------------------------------------------------
    # Kernel logs / Xid
    # --------------------------------------------------------

    if progress:
        progress.checking(
            "xid",
            "Scanning NVIDIA kernel events",
        )

    if gpus:
        kernel_text, kernel_note = (
            collect_kernel_logs()
        )

        if kernel_note:
            notes.append(
                kernel_note
            )

        if kernel_text:
            xid_events = parse_xid_events(
                kernel_text,
                gpus,
            )

        if progress:
            if kernel_note:
                if _capability_skip(
                    kernel_note
                ):
                    progress.skip(
                        "xid",
                        kernel_note,
                    )
                else:
                    progress.warning(
                        "xid",
                        kernel_note,
                    )

            elif xid_events:
                progress.warning(
                    "xid",
                    (
                        f"{len(xid_events)} "
                        "NVIDIA Xid event(s) found"
                    ),
                )

            else:
                progress.pass_(
                    "xid",
                    "No Xid events detected",
                )

    elif progress:
        progress.skip(
            "xid",
            "No GPU available",
        )

    # --------------------------------------------------------
    # Deep DCGM
    # --------------------------------------------------------

    if deep:
        if progress:
            progress.checking(
                "dcgm_deep",
                "Running active DCGM Level 2 diagnostics",
            )

        dcgm_results, dcgm_note = (
            run_dcgm_diagnostics(
                level=2,
            )
        )

        if dcgm_note:
            notes.append(
                dcgm_note
            )

        if progress:
            if not dcgm_status.installed:
                progress.skip(
                    "dcgm_deep",
                    "DCGM is not installed",
                )

            elif dcgm_note:
                progress.warning(
                    "dcgm_deep",
                    dcgm_note,
                )

            else:
                failed_dcgm = [
                    result
                    for result in dcgm_results
                    if result.status.lower()
                    in {
                        "fail",
                        "failed",
                        "failure",
                    }
                ]

                warning_dcgm = [
                    result
                    for result in dcgm_results
                    if result.status.lower()
                    in {
                        "warn",
                        "warning",
                    }
                ]

                if failed_dcgm:
                    progress.fail(
                        "dcgm_deep",
                        (
                            f"{len(failed_dcgm)} "
                            "DCGM test(s) failed"
                        ),
                    )

                elif warning_dcgm:
                    progress.warning(
                        "dcgm_deep",
                        (
                            f"{len(warning_dcgm)} "
                            "DCGM warning(s)"
                        ),
                    )

                else:
                    progress.pass_(
                        "dcgm_deep",
                        (
                            f"{len(dcgm_results)} "
                            "test result(s) collected"
                        ),
                    )

    # --------------------------------------------------------
    # Diagnostic rules
    # --------------------------------------------------------

    if progress:
        progress.checking(
            "analysis",
            "Correlating evidence and severity",
        )

    findings = run_diagnostics(
        gpus,
        xid_events=xid_events,
        fabric_manager=fabric_manager,
        dcgm_status=dcgm_status,
        dcgm_results=dcgm_results,
        deep_requested=deep,
    )

    highest = _highest_severity(
        findings
    )

    if progress:
        critical = sum(
            1
            for item in findings
            if item.severity
            is Severity.CRITICAL
        )

        high = sum(
            1
            for item in findings
            if item.severity
            is Severity.HIGH
        )

        warnings = sum(
            1
            for item in findings
            if item.severity
            is Severity.WARNING
        )

        info = sum(
            1
            for item in findings
            if item.severity
            is Severity.INFO
        )

        if highest is Severity.CRITICAL:
            progress.fail(
                "analysis",
                (
                    f"{critical} critical • "
                    f"{high} high • "
                    f"{warnings} warning"
                ),
            )

            progress.set_overall(
                "CRITICAL",
                "Immediate investigation recommended",
            )

        elif highest is Severity.HIGH:
            progress.fail(
                "analysis",
                (
                    f"{high} high • "
                    f"{warnings} warning"
                ),
            )

            progress.set_overall(
                "DEGRADED",
                "Significant issue detected",
            )

        elif highest is Severity.WARNING:
            progress.warning(
                "analysis",
                (
                    f"{warnings} warning(s)"
                ),
            )

            progress.set_overall(
                "ATTENTION",
                "Review diagnostic warnings",
            )

        else:
            if info:
                detail = (
                    f"PASS • {info} informational note(s)"
                )
            else:
                detail = (
                    "No actionable findings"
                )

            progress.pass_(
                "analysis",
                detail,
            )

            progress.set_overall(
                "PASS",
                "Node health checks completed",
            )

        progress.stop()

    # --------------------------------------------------------
    # JSON
    # --------------------------------------------------------

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
                "status": asdict(
                    dcgm_status
                ),
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
                    "severity":
                        item.severity.name,
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

    # --------------------------------------------------------
    # Detailed output
    # --------------------------------------------------------

    console.print("")

    print_host(
        host
    )

    if error:
        print_gpu_error(
            error
        )

    if gpus:
        print_gpus(
            gpus
        )

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

    print_findings(
        findings
    )

    if notes:
        console.print("")

        for note in notes:
            console.print(
                "[dim]• "
                f"{note}"
                "[/dim]"
            )


def main() -> None:
    app()


if __name__ == "__main__":
    main()
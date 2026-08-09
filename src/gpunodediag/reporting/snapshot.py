from dataclasses import asdict
from datetime import datetime, timezone
from typing import Any, Optional

from gpunodediag import __version__
from gpunodediag.checks.engine import run_diagnostics
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


def _finding_dict(finding) -> dict[str, Any]:
    data = asdict(finding)
    data["severity"] = finding.severity.name
    return data


def collect_diagnostic_snapshot(
    gpu_index: Optional[int] = None,
    deep: bool = False,
) -> dict[str, Any]:
    host = collect_host_info()
    gpus, error = collect_gpus()

    if gpu_index is not None:
        gpus = [
            gpu
            for gpu in gpus
            if gpu.index == gpu_index
        ]

        if not gpus and error is None:
            error = f"GPU index {gpu_index} was not found"

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
            run_dcgm_diagnostics(level=2)
        )

        if dcgm_note:
            notes.append(dcgm_note)

    findings = run_diagnostics(
        gpus,
        xid_events=xid_events,
        fabric_manager=fabric_manager,
        dcgm_status=dcgm_status,
        dcgm_results=dcgm_results,
        deep_requested=deep,
    )

    return {
        "schema_version": 1,
        "tool": "GPUNodeDiag",
        "version": __version__,
        "generated_at": datetime.now(
            timezone.utc
        ).isoformat(),
        "host": asdict(host),
        "gpus": [
            asdict(gpu)
            for gpu in gpus
        ],
        "dcgm": {
            "status": asdict(dcgm_status),
            "deep_requested": deep,
            "results": [
                asdict(result)
                for result in dcgm_results
            ],
        },
        "fabric_manager": asdict(
            fabric_manager
        ),
        "nvlink_p2p": p2p_matrix,
        "xid_events": [
            asdict(event)
            for event in xid_events
        ],
        "findings": [
            _finding_dict(finding)
            for finding in findings
        ],
        "notes": notes,
        "error": error,
    }
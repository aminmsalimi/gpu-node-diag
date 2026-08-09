from gpunodediag.models import (
    FabricManagerStatus,
    Finding,
    GPUInfo,
    Severity,
)


def _fabric_is_relevant(gpus: list[GPUInfo]) -> bool:
    for gpu in gpus:
        if gpu.fabric_state and gpu.fabric_state.lower() not in {
            "not supported",
            "n/a",
        }:
            return True

    return False


def check_gpu_fabric(gpu: GPUInfo) -> list[Finding]:
    findings: list[Finding] = []

    if (
        gpu.nvlink_supported is True
        and gpu.nvlink_inactive_links
    ):
        findings.append(
            Finding(
                code="NVLINK_INACTIVE_LINKS",
                severity=Severity.HIGH,
                title="Inactive NVLink detected",
                message=(
                    f"GPU {gpu.index} has "
                    f"{len(gpu.nvlink_inactive_links)} inactive "
                    "NVLink link(s)."
                ),
                gpu_index=gpu.index,
                evidence={
                    "total_links": gpu.nvlink_total_links,
                    "active_links": gpu.nvlink_active_links,
                    "inactive_links": gpu.nvlink_inactive_links,
                },
                recommendations=[
                    "Inspect NVLink connectivity and topology.",
                    "Review NVIDIA Xid events, especially Xid 74.",
                    "Run DCGM fabric diagnostics if available.",
                    "Check Fabric Manager on NVSwitch-based systems.",
                ],
            )
        )

    error_total = sum(
        gpu.nvlink_error_counts.values()
    )

    if error_total > 0:
        findings.append(
            Finding(
                code="NVLINK_ERRORS_DETECTED",
                severity=Severity.WARNING,
                title="NVLink error counters detected",
                message=(
                    f"GPU {gpu.index} reports "
                    f"{error_total} NVLink error event(s)."
                ),
                gpu_index=gpu.index,
                evidence={
                    "nvlink_error_counts": gpu.nvlink_error_counts,
                },
                recommendations=[
                    "Monitor whether NVLink error counters continue increasing.",
                    "Review kernel logs for Xid 74 or related fabric errors.",
                    "Run DCGM NVLink/fabric diagnostics if available.",
                ],
            )
        )

    if gpu.fabric_state:
        state = gpu.fabric_state.strip().lower()

        if state not in {
            "completed",
            "not supported",
            "n/a",
        }:
            findings.append(
                Finding(
                    code="GPU_FABRIC_NOT_READY",
                    severity=Severity.HIGH,
                    title="GPU fabric registration incomplete",
                    message=(
                        f"GPU {gpu.index} fabric state is "
                        f"'{gpu.fabric_state}'."
                    ),
                    gpu_index=gpu.index,
                    evidence={
                        "fabric_state": gpu.fabric_state,
                        "fabric_status": gpu.fabric_status,
                    },
                    recommendations=[
                        "Check NVIDIA Fabric Manager status.",
                        "Review Fabric Manager and NVIDIA kernel logs.",
                        "Verify all expected NVLinks are active.",
                    ],
                )
            )

    if gpu.fabric_status:
        status = gpu.fabric_status.strip().lower()

        if status not in {
            "success",
            "nvml_success",
            "not supported",
            "n/a",
        }:
            findings.append(
                Finding(
                    code="GPU_FABRIC_ERROR",
                    severity=Severity.HIGH,
                    title="GPU fabric reported an error",
                    message=(
                        f"GPU {gpu.index} fabric status is "
                        f"'{gpu.fabric_status}'."
                    ),
                    gpu_index=gpu.index,
                    evidence={
                        "fabric_state": gpu.fabric_state,
                        "fabric_status": gpu.fabric_status,
                    },
                    recommendations=[
                        "Check NVIDIA Fabric Manager.",
                        "Review NVSwitch and NVLink health.",
                        "Run DCGM fabric diagnostics.",
                    ],
                )
            )

    return findings


def check_fabric_manager(
    gpus: list[GPUInfo],
    status: FabricManagerStatus | None,
) -> list[Finding]:
    if status is None:
        return []

    if not _fabric_is_relevant(gpus):
        return []

    if status.installed is False:
        return [
            Finding(
                code="FABRIC_MANAGER_MISSING",
                severity=Severity.HIGH,
                title="NVIDIA Fabric Manager not installed",
                message=(
                    "The GPU fabric appears to require Fabric Manager, "
                    "but the service is not installed."
                ),
                evidence={
                    "load_state": status.load_state,
                },
                recommendations=[
                    "Verify the platform requires NVIDIA Fabric Manager.",
                    "Install the Fabric Manager version matching the NVIDIA driver.",
                ],
            )
        ]

    if (
        status.installed is True
        and status.active is False
    ):
        return [
            Finding(
                code="FABRIC_MANAGER_INACTIVE",
                severity=Severity.HIGH,
                title="NVIDIA Fabric Manager is not running",
                message=(
                    "The GPU fabric is present but "
                    "nvidia-fabricmanager is not active."
                ),
                evidence={
                    "load_state": status.load_state,
                    "active_state": status.active_state,
                },
                recommendations=[
                    "Inspect nvidia-fabricmanager service logs.",
                    "Verify driver and Fabric Manager versions are compatible.",
                ],
            )
        ]

    return []
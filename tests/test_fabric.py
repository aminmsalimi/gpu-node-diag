from gpunodediag.checks.fabric import (
    check_fabric_manager,
    check_gpu_fabric,
)
from gpunodediag.models import (
    FabricManagerStatus,
    GPUInfo,
    Severity,
)


def make_gpu(**overrides):
    values = {
        "index": 0,
        "name": "NVIDIA H100 80GB HBM3",
        "uuid": "GPU-test",
        "driver_version": "580.0",
        "pci_bus_id": "00000000:41:00.0",
    }

    values.update(overrides)

    return GPUInfo(**values)


def test_unsupported_nvlink_is_not_an_error():
    gpu = make_gpu(
        nvlink_supported=False,
    )

    assert check_gpu_fabric(gpu) == []


def test_inactive_nvlink_is_high():
    gpu = make_gpu(
        nvlink_supported=True,
        nvlink_total_links=18,
        nvlink_active_links=17,
        nvlink_inactive_links=[7],
    )

    findings = check_gpu_fabric(gpu)

    assert any(
        item.code == "NVLINK_INACTIVE_LINKS"
        and item.severity is Severity.HIGH
        for item in findings
    )


def test_nvlink_errors_are_warning():
    gpu = make_gpu(
        nvlink_supported=True,
        nvlink_total_links=18,
        nvlink_active_links=18,
        nvlink_error_counts={
            "replay": 3,
        },
    )

    findings = check_gpu_fabric(gpu)

    assert any(
        item.code == "NVLINK_ERRORS_DETECTED"
        and item.severity is Severity.WARNING
        for item in findings
    )


def test_incomplete_fabric_is_high():
    gpu = make_gpu(
        fabric_state="In Progress",
        fabric_status="Success",
    )

    findings = check_gpu_fabric(gpu)

    assert any(
        item.code == "GPU_FABRIC_NOT_READY"
        and item.severity is Severity.HIGH
        for item in findings
    )


def test_fabric_manager_inactive_is_high_when_relevant():
    gpu = make_gpu(
        fabric_state="Completed",
        fabric_status="Success",
    )

    fm = FabricManagerStatus(
        installed=True,
        active=False,
        load_state="loaded",
        active_state="inactive",
    )

    findings = check_fabric_manager(
        [gpu],
        fm,
    )

    assert any(
        item.code == "FABRIC_MANAGER_INACTIVE"
        and item.severity is Severity.HIGH
        for item in findings
    )


def test_missing_fabric_manager_not_flagged_on_normal_gpu():
    gpu = make_gpu(
        nvlink_supported=False,
        fabric_state="Not supported",
    )

    fm = FabricManagerStatus(
        installed=False,
        active=False,
        load_state="not-found",
        active_state="inactive",
    )

    assert check_fabric_manager(
        [gpu],
        fm,
    ) == []
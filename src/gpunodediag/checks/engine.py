from gpunodediag.checks.anomalies import check_temperature_outliers
from gpunodediag.checks.ecc import check_ecc
from gpunodediag.checks.fabric import (
    check_fabric_manager,
    check_gpu_fabric,
)
from gpunodediag.checks.pcie import check_pcie
from gpunodediag.checks.power import check_power_and_slowdown
from gpunodediag.checks.thermal import check_temperature
from gpunodediag.checks.xid import check_xid_events
from gpunodediag.models import (
    FabricManagerStatus,
    Finding,
    GPUInfo,
    XidEvent,
)


def run_diagnostics(
    gpus: list[GPUInfo],
    xid_events: list[XidEvent] | None = None,
    fabric_manager: FabricManagerStatus | None = None,
) -> list[Finding]:
    findings: list[Finding] = []

    for gpu in gpus:
        findings.extend(check_temperature(gpu))
        findings.extend(check_pcie(gpu))
        findings.extend(check_power_and_slowdown(gpu))
        findings.extend(check_ecc(gpu))
        findings.extend(check_gpu_fabric(gpu))

    findings.extend(check_temperature_outliers(gpus))

    findings.extend(
        check_fabric_manager(
            gpus,
            fabric_manager,
        )
    )

    if xid_events:
        findings.extend(check_xid_events(xid_events))

    return sorted(
        findings,
        key=lambda finding: finding.severity.value,
        reverse=True,
    )
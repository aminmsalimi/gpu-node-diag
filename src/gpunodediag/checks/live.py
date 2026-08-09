from gpunodediag.checks.anomalies import check_temperature_outliers
from gpunodediag.checks.ecc import check_ecc
from gpunodediag.checks.pcie import check_pcie
from gpunodediag.checks.power import check_power_and_slowdown
from gpunodediag.checks.thermal import check_temperature
from gpunodediag.models import Finding, GPUInfo


def run_live_diagnostics(
    gpus: list[GPUInfo],
) -> list[Finding]:
    findings: list[Finding] = []

    for gpu in gpus:
        findings.extend(check_temperature(gpu))
        findings.extend(check_pcie(gpu))
        findings.extend(check_power_and_slowdown(gpu))
        findings.extend(check_ecc(gpu))

    findings.extend(
        check_temperature_outliers(gpus)
    )

    return sorted(
        findings,
        key=lambda finding: finding.severity.value,
        reverse=True,
    )
from gpunodediag.checks.anomalies import check_temperature_outliers
from gpunodediag.checks.pcie import check_pcie
from gpunodediag.checks.thermal import check_temperature
from gpunodediag.models import Finding, GPUInfo


def run_diagnostics(gpus: list[GPUInfo]) -> list[Finding]:
    findings: list[Finding] = []

    for gpu in gpus:
        findings.extend(check_temperature(gpu))
        findings.extend(check_pcie(gpu))

    findings.extend(check_temperature_outliers(gpus))

    return sorted(
        findings,
        key=lambda finding: finding.severity.value,
        reverse=True,
    )

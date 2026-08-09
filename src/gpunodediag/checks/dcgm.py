from gpunodediag.models import (
    DCGMStatus,
    DCGMTestResult,
    Finding,
    Severity,
)


def check_dcgm_status(
    status: DCGMStatus,
    deep_requested: bool = False,
) -> list[Finding]:
    findings: list[Finding] = []

    if not status.installed:
        if deep_requested:
            findings.append(
                Finding(
                    code="DCGM_NOT_INSTALLED",
                    severity=Severity.WARNING,
                    title="DCGM unavailable",
                    message=(
                        "Deep diagnostics were requested but "
                        "NVIDIA DCGM is not installed."
                    ),
                    recommendations=[
                        "Install the NVIDIA Data Center GPU Manager package.",
                        "Ensure the DCGM package matches the CUDA/driver environment.",
                    ],
                )
            )

        return findings

    if status.hostengine_reachable is False:
        findings.append(
            Finding(
                code="DCGM_HOSTENGINE_UNREACHABLE",
                severity=Severity.WARNING,
                title="DCGM host engine unavailable",
                message=(
                    "dcgmi is installed but could not communicate "
                    "with the NVIDIA DCGM host engine."
                ),
                evidence={
                    "error": status.error,
                },
                recommendations=[
                    "Check the nvidia-dcgm service or nv-hostengine process.",
                    "Review DCGM service logs.",
                    "Verify driver and DCGM compatibility.",
                ],
            )
        )

    return findings


def check_dcgm_results(
    results: list[DCGMTestResult],
) -> list[Finding]:
    findings: list[Finding] = []

    for result in results:
        state = result.status.strip().lower()

        if state in {
            "pass",
            "passed",
            "skip",
            "skipped",
            "not run",
            "not_run",
        }:
            continue

        if state in {
            "warn",
            "warning",
        }:
            severity = Severity.WARNING
        elif state in {
            "fail",
            "failed",
            "failure",
        }:
            severity = Severity.HIGH
        else:
            continue

        entity = ""

        if result.entity_group is not None:
            entity = result.entity_group

            if result.entity_id is not None:
                entity += f" {result.entity_id}"

        message = (
            f"DCGM test '{result.name}' returned "
            f"status '{result.status}'."
        )

        if entity:
            message += f" Affected entity: {entity}."

        findings.append(
            Finding(
                code=(
                    "DCGM_"
                    + result.name.upper()
                    .replace(" ", "_")
                    .replace("-", "_")
                ),
                severity=severity,
                title=f"DCGM {result.name} diagnostic",
                message=message,
                evidence={
                    "test": result.name,
                    "status": result.status,
                    "entity_group": result.entity_group,
                    "entity_id": result.entity_id,
                    "info": result.info,
                    "warnings": result.warnings,
                },
                recommendations=[
                    "Review the DCGM diagnostic details.",
                    "Correlate this result with GPUNodeDiag findings.",
                    "Investigate the affected GPU before returning it to service if the failure persists.",
                ],
            )
        )

    return findings
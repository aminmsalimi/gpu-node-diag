from gpunodediag.models import Finding, GPUInfo, Severity


def check_ecc(gpu: GPUInfo) -> list[Finding]:
    findings: list[Finding] = []

    if gpu.ecc_supported is False:
        return findings

    if gpu.ecc_supported is True and gpu.ecc_enabled is False:
        findings.append(
            Finding(
                code="ECC_DISABLED",
                severity=Severity.INFO,
                title="ECC disabled",
                message=(
                    f"GPU {gpu.index} supports ECC but ECC is currently disabled."
                ),
                gpu_index=gpu.index,
                recommendations=[
                    "Confirm whether ECC being disabled is intentional.",
                ],
            )
        )

        return findings

    corrected = gpu.ecc_corrected_volatile
    uncorrected = gpu.ecc_uncorrected_volatile

    if uncorrected is not None and uncorrected > 0:
        findings.append(
            Finding(
                code="ECC_UNCORRECTED_ERRORS",
                severity=Severity.CRITICAL,
                title="Uncorrectable ECC errors detected",
                message=(
                    f"GPU {gpu.index} reports {uncorrected} "
                    "volatile uncorrectable ECC error(s)."
                ),
                gpu_index=gpu.index,
                evidence={
                    "uncorrectable_volatile": uncorrected,
                    "corrected_volatile": corrected,
                },
                recommendations=[
                    "Drain workloads from this GPU if possible.",
                    "Review NVIDIA Xid and kernel events.",
                    "Run extended DCGM memory diagnostics.",
                    "Investigate GPU memory health before returning the GPU to service.",
                ],
            )
        )

    if corrected is not None and corrected > 0:
        findings.append(
            Finding(
                code="ECC_CORRECTED_ERRORS",
                severity=Severity.WARNING,
                title="Corrected ECC errors detected",
                message=(
                    f"GPU {gpu.index} reports {corrected} "
                    "volatile corrected ECC error(s)."
                ),
                gpu_index=gpu.index,
                evidence={
                    "corrected_volatile": corrected,
                    "uncorrectable_volatile": uncorrected,
                },
                recommendations=[
                    "Monitor whether the corrected ECC count continues increasing.",
                    "Review DCGM and kernel events for additional memory warnings.",
                ],
            )
        )

    return findings
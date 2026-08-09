from gpunodediag.models import Finding, GPUInfo, Severity


def _to_int(value: str | None) -> int | None:
    if value is None:
        return None

    try:
        return int(value)
    except ValueError:
        return None


def check_pcie(gpu: GPUInfo) -> list[Finding]:
    findings: list[Finding] = []

    current_width = _to_int(gpu.pcie_width)
    max_width = _to_int(gpu.pcie_width_max)

    current_gen = _to_int(gpu.pcie_generation)
    max_gen = _to_int(gpu.pcie_generation_max)

    if (
        current_width is not None
        and max_width is not None
        and current_width < max_width
    ):
        severity = Severity.WARNING

        if current_width <= max_width / 2:
            severity = Severity.HIGH

        findings.append(
            Finding(
                code="PCIE_WIDTH_DEGRADED",
                severity=severity,
                title="PCIe link width degraded",
                message=(
                    f"GPU {gpu.index} is operating at x{current_width} "
                    f"but supports x{max_width}."
                ),
                gpu_index=gpu.index,
                evidence={
                    "current_width": current_width,
                    "maximum_width": max_width,
                },
                recommendations=[
                    "Inspect the PCIe slot and riser configuration.",
                    "Check BIOS PCIe and bifurcation settings.",
                    "Compare the GPU slot with healthy GPUs in the node.",
                ],
            )
        )

    # PCIe generation may downshift while idle due to power management.
    # Only flag it while the GPU is under meaningful load.
    if (
        current_gen is not None
        and max_gen is not None
        and current_gen < max_gen
        and gpu.utilization_percent is not None
        and gpu.utilization_percent >= 50
    ):
        findings.append(
            Finding(
                code="PCIE_GENERATION_DEGRADED",
                severity=Severity.WARNING,
                title="PCIe generation below maximum under load",
                message=(
                    f"GPU {gpu.index} is using PCIe Gen{current_gen} "
                    f"while Gen{max_gen} is supported."
                ),
                gpu_index=gpu.index,
                evidence={
                    "current_generation": current_gen,
                    "maximum_generation": max_gen,
                    "utilization_percent": gpu.utilization_percent,
                },
                recommendations=[
                    "Verify PCIe negotiation under sustained GPU load.",
                    "Inspect BIOS and platform PCIe configuration.",
                ],
            )
        )

    return findings

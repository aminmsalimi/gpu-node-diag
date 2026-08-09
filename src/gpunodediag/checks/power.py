from gpunodediag.models import Finding, GPUInfo, Severity


def check_power_and_slowdown(gpu: GPUInfo) -> list[Finding]:
    findings: list[Finding] = []

    if gpu.clock_event_hw_slowdown is True:
        findings.append(
            Finding(
                code="GPU_HW_SLOWDOWN_ACTIVE",
                severity=Severity.HIGH,
                title="Hardware slowdown active",
                message=(
                    f"GPU {gpu.index} reports an active NVIDIA "
                    "hardware slowdown condition."
                ),
                gpu_index=gpu.index,
                evidence={
                    "clock_event_mask": gpu.clock_event_mask,
                    "temperature_c": gpu.temperature_c,
                    "power_draw_w": gpu.power_draw_w,
                    "power_limit_w": gpu.power_limit_w,
                },
                recommendations=[
                    "Inspect GPU temperature and cooling.",
                    "Check system and GPU power delivery.",
                    "Review NVIDIA kernel and Xid events.",
                    "Run extended DCGM diagnostics if available.",
                ],
            )
        )

    if gpu.clock_event_sw_thermal_slowdown is True:
        findings.append(
            Finding(
                code="GPU_SW_THERMAL_SLOWDOWN_ACTIVE",
                severity=Severity.HIGH,
                title="Thermal slowdown active",
                message=(
                    f"GPU {gpu.index} is reducing clocks because "
                    "of a thermal condition."
                ),
                gpu_index=gpu.index,
                evidence={
                    "temperature_c": gpu.temperature_c,
                    "clock_event_mask": gpu.clock_event_mask,
                },
                recommendations=[
                    "Inspect chassis airflow and cooling.",
                    "Compare this GPU temperature with other GPUs.",
                    "Check whether thermal pressure persists after workload reduction.",
                ],
            )
        )

    if gpu.clock_event_sw_power_cap is True:
        findings.append(
            Finding(
                code="GPU_POWER_CAP_ACTIVE",
                severity=Severity.WARNING,
                title="Power limiting active",
                message=(
                    f"GPU {gpu.index} clocks are currently being "
                    "limited by the configured power policy."
                ),
                gpu_index=gpu.index,
                evidence={
                    "power_draw_w": gpu.power_draw_w,
                    "power_limit_w": gpu.power_limit_w,
                    "clock_event_mask": gpu.clock_event_mask,
                },
                recommendations=[
                    "Confirm that the configured power limit is intentional.",
                    "Check whether power limiting affects workload performance.",
                ],
            )
        )

    return findings

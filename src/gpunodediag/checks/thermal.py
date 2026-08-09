from gpunodediag.models import Finding, GPUInfo, Severity


def check_temperature(gpu: GPUInfo) -> list[Finding]:
    findings: list[Finding] = []

    if gpu.temperature_c is None:
        return findings

    temp = gpu.temperature_c

    if temp >= 90:
        findings.append(
            Finding(
                code="GPU_TEMP_CRITICAL",
                severity=Severity.CRITICAL,
                title="Critical GPU temperature",
                message=f"GPU {gpu.index} is operating at {temp:.0f} C.",
                gpu_index=gpu.index,
                evidence={
                    "temperature_c": temp,
                },
                recommendations=[
                    "Check chassis airflow and cooling.",
                    "Inspect GPU fan and thermal state.",
                    "Consider draining workloads from this GPU.",
                ],
            )
        )

    elif temp >= 85:
        findings.append(
            Finding(
                code="GPU_TEMP_HIGH",
                severity=Severity.HIGH,
                title="High GPU temperature",
                message=f"GPU {gpu.index} is operating at {temp:.0f} C.",
                gpu_index=gpu.index,
                evidence={
                    "temperature_c": temp,
                },
                recommendations=[
                    "Inspect cooling and airflow.",
                    "Check whether the workload is causing sustained thermal pressure.",
                ],
            )
        )

    elif temp >= 80:
        findings.append(
            Finding(
                code="GPU_TEMP_WARNING",
                severity=Severity.WARNING,
                title="Elevated GPU temperature",
                message=f"GPU {gpu.index} temperature is {temp:.0f} C.",
                gpu_index=gpu.index,
                evidence={
                    "temperature_c": temp,
                },
                recommendations=[
                    "Monitor GPU temperature.",
                    "Compare temperature with other GPUs in the node.",
                ],
            )
        )

    return findings

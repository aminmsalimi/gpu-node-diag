from statistics import median

from gpunodediag.models import Finding, GPUInfo, Severity


def check_temperature_outliers(gpus: list[GPUInfo]) -> list[Finding]:
    findings: list[Finding] = []

    temperatures = [
        gpu.temperature_c
        for gpu in gpus
        if gpu.temperature_c is not None
    ]

    if len(temperatures) < 2:
        return findings

    node_median = median(temperatures)

    for gpu in gpus:
        if gpu.temperature_c is None:
            continue

        delta = gpu.temperature_c - node_median

        if gpu.temperature_c >= 70 and delta >= 20:
            severity = Severity.WARNING

            if delta >= 30:
                severity = Severity.HIGH

            findings.append(
                Finding(
                    code="GPU_TEMP_OUTLIER",
                    severity=severity,
                    title="GPU temperature anomaly",
                    message=(
                        f"GPU {gpu.index} is {delta:.1f} C hotter "
                        f"than the node median."
                    ),
                    gpu_index=gpu.index,
                    evidence={
                        "temperature_c": gpu.temperature_c,
                        "node_median_c": node_median,
                        "difference_c": delta,
                    },
                    recommendations=[
                        "Compare airflow around this GPU with neighboring devices.",
                        "Inspect workload and cooling conditions.",
                    ],
                )
            )

    return findings

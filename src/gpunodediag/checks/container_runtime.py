from gpunodediag.models import (
    ContainerStatus,
    Finding,
    Severity,
)


def check_container_stack(
    status: ContainerStatus,
    gpu_count: int,
) -> list[Finding]:
    findings: list[Finding] = []

    installed_runtimes = [
        runtime
        for runtime in status.runtimes
        if runtime.installed
    ]

    if not installed_runtimes:
        findings.append(
            Finding(
                code="CONTAINER_RUNTIME_NOT_FOUND",
                severity=Severity.WARNING,
                title="No container runtime detected",
                message=(
                    "Docker, containerd, CRI-O, or Podman "
                    "was not detected."
                ),
                recommendations=[
                    "Install or expose the expected container runtime.",
                ],
            )
        )

        return findings

    if (
        gpu_count > 0
        and not status.nvidia_ctk
    ):
        findings.append(
            Finding(
                code="NVIDIA_CONTAINER_TOOLKIT_MISSING",
                severity=Severity.HIGH,
                title="NVIDIA Container Toolkit not detected",
                message=(
                    "NVIDIA GPUs are present but nvidia-ctk "
                    "was not found."
                ),
                evidence={
                    "gpu_count": gpu_count,
                },
                recommendations=[
                    "Install NVIDIA Container Toolkit.",
                    "Configure the runtime for NVIDIA GPU access.",
                ],
            )
        )

    if (
        gpu_count > 0
        and status.platform == "Linux"
        and status.missing_device_nodes
    ):
        findings.append(
            Finding(
                code="NVIDIA_DEVICE_NODES_MISSING",
                severity=Severity.HIGH,
                title="NVIDIA device nodes are missing",
                message=(
                    "Expected NVIDIA device files are missing "
                    "from /dev."
                ),
                evidence={
                    "missing": status.missing_device_nodes,
                },
                recommendations=[
                    "Verify that the NVIDIA kernel driver is loaded.",
                    "Check udev/device node creation.",
                    "Confirm nvidia-smi works on the host.",
                ],
            )
        )

    for runtime in installed_runtimes:
        if runtime.name == "podman":
            continue

        if runtime.nvidia_configured is False:
            findings.append(
                Finding(
                    code=(
                        "NVIDIA_RUNTIME_CONFIG_NOT_FOUND_"
                        + runtime.name
                        .upper()
                        .replace("-", "_")
                    ),
                    severity=Severity.WARNING,
                    title=(
                        f"NVIDIA configuration not found for "
                        f"{runtime.name}"
                    ),
                    message=(
                        "GPUNodeDiag could not identify NVIDIA "
                        "runtime configuration in the common "
                        f"{runtime.name} configuration paths."
                    ),
                    evidence={
                        "runtime": runtime.name,
                        "config_paths": runtime.config_paths,
                    },
                    recommendations=[
                        "Review NVIDIA Container Toolkit runtime configuration.",
                        "Confirm GPU access with a known-good GPU container.",
                    ],
                )
            )

    return findings
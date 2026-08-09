from gpunodediag.models import (
    Finding,
    KubernetesStatus,
    Severity,
)


def check_kubernetes_gpu_stack(
    status: KubernetesStatus,
) -> list[Finding]:
    findings: list[Finding] = []

    if not status.kubectl_installed:
        findings.append(
            Finding(
                code="KUBECTL_NOT_FOUND",
                severity=Severity.WARNING,
                title="kubectl not detected",
                message=(
                    "Kubernetes GPU diagnostics require kubectl."
                ),
                recommendations=[
                    "Install kubectl or run this command from a Kubernetes administration host.",
                ],
            )
        )

        return findings

    if status.cluster_reachable is False:
        findings.append(
            Finding(
                code="KUBERNETES_UNREACHABLE",
                severity=Severity.HIGH,
                title="Kubernetes cluster is unreachable",
                message=(
                    "kubectl is installed but the cluster "
                    "could not be queried."
                ),
                evidence={
                    "context": status.current_context,
                    "error": status.error,
                },
                recommendations=[
                    "Verify kubeconfig and current context.",
                    "Check API server connectivity.",
                    "Verify Kubernetes credentials.",
                ],
            )
        )

        return findings

    gpu_nodes = [
        node
        for node in status.nodes
        if (
            node.gpu_capacity > 0
            or node.gpu_allocatable > 0
            or node.mig_capacity
            or node.mig_allocatable
        )
    ]

    if not gpu_nodes:
        findings.append(
            Finding(
                code="K8S_NO_GPU_RESOURCES",
                severity=Severity.WARNING,
                title="No NVIDIA GPU resources advertised",
                message=(
                    "No Kubernetes node currently advertises "
                    "NVIDIA GPU or MIG resources."
                ),
                recommendations=[
                    "Verify NVIDIA device plugin or GPU Operator deployment.",
                    "Check the NVIDIA container stack on GPU worker nodes.",
                ],
            )
        )

    for node in gpu_nodes:
        if (
            node.gpu_capacity > 0
            and node.gpu_allocatable
            < node.gpu_capacity
        ):
            findings.append(
                Finding(
                    code="K8S_GPU_CAPACITY_MISMATCH",
                    severity=Severity.HIGH,
                    title="GPU capacity exceeds allocatable GPUs",
                    message=(
                        f"Node {node.name} reports "
                        f"{node.gpu_capacity} GPU(s) in capacity "
                        f"but only {node.gpu_allocatable} "
                        "allocatable."
                    ),
                    evidence={
                        "node": node.name,
                        "capacity": node.gpu_capacity,
                        "allocatable": node.gpu_allocatable,
                    },
                    recommendations=[
                        "Inspect NVIDIA device plugin logs.",
                        "Check the node for NVIDIA Xid errors.",
                        "Verify GPU health with gdiag.",
                    ],
                )
            )

    if (
        gpu_nodes
        and not status.device_plugin_pods
        and not any(
            "Unable to list cluster pods"
            in note
            for note in status.notes
        )
    ):
        findings.append(
            Finding(
                code="K8S_DEVICE_PLUGIN_NOT_FOUND",
                severity=Severity.WARNING,
                title="NVIDIA device plugin pod not detected",
                message=(
                    "GPU resources exist but GPUNodeDiag could "
                    "not find an NVIDIA device plugin pod."
                ),
                recommendations=[
                    "Verify NVIDIA device plugin or GPU Operator deployment.",
                ],
            )
        )

    for pod in status.device_plugin_pods:
        if (
            pod.phase.lower()
            != "running"
            or not pod.ready
        ):
            findings.append(
                Finding(
                    code="K8S_DEVICE_PLUGIN_UNHEALTHY",
                    severity=Severity.HIGH,
                    title="NVIDIA device plugin is unhealthy",
                    message=(
                        f"{pod.namespace}/{pod.name} is "
                        f"{pod.phase} and ready={pod.ready}."
                    ),
                    evidence={
                        "namespace": pod.namespace,
                        "pod": pod.name,
                        "phase": pod.phase,
                        "ready": pod.ready,
                        "restarts": pod.restarts,
                    },
                    recommendations=[
                        "Inspect the device plugin pod logs.",
                        "Check NVIDIA driver and NVML availability on the node.",
                        "Check for Xid events on the affected node.",
                    ],
                )
            )

        elif pod.restarts >= 5:
            findings.append(
                Finding(
                    code="K8S_DEVICE_PLUGIN_RESTARTS",
                    severity=Severity.WARNING,
                    title="NVIDIA device plugin has restarted repeatedly",
                    message=(
                        f"{pod.namespace}/{pod.name} has "
                        f"restarted {pod.restarts} times."
                    ),
                    evidence={
                        "restarts": pod.restarts,
                    },
                    recommendations=[
                        "Review device plugin logs and previous container logs.",
                    ],
                )
            )

    return findings
from gpunodediag.checks.container_runtime import (
    check_container_stack,
)
from gpunodediag.checks.kubernetes import (
    check_kubernetes_gpu_stack,
)
from gpunodediag.collectors.kubernetes import (
    parse_device_plugin_pods,
    parse_kubernetes_nodes,
)
from gpunodediag.models import (
    ContainerRuntimeInfo,
    ContainerStatus,
    KubernetesGPUNode,
    KubernetesPodStatus,
    KubernetesStatus,
    Severity,
)


def test_missing_toolkit_on_gpu_host_is_high():
    status = ContainerStatus(
        platform="Linux",
        runtimes=[
            ContainerRuntimeInfo(
                name="containerd",
                installed=True,
                nvidia_configured=True,
            )
        ],
        nvidia_ctk=False,
    )

    findings = check_container_stack(
        status,
        gpu_count=4,
    )

    assert any(
        item.code
        == "NVIDIA_CONTAINER_TOOLKIT_MISSING"
        and item.severity is Severity.HIGH
        for item in findings
    )


def test_unconfigured_runtime_is_warning():
    status = ContainerStatus(
        platform="Linux",
        runtimes=[
            ContainerRuntimeInfo(
                name="containerd",
                installed=True,
                nvidia_configured=False,
            )
        ],
        nvidia_ctk=True,
    )

    findings = check_container_stack(
        status,
        gpu_count=0,
    )

    assert any(
        item.code
        == "NVIDIA_RUNTIME_CONFIG_NOT_FOUND_CONTAINERD"
        and item.severity is Severity.WARNING
        for item in findings
    )


def test_parse_gpu_capacity_and_allocatable():
    document = {
        "items": [
            {
                "metadata": {
                    "name": "gpu-worker-01",
                },
                "status": {
                    "capacity": {
                        "nvidia.com/gpu": "4",
                    },
                    "allocatable": {
                        "nvidia.com/gpu": "3",
                    },
                },
            }
        ]
    }

    nodes = parse_kubernetes_nodes(
        document
    )

    assert len(nodes) == 1
    assert nodes[0].gpu_capacity == 4
    assert nodes[0].gpu_allocatable == 3


def test_capacity_mismatch_is_high():
    status = KubernetesStatus(
        kubectl_installed=True,
        cluster_reachable=True,
        nodes=[
            KubernetesGPUNode(
                name="gpu-worker-01",
                gpu_capacity=4,
                gpu_allocatable=3,
            )
        ],
        device_plugin_pods=[
            KubernetesPodStatus(
                namespace="gpu-operator",
                name="nvidia-device-plugin-abc",
                phase="Running",
                ready=True,
            )
        ],
    )

    findings = check_kubernetes_gpu_stack(
        status
    )

    assert any(
        item.code
        == "K8S_GPU_CAPACITY_MISMATCH"
        and item.severity is Severity.HIGH
        for item in findings
    )


def test_unhealthy_device_plugin_is_high():
    status = KubernetesStatus(
        kubectl_installed=True,
        cluster_reachable=True,
        nodes=[
            KubernetesGPUNode(
                name="gpu-worker-01",
                gpu_capacity=4,
                gpu_allocatable=4,
            )
        ],
        device_plugin_pods=[
            KubernetesPodStatus(
                namespace="gpu-operator",
                name="nvidia-device-plugin-abc",
                phase="CrashLoopBackOff",
                ready=False,
                restarts=10,
            )
        ],
    )

    findings = check_kubernetes_gpu_stack(
        status
    )

    assert any(
        item.code
        == "K8S_DEVICE_PLUGIN_UNHEALTHY"
        and item.severity is Severity.HIGH
        for item in findings
    )


def test_parse_device_plugin_pod():
    document = {
        "items": [
            {
                "metadata": {
                    "name":
                        "nvidia-device-plugin-daemonset-abc",
                    "namespace": "gpu-operator",
                },
                "spec": {
                    "containers": [
                        {
                            "name":
                                "nvidia-device-plugin",
                        }
                    ]
                },
                "status": {
                    "phase": "Running",
                    "containerStatuses": [
                        {
                            "ready": True,
                            "restartCount": 2,
                        }
                    ],
                },
            }
        ]
    }

    pods = parse_device_plugin_pods(
        document
    )

    assert len(pods) == 1
    assert pods[0].ready is True
    assert pods[0].restarts == 2


def test_healthy_kubernetes_gpu_stack():
    status = KubernetesStatus(
        kubectl_installed=True,
        cluster_reachable=True,
        nodes=[
            KubernetesGPUNode(
                name="gpu-worker-01",
                gpu_capacity=4,
                gpu_allocatable=4,
            )
        ],
        device_plugin_pods=[
            KubernetesPodStatus(
                namespace="gpu-operator",
                name="nvidia-device-plugin-abc",
                phase="Running",
                ready=True,
                restarts=0,
            )
        ],
    )

    assert (
        check_kubernetes_gpu_stack(
            status
        )
        == []
    )
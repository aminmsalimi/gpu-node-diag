import json
import shutil
import subprocess

from gpunodediag.models import (
    KubernetesGPUNode,
    KubernetesPodStatus,
    KubernetesStatus,
)


def _run(
    command: list[str],
    timeout: int = 15,
) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        command,
        capture_output=True,
        text=True,
        timeout=timeout,
        check=False,
    )


def _to_int(value) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return 0


def parse_kubernetes_nodes(
    document: dict,
) -> list[KubernetesGPUNode]:
    nodes: list[KubernetesGPUNode] = []

    for item in document.get("items", []):
        metadata = item.get("metadata", {})
        status = item.get("status", {})

        capacity = status.get("capacity", {})
        allocatable = status.get("allocatable", {})

        mig_capacity = {
            key: _to_int(value)
            for key, value in capacity.items()
            if key.startswith("nvidia.com/mig-")
        }

        mig_allocatable = {
            key: _to_int(value)
            for key, value in allocatable.items()
            if key.startswith("nvidia.com/mig-")
        }

        nodes.append(
            KubernetesGPUNode(
                name=metadata.get("name", "unknown"),
                gpu_capacity=_to_int(
                    capacity.get("nvidia.com/gpu", 0)
                ),
                gpu_allocatable=_to_int(
                    allocatable.get("nvidia.com/gpu", 0)
                ),
                mig_capacity=mig_capacity,
                mig_allocatable=mig_allocatable,
            )
        )

    return nodes


def _is_device_plugin_pod(
    pod: dict,
) -> bool:
    metadata = pod.get("metadata", {})

    name = str(
        metadata.get("name", "")
    ).lower()

    if "nvidia-device-plugin" in name:
        return True

    labels = metadata.get("labels", {})

    if any(
        "nvidia-device-plugin" in str(value).lower()
        for value in labels.values()
    ):
        return True

    containers = (
        pod.get("spec", {})
        .get("containers", [])
    )

    return any(
        "nvidia-device-plugin"
        in str(container.get("name", "")).lower()
        for container in containers
    )


def parse_device_plugin_pods(
    document: dict,
) -> list[KubernetesPodStatus]:
    pods: list[KubernetesPodStatus] = []

    for item in document.get("items", []):
        if not _is_device_plugin_pod(item):
            continue

        metadata = item.get("metadata", {})
        pod_status = item.get("status", {})

        containers = pod_status.get(
            "containerStatuses",
            [],
        )

        ready = (
            bool(containers)
            and all(
                bool(container.get("ready", False))
                for container in containers
            )
        )

        restarts = sum(
            _to_int(
                container.get("restartCount", 0)
            )
            for container in containers
        )

        pods.append(
            KubernetesPodStatus(
                namespace=metadata.get(
                    "namespace",
                    "default",
                ),
                name=metadata.get(
                    "name",
                    "unknown",
                ),
                phase=pod_status.get(
                    "phase",
                    "Unknown",
                ),
                ready=ready,
                restarts=restarts,
            )
        )

    return pods


def collect_kubernetes_status() -> KubernetesStatus:
    kubectl = shutil.which("kubectl")

    if not kubectl:
        return KubernetesStatus(
            kubectl_installed=False,
        )

    result = KubernetesStatus(
        kubectl_installed=True,
        kubectl_path=kubectl,
    )

    try:
        version = _run(
            [
                kubectl,
                "version",
                "--client",
                "-o",
                "json",
            ],
            timeout=10,
        )

        if version.returncode == 0:
            document = json.loads(
                version.stdout
            )

            result.client_version = (
                document
                .get("clientVersion", {})
                .get("gitVersion")
            )

    except Exception:
        pass

    try:
        context = _run(
            [
                kubectl,
                "config",
                "current-context",
            ],
            timeout=5,
        )

        if context.returncode == 0:
            result.current_context = (
                context.stdout.strip()
                or None
            )

    except Exception:
        pass

    try:
        nodes = _run(
            [
                kubectl,
                "get",
                "nodes",
                "-o",
                "json",
            ],
            timeout=20,
        )

    except subprocess.TimeoutExpired:
        result.cluster_reachable = False
        result.error = (
            "Timed out while querying Kubernetes nodes."
        )
        return result

    except Exception as exc:
        result.cluster_reachable = False
        result.error = str(exc)
        return result

    if nodes.returncode != 0:
        result.cluster_reachable = False
        result.error = (
            nodes.stderr.strip()
            or nodes.stdout.strip()
            or "kubectl get nodes failed"
        )
        return result

    result.cluster_reachable = True

    try:
        result.nodes = parse_kubernetes_nodes(
            json.loads(nodes.stdout)
        )

    except json.JSONDecodeError:
        result.notes.append(
            "Unable to parse kubectl node JSON."
        )

    try:
        pods = _run(
            [
                kubectl,
                "get",
                "pods",
                "-A",
                "-o",
                "json",
            ],
            timeout=20,
        )

        if pods.returncode == 0:
            result.device_plugin_pods = (
                parse_device_plugin_pods(
                    json.loads(pods.stdout)
                )
            )
        else:
            result.notes.append(
                "Unable to list cluster pods: "
                + (
                    pods.stderr.strip()
                    or "permission denied or query failed"
                )
            )

    except Exception as exc:
        result.notes.append(
            f"Unable to inspect Kubernetes pods: {exc}"
        )

    return result
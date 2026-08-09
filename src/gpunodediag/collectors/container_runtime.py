import json
import platform
import re
import shutil
import subprocess
from pathlib import Path

from gpunodediag.models import (
    ContainerRuntimeInfo,
    ContainerStatus,
)


def _run(
    command: list[str],
    timeout: int = 10,
) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        command,
        capture_output=True,
        text=True,
        timeout=timeout,
        check=False,
    )


def _systemd_active(
    unit: str,
) -> bool | None:
    if platform.system() != "Linux":
        return None

    if shutil.which("systemctl") is None:
        return None

    try:
        result = _run(
            ["systemctl", "is-active", unit],
            timeout=5,
        )

        return (
            result.returncode == 0
            and result.stdout.strip() == "active"
        )

    except Exception:
        return None


def _existing_files(
    paths: list[str],
) -> list[str]:
    return [
        path
        for path in paths
        if Path(path).is_file()
    ]


def _text_contains_nvidia(
    paths: list[str],
) -> bool:
    for path in paths:
        try:
            text = Path(path).read_text(
                encoding="utf-8",
                errors="ignore",
            ).lower()

            if (
                "nvidia-container-runtime" in text
                or 'runtime = "nvidia"' in text
                or 'default_runtime = "nvidia"' in text
                or 'default-runtime": "nvidia"' in text
            ):
                return True

        except OSError:
            continue

    return False


def _docker_configured(
    paths: list[str],
) -> bool:
    for path in paths:
        try:
            document = json.loads(
                Path(path).read_text(
                    encoding="utf-8",
                )
            )

            runtimes = document.get(
                "runtimes",
                {},
            )

            if "nvidia" in runtimes:
                return True

            if (
                document.get("default-runtime")
                == "nvidia"
            ):
                return True

        except (
            OSError,
            json.JSONDecodeError,
        ):
            pass

    return _text_contains_nvidia(paths)


def _collect_cdi(
    nvidia_ctk: str | None,
) -> tuple[list[str], str | None]:
    if not nvidia_ctk:
        return [], None

    try:
        result = _run(
            [
                nvidia_ctk,
                "cdi",
                "list",
            ],
            timeout=10,
        )

    except Exception as exc:
        return [], str(exc)

    if result.returncode != 0:
        return (
            [],
            (
                result.stderr.strip()
                or result.stdout.strip()
                or "nvidia-ctk cdi list failed"
            ),
        )

    devices: list[str] = []

    for line in result.stdout.splitlines():
        value = line.strip()

        if re.search(
            r"nvidia\.com/gpu=",
            value,
            re.IGNORECASE,
        ):
            devices.append(value)

    return devices, None


def collect_container_status() -> ContainerStatus:
    system = platform.system()

    nvidia_ctk_path = shutil.which(
        "nvidia-ctk"
    )

    cdi_devices, cdi_error = _collect_cdi(
        nvidia_ctk_path
    )

    ctk_version = None

    if nvidia_ctk_path:
        try:
            result = _run(
                [
                    nvidia_ctk_path,
                    "--version",
                ]
            )

            text = (
                result.stdout.strip()
                or result.stderr.strip()
            )

            if text:
                ctk_version = text.splitlines()[0]

        except Exception:
            pass

    runtime_specs = [
        (
            "docker",
            "docker",
            "docker",
            [
                "/etc/docker/daemon.json",
            ],
        ),
        (
            "containerd",
            "containerd",
            "containerd",
            [
                "/etc/containerd/config.toml",
                "/etc/containerd/conf.d/99-nvidia.toml",
            ],
        ),
        (
            "cri-o",
            "crio",
            "crio",
            [
                "/etc/crio/crio.conf",
                "/etc/crio/crio.conf.d/99-nvidia.conf",
                "/etc/crio/conf.d/99-nvidia.toml",
            ],
        ),
        (
            "podman",
            "podman",
            None,
            [],
        ),
    ]

    runtimes: list[ContainerRuntimeInfo] = []

    for (
        name,
        command,
        service,
        candidate_paths,
    ) in runtime_specs:

        executable = shutil.which(command)
        existing_paths = _existing_files(
            candidate_paths
        )

        if name == "docker":
            configured = (
                _docker_configured(
                    existing_paths
                )
                if executable
                else None
            )

        elif name == "podman":
            configured = (
                bool(cdi_devices)
                if executable
                else None
            )

        else:
            configured = (
                _text_contains_nvidia(
                    existing_paths
                )
                if executable
                else None
            )

        runtimes.append(
            ContainerRuntimeInfo(
                name=name,
                installed=executable is not None,
                executable=executable,
                active=(
                    _systemd_active(service)
                    if service and executable
                    else None
                ),
                nvidia_configured=configured,
                config_paths=existing_paths,
            )
        )

    device_nodes: list[str] = []
    missing_device_nodes: list[str] = []

    if system == "Linux":
        dev = Path("/dev")

        device_nodes = sorted(
            str(path)
            for path in dev.glob("nvidia*")
            if path.exists()
        )

        if not Path(
            "/dev/nvidiactl"
        ).exists():
            missing_device_nodes.append(
                "/dev/nvidiactl"
            )

        gpu_devices = [
            path
            for path in device_nodes
            if re.fullmatch(
                r"/dev/nvidia\d+",
                path,
            )
        ]

        if not gpu_devices:
            missing_device_nodes.append(
                "/dev/nvidia<N>"
            )

    notes: list[str] = []

    if system != "Linux":
        notes.append(
            "Host runtime configuration checks are Linux-focused."
        )

    return ContainerStatus(
        platform=system,
        runtimes=runtimes,
        nvidia_ctk=nvidia_ctk_path is not None,
        nvidia_ctk_version=ctk_version,
        nvidia_container_runtime=(
            shutil.which(
                "nvidia-container-runtime"
            )
            is not None
        ),
        nvidia_container_cli=(
            shutil.which(
                "nvidia-container-cli"
            )
            is not None
        ),
        device_nodes=device_nodes,
        missing_device_nodes=missing_device_nodes,
        cdi_devices=cdi_devices,
        cdi_error=cdi_error,
        notes=notes,
    )
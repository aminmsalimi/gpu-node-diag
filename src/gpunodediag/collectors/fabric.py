import platform
import shutil
import subprocess
from typing import Optional

import pynvml

from gpunodediag.models import FabricManagerStatus, GPUInfo


ERROR_COUNTERS = {
    "replay": "NVML_NVLINK_ERROR_DL_REPLAY",
    "recovery": "NVML_NVLINK_ERROR_DL_RECOVERY",
    "crc_flit": "NVML_NVLINK_ERROR_DL_CRC_FLIT",
    "crc_data": "NVML_NVLINK_ERROR_DL_CRC_DATA",
    "ecc_data": "NVML_NVLINK_ERROR_DL_ECC_DATA",
}


def _normalize_bus_id(value: str | None) -> str | None:
    if not value:
        return None

    value = value.strip().lower()

    if value.startswith("pci:"):
        value = value[4:]

    if "." in value:
        value = value.split(".", 1)[0]

    parts = value.split(":")

    if len(parts) >= 2:
        return ":".join(parts[-2:])

    return value


def enrich_nvlink_state(gpus: list[GPUInfo]) -> Optional[str]:
    if not gpus:
        return None

    try:
        pynvml.nvmlInit()
    except Exception as exc:
        return f"NVML initialization for NVLink failed: {exc}"

    errors: list[str] = []

    max_links = int(
        getattr(
            pynvml,
            "NVML_NVLINK_MAX_LINKS",
            36,
        )
    )

    valid_capability = getattr(
        pynvml,
        "NVML_NVLINK_CAP_VALID",
        5,
    )

    try:
        for gpu in gpus:
            try:
                handle = pynvml.nvmlDeviceGetHandleByUUID(gpu.uuid)
            except Exception as exc:
                errors.append(
                    f"GPU {gpu.index}: unable to get NVML handle: {exc}"
                )
                continue

            gpu.nvlink_supported = False

            for link in range(max_links):
                try:
                    valid = pynvml.nvmlDeviceGetNvLinkCapability(
                        handle,
                        link,
                        valid_capability,
                    )
                except pynvml.NVMLError_NotSupported:
                    break
                except pynvml.NVMLError_InvalidArgument:
                    continue
                except Exception:
                    continue

                if not valid:
                    continue

                gpu.nvlink_supported = True
                gpu.nvlink_total_links += 1

                try:
                    active = bool(
                        pynvml.nvmlDeviceGetNvLinkState(
                            handle,
                            link,
                        )
                    )
                except Exception:
                    active = False

                if active:
                    gpu.nvlink_active_links += 1
                else:
                    gpu.nvlink_inactive_links.append(link)

                for name, constant_name in ERROR_COUNTERS.items():
                    counter_type = getattr(
                        pynvml,
                        constant_name,
                        None,
                    )

                    if counter_type is None:
                        continue

                    try:
                        value = int(
                            pynvml.nvmlDeviceGetNvLinkErrorCounter(
                                handle,
                                link,
                                counter_type,
                            )
                        )
                    except Exception:
                        continue

                    if value:
                        gpu.nvlink_error_counts[name] = (
                            gpu.nvlink_error_counts.get(name, 0)
                            + value
                        )

    finally:
        try:
            pynvml.nvmlShutdown()
        except Exception:
            pass

    if errors:
        return "; ".join(errors)

    return None


def enrich_fabric_registration(
    gpus: list[GPUInfo],
) -> Optional[str]:
    if not gpus:
        return None

    if shutil.which("nvidia-smi") is None:
        return "nvidia-smi is unavailable for fabric registration checks"

    try:
        result = subprocess.run(
            ["nvidia-smi", "-q"],
            capture_output=True,
            text=True,
            timeout=15,
            check=False,
        )
    except Exception as exc:
        return f"Unable to query NVIDIA fabric state: {exc}"

    if result.returncode != 0:
        return (
            result.stderr.strip()
            or "nvidia-smi fabric query failed"
        )

    gpu_by_bus: dict[str, GPUInfo] = {}

    for gpu in gpus:
        bus = _normalize_bus_id(gpu.pci_bus_id)

        if bus:
            gpu_by_bus[bus] = gpu

    current_gpu: GPUInfo | None = None
    in_fabric = False
    fabric_lines_left = 0

    for raw_line in result.stdout.splitlines():
        stripped = raw_line.strip()

        if raw_line.startswith("GPU "):
            parts = stripped.split()

            if len(parts) >= 2:
                bus = _normalize_bus_id(parts[1])
                current_gpu = gpu_by_bus.get(bus)

            in_fabric = False
            fabric_lines_left = 0
            continue

        if current_gpu is None:
            continue

        if stripped == "Fabric":
            in_fabric = True
            fabric_lines_left = 10
            continue

        if not in_fabric:
            continue

        fabric_lines_left -= 1

        if fabric_lines_left < 0:
            in_fabric = False
            continue

        if stripped.startswith("State") and ":" in stripped:
            current_gpu.fabric_state = (
                stripped.split(":", 1)[1].strip()
            )

        elif stripped.startswith("Status") and ":" in stripped:
            current_gpu.fabric_status = (
                stripped.split(":", 1)[1].strip()
            )

    return None


def collect_fabric_manager_status(
) -> tuple[FabricManagerStatus, Optional[str]]:
    status = FabricManagerStatus()

    if platform.system().lower() != "linux":
        return (
            status,
            "Fabric Manager service check is available on Linux only",
        )

    if shutil.which("systemctl") is None:
        return status, "systemctl is unavailable"

    try:
        result = subprocess.run(
            [
                "systemctl",
                "show",
                "nvidia-fabricmanager.service",
                "--property=LoadState",
                "--property=ActiveState",
                "--no-pager",
            ],
            capture_output=True,
            text=True,
            timeout=10,
            check=False,
        )
    except Exception as exc:
        return status, f"Fabric Manager service query failed: {exc}"

    values: dict[str, str] = {}

    for line in result.stdout.splitlines():
        if "=" not in line:
            continue

        key, value = line.split("=", 1)
        values[key.strip()] = value.strip()

    load_state = values.get("LoadState")
    active_state = values.get("ActiveState")

    status.load_state = load_state
    status.active_state = active_state

    if load_state:
        status.installed = load_state != "not-found"

    if active_state:
        status.active = active_state == "active"

    return status, None


def collect_nvlink_p2p(
) -> tuple[dict[str, dict[str, str]], Optional[str]]:
    matrix: dict[str, dict[str, str]] = {}

    if platform.system().lower() != "linux":
        return (
            matrix,
            "NVLink P2P topology check is available on Linux only",
        )

    if shutil.which("nvidia-smi") is None:
        return matrix, "nvidia-smi is unavailable"

    try:
        result = subprocess.run(
            [
                "nvidia-smi",
                "topo",
                "-p2p",
                "n",
            ],
            capture_output=True,
            text=True,
            timeout=15,
            check=False,
        )
    except Exception as exc:
        return matrix, f"Unable to query NVLink P2P topology: {exc}"

    if result.returncode != 0:
        return (
            matrix,
            result.stderr.strip()
            or "NVLink P2P topology query failed",
        )

    header: list[str] = []

    for raw_line in result.stdout.splitlines():
        parts = raw_line.split()

        if not parts:
            continue

        if not header and all(
            item.startswith("GPU")
            for item in parts
        ):
            header = parts
            continue

        if (
            header
            and parts[0].startswith("GPU")
            and len(parts) >= len(header) + 1
        ):
            row_name = parts[0]
            values = parts[1:1 + len(header)]

            matrix[row_name] = dict(
                zip(
                    header,
                    values,
                )
            )

    return matrix, None
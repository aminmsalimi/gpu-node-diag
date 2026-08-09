import shutil
import subprocess
from typing import Optional

from gpunodediag.models import GPUInfo


QUERY_FIELDS = [
    "index",
    "name",
    "uuid",
    "driver_version",
    "temperature.gpu",
    "power.draw",
    "power.limit",
    "utilization.gpu",
    "memory.used",
    "memory.total",
    "pcie.link.gen.current",
    "pcie.link.gen.max",
    "pcie.link.width.current",
    "pcie.link.width.max",
    "persistence_mode",
    "mig.mode.current",
]


def _to_float(value: str) -> Optional[float]:
    value = value.strip()

    if value.lower() in {
        "n/a",
        "na",
        "not supported",
        "[not supported]",
        "",
    }:
        return None

    try:
        return float(value)
    except ValueError:
        return None


def _clean(value: str) -> Optional[str]:
    value = value.strip()

    if value.lower() in {
        "n/a",
        "na",
        "not supported",
        "[not supported]",
        "",
    }:
        return None

    return value


def nvidia_smi_available() -> bool:
    return shutil.which("nvidia-smi") is not None


def collect_gpus() -> tuple[list[GPUInfo], Optional[str]]:
    if not nvidia_smi_available():
        return [], "nvidia-smi was not found in PATH"

    command = [
        "nvidia-smi",
        f"--query-gpu={','.join(QUERY_FIELDS)}",
        "--format=csv,noheader,nounits",
    ]

    try:
        result = subprocess.run(
            command,
            capture_output=True,
            text=True,
            timeout=10,
            check=False,
        )
    except subprocess.TimeoutExpired:
        return [], "nvidia-smi timed out"
    except OSError as exc:
        return [], f"Unable to execute nvidia-smi: {exc}"

    if result.returncode != 0:
        message = result.stderr.strip() or result.stdout.strip()
        return [], f"nvidia-smi failed: {message}"

    gpus: list[GPUInfo] = []

    for line in result.stdout.splitlines():
        if not line.strip():
            continue

        values = [value.strip() for value in line.split(",")]

        if len(values) != len(QUERY_FIELDS):
            continue

        try:
            gpu_index = int(values[0])
        except ValueError:
            continue

        gpus.append(
            GPUInfo(
                index=gpu_index,
                name=values[1],
                uuid=values[2],
                driver_version=values[3],
                temperature_c=_to_float(values[4]),
                power_draw_w=_to_float(values[5]),
                power_limit_w=_to_float(values[6]),
                utilization_percent=_to_float(values[7]),
                memory_used_mb=_to_float(values[8]),
                memory_total_mb=_to_float(values[9]),
                pcie_generation=_clean(values[10]),
                pcie_generation_max=_clean(values[11]),
                pcie_width=_clean(values[12]),
                pcie_width_max=_clean(values[13]),
                persistence_mode=_clean(values[14]),
                mig_mode=_clean(values[15]),
            )
        )

    if not gpus:
        return [], "nvidia-smi returned no usable GPU data"

    return gpus, None

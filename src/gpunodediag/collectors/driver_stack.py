import ctypes.util
import os
import platform
import re
import shutil
import subprocess
from pathlib import Path

from gpunodediag.models import DriverStackStatus


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


def parse_driver_cuda_version(
    text: str,
) -> str | None:
    match = re.search(
        r"CUDA Version:\s*([0-9]+\.[0-9]+)",
        text,
        re.IGNORECASE,
    )

    return (
        match.group(1)
        if match
        else None
    )


def parse_nvcc_version(
    text: str,
) -> str | None:
    match = re.search(
        r"\brelease\s+([0-9]+\.[0-9]+)",
        text,
        re.IGNORECASE,
    )

    return (
        match.group(1)
        if match
        else None
    )


def parse_kernel_module_version(
    text: str,
) -> str | None:
    match = re.search(
        r"Kernel Module.*?\b([0-9]{3,}\.[0-9.]+)",
        text,
        re.IGNORECASE,
    )

    return (
        match.group(1)
        if match
        else None
    )


def parse_loaded_modules(
    text: str,
) -> set[str]:
    modules: set[str] = set()

    for line in text.splitlines():
        parts = line.split()

        if parts:
            modules.add(
                parts[0]
            )

    return modules


def _discover_toolkit_paths() -> list[str]:
    paths: list[Path] = []

    for variable in (
        "CUDA_HOME",
        "CUDA_PATH",
    ):
        value = os.environ.get(
            variable
        )

        if value:
            paths.append(
                Path(value)
            )

    nvcc = shutil.which(
        "nvcc"
    )

    if nvcc:
        try:
            paths.append(
                Path(nvcc)
                .resolve()
                .parent
                .parent
            )
        except OSError:
            pass

    if platform.system() == "Linux":
        paths.extend(
            Path("/usr/local").glob(
                "cuda*"
            )
        )

        paths.extend(
            Path("/opt").glob(
                "cuda*"
            )
        )

    elif platform.system() == "Windows":
        root = Path(
            os.environ.get(
                "ProgramFiles",
                r"C:\Program Files",
            )
        )

        cuda_root = (
            root
            / "NVIDIA GPU Computing Toolkit"
            / "CUDA"
        )

        if cuda_root.exists():
            paths.extend(
                cuda_root.glob("v*")
            )

    unique: list[str] = []
    seen: set[str] = set()

    for path in paths:
        try:
            if not path.exists():
                continue

            value = str(
                path.resolve()
            )

        except OSError:
            value = str(path)

        lowered = value.lower()

        if lowered not in seen:
            seen.add(lowered)
            unique.append(value)

    return unique


def _find_cuda_driver_library() -> str | None:
    candidates = [
        ctypes.util.find_library(
            "cuda"
        ),
        ctypes.util.find_library(
            "nvcuda"
        ),
    ]

    for candidate in candidates:
        if candidate:
            return candidate

    if platform.system() == "Windows":
        windows = os.environ.get(
            "WINDIR"
        )

        if windows:
            path = (
                Path(windows)
                / "System32"
                / "nvcuda.dll"
            )

            if path.exists():
                return str(path)

    return None


def _find_cudart(
    toolkit_paths: list[str],
) -> str | None:
    library = ctypes.util.find_library(
        "cudart"
    )

    if library:
        return library

    patterns = []

    if platform.system() == "Windows":
        patterns = [
            "bin/cudart64_*.dll",
        ]
    else:
        patterns = [
            "lib64/libcudart.so*",
            "lib/libcudart.so*",
            "targets/*/lib/libcudart.so*",
        ]

    for toolkit in toolkit_paths:
        root = Path(toolkit)

        for pattern in patterns:
            matches = list(
                root.glob(pattern)
            )

            if matches:
                return str(
                    matches[0]
                )

    return None


def _secure_boot_state() -> bool | None:
    if platform.system() != "Linux":
        return None

    mokutil = shutil.which(
        "mokutil"
    )

    if not mokutil:
        return None

    try:
        result = _run(
            [
                mokutil,
                "--sb-state",
            ],
            timeout=5,
        )

    except Exception:
        return None

    text = (
        result.stdout
        + "\n"
        + result.stderr
    ).lower()

    if "secureboot enabled" in text:
        return True

    if "secure boot enabled" in text:
        return True

    if "secureboot disabled" in text:
        return False

    if "secure boot disabled" in text:
        return False

    return None


def collect_driver_stack() -> DriverStackStatus:
    system = platform.system()

    status = DriverStackStatus(
        platform=system,
    )

    status.toolkit_paths = (
        _discover_toolkit_paths()
    )

    status.cuda_home = (
        os.environ.get("CUDA_HOME")
        or os.environ.get("CUDA_PATH")
    )

    #
    # nvidia-smi / user-space driver
    #

    nvidia_smi = shutil.which(
        "nvidia-smi"
    )

    status.nvidia_smi_path = (
        nvidia_smi
    )

    if nvidia_smi:
        try:
            query = _run(
                [
                    nvidia_smi,
                    "--query-gpu=driver_version",
                    "--format=csv,noheader",
                ]
            )

            if query.returncode == 0:
                versions = [
                    line.strip()
                    for line
                    in query.stdout.splitlines()
                    if line.strip()
                ]

                status.nvidia_smi_ok = (
                    True
                )

                if versions:
                    status.driver_version = (
                        versions[0]
                    )

            else:
                status.nvidia_smi_ok = (
                    False
                )

                status.error = (
                    query.stderr.strip()
                    or query.stdout.strip()
                    or "nvidia-smi failed"
                )

        except Exception as exc:
            status.nvidia_smi_ok = False
            status.error = str(exc)

        try:
            normal = _run(
                [nvidia_smi]
            )

            text = (
                normal.stdout
                + "\n"
                + normal.stderr
            )

            status.driver_cuda_max = (
                parse_driver_cuda_version(
                    text
                )
            )

        except Exception:
            pass

    else:
        status.nvidia_smi_ok = False

    #
    # CUDA Toolkit / nvcc
    #

    nvcc = shutil.which(
        "nvcc"
    )

    status.nvcc_path = nvcc

    if nvcc:
        try:
            result = _run(
                [
                    nvcc,
                    "--version",
                ]
            )

            status.cuda_toolkit_version = (
                parse_nvcc_version(
                    result.stdout
                    + "\n"
                    + result.stderr
                )
            )

        except Exception:
            pass

    #
    # Libraries
    #

    status.cuda_driver_library = (
        _find_cuda_driver_library()
    )

    status.cuda_runtime_library = (
        _find_cudart(
            status.toolkit_paths
        )
    )

    #
    # Linux kernel driver
    #

    if system == "Linux":
        try:
            modules_text = Path(
                "/proc/modules"
            ).read_text(
                encoding="utf-8",
                errors="ignore",
            )

            modules = (
                parse_loaded_modules(
                    modules_text
                )
            )

            status.kernel_module_loaded = (
                "nvidia" in modules
            )

            status.nvidia_uvm_loaded = (
                "nvidia_uvm" in modules
            )

            status.nvidia_drm_loaded = (
                "nvidia_drm" in modules
            )

            status.nvidia_modeset_loaded = (
                "nvidia_modeset"
                in modules
            )

            status.nvidia_peermem_loaded = (
                "nvidia_peermem"
                in modules
            )

        except OSError:
            status.notes.append(
                "Unable to read /proc/modules."
            )

        version_file = Path(
            "/proc/driver/nvidia/version"
        )

        if version_file.exists():
            try:
                text = (
                    version_file.read_text(
                        encoding="utf-8",
                        errors="ignore",
                    )
                )

                status.kernel_module_version = (
                    parse_kernel_module_version(
                        text
                    )
                )

                if (
                    "open kernel module"
                    in text.lower()
                ):
                    status.kernel_module_flavor = (
                        "open"
                    )

                elif (
                    "kernel module"
                    in text.lower()
                ):
                    status.kernel_module_flavor = (
                        "proprietary"
                    )

            except OSError:
                pass

        status.secure_boot_enabled = (
            _secure_boot_state()
        )

    else:
        status.notes.append(
            "Kernel module and Secure Boot checks are Linux-focused."
        )

    return status
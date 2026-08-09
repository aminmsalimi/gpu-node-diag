from gpunodediag.models import (
    DriverStackStatus,
    Finding,
    Severity,
)


def _version_tuple(
    value: str | None,
) -> tuple[int, ...] | None:
    if not value:
        return None

    try:
        return tuple(
            int(part)
            for part
            in value.split(".")
        )

    except ValueError:
        return None


def check_driver_stack(
    status: DriverStackStatus,
) -> list[Finding]:
    findings: list[Finding] = []

    if not status.nvidia_smi_path:
        findings.append(
            Finding(
                code="NVIDIA_SMI_NOT_FOUND",
                severity=Severity.HIGH,
                title="nvidia-smi not detected",
                message=(
                    "The NVIDIA management utility "
                    "was not found on PATH."
                ),
                recommendations=[
                    "Verify that the NVIDIA GPU driver is installed.",
                    "Check the system PATH and driver installation.",
                ],
            )
        )

    elif status.nvidia_smi_ok is False:
        findings.append(
            Finding(
                code="NVIDIA_SMI_FAILED",
                severity=Severity.HIGH,
                title="nvidia-smi cannot communicate with the driver",
                message=(
                    "nvidia-smi was found but failed "
                    "to query the NVIDIA driver."
                ),
                evidence={
                    "error": status.error,
                },
                recommendations=[
                    "Check whether the NVIDIA kernel driver is loaded.",
                    "Review kernel logs for NVIDIA driver errors.",
                    "Check for a driver/userspace version mismatch.",
                    "Reboot if the driver package was recently upgraded.",
                ],
            )
        )

    if (
        status.platform == "Linux"
        and status.nvidia_smi_path
        and status.kernel_module_loaded
        is False
    ):
        recommendations = [
            "Verify that the NVIDIA kernel module can load.",
            "Check dmesg or journalctl for NVIDIA module errors.",
        ]

        if status.secure_boot_enabled:
            recommendations.append(
                "Secure Boot is enabled; verify that the NVIDIA kernel module is correctly signed and trusted."
            )

        findings.append(
            Finding(
                code="NVIDIA_KERNEL_MODULE_NOT_LOADED",
                severity=Severity.HIGH,
                title="NVIDIA kernel module is not loaded",
                message=(
                    "The NVIDIA userspace tools are present, "
                    "but the nvidia kernel module is not loaded."
                ),
                evidence={
                    "secure_boot_enabled":
                        status.secure_boot_enabled,
                },
                recommendations=recommendations,
            )
        )

    if (
        status.driver_version
        and status.kernel_module_version
        and status.driver_version
        != status.kernel_module_version
    ):
        findings.append(
            Finding(
                code="NVIDIA_DRIVER_MODULE_MISMATCH",
                severity=Severity.HIGH,
                title="NVIDIA driver version mismatch",
                message=(
                    "The loaded NVIDIA kernel module version "
                    "does not match the userspace driver version."
                ),
                evidence={
                    "userspace_driver":
                        status.driver_version,
                    "kernel_module":
                        status.kernel_module_version,
                },
                recommendations=[
                    "Check whether the NVIDIA driver was upgraded without rebooting.",
                    "Verify that userspace and kernel driver packages come from the same driver release.",
                    "Reboot the node if an updated kernel module is waiting to be loaded.",
                ],
            )
        )

    if (
        status.platform == "Linux"
        and status.kernel_module_loaded
        and status.nvidia_uvm_loaded is False
    ):
        findings.append(
            Finding(
                code="NVIDIA_UVM_NOT_LOADED",
                severity=Severity.INFO,
                title="NVIDIA UVM module is not currently loaded",
                message=(
                    "nvidia_uvm is not loaded at this snapshot. "
                    "It may be loaded automatically when a CUDA "
                    "workload requires it."
                ),
                recommendations=[
                    "If CUDA applications fail, verify that nvidia_uvm can be loaded.",
                ],
            )
        )

    toolkit = _version_tuple(
        status.cuda_toolkit_version
    )

    driver_cuda = _version_tuple(
        status.driver_cuda_max
    )

    if (
        toolkit is not None
        and driver_cuda is not None
        and toolkit > driver_cuda
    ):
        findings.append(
            Finding(
                code="CUDA_TOOLKIT_NEWER_THAN_DRIVER",
                severity=Severity.WARNING,
                title="CUDA Toolkit is newer than driver capability",
                message=(
                    f"CUDA Toolkit {status.cuda_toolkit_version} "
                    f"is installed, while the driver reports "
                    f"CUDA {status.driver_cuda_max} as its "
                    "maximum supported CUDA version."
                ),
                evidence={
                    "toolkit":
                        status.cuda_toolkit_version,
                    "driver_cuda_max":
                        status.driver_cuda_max,
                    "driver":
                        status.driver_version,
                },
                recommendations=[
                    "Verify the CUDA Toolkit and driver compatibility requirements.",
                    "Upgrade the NVIDIA driver or verify whether a supported CUDA forward-compatibility package is intentionally being used.",
                ],
            )
        )

    if (
        status.nvcc_path is None
        and not status.toolkit_paths
    ):
        findings.append(
            Finding(
                code="CUDA_TOOLKIT_NOT_DETECTED",
                severity=Severity.INFO,
                title="CUDA Toolkit not detected",
                message=(
                    "nvcc and common CUDA Toolkit installation "
                    "paths were not detected. This is normal "
                    "for runtime-only GPU nodes."
                ),
                recommendations=[
                    "Install the CUDA Toolkit only if local CUDA development or compilation is required.",
                ],
            )
        )

    elif (
        status.nvcc_path is None
        and status.toolkit_paths
    ):
        findings.append(
            Finding(
                code="NVCC_NOT_ON_PATH",
                severity=Severity.WARNING,
                title="CUDA Toolkit detected but nvcc is unavailable",
                message=(
                    "CUDA Toolkit directories were detected, "
                    "but nvcc is not available on PATH."
                ),
                evidence={
                    "toolkit_paths":
                        status.toolkit_paths,
                },
                recommendations=[
                    "Verify CUDA_HOME/CUDA_PATH.",
                    "Add the CUDA Toolkit bin directory to PATH if local compilation is required.",
                ],
            )
        )

    if (
        status.nvidia_smi_ok
        and not status.cuda_driver_library
    ):
        findings.append(
            Finding(
                code="CUDA_DRIVER_LIBRARY_NOT_FOUND",
                severity=Severity.WARNING,
                title="CUDA driver library not discoverable",
                message=(
                    "The NVIDIA driver is responding, but "
                    "GPUNodeDiag could not locate the CUDA "
                    "driver library."
                ),
                recommendations=[
                    "Verify libcuda.so or nvcuda.dll installation and library search paths.",
                    "Check the NVIDIA driver package installation.",
                ],
            )
        )

    if (
        status.cuda_toolkit_version
        and not status.cuda_runtime_library
    ):
        findings.append(
            Finding(
                code="CUDA_RUNTIME_LIBRARY_NOT_FOUND",
                severity=Severity.INFO,
                title="CUDA runtime library not discoverable",
                message=(
                    "A CUDA Toolkit was detected but libcudart "
                    "was not found through the standard library "
                    "search paths."
                ),
                recommendations=[
                    "Check CUDA Toolkit library paths if CUDA applications cannot locate libcudart.",
                ],
            )
        )

    return sorted(
        findings,
        key=lambda item: item.severity.value,
        reverse=True,
    )
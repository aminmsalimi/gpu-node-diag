from gpunodediag.checks.driver_stack import (
    check_driver_stack,
)
from gpunodediag.collectors.driver_stack import (
    parse_driver_cuda_version,
    parse_kernel_module_version,
    parse_loaded_modules,
    parse_nvcc_version,
)
from gpunodediag.models import (
    DriverStackStatus,
    Severity,
)


def test_parse_driver_cuda_version():
    text = """
    NVIDIA-SMI 580.10
    Driver Version: 580.10
    CUDA Version: 13.0
    """

    assert (
        parse_driver_cuda_version(text)
        == "13.0"
    )


def test_parse_nvcc_version():
    text = """
    Cuda compilation tools,
    release 13.0, V13.0.88
    """

    assert (
        parse_nvcc_version(text)
        == "13.0"
    )


def test_parse_kernel_module_version():
    text = (
        "NVRM version: NVIDIA UNIX x86_64 "
        "Kernel Module  580.10.02"
    )

    assert (
        parse_kernel_module_version(text)
        == "580.10.02"
    )


def test_parse_loaded_modules():
    text = """
    nvidia_uvm 123 0 - Live
    nvidia 999 1 nvidia_uvm, Live
    """

    modules = parse_loaded_modules(
        text
    )

    assert "nvidia" in modules
    assert "nvidia_uvm" in modules


def test_nvidia_smi_failure_is_high():
    status = DriverStackStatus(
        platform="Linux",
        nvidia_smi_path="/usr/bin/nvidia-smi",
        nvidia_smi_ok=False,
        error="driver communication failed",
    )

    findings = check_driver_stack(
        status
    )

    assert any(
        item.code == "NVIDIA_SMI_FAILED"
        and item.severity is Severity.HIGH
        for item in findings
    )


def test_driver_module_mismatch_is_high():
    status = DriverStackStatus(
        platform="Linux",
        nvidia_smi_path="/usr/bin/nvidia-smi",
        nvidia_smi_ok=True,
        driver_version="580.10.02",
        kernel_module_loaded=True,
        kernel_module_version="575.50.01",
        cuda_driver_library="libcuda.so.1",
    )

    findings = check_driver_stack(
        status
    )

    assert any(
        item.code
        == "NVIDIA_DRIVER_MODULE_MISMATCH"
        and item.severity is Severity.HIGH
        for item in findings
    )


def test_newer_toolkit_is_warning():
    status = DriverStackStatus(
        platform="Linux",
        nvidia_smi_path="/usr/bin/nvidia-smi",
        nvidia_smi_ok=True,
        driver_version="570.1",
        driver_cuda_max="12.8",
        kernel_module_loaded=True,
        kernel_module_version="570.1",
        cuda_toolkit_version="13.0",
        nvcc_path="/usr/local/cuda/bin/nvcc",
        cuda_driver_library="libcuda.so.1",
        cuda_runtime_library="libcudart.so",
    )

    findings = check_driver_stack(
        status
    )

    assert any(
        item.code
        == "CUDA_TOOLKIT_NEWER_THAN_DRIVER"
        and item.severity is Severity.WARNING
        for item in findings
    )


def test_missing_toolkit_is_only_info():
    status = DriverStackStatus(
        platform="Linux",
        nvidia_smi_path="/usr/bin/nvidia-smi",
        nvidia_smi_ok=True,
        driver_version="580.1",
        driver_cuda_max="13.0",
        kernel_module_loaded=True,
        kernel_module_version="580.1",
        cuda_driver_library="libcuda.so.1",
    )

    findings = check_driver_stack(
        status
    )

    matching = [
        item
        for item in findings
        if item.code
        == "CUDA_TOOLKIT_NOT_DETECTED"
    ]

    assert len(matching) == 1

    assert (
        matching[0].severity
        is Severity.INFO
    )


def test_healthy_stack_has_no_high_findings():
    status = DriverStackStatus(
        platform="Linux",
        nvidia_smi_path="/usr/bin/nvidia-smi",
        nvidia_smi_ok=True,
        driver_version="580.1",
        driver_cuda_max="13.0",
        kernel_module_loaded=True,
        kernel_module_version="580.1",
        nvidia_uvm_loaded=True,
        nvcc_path="/usr/local/cuda/bin/nvcc",
        cuda_toolkit_version="13.0",
        toolkit_paths=[
            "/usr/local/cuda",
        ],
        cuda_driver_library="libcuda.so.1",
        cuda_runtime_library="libcudart.so",
    )

    findings = check_driver_stack(
        status
    )

    assert not any(
        item.severity in {
            Severity.HIGH,
            Severity.CRITICAL,
        }
        for item in findings
    )
from typing import Optional

import pynvml

from gpunodediag.models import GPUInfo


SW_POWER_CAP = 0x0000000000000004
HW_SLOWDOWN = 0x0000000000000008
SW_THERMAL_SLOWDOWN = 0x0000000000000020


def _collect_clock_events(handle, gpu: GPUInfo) -> None:
    get_reasons = getattr(
        pynvml,
        "nvmlDeviceGetCurrentClocksEventReasons",
        None,
    )

    if get_reasons is None:
        get_reasons = getattr(
            pynvml,
            "nvmlDeviceGetCurrentClocksThrottleReasons",
            None,
        )

    if get_reasons is None:
        return

    mask = int(get_reasons(handle))

    gpu.clock_event_mask = mask
    gpu.clock_event_sw_power_cap = bool(mask & SW_POWER_CAP)
    gpu.clock_event_hw_slowdown = bool(mask & HW_SLOWDOWN)
    gpu.clock_event_sw_thermal_slowdown = bool(
        mask & SW_THERMAL_SLOWDOWN
    )


def _collect_ecc(handle, gpu: GPUInfo) -> None:
    try:
        current_mode, _pending_mode = pynvml.nvmlDeviceGetEccMode(handle)

        gpu.ecc_supported = True
        gpu.ecc_enabled = bool(current_mode)

    except pynvml.NVMLError_NotSupported:
        gpu.ecc_supported = False
        gpu.ecc_enabled = False
        return

    if not gpu.ecc_enabled:
        return

    try:
        gpu.ecc_corrected_volatile = int(
            pynvml.nvmlDeviceGetTotalEccErrors(
                handle,
                pynvml.NVML_MEMORY_ERROR_TYPE_CORRECTED,
                pynvml.NVML_VOLATILE_ECC,
            )
        )
    except pynvml.NVMLError_NotSupported:
        gpu.ecc_corrected_volatile = None

    try:
        gpu.ecc_uncorrected_volatile = int(
            pynvml.nvmlDeviceGetTotalEccErrors(
                handle,
                pynvml.NVML_MEMORY_ERROR_TYPE_UNCORRECTED,
                pynvml.NVML_VOLATILE_ECC,
            )
        )
    except pynvml.NVMLError_NotSupported:
        gpu.ecc_uncorrected_volatile = None


def enrich_nvml_state(gpus: list[GPUInfo]) -> Optional[str]:
    if not gpus:
        return None

    try:
        pynvml.nvmlInit()
    except Exception as exc:
        return f"NVML initialization failed: {exc}"

    errors: list[str] = []

    try:
        for gpu in gpus:
            try:
                handle = pynvml.nvmlDeviceGetHandleByUUID(gpu.uuid)

                _collect_clock_events(handle, gpu)
                _collect_ecc(handle, gpu)

            except Exception as exc:
                errors.append(
                    f"GPU {gpu.index}: NVML collection failed: {exc}"
                )

    finally:
        try:
            pynvml.nvmlShutdown()
        except Exception:
            pass

    if errors:
        return "; ".join(errors)

    return None


# Backward-compatible alias used by older code.
def enrich_clock_events(gpus: list[GPUInfo]) -> Optional[str]:
    return enrich_nvml_state(gpus)
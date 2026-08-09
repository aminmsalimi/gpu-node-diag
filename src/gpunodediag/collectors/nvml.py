from typing import Optional

import pynvml

from gpunodediag.models import GPUInfo


# NVML clock-event bit values.
#
# SW Power Cap:
# GPU clocks are being constrained by software power management.
SW_POWER_CAP = 0x0000000000000004

# HW Slowdown:
# Significant hardware-driven clock reduction is active.
HW_SLOWDOWN = 0x0000000000000008

# SW Thermal Slowdown:
# Software thermal control is reducing clocks.
SW_THERMAL_SLOWDOWN = 0x0000000000000020


def enrich_clock_events(gpus: list[GPUInfo]) -> Optional[str]:
    """
    Enrich GPUInfo objects with current NVML clock-event reasons.

    Returns an informational error string if NVML clock-event
    information could not be collected. Diagnostics remain usable
    even when this optional capability is unavailable.
    """

    if not gpus:
        return None

    try:
        pynvml.nvmlInit()
    except Exception as exc:
        return f"NVML initialization failed: {exc}"

    errors: list[str] = []

    try:
        get_reasons = getattr(
            pynvml,
            "nvmlDeviceGetCurrentClocksEventReasons",
            None,
        )

        # Compatibility fallback for older Python bindings/drivers.
        if get_reasons is None:
            get_reasons = getattr(
                pynvml,
                "nvmlDeviceGetCurrentClocksThrottleReasons",
                None,
            )

        if get_reasons is None:
            return "NVML clock-event API is unavailable"

        for gpu in gpus:
            try:
                handle = pynvml.nvmlDeviceGetHandleByUUID(gpu.uuid)
                mask = int(get_reasons(handle))

                gpu.clock_event_mask = mask
                gpu.clock_event_sw_power_cap = bool(
                    mask & SW_POWER_CAP
                )
                gpu.clock_event_hw_slowdown = bool(
                    mask & HW_SLOWDOWN
                )
                gpu.clock_event_sw_thermal_slowdown = bool(
                    mask & SW_THERMAL_SLOWDOWN
                )

            except Exception as exc:
                errors.append(
                    f"GPU {gpu.index}: unable to read clock events: {exc}"
                )

    finally:
        try:
            pynvml.nvmlShutdown()
        except Exception:
            pass

    if errors:
        return "; ".join(errors)

    return None

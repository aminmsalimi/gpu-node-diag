from gpunodediag.checks.engine import run_diagnostics
from gpunodediag.models import GPUInfo, Severity


def make_gpu(**overrides):
    values = {
        "index": 0,
        "name": "NVIDIA Test GPU",
        "uuid": "GPU-test",
        "driver_version": "580.0",
        "temperature_c": 50,
        "power_draw_w": 100,
        "power_limit_w": 700,
        "utilization_percent": 80,
        "memory_used_mb": 1000,
        "memory_total_mb": 80000,
        "pcie_generation": "5",
        "pcie_generation_max": "5",
        "pcie_width": "16",
        "pcie_width_max": "16",
        "persistence_mode": "Enabled",
        "mig_mode": "Disabled",
    }

    values.update(overrides)

    return GPUInfo(**values)


def test_healthy_gpu_has_no_findings():
    findings = run_diagnostics([make_gpu()])

    assert findings == []


def test_high_temperature_is_detected():
    findings = run_diagnostics(
        [
            make_gpu(
                temperature_c=87,
            )
        ]
    )

    assert any(
        finding.code == "GPU_TEMP_HIGH"
        and finding.severity is Severity.HIGH
        for finding in findings
    )


def test_degraded_pcie_width_is_detected():
    findings = run_diagnostics(
        [
            make_gpu(
                pcie_width="4",
                pcie_width_max="16",
            )
        ]
    )

    assert any(
        finding.code == "PCIE_WIDTH_DEGRADED"
        and finding.severity is Severity.HIGH
        for finding in findings
    )


def test_temperature_outlier_is_detected():
    gpu0 = make_gpu(index=0, temperature_c=50)
    gpu1 = make_gpu(index=1, temperature_c=52)
    gpu2 = make_gpu(index=2, temperature_c=82)

    findings = run_diagnostics([gpu0, gpu1, gpu2])

    assert any(
        finding.code == "GPU_TEMP_OUTLIER"
        and finding.gpu_index == 2
        for finding in findings
    )


def test_power_cap_is_detected():
    findings = run_diagnostics(
        [
            make_gpu(
                clock_event_mask=4,
                clock_event_sw_power_cap=True,
            )
        ]
    )

    assert any(
        finding.code == "GPU_POWER_CAP_ACTIVE"
        and finding.severity is Severity.WARNING
        for finding in findings
    )


def test_hardware_slowdown_is_detected():
    findings = run_diagnostics(
        [
            make_gpu(
                clock_event_mask=8,
                clock_event_hw_slowdown=True,
            )
        ]
    )

    assert any(
        finding.code == "GPU_HW_SLOWDOWN_ACTIVE"
        and finding.severity is Severity.HIGH
        for finding in findings
    )


def test_thermal_slowdown_is_detected():
    findings = run_diagnostics(
        [
            make_gpu(
                temperature_c=88,
                clock_event_mask=32,
                clock_event_sw_thermal_slowdown=True,
            )
        ]
    )

    assert any(
        finding.code == "GPU_SW_THERMAL_SLOWDOWN_ACTIVE"
        and finding.severity is Severity.HIGH
        for finding in findings
    )

from io import StringIO

from rich.console import Console

from gpunodediag.checks.live import run_live_diagnostics
from gpunodediag.models import (
    GPUInfo,
    HostInfo,
    Severity,
)
from gpunodediag.output.watch import build_watch_dashboard


def make_gpu(
    index: int = 0,
    temperature: float = 50,
) -> GPUInfo:
    return GPUInfo(
        index=index,
        name="NVIDIA Test GPU",
        uuid=f"GPU-{index}",
        driver_version="999.0",
        temperature_c=temperature,
        power_draw_w=300,
        power_limit_w=700,
        utilization_percent=80,
        memory_used_mb=40960,
        memory_total_mb=81920,
        pcie_generation="5",
        pcie_generation_max="5",
        pcie_width="16",
        pcie_width_max="16",
        ecc_supported=True,
        ecc_enabled=True,
        ecc_corrected_volatile=0,
        ecc_uncorrected_volatile=0,
    )


def make_host() -> HostInfo:
    return HostInfo(
        hostname="gpu-node-test",
        operating_system="Linux",
        release="test",
        architecture="x86_64",
        python_version="3.x",
    )


def render_dashboard(
    gpus,
    findings,
) -> str:
    output = StringIO()

    console = Console(
        file=output,
        force_terminal=False,
        width=180,
    )

    console.print(
        build_watch_dashboard(
            host=make_host(),
            gpus=gpus,
            findings=findings,
            interval=2,
            updated_at="12:00:00",
            sample_number=3,
        )
    )

    return output.getvalue()


def test_live_healthy_gpu_has_no_findings():
    gpu = make_gpu()

    findings = run_live_diagnostics(
        [gpu]
    )

    assert findings == []


def test_live_high_temperature_is_detected():
    gpu = make_gpu(
        temperature=86,
    )

    findings = run_live_diagnostics(
        [gpu]
    )

    assert findings
    assert findings[0].severity in {
        Severity.HIGH,
        Severity.CRITICAL,
    }


def test_watch_dashboard_contains_gpu_data():
    gpu = make_gpu()

    text = render_dashboard(
        [gpu],
        [],
    )

    assert "GPUNodeDiag Live" in text
    assert "gpu-node-test" in text
    assert "NVIDIA Test GPU" in text
    assert "40.0/80.0 GiB" in text
    assert "HEALTHY" in text


def test_watch_dashboard_shows_finding():
    gpu = make_gpu(
        temperature=91,
    )

    findings = run_live_diagnostics(
        [gpu]
    )

    text = render_dashboard(
        [gpu],
        findings,
    )

    assert "CRITICAL" in text
    assert "Critical GPU temperature" in text
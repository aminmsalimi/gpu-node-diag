from gpunodediag.reporting.html import (
    render_html_report,
    snapshot_status,
)


def make_snapshot():
    return {
        "schema_version": 1,
        "tool": "GPUNodeDiag",
        "version": "0.1.0",
        "generated_at": "2026-08-09T12:00:00+00:00",
        "host": {
            "hostname": "gpu-node-01",
            "operating_system": "Linux",
            "release": "Ubuntu 24.04",
            "architecture": "x86_64",
            "python_version": "3.14",
        },
        "gpus": [
            {
                "index": 0,
                "name": "NVIDIA H100 80GB HBM3",
                "uuid": "GPU-TEST",
                "driver_version": "580.0",
                "pci_bus_id": "41:00",
                "temperature_c": 52,
                "power_draw_w": 400,
                "power_limit_w": 700,
                "utilization_percent": 91,
                "memory_used_mb": 65536,
                "memory_total_mb": 81920,
                "pcie_generation": "5",
                "pcie_generation_max": "5",
                "pcie_width": "16",
                "pcie_width_max": "16",
                "persistence_mode": "Enabled",
                "mig_mode": "Disabled",
                "clock_event_mask": 0,
                "clock_event_sw_power_cap": False,
                "clock_event_hw_slowdown": False,
                "clock_event_sw_thermal_slowdown": False,
                "ecc_supported": True,
                "ecc_enabled": True,
                "ecc_corrected_volatile": 0,
                "ecc_uncorrected_volatile": 0,
                "nvlink_supported": True,
                "nvlink_total_links": 18,
                "nvlink_active_links": 18,
                "nvlink_inactive_links": [],
                "nvlink_error_counts": {},
                "fabric_state": "Completed",
                "fabric_status": "Success",
            }
        ],
        "dcgm": {
            "status": {
                "installed": True,
                "version": "4.x",
                "hostengine_reachable": True,
                "discovery_ok": True,
                "error": None,
            },
            "deep_requested": False,
            "results": [],
        },
        "fabric_manager": {
            "installed": True,
            "active": True,
            "load_state": "loaded",
            "active_state": "active",
        },
        "nvlink_p2p": {},
        "xid_events": [],
        "findings": [],
        "notes": [],
        "error": None,
    }


def test_healthy_snapshot_status():
    snapshot = make_snapshot()

    assert (
        snapshot_status(snapshot)
        == "HEALTHY"
    )


def test_critical_snapshot_status():
    snapshot = make_snapshot()

    snapshot["findings"] = [
        {
            "code": "TEST",
            "severity": "CRITICAL",
            "title": "Critical problem",
            "message": "Something failed",
            "gpu_index": 0,
            "evidence": {},
            "recommendations": [],
        }
    ]

    assert (
        snapshot_status(snapshot)
        == "CRITICAL"
    )


def test_html_contains_gpu_and_host():
    html = render_html_report(
        make_snapshot()
    )

    assert "GPU Node Diagnostic Report" in html
    assert "gpu-node-01" in html
    assert "NVIDIA H100 80GB HBM3" in html
    assert "64.0 / 80.0 GiB" in html
    assert "18/18" in html


def test_html_contains_findings():
    snapshot = make_snapshot()

    snapshot["findings"] = [
        {
            "code": "GPU_TEMP_CRITICAL",
            "severity": "CRITICAL",
            "title": "Critical GPU temperature",
            "message": "GPU temperature is too high.",
            "gpu_index": 0,
            "evidence": {
                "temperature_c": 94,
            },
            "recommendations": [
                "Inspect cooling.",
                "Reduce workload.",
            ],
        }
    ]

    html = render_html_report(
        snapshot
    )

    assert "Critical GPU temperature" in html
    assert "GPU_TEMP_CRITICAL" in html
    assert "Inspect cooling." in html
    assert "CRITICAL" in html


def test_html_escapes_untrusted_text():
    snapshot = make_snapshot()

    snapshot["host"]["hostname"] = (
        "<script>alert(1)</script>"
    )

    html = render_html_report(
        snapshot
    )

    assert (
        "<script>alert(1)</script>"
        not in html
    )

    assert (
        "&lt;script&gt;alert(1)&lt;/script&gt;"
        in html
    )
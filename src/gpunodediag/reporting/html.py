from html import escape
from typing import Any


SEVERITY_RANK = {
    "INFO": 1,
    "WARNING": 2,
    "HIGH": 3,
    "CRITICAL": 4,
}


def _e(value: Any) -> str:
    if value is None:
        return "—"

    return escape(str(value))


def _number(
    value: Any,
    suffix: str = "",
    decimals: int = 0,
) -> str:
    if value is None:
        return "—"

    try:
        number = float(value)

        return (
            f"{number:.{decimals}f}"
            f"{suffix}"
        )
    except (TypeError, ValueError):
        return _e(value)


def snapshot_status(
    snapshot: dict[str, Any],
) -> str:
    findings = snapshot.get(
        "findings",
        [],
    )

    if not findings:
        return "HEALTHY"

    highest = max(
        (
            SEVERITY_RANK.get(
                str(
                    finding.get(
                        "severity",
                        "INFO",
                    )
                ).upper(),
                1,
            )
            for finding in findings
        ),
        default=1,
    )

    if highest >= 4:
        return "CRITICAL"

    if highest == 3:
        return "DEGRADED"

    if highest == 2:
        return "WARNING"

    return "INFO"


def _status_class(status: str) -> str:
    status = status.upper()

    if status == "CRITICAL":
        return "critical"

    if status in {
        "DEGRADED",
        "HIGH",
    }:
        return "high"

    if status == "WARNING":
        return "warning"

    if status == "INFO":
        return "info"

    return "healthy"


def _gpu_status(
    index: int,
    findings: list[dict[str, Any]],
) -> str:
    gpu_findings = [
        finding
        for finding in findings
        if finding.get("gpu_index") == index
    ]

    if not gpu_findings:
        return "OK"

    rank = max(
        SEVERITY_RANK.get(
            str(
                finding.get(
                    "severity",
                    "INFO",
                )
            ).upper(),
            1,
        )
        for finding in gpu_findings
    )

    if rank >= 4:
        return "CRITICAL"

    if rank == 3:
        return "HIGH"

    if rank == 2:
        return "WARNING"

    return "INFO"


def _render_gpu_rows(
    snapshot: dict[str, Any],
) -> str:
    findings = snapshot.get(
        "findings",
        [],
    )

    rows: list[str] = []

    for gpu in snapshot.get(
        "gpus",
        [],
    ):
        index = gpu.get(
            "index",
            0,
        )

        status = _gpu_status(
            index,
            findings,
        )

        memory_used = gpu.get(
            "memory_used_mb"
        )

        memory_total = gpu.get(
            "memory_total_mb"
        )

        if (
            memory_used is not None
            and memory_total is not None
        ):
            memory = (
                f"{float(memory_used) / 1024:.1f}"
                f" / "
                f"{float(memory_total) / 1024:.1f}"
                f" GiB"
            )
        else:
            memory = "—"

        pcie_gen = gpu.get(
            "pcie_generation"
        )

        pcie_width = gpu.get(
            "pcie_width"
        )

        if pcie_gen and pcie_width:
            pcie = (
                f"Gen{_e(pcie_gen)} "
                f"x{_e(pcie_width)}"
            )
        else:
            pcie = "—"

        corrected = gpu.get(
            "ecc_corrected_volatile"
        )

        uncorrected = gpu.get(
            "ecc_uncorrected_volatile"
        )

        if gpu.get(
            "ecc_supported"
        ) is False:
            ecc = "N/A"
        elif (
            corrected is None
            and uncorrected is None
        ):
            ecc = "—"
        else:
            ecc = (
                f"C:{corrected or 0} "
                f"U:{uncorrected or 0}"
            )

        nvlink_total = gpu.get(
            "nvlink_total_links",
            0,
        )

        nvlink_active = gpu.get(
            "nvlink_active_links",
            0,
        )

        if gpu.get(
            "nvlink_supported"
        ):
            nvlink = (
                f"{nvlink_active}/"
                f"{nvlink_total}"
            )
        else:
            nvlink = "N/A"

        rows.append(
            f"""
            <tr>
                <td>{_e(index)}</td>
                <td class="model">{_e(gpu.get("name"))}</td>
                <td>{_number(gpu.get("temperature_c"), " °C")}</td>
                <td>{_number(gpu.get("utilization_percent"), "%")}</td>
                <td>{_number(gpu.get("power_draw_w"), " W")}</td>
                <td>{_e(memory)}</td>
                <td>{pcie}</td>
                <td>{_e(ecc)}</td>
                <td>{_e(nvlink)}</td>
                <td>
                    <span class="badge {_status_class(status)}">
                        {_e(status)}
                    </span>
                </td>
            </tr>
            """
        )

    if not rows:
        return (
            '<tr><td colspan="10" class="empty">'
            "No NVIDIA GPUs detected."
            "</td></tr>"
        )

    return "\n".join(rows)


def _render_findings(
    snapshot: dict[str, Any],
) -> str:
    findings = snapshot.get(
        "findings",
        [],
    )

    if not findings:
        return """
        <div class="good-box">
            No diagnostic findings were detected.
        </div>
        """

    blocks: list[str] = []

    for finding in findings:
        severity = str(
            finding.get(
                "severity",
                "INFO",
            )
        ).upper()

        gpu_index = finding.get(
            "gpu_index"
        )

        target = (
            f"GPU {gpu_index}"
            if gpu_index is not None
            else "Node"
        )

        evidence = finding.get(
            "evidence",
            {},
        )

        recommendations = finding.get(
            "recommendations",
            [],
        )

        evidence_html = ""

        if evidence:
            items = "".join(
                (
                    "<li><strong>"
                    f"{_e(key)}:"
                    "</strong> "
                    f"{_e(value)}</li>"
                )
                for key, value
                in evidence.items()
            )

            evidence_html = (
                '<div class="detail-title">'
                "Evidence"
                "</div>"
                f'<ul class="details">{items}</ul>'
            )

        recommendation_html = ""

        if recommendations:
            items = "".join(
                f"<li>{_e(item)}</li>"
                for item in recommendations
            )

            recommendation_html = (
                '<div class="detail-title">'
                "Recommended action"
                "</div>"
                f'<ul class="details">{items}</ul>'
            )

        blocks.append(
            f"""
            <article class="finding {_status_class(severity)}-border">
                <div class="finding-head">
                    <span class="badge {_status_class(severity)}">
                        {_e(severity)}
                    </span>
                    <span class="target">{_e(target)}</span>
                    <span class="code">{_e(finding.get("code"))}</span>
                </div>

                <h3>{_e(finding.get("title"))}</h3>

                <p>
                    {_e(finding.get("message"))}
                </p>

                {evidence_html}
                {recommendation_html}
            </article>
            """
        )

    return "\n".join(blocks)


def _render_dcgm(
    snapshot: dict[str, Any],
) -> str:
    dcgm = snapshot.get(
        "dcgm",
        {},
    )

    status = dcgm.get(
        "status",
        {},
    )

    installed = status.get(
        "installed"
    )

    reachable = status.get(
        "hostengine_reachable"
    )

    results = dcgm.get(
        "results",
        [],
    )

    if installed:
        installed_text = "Installed"
    else:
        installed_text = "Not detected"

    if reachable is True:
        engine_text = "Reachable"
    elif reachable is False:
        engine_text = "Unreachable"
    else:
        engine_text = "Unknown"

    result_rows = []

    for result in results:
        state = str(
            result.get(
                "status",
                "Unknown",
            )
        )

        entity = result.get(
            "entity_group"
        ) or "—"

        entity_id = result.get(
            "entity_id"
        )

        if entity_id is not None:
            entity = (
                f"{entity} "
                f"{entity_id}"
            )

        result_rows.append(
            f"""
            <tr>
                <td>{_e(result.get("name"))}</td>
                <td>{_e(entity)}</td>
                <td>
                    <span class="badge {_status_class(state)}">
                        {_e(state)}
                    </span>
                </td>
            </tr>
            """
        )

    result_table = ""

    if result_rows:
        result_table = f"""
        <table class="compact">
            <thead>
                <tr>
                    <th>Test</th>
                    <th>Entity</th>
                    <th>Status</th>
                </tr>
            </thead>
            <tbody>
                {''.join(result_rows)}
            </tbody>
        </table>
        """

    return f"""
    <div class="info-grid">
        <div>
            <span>DCGM</span>
            <strong>{_e(installed_text)}</strong>
        </div>
        <div>
            <span>Version</span>
            <strong>{_e(status.get("version"))}</strong>
        </div>
        <div>
            <span>Host engine</span>
            <strong>{_e(engine_text)}</strong>
        </div>
        <div>
            <span>Deep diagnostics</span>
            <strong>
                {"Yes" if dcgm.get("deep_requested") else "No"}
            </strong>
        </div>
    </div>

    {result_table}
    """


def _render_xids(
    snapshot: dict[str, Any],
) -> str:
    events = snapshot.get(
        "xid_events",
        [],
    )

    if not events:
        return (
            '<div class="good-box">'
            "No NVIDIA Xid events were collected."
            "</div>"
        )

    rows = []

    for event in events:
        rows.append(
            f"""
            <tr>
                <td>{_e(event.get("xid"))}</td>
                <td>{_e(event.get("gpu_index"))}</td>
                <td>{_e(event.get("pci_bus_id"))}</td>
                <td>{_e(event.get("timestamp"))}</td>
                <td class="message">{_e(event.get("raw_message"))}</td>
            </tr>
            """
        )

    return f"""
    <table class="compact">
        <thead>
            <tr>
                <th>Xid</th>
                <th>GPU</th>
                <th>PCI Bus</th>
                <th>Timestamp</th>
                <th>Kernel message</th>
            </tr>
        </thead>
        <tbody>
            {''.join(rows)}
        </tbody>
    </table>
    """


def _render_notes(
    snapshot: dict[str, Any],
) -> str:
    notes = snapshot.get(
        "notes",
        [],
    )

    if not notes:
        return (
            '<div class="muted">'
            "No capability notes."
            "</div>"
        )

    return (
        "<ul>"
        + "".join(
            f"<li>{_e(note)}</li>"
            for note in notes
        )
        + "</ul>"
    )


def render_html_report(
    snapshot: dict[str, Any],
) -> str:
    host = snapshot.get(
        "host",
        {},
    )

    gpus = snapshot.get(
        "gpus",
        [],
    )

    findings = snapshot.get(
        "findings",
        [],
    )

    status = snapshot_status(
        snapshot
    )

    driver = (
        gpus[0].get(
            "driver_version"
        )
        if gpus
        else "—"
    )

    critical = sum(
        1
        for finding in findings
        if finding.get("severity") == "CRITICAL"
    )

    high = sum(
        1
        for finding in findings
        if finding.get("severity") == "HIGH"
    )

    warning = sum(
        1
        for finding in findings
        if finding.get("severity") == "WARNING"
    )

    info = sum(
        1
        for finding in findings
        if finding.get("severity") == "INFO"
    )

    error = snapshot.get(
        "error"
    )

    error_html = ""

    if error:
        error_html = (
            '<div class="alert">'
            f"{_e(error)}"
            "</div>"
        )

    return f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>GPUNodeDiag Report - {_e(host.get("hostname"))}</title>

<style>
:root {{
    color-scheme: dark;
    --bg: #0b0f17;
    --panel: #121925;
    --panel2: #17202d;
    --line: #273346;
    --text: #e8edf5;
    --muted: #8c99ab;
    --cyan: #4fd1e8;
    --green: #52d273;
    --yellow: #f2c94c;
    --orange: #f2994a;
    --red: #ff5e69;
}}

* {{
    box-sizing: border-box;
}}

body {{
    margin: 0;
    background: var(--bg);
    color: var(--text);
    font-family:
        Inter,
        ui-sans-serif,
        system-ui,
        -apple-system,
        BlinkMacSystemFont,
        "Segoe UI",
        sans-serif;
    line-height: 1.5;
}}

.container {{
    max-width: 1500px;
    margin: 0 auto;
    padding: 36px 28px 70px;
}}

.hero {{
    background:
        linear-gradient(
            135deg,
            rgba(79, 209, 232, .13),
            rgba(82, 210, 115, .04)
        ),
        var(--panel);
    border: 1px solid var(--line);
    border-radius: 18px;
    padding: 28px;
}}

.eyebrow {{
    color: var(--cyan);
    font-weight: 700;
    letter-spacing: .12em;
    text-transform: uppercase;
    font-size: 12px;
}}

h1 {{
    margin: 6px 0 4px;
    font-size: 32px;
}}

.subtitle {{
    color: var(--muted);
}}

.summary {{
    display: grid;
    grid-template-columns:
        repeat(auto-fit, minmax(170px, 1fr));
    gap: 14px;
    margin-top: 24px;
}}

.summary-card,
.info-grid > div {{
    background: rgba(255,255,255,.025);
    border: 1px solid var(--line);
    border-radius: 12px;
    padding: 14px;
}}

.summary-card span,
.info-grid span {{
    display: block;
    color: var(--muted);
    font-size: 12px;
    margin-bottom: 4px;
}}

.summary-card strong,
.info-grid strong {{
    font-size: 16px;
}}

section {{
    margin-top: 34px;
}}

.section-title {{
    display: flex;
    align-items: center;
    justify-content: space-between;
    margin-bottom: 12px;
}}

h2 {{
    margin: 0;
    font-size: 20px;
}}

table {{
    width: 100%;
    border-collapse: collapse;
    background: var(--panel);
    border: 1px solid var(--line);
    overflow: hidden;
    border-radius: 14px;
}}

th,
td {{
    padding: 12px 11px;
    text-align: left;
    border-bottom: 1px solid var(--line);
    vertical-align: top;
}}

th {{
    color: var(--muted);
    font-size: 12px;
    text-transform: uppercase;
    letter-spacing: .04em;
}}

tr:last-child td {{
    border-bottom: 0;
}}

.model {{
    min-width: 180px;
}}

.message {{
    min-width: 300px;
    word-break: break-word;
}}

.badge {{
    display: inline-block;
    border-radius: 999px;
    padding: 3px 9px;
    font-size: 11px;
    font-weight: 800;
}}

.healthy {{
    background: rgba(82,210,115,.13);
    color: var(--green);
}}

.info {{
    background: rgba(79,209,232,.13);
    color: var(--cyan);
}}

.warning {{
    background: rgba(242,201,76,.14);
    color: var(--yellow);
}}

.high {{
    background: rgba(242,153,74,.14);
    color: var(--orange);
}}

.critical {{
    background: rgba(255,94,105,.14);
    color: var(--red);
}}

.finding {{
    background: var(--panel);
    border: 1px solid var(--line);
    border-left-width: 4px;
    border-radius: 12px;
    margin-bottom: 12px;
    padding: 17px 18px;
}}

.healthy-border {{
    border-left-color: var(--green);
}}

.info-border {{
    border-left-color: var(--cyan);
}}

.warning-border {{
    border-left-color: var(--yellow);
}}

.high-border {{
    border-left-color: var(--orange);
}}

.critical-border {{
    border-left-color: var(--red);
}}

.finding-head {{
    display: flex;
    align-items: center;
    gap: 9px;
}}

.target,
.code {{
    color: var(--muted);
    font-size: 12px;
}}

.finding h3 {{
    margin: 12px 0 5px;
}}

.finding p {{
    color: #c5cfdd;
}}

.detail-title {{
    color: var(--muted);
    text-transform: uppercase;
    font-size: 11px;
    font-weight: 800;
    margin-top: 12px;
}}

.details {{
    margin-top: 6px;
}}

.info-grid {{
    display: grid;
    grid-template-columns:
        repeat(auto-fit, minmax(190px, 1fr));
    gap: 12px;
    margin-bottom: 14px;
}}

.good-box {{
    border: 1px solid rgba(82,210,115,.4);
    background: rgba(82,210,115,.07);
    color: var(--green);
    border-radius: 12px;
    padding: 16px;
}}

.alert {{
    margin-top: 16px;
    border: 1px solid rgba(242,201,76,.4);
    background: rgba(242,201,76,.08);
    color: var(--yellow);
    border-radius: 12px;
    padding: 14px;
}}

.muted,
.empty {{
    color: var(--muted);
}}

.counts {{
    color: var(--muted);
    font-size: 13px;
}}

footer {{
    margin-top: 42px;
    color: var(--muted);
    font-size: 12px;
}}

@media print {{
    :root {{
        color-scheme: light;
    }}

    body {{
        background: white;
        color: #111;
    }}

    .hero,
    table,
    .finding,
    .summary-card,
    .info-grid > div {{
        background: white;
        color: #111;
    }}

    .container {{
        max-width: none;
        padding: 10px;
    }}
}}
</style>
</head>

<body>
<div class="container">

<header class="hero">
    <div class="eyebrow">GPUNodeDiag</div>

    <h1>GPU Node Diagnostic Report</h1>

    <div class="subtitle">
        Infrastructure health snapshot and troubleshooting evidence
    </div>

    <div class="summary">
        <div class="summary-card">
            <span>Node</span>
            <strong>{_e(host.get("hostname"))}</strong>
        </div>

        <div class="summary-card">
            <span>Status</span>
            <strong>
                <span class="badge {_status_class(status)}">
                    {_e(status)}
                </span>
            </strong>
        </div>

        <div class="summary-card">
            <span>GPUs</span>
            <strong>{len(gpus)}</strong>
        </div>

        <div class="summary-card">
            <span>Driver</span>
            <strong>{_e(driver)}</strong>
        </div>

        <div class="summary-card">
            <span>Generated UTC</span>
            <strong>{_e(snapshot.get("generated_at"))}</strong>
        </div>
    </div>

    {error_html}
</header>

<section>
    <div class="section-title">
        <h2>Host</h2>
    </div>

    <div class="info-grid">
        <div>
            <span>Operating system</span>
            <strong>{_e(host.get("operating_system"))}</strong>
        </div>

        <div>
            <span>Release</span>
            <strong>{_e(host.get("release"))}</strong>
        </div>

        <div>
            <span>Architecture</span>
            <strong>{_e(host.get("architecture"))}</strong>
        </div>

        <div>
            <span>Python</span>
            <strong>{_e(host.get("python_version"))}</strong>
        </div>

        <div>
            <span>GPUNodeDiag</span>
            <strong>{_e(snapshot.get("version"))}</strong>
        </div>
    </div>
</section>

<section>
    <div class="section-title">
        <h2>GPU Inventory & Telemetry</h2>
    </div>

    <table>
        <thead>
            <tr>
                <th>GPU</th>
                <th>Model</th>
                <th>Temp</th>
                <th>Util</th>
                <th>Power</th>
                <th>Memory</th>
                <th>PCIe</th>
                <th>ECC</th>
                <th>NVLink</th>
                <th>Status</th>
            </tr>
        </thead>

        <tbody>
            {_render_gpu_rows(snapshot)}
        </tbody>
    </table>
</section>

<section>
    <div class="section-title">
        <h2>Diagnostic Findings</h2>

        <div class="counts">
            {critical} critical ·
            {high} high ·
            {warning} warning ·
            {info} info
        </div>
    </div>

    {_render_findings(snapshot)}
</section>

<section>
    <div class="section-title">
        <h2>DCGM</h2>
    </div>

    {_render_dcgm(snapshot)}
</section>

<section>
    <div class="section-title">
        <h2>NVIDIA Xid Events</h2>
    </div>

    {_render_xids(snapshot)}
</section>

<section>
    <div class="section-title">
        <h2>Capability Notes</h2>
    </div>

    {_render_notes(snapshot)}
</section>

<footer>
    Generated by GPUNodeDiag {_e(snapshot.get("version"))}.
    This report is a diagnostic snapshot; correlate findings with
    workload behavior and platform documentation before disruptive action.
</footer>

</div>
</body>
</html>
"""


__all__ = [
    "render_html_report",
    "snapshot_status",
]
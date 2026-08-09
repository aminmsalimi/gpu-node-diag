from collections import Counter

from gpunodediag.models import Finding, Severity, XidEvent


XID_KNOWLEDGE = {
    31: {
        "severity": Severity.HIGH,
        "title": "GPU memory management fault",
        "summary": "Xid 31 indicates a GPU MMU or memory-management fault.",
        "recommendations": [
            "Review the affected application and CUDA workload.",
            "Check whether the event repeats across workloads.",
            "Run DCGM diagnostics if the issue persists.",
        ],
    },
    48: {
        "severity": Severity.CRITICAL,
        "title": "Double-bit ECC memory error",
        "summary": "Xid 48 indicates an uncorrectable GPU memory ECC condition.",
        "recommendations": [
            "Drain workloads from the affected GPU.",
            "Inspect ECC counters.",
            "Run extended DCGM memory diagnostics.",
        ],
    },
    63: {
        "severity": Severity.WARNING,
        "title": "GPU memory row/page retirement event",
        "summary": "Xid 63 indicates a GPU memory retirement-related event.",
        "recommendations": [
            "Review ECC counters.",
            "Monitor whether additional memory errors appear.",
        ],
    },
    64: {
        "severity": Severity.WARNING,
        "title": "GPU memory row-remapping event",
        "summary": "Xid 64 indicates a GPU memory row-remapping-related event.",
        "recommendations": [
            "Review ECC counters and GPU memory health.",
            "Monitor for recurring events.",
        ],
    },
    74: {
        "severity": Severity.HIGH,
        "title": "NVLink error",
        "summary": "Xid 74 indicates an NVLink-related error.",
        "recommendations": [
            "Inspect NVLink topology and link health.",
            "Run DCGM fabric diagnostics if supported.",
            "Check whether the event affects multiple GPUs.",
        ],
    },
    79: {
        "severity": Severity.CRITICAL,
        "title": "GPU fallen off the PCIe bus",
        "summary": "Xid 79 indicates loss of communication with the GPU over PCIe.",
        "recommendations": [
            "Drain workloads from the affected GPU or node.",
            "Inspect the PCIe slot, riser, and physical connection.",
            "Check GPU and system power delivery.",
            "Review whether the event repeats under load.",
        ],
    },
    94: {
        "severity": Severity.HIGH,
        "title": "Contained GPU error",
        "summary": "Xid 94 indicates a contained GPU error condition.",
        "recommendations": [
            "Review workload impact and GPU health.",
            "Run DCGM diagnostics before returning the GPU to normal service.",
        ],
    },
    95: {
        "severity": Severity.CRITICAL,
        "title": "Uncontained GPU error",
        "summary": "Xid 95 indicates an uncontained GPU error condition.",
        "recommendations": [
            "Drain workloads from the affected GPU or node.",
            "Run extended DCGM diagnostics.",
            "Investigate hardware health before reuse.",
        ],
    },
    119: {
        "severity": Severity.HIGH,
        "title": "GSP RPC timeout",
        "summary": "Xid 119 indicates a GPU System Processor communication timeout.",
        "recommendations": [
            "Review NVIDIA driver and kernel logs.",
            "Check whether the condition repeats after workload restart.",
            "Consider driver or firmware investigation if persistent.",
        ],
    },
    120: {
        "severity": Severity.HIGH,
        "title": "GSP error",
        "summary": "Xid 120 indicates a GPU System Processor error.",
        "recommendations": [
            "Review NVIDIA driver and kernel logs.",
            "Run DCGM diagnostics.",
            "Investigate driver, firmware, or GPU health if recurring.",
        ],
    },
}


def check_xid_events(events: list[XidEvent]) -> list[Finding]:
    findings: list[Finding] = []

    grouped = Counter(
        (event.xid, event.gpu_index)
        for event in events
    )

    for (xid, gpu_index), count in grouped.items():
        knowledge = XID_KNOWLEDGE.get(xid)

        if knowledge is None:
            findings.append(
                Finding(
                    code=f"XID_{xid}",
                    severity=Severity.WARNING,
                    title=f"NVIDIA Xid {xid} detected",
                    message=(
                        f"NVIDIA Xid {xid} occurred {count} time(s)."
                    ),
                    gpu_index=gpu_index,
                    evidence={
                        "xid": xid,
                        "occurrences": count,
                    },
                    recommendations=[
                        "Review the full NVIDIA kernel log entry.",
                        "Check NVIDIA documentation for this Xid code.",
                    ],
                )
            )

            continue

        findings.append(
            Finding(
                code=f"XID_{xid}",
                severity=knowledge["severity"],
                title=knowledge["title"],
                message=(
                    f"{knowledge['summary']} "
                    f"Observed {count} time(s)."
                ),
                gpu_index=gpu_index,
                evidence={
                    "xid": xid,
                    "occurrences": count,
                },
                recommendations=knowledge["recommendations"],
            )
        )

    return findings
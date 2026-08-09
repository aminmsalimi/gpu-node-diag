from gpunodediag.checks.ecc import check_ecc
from gpunodediag.checks.xid import check_xid_events
from gpunodediag.collectors.xid import parse_xid_events
from gpunodediag.models import GPUInfo, Severity


def make_gpu(**overrides):
    values = {
        "index": 0,
        "name": "NVIDIA H100 80GB HBM3",
        "uuid": "GPU-test",
        "driver_version": "580.0",
        "pci_bus_id": "00000000:41:00.0",
    }

    values.update(overrides)

    return GPUInfo(**values)


def test_corrected_ecc_error_is_warning():
    gpu = make_gpu(
        ecc_supported=True,
        ecc_enabled=True,
        ecc_corrected_volatile=7,
        ecc_uncorrected_volatile=0,
    )

    findings = check_ecc(gpu)

    assert any(
        item.code == "ECC_CORRECTED_ERRORS"
        and item.severity is Severity.WARNING
        for item in findings
    )


def test_uncorrected_ecc_error_is_critical():
    gpu = make_gpu(
        ecc_supported=True,
        ecc_enabled=True,
        ecc_corrected_volatile=0,
        ecc_uncorrected_volatile=2,
    )

    findings = check_ecc(gpu)

    assert any(
        item.code == "ECC_UNCORRECTED_ERRORS"
        and item.severity is Severity.CRITICAL
        for item in findings
    )


def test_xid_parser_maps_pci_bus_to_gpu():
    gpu = make_gpu()

    log = (
        "kernel: NVRM: Xid (PCI:0000:41:00): 79, "
        "GPU has fallen off the bus."
    )

    events = parse_xid_events(
        log,
        [gpu],
    )

    assert len(events) == 1
    assert events[0].xid == 79
    assert events[0].gpu_index == 0


def test_xid_79_is_critical():
    gpu = make_gpu()

    events = parse_xid_events(
        "NVRM: Xid (PCI:0000:41:00): 79, test",
        [gpu],
    )

    findings = check_xid_events(events)

    assert any(
        item.code == "XID_79"
        and item.severity is Severity.CRITICAL
        for item in findings
    )


def test_multiple_same_xids_are_grouped():
    gpu = make_gpu()

    log = """
NVRM: Xid (PCI:0000:41:00): 74, first
NVRM: Xid (PCI:0000:41:00): 74, second
NVRM: Xid (PCI:0000:41:00): 74, third
"""

    events = parse_xid_events(
        log,
        [gpu],
    )

    findings = check_xid_events(events)

    xid74 = next(
        item
        for item in findings
        if item.code == "XID_74"
    )

    assert xid74.evidence["occurrences"] == 3
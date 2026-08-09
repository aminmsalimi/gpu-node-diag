import re

from gpunodediag.models import GPUInfo, XidEvent


XID_PATTERN = re.compile(
    r"Xid\s+\(PCI:(?P<pci>[0-9a-fA-F:.]+)\):\s*(?P<xid>\d+)",
    re.IGNORECASE,
)


def _normalize_bus_id(value: str | None) -> str | None:
    if not value:
        return None

    value = value.lower().strip()

    if value.startswith("pci:"):
        value = value[4:]

    # nvidia-smi commonly returns:
    # 00000000:41:00.0
    #
    # Kernel Xid logs commonly contain:
    # 0000:41:00
    #
    # Normalize both to:
    # 41:00

    if "." in value:
        value = value.split(".", 1)[0]

    parts = value.split(":")

    if len(parts) >= 2:
        return ":".join(parts[-2:])

    return value


def parse_xid_events(
    text: str,
    gpus: list[GPUInfo],
) -> list[XidEvent]:
    events: list[XidEvent] = []

    gpu_by_bus: dict[str, int] = {}

    for gpu in gpus:
        normalized = _normalize_bus_id(gpu.pci_bus_id)

        if normalized:
            gpu_by_bus[normalized] = gpu.index

    for line in text.splitlines():
        if "xid" not in line.lower():
            continue

        match = XID_PATTERN.search(line)

        if not match:
            continue

        xid = int(match.group("xid"))
        pci = match.group("pci")
        normalized_pci = _normalize_bus_id(pci)

        gpu_index = None

        if normalized_pci:
            gpu_index = gpu_by_bus.get(normalized_pci)

        events.append(
            XidEvent(
                xid=xid,
                raw_message=line.strip(),
                pci_bus_id=pci,
                gpu_index=gpu_index,
            )
        )

    return events
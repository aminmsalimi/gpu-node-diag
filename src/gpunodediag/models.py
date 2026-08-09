from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Optional


class Severity(Enum):
    INFO = 1
    WARNING = 2
    HIGH = 3
    CRITICAL = 4


@dataclass
class Finding:
    code: str
    severity: Severity
    title: str
    message: str
    gpu_index: Optional[int] = None
    evidence: dict[str, Any] = field(default_factory=dict)
    recommendations: list[str] = field(default_factory=list)


@dataclass
class HostInfo:
    hostname: str
    operating_system: str
    release: str
    architecture: str
    python_version: str


@dataclass
class XidEvent:
    xid: int
    raw_message: str
    pci_bus_id: Optional[str] = None
    gpu_index: Optional[int] = None
    timestamp: Optional[str] = None


@dataclass
class FabricManagerStatus:
    installed: Optional[bool] = None
    active: Optional[bool] = None
    load_state: Optional[str] = None
    active_state: Optional[str] = None


@dataclass
class GPUInfo:
    index: int
    name: str
    uuid: str
    driver_version: str

    pci_bus_id: Optional[str] = None

    temperature_c: Optional[float] = None
    power_draw_w: Optional[float] = None
    power_limit_w: Optional[float] = None

    utilization_percent: Optional[float] = None
    memory_used_mb: Optional[float] = None
    memory_total_mb: Optional[float] = None

    pcie_generation: Optional[str] = None
    pcie_generation_max: Optional[str] = None
    pcie_width: Optional[str] = None
    pcie_width_max: Optional[str] = None

    persistence_mode: Optional[str] = None
    mig_mode: Optional[str] = None

    # NVML clock event state
    clock_event_mask: Optional[int] = None
    clock_event_sw_power_cap: Optional[bool] = None
    clock_event_hw_slowdown: Optional[bool] = None
    clock_event_sw_thermal_slowdown: Optional[bool] = None

    # ECC
    ecc_supported: Optional[bool] = None
    ecc_enabled: Optional[bool] = None
    ecc_corrected_volatile: Optional[int] = None
    ecc_uncorrected_volatile: Optional[int] = None

    # NVLink / GPU fabric
    nvlink_supported: Optional[bool] = None
    nvlink_total_links: int = 0
    nvlink_active_links: int = 0
    nvlink_inactive_links: list[int] = field(default_factory=list)
    nvlink_error_counts: dict[str, int] = field(default_factory=dict)

    fabric_state: Optional[str] = None
    fabric_status: Optional[str] = None
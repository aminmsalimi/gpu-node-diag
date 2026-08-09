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

@dataclass
class DCGMStatus:
    installed: bool = False
    version: Optional[str] = None
    hostengine_reachable: Optional[bool] = None
    discovery_ok: Optional[bool] = None
    error: Optional[str] = None


@dataclass
class DCGMTestResult:
    name: str
    status: str
    entity_group: Optional[str] = None
    entity_id: Optional[int] = None
    info: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)

@dataclass
class ContainerRuntimeInfo:
    name: str
    installed: bool = False
    executable: Optional[str] = None
    active: Optional[bool] = None
    nvidia_configured: Optional[bool] = None
    config_paths: list[str] = field(default_factory=list)


@dataclass
class ContainerStatus:
    platform: str
    runtimes: list[ContainerRuntimeInfo] = field(default_factory=list)
    nvidia_ctk: bool = False
    nvidia_ctk_version: Optional[str] = None
    nvidia_container_runtime: bool = False
    nvidia_container_cli: bool = False
    device_nodes: list[str] = field(default_factory=list)
    missing_device_nodes: list[str] = field(default_factory=list)
    cdi_devices: list[str] = field(default_factory=list)
    cdi_error: Optional[str] = None
    notes: list[str] = field(default_factory=list)


@dataclass
class KubernetesGPUNode:
    name: str
    gpu_capacity: int = 0
    gpu_allocatable: int = 0
    mig_capacity: dict[str, int] = field(default_factory=dict)
    mig_allocatable: dict[str, int] = field(default_factory=dict)


@dataclass
class KubernetesPodStatus:
    namespace: str
    name: str
    phase: str
    ready: bool = False
    restarts: int = 0


@dataclass
class KubernetesStatus:
    kubectl_installed: bool = False
    kubectl_path: Optional[str] = None
    client_version: Optional[str] = None
    current_context: Optional[str] = None
    cluster_reachable: Optional[bool] = None
    nodes: list[KubernetesGPUNode] = field(default_factory=list)
    device_plugin_pods: list[KubernetesPodStatus] = field(default_factory=list)
    error: Optional[str] = None
    notes: list[str] = field(default_factory=list)
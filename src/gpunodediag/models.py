from dataclasses import dataclass
from typing import Optional


@dataclass
class HostInfo:
    hostname: str
    operating_system: str
    release: str
    architecture: str
    python_version: str


@dataclass
class GPUInfo:
    index: int
    name: str
    uuid: str
    driver_version: str

    temperature_c: Optional[float] = None
    power_draw_w: Optional[float] = None
    power_limit_w: Optional[float] = None

    utilization_percent: Optional[float] = None
    memory_used_mb: Optional[float] = None
    memory_total_mb: Optional[float] = None

    pcie_generation: Optional[str] = None
    pcie_width: Optional[str] = None

    persistence_mode: Optional[str] = None
    mig_mode: Optional[str] = None

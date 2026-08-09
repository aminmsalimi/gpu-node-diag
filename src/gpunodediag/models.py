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
    pcie_generation_max: Optional[str] = None
    pcie_width: Optional[str] = None
    pcie_width_max: Optional[str] = None

    persistence_mode: Optional[str] = None
    mig_mode: Optional[str] = None

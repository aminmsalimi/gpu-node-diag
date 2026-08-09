import platform
import socket

from gpunodediag.models import HostInfo


def collect_host_info() -> HostInfo:
    return HostInfo(
        hostname=socket.gethostname(),
        operating_system=platform.system(),
        release=platform.release(),
        architecture=platform.machine(),
        python_version=platform.python_version(),
    )

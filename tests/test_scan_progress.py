from io import StringIO

from rich.console import Console

from gpunodediag.output.progress import (
    ScanProgress,
)


def _render(
    progress: ScanProgress,
) -> str:
    output = StringIO()

    console = Console(
        file=output,
        force_terminal=False,
        width=140,
    )

    console.print(
        progress.render()
    )

    return output.getvalue()


def test_scan_progress_pass_state():
    console = Console(
        file=StringIO()
    )

    progress = ScanProgress(
        console=console,
    )

    progress.pass_(
        "host",
        "gpu-node-01",
    )

    progress.pass_(
        "gpu",
        "4 NVIDIA GPUs detected",
    )

    progress.set_overall(
        "PASS",
        "Node health checks completed",
    )

    text = _render(
        progress
    )

    assert "Node inventory" in text
    assert "NVIDIA GPU discovery" in text
    assert "PASS" in text
    assert "gpu-node-01" in text


def test_scan_progress_warning_state():
    console = Console(
        file=StringIO()
    )

    progress = ScanProgress(
        console=console,
    )

    progress.warning(
        "xid",
        "1 NVIDIA Xid event found",
    )

    progress.set_overall(
        "ATTENTION",
        "Review diagnostic warnings",
    )

    text = _render(
        progress
    )

    assert "WARN" in text
    assert "ATTENTION" in text
    assert "Xid" in text


def test_deep_scan_adds_dcgm_step():
    console = Console(
        file=StringIO()
    )

    progress = ScanProgress(
        console=console,
        deep=True,
    )

    text = _render(
        progress
    )

    assert (
        "DCGM Level 2 diagnostics"
        in text
    )


def test_completed_count():
    console = Console(
        file=StringIO()
    )

    progress = ScanProgress(
        console=console,
    )

    assert (
        progress.completed_count()
        == 0
    )

    progress.pass_(
        "host"
    )

    progress.skip(
        "fabric_manager"
    )

    progress.warning(
        "xid"
    )

    assert (
        progress.completed_count()
        == 3
    )
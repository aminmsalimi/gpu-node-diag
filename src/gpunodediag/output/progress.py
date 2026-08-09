import os
import time
from dataclasses import dataclass

from rich import box
from rich.console import Console, Group
from rich.live import Live
from rich.panel import Panel
from rich.table import Table
from rich.text import Text


FINAL_STATES = {
    "pass",
    "warn",
    "fail",
    "skip",
}


@dataclass
class ScanStep:
    key: str
    label: str
    state: str = "pending"
    detail: str = ""


class ScanProgress:
    """
    Live GPUNodeDiag diagnostic checklist.

    Human-facing terminal scans intentionally remain visible long
    enough for the user to follow the individual diagnostic stages.

    JSON/non-interactive execution is never artificially delayed.
    """

    def __init__(
        self,
        console: Console,
        deep: bool = False,
        minimum_duration: float = 7.0,
    ) -> None:
        self.console = console

        # Only animate/delay when connected to a real interactive terminal.
        #
        # This keeps:
        #   pytest
        #   gdiag --json
        #   redirected output
        #   automation
        #
        # fast.
        self.animated = (
            bool(console.is_terminal)
            and os.environ.get(
                "GDIAG_NO_ANIMATION",
                "",
            ).lower()
            not in {
                "1",
                "true",
                "yes",
            }
        )

        self.minimum_duration = (
            minimum_duration
            if self.animated
            else 0.0
        )

        self.step_pause = (
            0.30
            if self.animated
            else 0.0
        )

        self._started_at: float | None = None

        definitions = [
            (
                "host",
                "Node inventory",
            ),
            (
                "gpu",
                "NVIDIA GPU discovery",
            ),
            (
                "nvml",
                "NVML telemetry & ECC",
            ),
            (
                "dcgm",
                "DCGM service",
            ),
            (
                "fabric_manager",
                "Fabric Manager",
            ),
            (
                "fabric",
                "NVLink / GPU fabric",
            ),
            (
                "xid",
                "Kernel / Xid history",
            ),
        ]

        if deep:
            definitions.append(
                (
                    "dcgm_deep",
                    "DCGM Level 2 diagnostics",
                )
            )

        definitions.append(
            (
                "analysis",
                "Diagnostic rules",
            )
        )

        self.steps = {
            key: ScanStep(
                key=key,
                label=label,
            )
            for key, label in definitions
        }

        self._order = [
            key
            for key, _ in definitions
        ]

        self.live: Live | None = None

        self.overall_label = "SCANNING"
        self.overall_style = "cyan"
        self.overall_detail = (
            "Running NVIDIA GPU node checks"
        )

    def start(self) -> None:
        if self.live is not None:
            return

        self._started_at = time.monotonic()

        self.live = Live(
            self.render(),
            console=self.console,
            refresh_per_second=12,
            transient=False,
            vertical_overflow="visible",
        )

        self.live.start()

    def stop(self) -> None:
        if self.live is None:
            return

        final_label = self.overall_label
        final_style = self.overall_style
        final_detail = self.overall_detail

        # ----------------------------------------------------
        # Presentation phase
        #
        # If the real diagnostics completed extremely quickly,
        # keep the terminal UI alive until the minimum scan
        # duration has elapsed.
        #
        # A real slow scan is never delayed further.
        # ----------------------------------------------------

        if (
            self.animated
            and self._started_at is not None
        ):
            elapsed = (
                time.monotonic()
                - self._started_at
            )

            remaining = max(
                0.0,
                self.minimum_duration
                - elapsed,
            )

            frame = 0

            while remaining > 0:
                dots = "." * (
                    (frame % 3) + 1
                )

                self.overall_label = (
                    "FINALIZING"
                )

                self.overall_style = "cyan"

                self.overall_detail = (
                    "Correlating findings "
                    f"and preparing results{dots}"
                )

                self.live.update(
                    self.render(),
                    refresh=True,
                )

                sleep_time = min(
                    0.25,
                    remaining,
                )

                time.sleep(
                    sleep_time
                )

                remaining -= sleep_time
                frame += 1

        # ----------------------------------------------------
        # Restore the real final result
        # ----------------------------------------------------

        self.overall_label = final_label
        self.overall_style = final_style
        self.overall_detail = final_detail

        self.live.update(
            self.render(),
            refresh=True,
        )

        # Briefly leave the final verdict visible before
        # printing the detailed diagnostic tables.
        if self.animated:
            time.sleep(0.55)

        self.live.stop()
        self.live = None

    def _update(self) -> None:
        if self.live is not None:
            self.live.update(
                self.render(),
                refresh=True,
            )

    def set(
        self,
        key: str,
        state: str,
        detail: str = "",
    ) -> None:
        step = self.steps[key]
        step.state = state
        step.detail = detail

        self._update()

        # Let each completed checkbox remain visible briefly so
        # the scan feels sequential instead of all results
        # appearing in one frame.
        if (
            self.animated
            and state in FINAL_STATES
            and self.live is not None
        ):
            time.sleep(
                self.step_pause
            )

    def checking(
        self,
        key: str,
        detail: str = "",
    ) -> None:
        self.set(
            key,
            "checking",
            detail,
        )

    def pass_(
        self,
        key: str,
        detail: str = "",
    ) -> None:
        self.set(
            key,
            "pass",
            detail,
        )

    def warning(
        self,
        key: str,
        detail: str = "",
    ) -> None:
        self.set(
            key,
            "warn",
            detail,
        )

    def fail(
        self,
        key: str,
        detail: str = "",
    ) -> None:
        self.set(
            key,
            "fail",
            detail,
        )

    def skip(
        self,
        key: str,
        detail: str = "",
    ) -> None:
        self.set(
            key,
            "skip",
            detail,
        )

    def set_overall(
        self,
        label: str,
        detail: str,
    ) -> None:
        self.overall_label = label
        self.overall_detail = detail

        normalized = label.upper()

        if normalized in {
            "PASS",
            "HEALTHY",
        }:
            self.overall_style = "green"

        elif normalized in {
            "ATTENTION",
            "WARNING",
            "DEGRADED",
            "HIGH",
        }:
            self.overall_style = "yellow"

        elif normalized == "CRITICAL":
            self.overall_style = "red"

        else:
            self.overall_style = "cyan"

        self._update()

    def completed_count(self) -> int:
        return sum(
            1
            for step in self.steps.values()
            if step.state in FINAL_STATES
        )

    def _state_cell(
        self,
        state: str,
    ) -> Text:
        if state == "pass":
            text = Text()
            text.append(
                "☑ ",
                style="bold green",
            )
            text.append(
                "PASS",
                style="bold green",
            )
            return text

        if state == "warn":
            text = Text()
            text.append(
                "⚠ ",
                style="bold yellow",
            )
            text.append(
                "WARN",
                style="bold yellow",
            )
            return text

        if state == "fail":
            text = Text()
            text.append(
                "☒ ",
                style="bold red",
            )
            text.append(
                "FAIL",
                style="bold red",
            )
            return text

        if state == "skip":
            text = Text()
            text.append(
                "⊟ ",
                style="dim",
            )
            text.append(
                "SKIP",
                style="dim",
            )
            return text

        if state == "checking":
            text = Text()
            text.append(
                "◉ ",
                style="bold cyan",
            )
            text.append(
                "CHECKING",
                style="bold cyan",
            )
            return text

        text = Text()
        text.append(
            "☐ ",
            style="dim",
        )
        text.append(
            "WAITING",
            style="dim",
        )

        return text

    def render(self):
        table = Table(
            box=box.SIMPLE_HEAD,
            expand=True,
            show_edge=False,
            pad_edge=False,
        )

        table.add_column(
            "",
            width=13,
            no_wrap=True,
        )

        table.add_column(
            "Check",
            style="bold",
            ratio=2,
        )

        table.add_column(
            "Result",
            ratio=3,
        )

        for key in self._order:
            step = self.steps[key]

            detail = Text(
                step.detail or "",
                style="dim",
            )

            table.add_row(
                self._state_cell(
                    step.state
                ),
                Text(
                    step.label
                ),
                detail,
            )

        completed = self.completed_count()
        total = len(self.steps)

        ratio = (
            completed / total
            if total
            else 0
        )

        blocks = 22

        filled = round(
            blocks * ratio
        )

        bar = (
            "█" * filled
            + "░" * (
                blocks - filled
            )
        )

        progress_line = Text()

        progress_line.append(
            bar,
            style=(
                self.overall_style
                if completed == total
                else "cyan"
            ),
        )

        progress_line.append(
            f"  {completed}/{total} checks complete",
            style="dim",
        )

        verdict = Text(
            justify="center",
        )

        verdict.append(
            self.overall_label,
            style=(
                f"bold {self.overall_style}"
            ),
        )

        if self.overall_detail:
            verdict.append(
                "  •  ",
                style="dim",
            )

            verdict.append(
                self.overall_detail,
                style="dim",
            )

        return Panel(
            Group(
                table,
                progress_line,
                Text(""),
                verdict,
            ),
            title=(
                "[bold cyan]"
                "GPUNodeDiag System Check"
                "[/bold cyan]"
            ),
            subtitle=(
                "[dim]"
                "NVIDIA infrastructure health analysis"
                "[/dim]"
            ),
            border_style=self.overall_style,
            padding=(0, 2),
        )


__all__ = [
    "ScanProgress",
    "ScanStep",
]
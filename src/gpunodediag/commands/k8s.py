import json
from dataclasses import asdict

import typer
from rich import box
from rich.panel import Panel
from rich.table import Table

from gpunodediag.checks.kubernetes import (
    check_kubernetes_gpu_stack,
)
from gpunodediag.collectors.kubernetes import (
    collect_kubernetes_status,
)
from gpunodediag.output.terminal import (
    console,
    print_findings,
)


def k8s_command(
    json_output: bool = typer.Option(
        False,
        "--json",
        help="Output machine-readable JSON.",
    ),
) -> None:
    """
    Diagnose Kubernetes NVIDIA GPU integration.
    """

    status = collect_kubernetes_status()

    findings = check_kubernetes_gpu_stack(
        status
    )

    if json_output:
        typer.echo(
            json.dumps(
                {
                    "kubernetes": asdict(
                        status
                    ),
                    "findings": [
                        {
                            **asdict(item),
                            "severity": item.severity.name,
                        }
                        for item in findings
                    ],
                },
                indent=2,
            )
        )

        return

    console.print(
        Panel(
            (
                "kubectl: "
                + (
                    "[green]FOUND[/green]"
                    if status.kubectl_installed
                    else "[yellow]NOT FOUND[/yellow]"
                )
                + "\n"
                f"Client: {status.client_version or 'N/A'}\n"
                f"Context: {status.current_context or 'N/A'}\n"
                "Cluster: "
                + (
                    "[green]REACHABLE[/green]"
                    if status.cluster_reachable is True
                    else (
                        "[red]UNREACHABLE[/red]"
                        if status.cluster_reachable is False
                        else "[dim]UNKNOWN[/dim]"
                    )
                )
            ),
            title="Kubernetes GPU Stack",
            border_style="cyan",
        )
    )

    if status.nodes:
        node_table = Table(
            title="GPU Resources",
            box=box.ROUNDED,
        )

        node_table.add_column(
            "Node"
        )

        node_table.add_column(
            "GPU Capacity",
            justify="right",
        )

        node_table.add_column(
            "GPU Allocatable",
            justify="right",
        )

        node_table.add_column(
            "MIG Resources",
            justify="right",
        )

        for node in status.nodes:
            mig_total = sum(
                node.mig_allocatable.values()
            )

            node_table.add_row(
                node.name,
                str(node.gpu_capacity),
                str(node.gpu_allocatable),
                str(mig_total),
            )

        console.print(
            node_table
        )

    if status.device_plugin_pods:
        pod_table = Table(
            title="NVIDIA Device Plugin",
            box=box.ROUNDED,
        )

        pod_table.add_column(
            "Namespace"
        )

        pod_table.add_column(
            "Pod"
        )

        pod_table.add_column(
            "Phase"
        )

        pod_table.add_column(
            "Ready"
        )

        pod_table.add_column(
            "Restarts",
            justify="right",
        )

        for pod in status.device_plugin_pods:
            pod_table.add_row(
                pod.namespace,
                pod.name,
                pod.phase,
                (
                    "[green]YES[/green]"
                    if pod.ready
                    else "[red]NO[/red]"
                ),
                str(pod.restarts),
            )

        console.print(
            pod_table
        )

    if status.error:
        console.print(
            f"[red]{status.error}[/red]"
        )

    print_findings(
        findings
    )

    for note in status.notes:
        console.print(
            f"[dim]Capability note: {note}[/dim]"
        )
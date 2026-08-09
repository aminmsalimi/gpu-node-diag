import json
from dataclasses import asdict
from typing import Optional

import typer

from gpunodediag import __version__
from gpunodediag.collectors.nvidia_smi import collect_gpus
from gpunodediag.collectors.system import collect_host_info
from gpunodediag.output.terminal import (
    console,
    print_banner,
    print_gpu_error,
    print_gpus,
    print_host,
)


app = typer.Typer(
    name="gdiag",
    help="NVIDIA GPU node diagnostics and troubleshooting.",
    add_completion=False,
    no_args_is_help=False,
)


@app.callback(invoke_without_command=True)
def run(
    ctx: typer.Context,
    gpu: Optional[int] = typer.Option(
        None,
        "--gpu",
        "-g",
        help="Inspect only a specific GPU index.",
    ),
    json_output: bool = typer.Option(
        False,
        "--json",
        help="Output machine-readable JSON.",
    ),
    version: bool = typer.Option(
        False,
        "--version",
        "-V",
        is_eager=True,
        help="Show GPUNodeDiag version.",
    ),
) -> None:
    if version:
        console.print(f"GPUNodeDiag {__version__}")
        raise typer.Exit()

    if ctx.invoked_subcommand is not None:
        return

    host = collect_host_info()
    gpus, error = collect_gpus()

    if gpu is not None:
        gpus = [item for item in gpus if item.index == gpu]

        if not gpus and error is None:
            error = f"GPU index {gpu} was not found"

    if json_output:
        payload = {
            "tool": "GPUNodeDiag",
            "version": __version__,
            "host": asdict(host),
            "gpus": [asdict(item) for item in gpus],
            "error": error,
        }

        typer.echo(json.dumps(payload, indent=2))
        return

    print_banner(__version__)
    print_host(host)

    if error:
        print_gpu_error(error)
    else:
        print_gpus(gpus)


def main() -> None:
    app()


if __name__ == "__main__":
    main()

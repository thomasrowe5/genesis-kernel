"""Typer CLI for Genesis Kernel."""
from __future__ import annotations

import json
import os
import time
import urllib.request
from typing import Any, Dict, Optional

import typer

app = typer.Typer(help="Interact with the Genesis Kernel control plane")


def _base_url() -> str:
    return os.getenv("GENESIS_API_URL", "http://localhost:8000")


def _post(path: str, payload: Dict[str, Any]) -> Dict[str, Any]:
    data = json.dumps(payload).encode()
    req = urllib.request.Request(
        f"{_base_url()}{path}", data=data, headers={"Content-Type": "application/json"}
    )
    with urllib.request.urlopen(req) as response:
        return json.loads(response.read().decode())


def _get(path: str) -> Dict[str, Any]:
    with urllib.request.urlopen(f"{_base_url()}{path}") as response:
        return json.loads(response.read().decode())


@app.command()
def enqueue(
    task: str = typer.Argument(..., help="Task type"),
    n: Optional[int] = typer.Option(None, help="Fibonacci argument"),
    url: Optional[str] = typer.Option(None, help="URL for http_fetch"),
    seconds: Optional[float] = typer.Option(None, help="Sleep duration"),
) -> None:
    args: list[Any] = []
    kwargs: Dict[str, Any] = {}
    if task == "fibonacci":
        if n is None:
            raise typer.BadParameter("--n is required for fibonacci")
        args.append(n)
    elif task == "http_fetch":
        if url is None:
            raise typer.BadParameter("--url is required for http_fetch")
        kwargs["url"] = url
    elif task == "sleep":
        kwargs["seconds"] = seconds or 1
    payload = {"task_type": task, "args": args, "kwargs": kwargs}
    result = _post("/jobs", payload)
    typer.echo(f"Enqueued job {result['job_id']}")


@app.command()
def stats() -> None:
    result = _get("/stats")
    typer.echo(json.dumps(result, indent=2))


@app.command()
def tail(
    state: str = typer.Option("failed", help="Job state to filter"),
    interval: float = typer.Option(2.0, help="Polling interval seconds"),
    iterations: int = typer.Option(5, help="Number of polls"),
) -> None:
    for _ in range(iterations):
        jobs = _get(f"/jobs?state={state}")
        typer.echo(json.dumps(jobs, indent=2))
        time.sleep(interval)


def main() -> None:
    app()


if __name__ == "__main__":  # pragma: no cover
    main()

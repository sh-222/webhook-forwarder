"""CLI interface with Rich formatting."""

from __future__ import annotations

from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from core.settings import settings

console = Console()


def print_banner() -> None:
    """Print application banner."""
    banner = Panel(
        "[bold cyan]Async Rate-Limited Webhook Forwarder & DLQ[/bold cyan]\n"
        f"[dim]Workers: {settings.worker_count} | "
        f"Rate Limit: {settings.rate_limit_rate} tok/s | "
        f"Queue Max: {settings.queue_max_size}[/dim]",
        border_style="cyan",
    )
    console.print(banner)


def print_event_submitted(event_id: str, target_url: str, priority: int) -> None:
    """Print event submission confirmation."""
    console.print(
        f"  [green]✓[/green] Event [cyan]{event_id[:8]}[/cyan] → "
        f"[yellow]{target_url}[/yellow] (priority={priority})"
    )


def print_event_delivered(event_id: str, target_url: str, status: int) -> None:
    """Print event delivery confirmation."""
    console.print(
        f"  [green]✓[/green] Delivered [cyan]{event_id[:8]}[/cyan] → "
        f"[yellow]{target_url}[/yellow] [green]{status}[/green]"
    )


def print_event_failed(event_id: str, target_url: str, error: str) -> None:
    """Print event failure."""
    console.print(
        f"  [red]✗[/red] Failed [cyan]{event_id[:8]}[/cyan] → "
        f"[yellow]{target_url}[/yellow] [red]{error}[/red]"
    )


def print_dlq_entry(event_id: str, target_url: str, error: str) -> None:
    """Print DLQ entry notification."""
    console.print(
        f"  [red bold]☠ DLQ[/red bold] [cyan]{event_id[:8]}[/cyan] → "
        f"[yellow]{target_url}[/yellow] [red]{error}[/red]"
    )


def print_stats(
    total: int,
    delivered: int,
    failed: int,
    dlq: int,
) -> None:
    """Print final statistics table."""
    table = Table(title="Delivery Statistics", border_style="blue")
    table.add_column("Metric", style="cyan")
    table.add_column("Value", justify="right", style="green")

    table.add_row("Total Events", str(total))
    table.add_row("Delivered", str(delivered))
    table.add_row("Failed (retried)", str(failed))
    table.add_row("Dead Letter Queue", str(dlq))

    console.print(table)


def print_shutdown(message: str = "Shutting down gracefully...") -> None:
    """Print shutdown message."""
    console.print(f"\n[yellow]{message}[/yellow]")

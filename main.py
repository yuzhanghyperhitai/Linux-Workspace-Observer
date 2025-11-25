"""LWO CLI entry point."""

import click

from lwo.daemon import start_daemon, stop_daemon
from lwo.cli.commands import report_command, daily_report


@click.group()
def cli():
    """Linux Workspace Observer - Intelligent work status monitoring assistant."""
    pass


@cli.command()
def start():
    """Start LWO daemon."""
    start_daemon()


@cli.command()
def stop():
    """Stop LWO daemon."""
    stop_daemon()


@cli.command()
def report():
    """Display current work status report."""
    report_command()


@cli.command()
def daily():
    """Generate daily work report."""
    daily_report()


if __name__ == '__main__':
    cli()


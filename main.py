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
@click.option('--hours', default=4, help='Hours to look back (default: 4)')
def report(hours):
    """Display current work status report."""
    report_command(hours=hours)


@cli.command()
def daily():
    """Generate daily work report."""
    daily_report()


if __name__ == '__main__':
    cli()


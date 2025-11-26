"""CLI commands for LWO."""

from lwo.reporting import WorkSummaryGenerator


def report_command(hours: int = 4):
    """Displays current work status report.
    
    Args:
        hours: Number of hours to look back (default: 4)
    """
    try:
        generator = WorkSummaryGenerator()
        summary = generator.generate_summary(hours=hours)
        output = generator.format_summary(summary)
        
        print(output)
    
    except Exception as e:
        print(f"❌ Error generating report: {e}")
        import traceback
        traceback.print_exc()


def daily_report():
    """Generates daily work report."""
    print("\n📋 Generating daily report...\n")
    report_command(hours=24)

"""CLI commands for LWO."""

from lwo.storage.database import get_database
from lwo.utils.logger import setup_logger

logger = setup_logger(__name__)


def report_command():
    """Display current work status report."""
    db = get_database()
    
    print("\n=== LWO Work Status Report ===\n")
    
    # Get latest analysis
    with db.session() as session:
        result = session.execute(
            """
            SELECT ts, status, summary, confidence
            FROM analyses
            ORDER BY ts DESC
            LIMIT 1
            """
        ).fetchone()
        
        if result:
            import time
            from datetime import datetime
            
            ts, status, summary, confidence = result
            dt = datetime.fromtimestamp(ts)
            
            print(f"Time: {dt.strftime('%Y-%m-%d %H:%M:%S')}")
            print(f"Status: {status}")
            print(f"Summary: {summary}")
            if confidence:
                print(f"Confidence: {confidence:.2f}")
        else:
            print("No analysis data available yet.")
            print("The AI analysis will be available after collecting enough activity data.")
    
    print()


def daily_report():
    """Generate daily work report."""
    import time
    from datetime import datetime
    from pathlib import Path
    
    from lwo.config import get_config
    
    config = get_config()
    db = get_database()
    
    # Get today's data
    today_start = int(time.mktime(datetime.now().replace(hour=0, minute=0, second=0).timetuple()))
    today_end = int(time.time())
    
    print("\n=== Generating Daily Report ===\n")
    
    # Collect statistics
    with db.session() as session:
        # Command count
        cmd_count = session.execute(
            "SELECT COUNT(*) FROM shell_commands WHERE ts >= :start AND ts <= :end",
            {'start': today_start, 'end': today_end}
        ).scalar()
        
        # File event count
        file_count = session.execute(
            "SELECT COUNT(DISTINCT file_path) FROM file_events WHERE ts >= :start AND ts <= :end",
            {'start': today_start, 'end': today_end}
        ).scalar()
        
        # Latest status
        status_result = session.execute(
            """
            SELECT status, summary
            FROM analyses
            WHERE ts >= :start AND ts <= :end
            ORDER BY ts DESC
            LIMIT 1
            """,
            {'start': today_start, 'end': today_end}
        ).fetchone()
    
    # Generate report
    today_str = datetime.now().strftime('%Y-%m-%d')
    report_dir = Path(config.get('reporting', 'report_output_dir')).expanduser()
    report_dir.mkdir(parents=True, exist_ok=True)
    
    report_file = report_dir / f"report-{today_str}.md"
    
    with open(report_file, 'w') as f:
        f.write(f"# Work Report - {today_str}\n\n")
        
        f.write("## Statistics\n\n")
        f.write(f"- Commands executed: {cmd_count or 0}\n")
        f.write(f"- Files modified: {file_count or 0}\n\n")
        
        if status_result:
            status, summary = status_result
            f.write("## Work Status\n\n")
            f.write(f"**Status**: {status}\n\n")
            f.write(f"**Summary**: {summary}\n\n")
        else:
            f.write("## Work Status\n\n")
            f.write("No AI analysis available for today.\n\n")
    
    print(f"Daily report generated: {report_file}")
    print()

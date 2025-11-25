"""CLI commands for LWO."""

from sqlalchemy import text

from lwo.storage.database import get_database
from lwo.utils.logger import setup_logger

logger = setup_logger(__name__)


def report_command():
    """Display current work status report."""
    import time
    from datetime import datetime
    
    db = get_database()
    
    print("\n" + "="*60)
    print("         LWO WORK STATUS REPORT")
    print("="*60 + "\n")
    
    # Get latest analysis
    with db.session() as session:
        # Latest AI analysis
        result = session.execute(
            text("""
            SELECT ts, status, summary, confidence
            FROM analyses
            ORDER BY ts DESC
            LIMIT 1
            """)
        ).fetchone()
        
        if result:
            ts, status, summary, confidence = result
            dt = datetime.fromtimestamp(ts)
            
            print(f"📊 Analysis Time: {dt.strftime('%Y-%m-%d %H:%M:%S')}")
            print(f"🎯 Work Status:   {status}")
            print(f"📝 Summary:       {summary}")
            if confidence:
                print(f"✓  Confidence:    {confidence:.0%}")
            print()
        else:
            print("⚠️  No AI analysis available yet.")
            print("   The analyzer runs every 10 minutes after collecting data.")
            print()
        
        # Recent activity stats (last 10 minutes)
        ten_min_ago = int(time.time()) - 600
        
        cmd_count = session.execute(
            text("SELECT COUNT(*) FROM shell_commands WHERE ts >= :ts"),
            {'ts': ten_min_ago}
        ).scalar()
        
        # Get Git context
        git_result = session.execute(
            text("""
            SELECT repo_path, branch, branch_type
            FROM git_contexts
            ORDER BY ts DESC
            LIMIT 1
            """)
        ).fetchone()
        
        # Get aggregated events
        event_results = session.execute(
            text("""
            SELECT event_type, description
            FROM aggregated_events
            WHERE start_time >= :ts
            ORDER BY start_time DESC
            LIMIT 3
            """),
            {'ts': ten_min_ago}
        ).fetchall()
    
    print("-" * 60)
    print("RECENT ACTIVITY (Last 10 minutes)")
    print("-" * 60)
    print(f"Commands executed: {cmd_count or 0}")
    
    if git_result:
        repo_path, branch, branch_type = git_result
        print(f"Current Git branch: {branch} ({branch_type})")
        print(f"Repository: {repo_path}")
    
    if event_results:
        print("\nActivity Patterns:")
        for event_type, description in event_results:
            print(f"  • {description}")
    
    print("\n" + "="*60 + "\n")


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

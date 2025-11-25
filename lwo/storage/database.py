"""PostgreSQL database management for LWO."""

import time
from pathlib import Path
from typing import Any, Dict, Optional
from contextlib import contextmanager

from sqlalchemy import create_engine, text, MetaData, Table, Column, Integer, String, Float, Boolean, BigInteger, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.pool import QueuePool
from sqlalchemy.exc import SQLAlchemyError

from lwo.config import get_config
from lwo.utils.logger import setup_logger

logger = setup_logger(__name__)


class Database:
    """PostgreSQL database manager for LWO."""
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """Initialize database connection.
        
        Args:
            config: Database configuration dict. If None, uses global config.
        """
        if config is None:
            config = get_config().db_config
        
        self.config = config
        self._engine = None
        self._session_factory = None
        self._metadata = MetaData()
        
        self._connect()
    
    def _connect(self):
        """Create database engine and session factory."""
        db_url = (
            f"postgresql://{self.config['user']}:{self.config['password']}"
            f"@{self.config['host']}:{self.config['port']}/{self.config['name']}"
        )
        
        try:
            self._engine = create_engine(
                db_url,
                poolclass=QueuePool,
                pool_size=10,
                max_overflow=20,
                pool_pre_ping=True,
                echo=False,
            )
            self._session_factory = sessionmaker(bind=self._engine)
            logger.info(f"Connected to PostgreSQL database: {self.config['name']}")
        except SQLAlchemyError as e:
            logger.error(f"Failed to connect to database: {e}")
            raise
    
    def init_schema(self):
        """Initialize database schema from SQL file."""
        schema_file = Path(__file__).parent / 'schema.sql'
        
        if not schema_file.exists():
            logger.error(f"Schema file not found: {schema_file}")
            return
        
        try:
            with open(schema_file, 'r') as f:
                schema_sql = f.read()
            
            with self._engine.begin() as conn:
                # Split by semicolon and execute each statement
                statements = [s.strip() for s in schema_sql.split(';') if s.strip()]
                for statement in statements:
                    conn.execute(text(statement))
            
            logger.info("Database schema initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize schema: {e}")
            raise
    
    @contextmanager
    def session(self):
        """Provide a transactional scope for database operations.
        
        Yields:
            SQLAlchemy Session object
        """
        session = self._session_factory()
        try:
            yield session
            session.commit()
        except Exception as e:
            session.rollback()
            logger.error(f"Database session error: {e}")
            raise
        finally:
            session.close()
    
    def insert_shell_command(self, command: str, sanitized_command: str, 
                            pwd: str, ts: int, duration: float, exit_code: int):
        """Insert shell command record.
        
        Args:
            command: Original command
            sanitized_command: Sanitized command
            pwd: Working directory
            ts: Unix timestamp
            duration: Execution duration in seconds
            exit_code: Command exit code
        """
        with self.session() as session:
            session.execute(
                text("""
                    INSERT INTO shell_commands 
                    (command, sanitized_command, pwd, ts, duration, exit_code)
                    VALUES (:cmd, :san_cmd, :pwd, :ts, :dur, :exit_code)
                """),
                {
                    'cmd': command,
                    'san_cmd': sanitized_command,
                    'pwd': pwd,
                    'ts': ts,
                    'dur': duration,
                    'exit_code': exit_code,
                }
            )
    
    def insert_process_snapshot(self, ts: int, process_name: str, pid: int,
                                cpu_percent: float, memory_mb: float):
        """Insert process snapshot record."""
        with self.session() as session:
            session.execute(
                text("""
                    INSERT INTO process_snapshots 
                    (ts, process_name, pid, cpu_percent, memory_mb)
                    VALUES (:ts, :name, :pid, :cpu, :mem)
                """),
                {
                    'ts': ts,
                    'name': process_name,
                    'pid': pid,
                    'cpu': cpu_percent,
                    'mem': memory_mb,
                }
            )
    
    def insert_git_context(self, ts: int, repo_path: str, branch: str, branch_type: str):
        """Insert Git context record."""
        with self.session() as session:
            session.execute(
                text("""
                    INSERT INTO git_contexts 
                    (ts, repo_path, branch, branch_type)
                    VALUES (:ts, :repo, :branch, :type)
                """),
                {
                    'ts': ts,
                    'repo': repo_path,
                    'branch': branch,
                    'type': branch_type,
                }
            )
    
    def insert_file_event(self, ts: int, file_path: str, sanitized_path: str, event_type: str):
        """Insert file event record."""
        with self.session() as session:
            session.execute(
                text("""
                    INSERT INTO file_events 
                    (ts, file_path, sanitized_path, event_type)
                    VALUES (:ts, :path, :san_path, :type)
                """),
                {
                    'ts': ts,
                    'path': file_path,
                    'san_path': sanitized_path,
                    'type': event_type,
                }
            )
    
    def insert_aggregated_event(self, event_type: str, description: str,
                                start_time: int, end_time: int, details: Dict):
        """Insert aggregated event record."""
        with self.session() as session:
            session.execute(
                text("""
                    INSERT INTO aggregated_events 
                    (event_type, description, start_time, end_time, details)
                    VALUES (:type, :desc, :start, :end, :details::jsonb)
                """),
                {
                    'type': event_type,
                    'desc': description,
                    'start': start_time,
                    'end': end_time,
                    'details': str(details),  # Convert to JSON string
                }
            )
    
    def insert_analysis(self, ts: int, status: str, summary: str, confidence: float = None):
        """Insert analysis result."""
        with self.session() as session:
            session.execute(
                text("""
                    INSERT INTO analyses 
                    (ts, status, summary, confidence)
                    VALUES (:ts, :status, :summary, :conf)
                """),
                {
                    'ts': ts,
                    'status': status,
                    'summary': summary,
                    'conf': confidence,
                }
            )
    
    def cleanup_old_data(self, days: int = 7):
        """Clean up data older than specified days.
        
        Args:
            days: Number of days to keep
        """
        cutoff_ts = int(time.time()) - (days * 24 * 3600)
        
        with self.session() as session:
            # Clean up raw data
            for table in ['shell_commands', 'process_snapshots', 'git_contexts', 'file_events']:
                result = session.execute(
                    text(f"DELETE FROM {table} WHERE ts < :cutoff"),
                    {'cutoff': cutoff_ts}
                )
                logger.info(f"Cleaned {result.rowcount} old records from {table}")
    
    def close(self):
        """Close database connection."""
        if self._engine:
            self._engine.dispose()
            logger.info("Database connection closed")


# Global database instance
_db: Optional[Database] = None


def get_database() -> Database:
    """Get global database instance."""
    global _db
    if _db is None:
        _db = Database()
        _db.init_schema()
    return _db

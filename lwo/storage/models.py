"""ORM models for LWO."""

from sqlalchemy import Column, Integer, BigInteger, Text, Float, Boolean, TIMESTAMP, JSON
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.sql import func

Base = declarative_base()


class ShellCommand(Base):
    """Shell command record."""
    __tablename__ = 'shell_commands'
    
    id = Column(Integer, primary_key=True)
    command = Column(Text, nullable=False)
    sanitized_command = Column(Text)
    pwd = Column(Text, nullable=False)
    ts = Column(BigInteger, nullable=False, index=True)
    duration = Column(Float, nullable=False)
    exit_code = Column(Integer, nullable=False)
    created_at = Column(TIMESTAMP, server_default=func.now())


class ProcessSnapshot(Base):
    """Process snapshot record."""
    __tablename__ = 'process_snapshots'
    
    id = Column(Integer, primary_key=True)
    ts = Column(BigInteger, nullable=False, index=True)
    process_name = Column(Text, nullable=False)
    pid = Column(Integer, nullable=False)
    cpu_percent = Column(Float, nullable=False)
    memory_mb = Column(Float, nullable=False)
    created_at = Column(TIMESTAMP, server_default=func.now())


class GitContext(Base):
    """Git context record."""
    __tablename__ = 'git_contexts'
    
    id = Column(Integer, primary_key=True)
    ts = Column(BigInteger, nullable=False, index=True)
    repo_path = Column(Text, nullable=False)
    branch = Column(Text, nullable=False)
    branch_type = Column(Text, nullable=False)
    created_at = Column(TIMESTAMP, server_default=func.now())


class FileEvent(Base):
    """File event record."""
    __tablename__ = 'file_events'
    
    id = Column(Integer, primary_key=True)
    ts = Column(BigInteger, nullable=False, index=True)
    file_path = Column(Text, nullable=False)
    event_type = Column(Text, nullable=False)
    created_at = Column(TIMESTAMP, server_default=func.now())


class AggregatedEvent(Base):
    """Aggregated event record."""
    __tablename__ = 'aggregated_events'
    
    id = Column(Integer, primary_key=True)
    event_type = Column(Text, nullable=False)
    description = Column(Text, nullable=False)
    start_time = Column(BigInteger, nullable=False, index=True)
    end_time = Column(BigInteger, nullable=False)
    details = Column(JSON)
    created_at = Column(TIMESTAMP, server_default=func.now())


class Analysis(Base):
    """Analysis result record."""
    __tablename__ = 'analyses'
    
    id = Column(Integer, primary_key=True)
    ts = Column(BigInteger, nullable=False, index=True)
    status = Column(Text, nullable=False)
    summary = Column(Text, nullable=False)
    confidence = Column(Float)
    created_at = Column(TIMESTAMP, server_default=func.now())


class AIIntervention(Base):
    """AI intervention record."""
    __tablename__ = 'ai_interventions'
    
    id = Column(Integer, primary_key=True)
    ts = Column(BigInteger, nullable=False, index=True)
    anomaly_type = Column(Text, nullable=False)
    trigger_context = Column(JSON)
    analysis_result = Column(JSON)
    tools_used = Column(JSON)
    confidence = Column(Float)
    created_at = Column(TIMESTAMP, server_default=func.now())


class BehaviorPattern(Base):
    """Behavior pattern record."""
    __tablename__ = 'behavior_patterns'
    
    id = Column(Integer, primary_key=True)
    pattern_type = Column(Text, nullable=False)
    context = Column(JSON)
    resolution = Column(JSON)
    success = Column(Boolean)
    created_at = Column(TIMESTAMP, server_default=func.now())


class DiscoveredDir(Base):
    """Discovered directory record."""
    __tablename__ = 'discovered_dirs'
    
    id = Column(Integer, primary_key=True)
    dir_path = Column(Text, nullable=False, unique=True)
    is_git_repo = Column(Boolean, default=False)
    access_count = Column(Integer, default=0)
    last_access_ts = Column(BigInteger)
    discovered_at = Column(BigInteger, nullable=False)
    is_active = Column(Boolean, default=True, index=True)
    ai_reasoning = Column(Text)
    created_at = Column(TIMESTAMP, server_default=func.now())


class HostLog(Base):
    """Host-level log entries from journalctl or syslog."""
    __tablename__ = 'host_logs'
    
    id = Column(Integer, primary_key=True)
    ts = Column(BigInteger, nullable=False, index=True)
    level = Column(Text, nullable=False)  # ERROR, WARN, INFO
    service = Column(Text, nullable=False)  # systemd, kernel, etc.
    message = Column(Text, nullable=False)
    raw_line = Column(Text, nullable=False)
    created_at = Column(TIMESTAMP, server_default=func.now())


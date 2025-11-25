-- PostgreSQL Schema for LWO

-- Shell 命令记录
CREATE TABLE IF NOT EXISTS shell_commands (
    id SERIAL PRIMARY KEY,
    command TEXT NOT NULL,
    sanitized_command TEXT,
    pwd TEXT NOT NULL,
    ts BIGINT NOT NULL,
    duration REAL NOT NULL,
    exit_code INTEGER NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX IF NOT EXISTS idx_shell_commands_ts ON shell_commands(ts);
CREATE INDEX IF NOT EXISTS idx_shell_commands_pwd ON shell_commands(pwd);

-- 进程快照
CREATE TABLE IF NOT EXISTS process_snapshots (
    id SERIAL PRIMARY KEY,
    ts BIGINT NOT NULL,
    process_name TEXT NOT NULL,
    pid INTEGER NOT NULL,
    cpu_percent REAL,
    memory_mb REAL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX IF NOT EXISTS idx_process_snapshots_ts ON process_snapshots(ts);

-- Git 上下文
CREATE TABLE IF NOT EXISTS git_contexts (
    id SERIAL PRIMARY KEY,
    ts BIGINT NOT NULL,
    repo_path TEXT NOT NULL,
    branch TEXT,
    branch_type TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX IF NOT EXISTS idx_git_contexts_ts ON git_contexts(ts);

-- 文件事件
CREATE TABLE IF NOT EXISTS file_events (
    id SERIAL PRIMARY KEY,
    ts BIGINT NOT NULL,
    file_path TEXT NOT NULL,
    sanitized_path TEXT,
    event_type TEXT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX IF NOT EXISTS idx_file_events_ts ON file_events(ts);

-- 聚合事件
CREATE TABLE IF NOT EXISTS aggregated_events (
    id SERIAL PRIMARY KEY,
    event_type TEXT NOT NULL,
    description TEXT,
    start_time BIGINT NOT NULL,
    end_time BIGINT NOT NULL,
    details JSONB,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX IF NOT EXISTS idx_aggregated_events_start_time ON aggregated_events(start_time);

-- AI 分析结果
CREATE TABLE IF NOT EXISTS analyses (
    id SERIAL PRIMARY KEY,
    ts BIGINT NOT NULL,
    status TEXT NOT NULL,
    summary TEXT NOT NULL,
    confidence REAL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX IF NOT EXISTS idx_analyses_ts ON analyses(ts);

-- 智能发现的监控目录
CREATE TABLE IF NOT EXISTS discovered_dirs (
    id SERIAL PRIMARY KEY,
    dir_path TEXT NOT NULL UNIQUE,
    is_git_repo BOOLEAN DEFAULT FALSE,
    access_count INTEGER DEFAULT 0,
    last_access_ts BIGINT,
    discovered_at BIGINT NOT NULL,
    is_active BOOLEAN DEFAULT TRUE,
    ai_reasoning TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX IF NOT EXISTS idx_discovered_dirs_is_active ON discovered_dirs(is_active);

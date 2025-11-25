-- AI intervention and behavior pattern tables
CREATE TABLE IF NOT EXISTS ai_interventions (
    id SERIAL PRIMARY KEY,
    ts BIGINT NOT NULL,
    anomaly_type TEXT NOT NULL,
    trigger_context JSONB,
    analysis_result JSONB,
    tools_used JSONB,
    confidence REAL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_ai_interventions_ts ON ai_interventions(ts);
CREATE INDEX IF NOT EXISTS idx_ai_interventions_anomaly_type ON ai_interventions(anomaly_type);

CREATE TABLE IF NOT EXISTS behavior_patterns (
    id SERIAL PRIMARY KEY,
    pattern_type TEXT NOT NULL,
    context JSONB,
    resolution JSONB,
    success BOOLEAN,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_behavior_patterns_type ON behavior_patterns(pattern_type);

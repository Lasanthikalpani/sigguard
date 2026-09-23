-- SigGuard Database Schema

CREATE TABLE IF NOT EXISTS documents (
    document_id SERIAL PRIMARY KEY,
    file_path VARCHAR(500) NOT NULL,
    label BOOLEAN NOT NULL,
    script VARCHAR(20) NOT NULL,
    signer_id VARCHAR(50) NOT NULL,
    forgery_type VARCHAR(50),
    degradation VARCHAR(50) DEFAULT 'clean',
    scanned_dpi INTEGER DEFAULT 600,
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX idx_documents_script ON documents(script);
CREATE INDEX idx_documents_label ON documents(label);
CREATE INDEX idx_documents_signer ON documents(signer_id);

CREATE TABLE IF NOT EXISTS experiment_runs (
    run_id SERIAL PRIMARY KEY,
    experiment_name VARCHAR(100) NOT NULL,
    config JSONB NOT NULL,
    commit_hash VARCHAR(40),
    started_at TIMESTAMP DEFAULT NOW(),
    completed_at TIMESTAMP,
    status VARCHAR(20) DEFAULT 'running'
);

CREATE TABLE IF NOT EXISTS metrics (
    metric_id SERIAL PRIMARY KEY,
    run_id INTEGER REFERENCES experiment_runs(run_id) ON DELETE CASCADE,
    fold INTEGER,
    accuracy FLOAT,
    precision FLOAT,
    recall FLOAT,
    f1 FLOAT,
    auc_roc FLOAT,
    inference_time_ms FLOAT,
    model_size_mb FLOAT,
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX idx_metrics_run ON metrics(run_id);

CREATE TABLE IF NOT EXISTS predictions (
    prediction_id SERIAL PRIMARY KEY,
    run_id INTEGER REFERENCES experiment_runs(run_id),
    document_id INTEGER REFERENCES documents(document_id),
    predicted_label BOOLEAN,
    confidence FLOAT,
    inference_time_ms FLOAT,
    explanation JSONB,
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS audit_log (
    audit_id SERIAL PRIMARY KEY,
    document_id INTEGER REFERENCES documents(document_id),
    action VARCHAR(50) NOT NULL,
    actor VARCHAR(100),
    qr_hash VARCHAR(64),
    ai_verdict VARCHAR(20),
    final_verdict VARCHAR(20),
    metadata JSONB,
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS user_studies (
    study_id SERIAL PRIMARY KEY,
    participant_id VARCHAR(50) NOT NULL,
    session_id VARCHAR(50) NOT NULL,
    group_name VARCHAR(20) NOT NULL,
    xts_score FLOAT,
    sus_score FLOAT,
    comprehension_rate FLOAT,
    decision_confidence FLOAT,
    task_completion_time FLOAT,
    metadata JSONB,
    created_at TIMESTAMP DEFAULT NOW()
);

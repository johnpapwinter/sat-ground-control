-- This file runs only on first container initialization when the data volume is empty.
CREATE TABLE telemetry (
    timestamp TIMESTAMPTZ,
    satellite_id INT NOT NULL,
    metric_id INT NOT NULL,
    value DOUBLE PRECISION NOT NULL,
    PRIMARY KEY ("timestamp", satellite_id, metric_id)
);

SELECT create_hypertable('telemetry', 'timestamp');

CREATE INDEX ix_sat_metric_time ON telemetry (satellite_id, metric_id, timestamp);

CREATE TABLE IF NOT EXISTS packet_gaps (
    timestamp TIMESTAMPTZ NOT NULL,
    satellite_id INTEGER NOT NULL,
    apid INTEGER NOT NULL,
    expected_seq INTEGER,
    received_seq INTEGER,
    gap_size INTEGER,
    PRIMARY KEY (timestamp, satellite_id, apid)
);

SELECT create_hypertable('packet_gaps', 'timestamp', if_not_exists => TRUE);

CREATE TABLE IF NOT EXISTS command_entries (
    command_id BIGSERIAL PRIMARY KEY,
    command_payload JSON,
    priority_level VARCHAR(15),
    state VARCHAR(15),
    opcode INTEGER,
    timestamp TIMESTAMP WITHOUT TIME ZONE
);



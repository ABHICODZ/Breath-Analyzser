-- Database schema for Breath-Analyzer
-- Creates hypertable for storing time-series air quality data

-- Ensure the TimescaleDB extension is enabled
CREATE EXTENSION IF NOT EXISTS timescaledb;
CREATE EXTENSION IF NOT EXISTS postgis;

-- 1. Create a table for static sensor station locations or grid points
CREATE TABLE IF NOT EXISTS location_nodes (
    node_id BIGINT PRIMARY KEY,  -- Corresponds to OSMnx Node ID
    lat DOUBLE PRECISION NOT NULL,
    lon DOUBLE PRECISION NOT NULL,
    geom GEOMETRY(Point, 4326)   -- PostGIS geometry for spatial queries
);

-- 2. Create the main hypertable for time-series air quality metrics
CREATE TABLE IF NOT EXISTS air_quality_data (
    time TIMESTAMPTZ NOT NULL,
    node_id BIGINT NOT NULL REFERENCES location_nodes(node_id),
    
    -- Pollutant Measurements
    pm2_5 DOUBLE PRECISION,
    pm10 DOUBLE PRECISION,
    no2 DOUBLE PRECISION,
    
    -- Environmental Factors
    temperature DOUBLE PRECISION,
    humidity DOUBLE PRECISION,
    
    -- Source of data (e.g., 'satellite', 'ground_sensor', 'model_prediction')
    source VARCHAR(50) NOT NULL
);

-- 3. Turn the table into a TimescaleDB hypertable
-- This partitions the data by 'time' for fast ingestion and querying
SELECT create_hypertable('air_quality_data', 'time', if_not_exists => TRUE);

-- 4. Create an index on node_id to speed up spatial filtering
CREATE INDEX IF NOT EXISTS ix_aq_data_node_id ON air_quality_data (node_id, time DESC);

-- 5. Create Continuous Aggregates (Optional but powerful for historical routing)
-- E.g., Hourly averages for prediction and analytics
CREATE MATERIALIZED VIEW IF NOT EXISTS hourly_air_quality
WITH (timescaledb.continuous) AS
SELECT time_bucket('1 hour', time) AS bucket,
       node_id,
       AVG(pm2_5) as avg_pm2_5,
       AVG(pm10) as avg_pm10,
       AVG(no2) as avg_no2
FROM air_quality_data
GROUP BY bucket, node_id;

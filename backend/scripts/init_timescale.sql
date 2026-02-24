-- Initialization script for TimescaleDB
-- Must be run as a superuser or a user with correct privileges.

-- 1. Create the database (Run via psql or PgAdmin before running this script)
-- CREATE DATABASE breath_analyzer;
-- \c breath_analyzer

-- 2. Enable the TimescaleDB extension
CREATE EXTENSION IF NOT EXISTS timescaledb;

-- 3. Create the table
CREATE TABLE IF NOT EXISTS sensor_data (
    time        TIMESTAMPTZ       NOT NULL,
    sensor_id   VARCHAR(50)       NOT NULL,
    latitude    DOUBLE PRECISION  NOT NULL,
    longitude   DOUBLE PRECISION  NOT NULL,
    pm25        DOUBLE PRECISION,
    pm10        DOUBLE PRECISION,
    no2         DOUBLE PRECISION,
    so2         DOUBLE PRECISION,
    co          DOUBLE PRECISION,
    o3          DOUBLE PRECISION,
    PRIMARY KEY (time, sensor_id)
);

-- 4. Create an index on sensor_id and time for fast querying
CREATE INDEX IF NOT EXISTS ix_sensor_data_sensor_id_time ON sensor_data (sensor_id, time DESC);

-- 5. Convert the table into a hypertable, partitioned by time
-- Assuming chunk_time_interval of 1 day (default is 7 days)
SELECT create_hypertable('sensor_data', 'time', if_not_exists => TRUE, chunk_time_interval => INTERVAL '1 day');

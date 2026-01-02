CREATE TABLE IF NOT EXISTS sections (
    section_id SERIAL PRIMARY KEY,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS section_connections (
    connection_id SERIAL PRIMARY KEY,
    from_section_id INTEGER NOT NULL REFERENCES sections(section_id) ON DELETE CASCADE,
    to_section_id INTEGER NOT NULL REFERENCES sections(section_id) ON DELETE CASCADE,
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(from_section_id, to_section_id)
);

CREATE INDEX IF NOT EXISTS idx_section_connections_from_to
    ON section_connections (from_section_id, to_section_id);

CREATE TABLE IF NOT EXISTS rail_blocks (
    block_id SERIAL PRIMARY KEY,
    block_name VARCHAR(100) UNIQUE NOT NULL,
    section_id INTEGER NOT NULL REFERENCES sections(section_id) ON DELETE CASCADE UNIQUE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS train_types (
    train_type_id SERIAL PRIMARY KEY,
    type_name VARCHAR(50) UNIQUE NOT NULL,
    priority_index INTEGER UNIQUE NOT NULL,
    cruising_speed FLOAT NOT NULL DEFAULT 0.5,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS trains (
    train_id SERIAL PRIMARY KEY,
    train_code VARCHAR(100) UNIQUE NOT NULL,
    train_type_id INTEGER NOT NULL REFERENCES train_types(train_type_id),
    current_section_id INTEGER REFERENCES sections(section_id),
    direction SMALLINT DEFAULT 1 CHECK (direction IN (-1, 1)),
    requires_maintenance BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS wagons (
    wagon_id SERIAL PRIMARY KEY,
    train_id INTEGER NOT NULL REFERENCES trains(train_id) ON DELETE CASCADE,
    wagon_index INTEGER NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(train_id, wagon_index)
);

CREATE TABLE IF NOT EXISTS wagon_positions (
    position_id SERIAL PRIMARY KEY,
    wagon_id INTEGER UNIQUE REFERENCES wagons(wagon_id) ON DELETE CASCADE,
    section_id INTEGER REFERENCES sections(section_id),
    position_offset FLOAT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS stops (
    stop_id SERIAL PRIMARY KEY,
    stop_name VARCHAR(100) UNIQUE NOT NULL,
    section_id INTEGER UNIQUE REFERENCES sections(section_id),
    platform_number INTEGER,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS train_schedules (
    schedule_id SERIAL PRIMARY KEY,
    train_id INTEGER NOT NULL REFERENCES trains(train_id) ON DELETE CASCADE,
    stop_id INTEGER NOT NULL REFERENCES stops(stop_id),
    scheduled_arrival_time TIMESTAMP NOT NULL,
    scheduled_departure_time TIMESTAMP NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    CHECK (scheduled_departure_time >= scheduled_arrival_time)
);

CREATE OR REPLACE VIEW train_delays_view AS
SELECT
    t.train_id,
    t.train_code,
    tt.type_name,
    tt.priority_index,
    ts.stop_id,
    st.stop_name,
    EXTRACT(EPOCH FROM (CURRENT_TIMESTAMP - ts.scheduled_arrival_time))::INT AS delay_seconds,
    CASE
        WHEN CURRENT_TIMESTAMP > ts.scheduled_arrival_time THEN 'DELAYED'
        ELSE 'ON_TIME'
    END AS status
FROM trains t
JOIN train_types tt ON t.train_type_id = tt.train_type_id
JOIN train_schedules ts ON ts.train_id = t.train_id
JOIN stops st ON st.stop_id = ts.stop_id;

CREATE OR REPLACE FUNCTION update_timestamp()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER update_timestamp_sections
    BEFORE UPDATE ON sections
    FOR EACH ROW
    EXECUTE FUNCTION update_timestamp();

CREATE TRIGGER update_timestamp_trains
    BEFORE UPDATE ON trains
    FOR EACH ROW
    EXECUTE FUNCTION update_timestamp();

CREATE TRIGGER update_timestamp_section_connections
    BEFORE UPDATE ON section_connections
    FOR EACH ROW
    EXECUTE FUNCTION update_timestamp();

CREATE TRIGGER update_timestamp_rail_blocks
    BEFORE UPDATE ON rail_blocks
    FOR EACH ROW
    EXECUTE FUNCTION update_timestamp();

CREATE TRIGGER update_timestamp_train_types
    BEFORE UPDATE ON train_types
    FOR EACH ROW
    EXECUTE FUNCTION update_timestamp();

CREATE TRIGGER update_timestamp_wagons
    BEFORE UPDATE ON wagons
    FOR EACH ROW
    EXECUTE FUNCTION update_timestamp();

CREATE TRIGGER update_timestamp_wagon_positions
    BEFORE UPDATE ON wagon_positions
    FOR EACH ROW
    EXECUTE FUNCTION update_timestamp();

CREATE TRIGGER update_timestamp_stops
    BEFORE UPDATE ON stops
    FOR EACH ROW
    EXECUTE FUNCTION update_timestamp();

CREATE TRIGGER update_timestamp_train_schedules
    BEFORE UPDATE ON train_schedules
    FOR EACH ROW
    EXECUTE FUNCTION update_timestamp();

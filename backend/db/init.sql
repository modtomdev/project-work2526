CREATE TABLE IF NOT EXISTS sections (
    section_id SERIAL PRIMARY KEY,
    is_switch BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS section_connections (
    connection_id SERIAL PRIMARY KEY,
    from_section_id INTEGER NOT NULL REFERENCES sections(section_id) ON DELETE CASCADE,
    to_section_id INTEGER NOT NULL REFERENCES sections(section_id) ON DELETE CASCADE,
    is_active BOOLEAN DEFAULT TRUE,
    UNIQUE(from_section_id, to_section_id)
);

CREATE INDEX IF NOT EXISTS idx_section_connections_from_to
    ON section_connections (from_section_id, to_section_id);

CREATE TABLE IF NOT EXISTS rail_blocks (
    block_id SERIAL PRIMARY KEY,
    block_name VARCHAR(100) UNIQUE NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS block_sections (
    block_section_id SERIAL PRIMARY KEY,
    block_id INTEGER NOT NULL REFERENCES rail_blocks(block_id) ON DELETE CASCADE,
    section_id INTEGER NOT NULL REFERENCES sections(section_id) ON DELETE CASCADE,
    UNIQUE(block_id, section_id)
);

CREATE TABLE IF NOT EXISTS train_types (
    train_type_id SERIAL PRIMARY KEY,
    type_name VARCHAR(50) UNIQUE NOT NULL,
    priority_index INTEGER UNIQUE NOT NULL,
    cruising_speed FLOAT NOT NULL DEFAULT 0.5 -- sections/min, remember section vs db section
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
    UNIQUE(train_id, wagon_index)
);

CREATE TABLE IF NOT EXISTS wagon_positions (
    position_id SERIAL PRIMARY KEY,
    wagon_id INTEGER UNIQUE REFERENCES wagons(wagon_id) ON DELETE CASCADE,
    section_id INTEGER REFERENCES sections(section_id),
    position_offset FLOAT NOT NULL, -- can be useful for smooth rendering
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS stops (
    stop_id SERIAL PRIMARY KEY,
    stop_name VARCHAR(100) UNIQUE NOT NULL,
    section_id INTEGER REFERENCES sections(section_id),
    platform_number INTEGER -- 1,2,3,4 for standard platform 5,6 for dead ends
);

CREATE TABLE IF NOT EXISTS train_schedules (
    schedule_id SERIAL PRIMARY KEY,
    train_id INTEGER NOT NULL REFERENCES trains(train_id) ON DELETE CASCADE,
    stop_id INTEGER NOT NULL REFERENCES stops(stop_id),
    scheduled_arrival_time TIME NOT NULL,
    scheduled_departure_time TIME NOT NULL,
    UNIQUE(train_id, stop_id),
    UNIQUE(train_id, sequence_index)
);

CREATE OR REPLACE VIEW train_delays_view AS
SELECT
    t.train_id,
    t.train_code,
    tt.type_name,
    tt.priority_index,
    ts.stop_id,
    st.stop_name,
    EXTRACT(EPOCH FROM (CURRENT_TIME - ts.scheduled_arrival_time))::INT AS delay_seconds,
    CASE
        WHEN CURRENT_TIME > ts.scheduled_arrival_time THEN 'DELAYED'
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

CREATE TRIGGER update_timestamp_generic
    BEFORE UPDATE ON sections, trains
    FOR EACH ROW
    EXECUTE FUNCTION update_timestamp();

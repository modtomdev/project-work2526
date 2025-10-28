CREATE CREATE TABLE IF NOT EXISTS sections (
    section_id SERIAL PRIMARY KEY,
    is_switch BOOLEAN DEFAULT FALSE,
    switch_state VARCHAR(20) CHECK (switch_state IN ('main', 'diverging', NULL)),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- The 'is_active' field can be leveraged for signaling
CREATE CREATE TABLE IF NOT EXISTS section_connections (
    connection_id SERIAL PRIMARY KEY,
    from_section_id INTEGER REFERENCES sections(section_id) ON DELETE CASCADE,
    to_section_id INTEGER REFERENCES sections(section_id) ON DELETE CASCADE,
    connection_type VARCHAR(20) CHECK (connection_type IN ('main', 'diverging', 'normal')),
    is_active BOOLEAN DEFAULT TRUE,
    UNIQUE(from_section_id, to_section_id, connection_type)
);

CREATE CREATE TABLE IF NOT EXISTS rail_blocks (
    block_id SERIAL PRIMARY KEY,
    block_name VARCHAR(100) UNIQUE NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE CREATE TABLE IF NOT EXISTS block_sections (
    block_section_id SERIAL PRIMARY KEY,
    block_id INTEGER REFERENCES rail_blocks(block_id) ON DELETE CASCADE,
    section_id INTEGER REFERENCES sections(section_id) ON DELETE CASCADE,
    section_order INTEGER NOT NULL,
    UNIQUE(block_id, section_id)
);

CREATE CREATE TABLE IF NOT EXISTS train_types (
    train_type_id SERIAL PRIMARY KEY,
    type_name VARCHAR(50) UNIQUE NOT NULL,
    priority INTEGER NOT NULL,
    cruising_speed INTEGER NOT NULL,
    is_cargo BOOLEAN NOT NULL
);

CREATE CREATE TABLE IF NOT EXISTS trains (
    train_id SERIAL PRIMARY KEY,
    train_code VARCHAR(100) UNIQUE NOT NULL,
    train_type_id INTEGER REFERENCES train_types(train_type_id),
    current_section_id INTEGER REFERENCES sections(section_id),
    is_moving BOOLEAN DEFAULT FALSE,
    direction INTEGER DEFAULT 1 CHECK (direction IN (-1, 1)),
    requires_maintenance BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE CREATE TABLE IF NOT EXISTS wagons (
    wagon_id SERIAL PRIMARY KEY,
    train_id INTEGER REFERENCES trains(train_id) ON DELETE CASCADE,
    wagon_index INTEGER NOT NULL,
    UNIQUE(train_id, wagon_index)
);

CREATE CREATE TABLE IF NOT EXISTS wagon_positions (
    position_id SERIAL PRIMARY KEY,
    wagon_id INTEGER UNIQUE REFERENCES wagons(wagon_id) ON DELETE CASCADE,
    section_id INTEGER REFERENCES sections(section_id),
    position_offset FLOAT NOT NULL,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE OR REPLACE FUNCTION update_timestamp()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER update_sections_timestamp
    BEFORE UPDATE ON sections
    FOR EACH ROW
    EXECUTE FUNCTION update_timestamp();

CREATE TRIGGER update_trains_timestamp
    BEFORE UPDATE ON trains
    FOR EACH ROW
    EXECUTE FUNCTION update_timestamp();
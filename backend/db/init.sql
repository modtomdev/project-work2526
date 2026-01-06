CREATE TABLE IF NOT EXISTS sections (
    section_id SERIAL PRIMARY KEY,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS rail_blocks (
    block_id SERIAL PRIMARY KEY,
    block_name VARCHAR(100) NOT NULL,
    section_id INTEGER NOT NULL REFERENCES sections(section_id) ON DELETE CASCADE UNIQUE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS section_connections (
    connection_id SERIAL PRIMARY KEY,
    from_section_id INTEGER NOT NULL REFERENCES sections(section_id) ON DELETE CASCADE,
    to_section_id INTEGER NOT NULL REFERENCES sections(section_id) ON DELETE CASCADE,
    exclude_previous_block_name VARCHAR(100),
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(from_section_id, to_section_id)
);

CREATE TABLE IF NOT EXISTS train_types (
    train_type_id SERIAL PRIMARY KEY,
    type_name VARCHAR(50) UNIQUE NOT NULL,
    priority_index INTEGER UNIQUE NOT NULL,
    cruising_speed FLOAT NOT NULL DEFAULT 50,
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

TRUNCATE train_schedules, stops, wagon_positions, wagons, trains, train_types,
rail_blocks, section_connections, sections RESTART IDENTITY CASCADE;

INSERT INTO sections (section_id)
VALUES
-- horizontal sections
(0),(1),(2),(3),(4),(5),(6),(7),(8),(9),(10),(11),(12),(13),(14),(15),(16),(17),(18),(19),(20),(21),(22),(23),(24),(25),(26),(27),(28),(29),(30),(31),(32),(33),(34),(35),(36),(37),(38),(39),(40),(41),
(100),(101),(102),(103),(104),(105),(106),(107),(108),(109),(110),(111),(112),(113),(114),(115),(116),(117),(118),(119),(120),(121),(122),(123),(124),(125),(126),(127),(128),(129),(130),(131),(132),(133),(134),(135),(136),(137),(138),(139),(140),(141),
(200),(201),(202),(203),(204),(205),(206),(207),(208),(209),(210),(211),(212),(213),(214),(215),(216),(217),(218),(219),(220),(221),(222),(223),(224),
(300),(301),(302),(303),(304),(305),(306),(307),(308),(309),(310),
-- diagonals sections
(1000),(1001),(1010),(1011),(1020),(1021),(1030),(1031),(1040),(1041),
(2000),(2001),(2010),(2011),(2020),(2021),(2030),(2031),
(3000),(3001),(3010),(3011),(3020),(3021);

INSERT INTO section_connections (from_section_id, to_section_id, exclude_previous_block_name)
VALUES
(0, 1, NULL), (1, 2, NULL),
(2, 3, 'L'), (2, 1000, 'C'),
(1000, 1001, NULL), (1001, 105, NULL),
(3, 4, NULL), (4, 5, NULL), (5, 6, NULL), (6, 7, NULL), (7, 8, NULL), (8, 9, NULL), (9, 10, NULL),
(10, 1010, 'E'), (1010, 1011, NULL), (1011, 113, NULL),
(10, 11, 'P'), (11, 12, NULL), (12, 13, NULL), (13, 14, NULL), (14, 15, NULL), (15, 16, NULL), (16, 17, NULL), (17, 18, NULL),
(18, 1020, 'G'), (1020, 1021, NULL), (1021, 121, NULL),
(18, 19, 'S'), (19, 20, NULL), (20, 21, NULL), (21, 22, NULL), (22, 23, NULL), (23, 24, NULL), (24, 25, NULL), (25, 26, NULL), (26, 27, NULL), (27, 28, NULL), (28, 29, NULL), (29, 30, NULL), (30, 31, NULL), (31, 32, NULL), (32, 33, NULL), (33, 34, NULL), (34, 35, NULL), (35, 36, NULL), (36, 37, NULL), (37, 38, NULL), (38, 39, NULL), (39, 40, NULL), (40, 41, NULL),
(41, 1040, 'I'), (1040, 1041, NULL), (1041, 138, NULL),
(41, 40, 'Y'), (40, 39, NULL), (39, 38, NULL), (38, 37, NULL), (37, 36, NULL), (36, 35, NULL), (35, 34, NULL), (34, 33, NULL),
(33, 1030, 'G'), (1030, 1031, NULL), (1031, 130, NULL),
(33, 32, 'U'), (32, 31, NULL), (31, 30, NULL), (30, 29, NULL), (29, 28, NULL), (28, 27, NULL), (27, 26, NULL), (26, 25, NULL), (25, 24, NULL), (24, 23, NULL), (23, 22, NULL), (22, 21, NULL), (21, 20, NULL), (20, 19, NULL), (19, 18, NULL), (18, 17, NULL), (17, 16, NULL), (16, 15, NULL), (15, 14, NULL), (14, 13, NULL), (13, 12, NULL), (12, 11, NULL), (11, 10, NULL), (10, 9, NULL), (9, 8, NULL), (8, 7, NULL), (7, 6, NULL), (6, 5, NULL), (5, 4, NULL), (4, 3, NULL), (3, 2, NULL), (2, 1, NULL), (1, 0, NULL),
--
(100, 101, NULL), (101, 102, NULL), (102, 103, NULL), (103, 104, NULL), (104, 105, NULL), (105, 106, NULL),
(106, 2000, 'N'), (2000, 2001, NULL), (2001, 200, NULL),
(106, 107, 'AA'), (107, 108, NULL), (108, 109, NULL), (109, 110, NULL),
(110, 2010, 'P'), (2010, 2011, NULL), (2011, 204, NULL),
(110, 111, 'AD'), (111, 112, NULL), (112, 113, NULL), (113, 114, NULL), (114, 115, NULL), (115, 116, NULL), (116, 117, NULL), (117, 118, NULL),
(118, 2020, 'S'), (2020, 2021, NULL), (2021, 212, NULL),
(118, 119, 'AH'), (119, 120, NULL), (120, 121, NULL), (121, 122, NULL), (122, 123, NULL), (123, 124, NULL), (124, 125, NULL), (125, 126, NULL), (126, 127, NULL), (127, 128, NULL),
(129, 130, NULL), (130, 1031, 'V'), (1031, 1030, NULL), (1030, 33, NULL),
(130, 131, 'H'), (131, 132, NULL), (132, 133, NULL), (133, 134, NULL), (134, 135, NULL), (135, 136, NULL), (136, 137, NULL), (137, 138, NULL),
(138, 1041, 'Z'), (1041, 1040, NULL), (1040, 41, NULL),
(138, 139, 'J'), (139, 140, NULL), (140, 141, NULL),
--
(141, 140, NULL), (140, 139, NULL), (139, 138, NULL), (138, 137, NULL), (137, 136, NULL),
(136, 2030, 'V'), (2030, 2031, NULL), (2031, 224, NULL),
(136, 135, 'AK'), (135, 134, NULL), (134, 133, NULL), (133, 132, NULL), (132, 131, NULL), (131, 130, NULL), (130, 129, NULL), (129, 128, NULL), (128, 127, NULL), (127, 126, NULL), (126, 125, NULL), (125, 124, NULL), (124, 123, NULL), (123, 122, NULL), (122, 121, NULL),
(121, 1021, 'R'), (1021, 1020, NULL), (1020, 18, NULL),
(121, 120, 'F'), (120, 119, NULL), (119, 118, NULL), (118, 117, NULL), (117, 116, NULL), (116, 115, NULL), (115, 114, NULL), (114, 113, NULL),
(113, 1011, 'O'), (1011, 1010, NULL), (1010, 10, NULL),
(113, 112, 'D'), (112, 111, NULL), (111, 110, NULL), (110, 109, NULL), (109, 108, NULL), (108, 107, NULL), (107, 106, NULL), (106, 105, NULL),
(105, 1001, 'K'), (1001, 1000, NULL), (1000, 2, NULL),
(105, 104, 'B'), (104, 103, NULL), (103, 102, NULL), (102, 101, NULL), (101, 100, NULL),
--
(200, 3000, 'AC'), (3000, 3001, NULL),
(200, 201, 'UNKNOWN'), (201, 202, NULL), (202, 203, NULL), (203, 204, NULL), (204, 205, NULL), (205, 206, NULL), (206, 207, NULL), (207, 208, NULL),
(208, 3010, 'AG'), (3010, 3011, NULL), (3011, 300, NULL),
(208, 209, 'AL'), (209, 210, NULL), (210, 211, NULL), (211, 212, NULL), (212, 213, NULL), (213, 214, NULL), (214, 215, NULL), (215, 216, NULL), (216, 217, NULL), (218, 219, NULL), (219, 220, NULL), (220, 221, NULL), (221, 222, NULL), (222, 223, NULL), (223, 224, NULL),
(224, 2031, NULL), (2031, 2030, NULL), (2030, 136, NULL),
(224, 3020, 'AI'), (3020, 3021, NULL), (3021, 310, NULL),
(224, 223, 'AL'), (223, 222, NULL), (222, 221, NULL), (221, 220, NULL), (220, 219, NULL), (219, 218, NULL), (218, 217, NULL), (217, 216, NULL), (216, 215, NULL), (215, 214, NULL), (214, 213, NULL), (213, 212, NULL),
(212, 2021, 'AG'), (2021, 2020, NULL), (2020, 118, NULL),
(212, 211, 'R'), (211, 210, NULL), (210, 209, NULL), (209, 208, NULL), (208, 207, NULL), (207, 206, NULL), (206, 205, NULL), (205, 204, NULL),
(204, 2011, 'AC'), (2011, 2010, NULL), (2010, 110, NULL),
(204, 203, 'O'), (203, 202, NULL), (202, 201, NULL), (201, 200, NULL), (200, 2001, NULL), (2001, 2000, NULL), (2000, 106, NULL),
--
(300, 301, NULL), (301, 302, NULL), (302, 303, NULL), (303, 304, NULL), (304, 305, NULL), (305, 306, NULL), (306, 307, NULL), (307, 308, NULL), (308, 309, NULL), (309, 310, NULL),
(310, 3021, NULL), (3021, 3020, NULL), (3020, 224, NULL),
(310, 309, NULL), (309, 308, NULL), (308, 307, NULL), (307, 306, NULL), (306, 305, NULL), (305, 304, NULL), (304, 303, NULL), (303, 302, NULL), (302, 301, NULL), (301, 300, NULL),
(300, 3011, NULL), (3011, 3010, NULL), (3010, 208, NULL);

INSERT INTO rail_blocks (block_name, section_id)
VALUES
('A', 0), ('A', 1),
('B', 2), ('B', 3), ('B', 1000),
('C', 4), ('C', 5), ('C', 6), ('C', 7), ('C', 8), ('C', 9),
('D', 10), ('D', 11), ('D', 1010),
('E', 12), ('E', 13), ('E', 14), ('E', 15), ('E', 16), ('E', 17),
('F', 18), ('F', 19), ('F', 1020),
('G', 20), ('G', 21), ('G', 22), ('G', 23), ('G', 24), ('G', 25), ('G', 26), ('G', 27), ('G', 28), ('G', 29), ('G', 30), ('G', 31),
('H', 32), ('H', 33), ('H', 1030),
('I', 34), ('I', 35), ('I', 36), ('I', 37), ('I', 38), ('I', 39),
('J', 40), ('J', 41), ('J', 1040),
('K', 100), ('K', 101), ('K', 102), ('K', 103),
('L', 104), ('L', 105), ('L', 1001),
('M', 106), ('M', 107), ('M', 2000),
('N', 108), ('N', 109), 
('O', 110), ('O', 111), ('O', 2010),
('P', 112), ('P', 113), ('P', 1011),
('Q', 114), ('Q', 115), ('Q', 116),('Q', 117),
('R', 118), ('R', 119), ('R', 2020),
('S', 120), ('S', 121), ('S', 1021),
('T', 122), ('T', 123), ('T', 124), ('T', 125), ('T', 126), ('T', 127), ('T', 128), ('T', 129),
('U', 130), ('U', 131), ('U', 1031),
('V', 132), ('V', 133), ('V', 134),
('W', 135), ('W', 136), ('W', 2030),
('X', 137), 
('Y', 138), ('Y', 139), ('Y', 1041),
('Z', 140), ('Z', 141),
('AA', 2001),
('AB', 200), ('AB', 201), ('AB', 3000),
-- 3001, connect to lower rails
('AC', 202),
('AD', 203), ('AD', 204), ('AD', 2011),
('AE', 205), ('AE', 206), ('AE', 207),
('AF', 208), ('AF', 209), ('AF', 3010),
('AG', 210),  
('AH', 211), ('AH', 212), ('AH', 2021),
('AI', 213), ('AI', 214), ('AI', 215), ('AI', 216), ('AI', 217), ('AI', 218), ('AI', 219), ('AI', 220), ('AI', 221), ('AI', 222),
('AJ', 223), ('AJ', 224), ('AJ', 3020),
('AK', 2031),
('AL', 3011), ('AL', 300), ('AL', 301), ('AL', 302), ('AL', 303), ('AL', 304), ('AL', 305), ('AL', 306), ('AL', 307), ('AL', 308), ('AL', 309), ('AL', 310), ('AL', 3021);

INSERT INTO train_types (type_name, priority_index, cruising_speed)
VALUES
('Regionale', 2, 70.0),
('Alta velocità', 1, 100.0);

INSERT INTO stops (stop_name, section_id)
VALUES
('Binario 1', 31),
('Binario 2', 129),
('Binario 3', 213),
('Binario 4', 301);
--('Binario Cargo', 999),

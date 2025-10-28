-- sample temporary inserts

INSERT INTO train_types (type_name, priority, cruising_speed) VALUES
    ('regionale', 1, 0.5),
    ('veloce', 2, 0.5),
    ('freccia', 3, 0.5),
    ('cargo', 4, 0.5);

INSERT INTO sections (section_id, is_switch) VALUES
    (1, FALSE),
    (2, FALSE),
    (3, FALSE),
    (4, TRUE),
    (5, FALSE),
    (6, FALSE),
    (7, FALSE),
    (8, FALSE);

INSERT INTO section_connections (from_section_id, to_section_id, connection_type) VALUES
    (1, 2, 'normal'),
    (2, 3, 'normal'),
    (3, 4, 'normal'),
    (4, 5, 'main'),
    (4, 6, 'diverging'),
    (5, 7, 'normal'),
    (6, 8, 'normal');

INSERT INTO rail_blocks (block_name) VALUES
    ('block_1'),
    ('block_2'),
    ('block_3'),
    ('block_4');

INSERT INTO block_sections (block_id, section_id, section_order) VALUES
    (1, 1, 1),
    (1, 2, 2),
    (2, 3, 1),
    (2, 4, 2),
    (3, 5, 1),
    (3, 7, 2),
    (4, 6, 1),
    (4, 8, 2);

INSERT INTO trains (train_code, train_type_id, current_section_id, is_moving) VALUES
    ('EXP001', 1, 1, FALSE);

INSERT INTO wagons (train_id, wagon_index) VALUES
    (1, 0),
    (1, 1),
    (1, 2);

INSERT INTO wagon_positions (wagon_id, section_id) VALUES
    (1, 1),
    (2, 1),
    (3, 1);
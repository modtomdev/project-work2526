INSERT INTO sections (is_switch) VALUES
(FALSE),
(FALSE),
(FALSE),
(FALSE),
(TRUE);

INSERT INTO section_connections (from_section_id, to_section_id, is_active) VALUES
(1, 5, TRUE),
(5, 2, TRUE),
(5, 3, TRUE),
(2, 4, TRUE),
(3, 4, TRUE);

INSERT INTO rail_blocks (block_name) VALUES
('BLOCK_A'),
('BLOCK_B');

INSERT INTO block_sections (block_id, section_id) VALUES
(1, 1),
(1, 5),
(1, 2),
(2, 3),
(2, 4);

INSERT INTO train_types (type_name, priority_index, cruising_speed) VALUES
('Regional', 2, 0.4),
('Freight', 1, 0.3);

INSERT INTO trains (train_code, train_type_id, current_section_id, direction, requires_maintenance) VALUES
('REG-101', 1, 2, 1, FALSE),
('FRG-202', 2, 3, 1, FALSE);

INSERT INTO wagons (train_id, wagon_index) VALUES
(1, 1),
(1, 2),
(2, 1),
(2, 2),
(2, 3);

INSERT INTO wagon_positions (wagon_id, section_id, position_offset) VALUES
(1, 2, 0.2),
(2, 2, 0.6),
(3, 3, 0.1),
(4, 3, 0.5),
(5, 3, 0.8);

INSERT INTO stops (stop_name, section_id, platform_number) VALUES
('Platform 1', 2, 1),
('Platform 2', 3, 2),
('Depot Entry', 1, 5),
('Exit Junction', 4, 6);

INSERT INTO train_schedules (train_id, stop_id, scheduled_arrival_time, scheduled_departure_time, sequence_index) VALUES
(1, 3, '08:00:00', '08:05:00', 1),
(1, 4, '08:10:00', '08:12:00', 2),
(2, 1, '08:00:00', '08:10:00', 1),
(2, 2, '08:15:00', '08:20:00', 2);

TRUNCATE train_schedules, stops, wagon_positions, wagons, trains, train_types,
rail_blocks, section_connections, sections RESTART IDENTITY CASCADE;

INSERT INTO sections (is_switch)
VALUES
(FALSE), (FALSE), (FALSE), (TRUE), (FALSE), (FALSE), (TRUE), (FALSE), (FALSE), (TRUE);

INSERT INTO section_connections (from_section_id, to_section_id)
VALUES
(1, 2), (2, 3), (3, 4), (4, 5),
(3, 6), (6, 7), (7, 8),
(5, 9), (9, 10),
(2, 1), (3, 2), (4, 3), (5, 4),
(6, 3), (7, 6), (8, 7), (9, 5), (10, 9);

INSERT INTO rail_blocks (block_name, section_id)
VALUES
('Block A', 1),
('Block B', 2),
('Block C', 3),
('Block D', 4),
('Block E', 5),
('Block F', 6),
('Block G', 7),
('Block H', 8),
('Block I', 9),
('Block J', 10);

INSERT INTO train_types (type_name, priority_index, cruising_speed)
VALUES
('regional', 1, 0.6),
('express', 2, 1.0),
('fast', 3, 0.8),
('cargo', 4, 0.4);

INSERT INTO trains (train_code, train_type_id, current_section_id, direction, requires_maintenance)
VALUES
('R101', 1, 2, 1, FALSE),
('F202', 2, 4, 1, FALSE),
('V303', 3, 7, -1, FALSE),
('C404', 4, 8, 1, FALSE),
('R105', 1, 3, -1, TRUE);

INSERT INTO wagons (train_id, wagon_index)
VALUES
(1, 1), (1, 2), (1, 3),
(2, 1), (2, 2), (2, 3), (2, 4),
(3, 1), (3, 2), (3, 3), (3, 4),
(4, 1), (4, 2),
(5, 1), (5, 2), (5, 3);

INSERT INTO wagon_positions (wagon_id, section_id, position_offset)
VALUES
(1, 2, 0.2), (2, 2, 0.5), (3, 2, 0.8),
(4, 4, 0.1), (5, 4, 0.4), (6, 4, 0.7), (7, 4, 0.9),
(8, 7, 0.2), (9, 7, 0.4), (10, 7, 0.6), (11, 7, 0.8),
(12, 8, 0.3), (13, 8, 0.6),
(14, 3, 0.2), (15, 3, 0.5), (16, 3, 0.7);

INSERT INTO stops (stop_name, section_id, platform_number)
VALUES
('Milano Centrale', 1, 1),
('Bologna Centrale', 2, 2),
('Firenze Santa Maria Novella', 3, 3),
('Roma Termini', 5, 4),
('North Depot', 9, 5),
('South Depot', 10, 6);

INSERT INTO train_schedules (train_id, stop_id, scheduled_arrival_time, scheduled_departure_time)
VALUES
(1, 1, '2025-11-12 08:00:00', '2025-11-12 08:05:00'),
(1, 2, '2025-11-12 08:20:00', '2025-11-12 08:25:00'),
(1, 3, '2025-11-12 08:40:00', '2025-11-12 08:42:00'),
(2, 1, '2025-11-12 09:00:00', '2025-11-12 09:03:00'),
(2, 3, '2025-11-12 09:25:00', '2025-11-12 09:27:00'),
(2, 4, '2025-11-12 09:50:00', '2025-11-12 09:55:00'),
(3, 4, '2025-11-12 10:00:00', '2025-11-12 10:05:00'),
(3, 3, '2025-11-12 10:15:00', '2025-11-12 10:17:00'),
(3, 2, '2025-11-12 10:30:00', '2025-11-12 10:32:00'),
(4, 1, '2025-11-12 10:45:00', '2025-11-12 10:46:00'),
(4, 4, '2025-11-12 10:58:00', '2025-11-12 10:59:00'),
(5, 3, '2025-11-12 11:00:00', '2025-11-12 11:02:00'),
(5, 5, '2025-11-12 11:15:00', '2025-11-12 11:20:00');

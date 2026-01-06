This is an educational application which aims to simulate a portion of a rail network (a station with 4 stops).
The rail network topology can be described with the following data:

- sections (section_id)
horizontal sections
(0),(1),(2),(3),(4),(5),(6),(7),(8),(9),(10),(11),(12),(13),(14),(15),(16),(17),(18),(19),(20),(21),(22),(23),(24),(25),(26),(27),(28),(29),(30),(31),(32),(33),(34),(35),(36),(37),(38),(39),(40),(41),
(100),(101),(102),(103),(104),(105),(106),(107),(108),(109),(110),(111),(112),(113),(114),(115),(116),(117),(118),(119),(120),(121),(122),(123),(124),(125),(126),(127),(128),(129),(130),(131),(132),(133),(134),(135),(136),(137),(138),(139),(140),(141),
(200),(201),(202),(203),(204),(205),(206),(207),(208),(209),(210),(211),(212),(213),(214),(215),(216),(217),(218),(219),(220),(221),(222),(223),(224),
(300),(301),(302),(303),(304),(305),(306),(307),(308),(309),(310),
diagonal sections
(1000),(1001),(1010),(1011),(1020),(1021),(1030),(1031),(1040),(1041),
(2000),(2001),(2010),(2011),(2020),(2021),(2030),(2031),
(3000),(3001),(3010),(3011),(3020),(3021);

- section_connections (from_section_id, to_section_id)
(0, 1), (1, 2), (2, 3), (2, 1000), (1000, 1001), (1001, 105), (3, 4), (4, 5), (5, 6), (6, 7), (7, 8), (8, 9), (9, 10), (10, 1010), (1010, 1011), (1011, 113), (10, 11), (11, 12), (12, 13), (13, 14), (14, 15), (15, 16), (16, 17), (17, 18), (18, 1020), (1020, 1021), (1021, 121), (18, 19), (19, 20), (20, 21), (21, 22), (22, 23), (23, 24), (24, 25), (25, 26), (26, 27), (27, 28), (28, 29), (29, 30), (30, 31), (31, 32), (32, 33), (33, 34), (34, 35), (35, 36), (36, 37), (37, 38), (38, 39), (39, 40), (40, 41),
(41, 1040), (1040, 1041), (1041, 138), (41, 40), (40, 39), (39, 38), (38, 37), (37, 36), (36, 35), (35, 34), (34, 33), (33, 1030), (1030, 1031), (1031, 130), (33, 32), (32, 31), (31, 30), (30 , 29), (29, 28), (28, 27), (27, 26), (26, 25), (25, 24), (24, 23), (23, 22), (22, 21), (21, 20), (20, 19), (19, 18), (18, 17), (17, 16), (16, 15), (15, 14), (14, 13), (13, 12), (12, 11), (11, 10), (10, 9), (9, 8), (8, 7), (7, 6), (6, 5), (5, 4), (4, 3), (3, 2), (2, 1), (1, 0),
(100, 101), (101, 102), (102, 103), (103, 104), (104, 105), (105, 106), (106, 2000), (2000, 2001), (2001, 200), (106, 107), (107, 108), (108, 109), (109, 110), (110, 2010), (2010, 2011), (2011, 204), (110, 111), (111, 112), (112, 113), (113, 114), (114, 115), (115, 116), (116, 117), (117, 118), (118, 2020), (2020, 2021), (2021, 212), (118, 119), (119, 120), (120, 121), (121, 122), (122, 123), (123, 124), (124, 125), (125, 126), (126, 127), (127, 128), (129, 130), (130, 1031), (1031, 1030), (1030, 33), (130, 131), (131, 132), (132, 133), (133, 134), (134, 135), (135, 136), (136, 137), (137, 138), (138, 1041), (1041, 1040), (1040, 41), (138, 139), (139, 140), (140, 141),  
(141, 140), (140, 139), (139, 138), (138, 137), (137, 136), (136, 2030), (2030, 2031), (2031, 224), (136, 135), (135, 134), (134, 133), (133, 132), (132, 131), (131, 130), (130, 129), (129, 128), (128, 127), (127, 126), (126, 125), (125, 124), (124, 123), (123, 122), (122, 121), (121, 1021), (1021, 1020), (1020, 18), (121, 120), (120, 119), (119, 118), (118, 117), (117, 116), (116, 115), (115, 114), (114, 113), (113, 1011), (1011, 1010), (1010, 10), (113, 112), (112, 111), (111, 110), (110, 109), (109, 108), (108, 107), (107, 106), (106, 105), (105, 1001), (1001, 1000), (1000, 2), (105, 104), (104, 103), (103, 102), (102, 101), (101, 100),
(200, 3000), (3000, 3001), (200, 201), (201, 202), (202, 203), (203, 204), (204, 205), (205, 206), (206, 207), (207, 208), (208, 3010), (3010, 3011), (3011, 300), (208, 209), (209, 210), (210, 211), (211, 212), (212, 213), (213, 214), (214, 215), (215, 216), (216, 217), (218, 219), (219, 220), (220, 221), (221, 222), (222, 223), (223, 224), (224, 2031), (2031, 2030), (2030, 136),   
(224, 3020), (3020, 3021), (3021, 310), (224, 223), (223, 222), (222, 221), (221, 220), (220, 219), (219, 218), (218, 217), (217, 216), (216, 215), (215, 214), (214, 213), (213, 212), (212, 2021), (2021, 2020), (2020, 118), (212, 211), (211, 210), (210, 209), (209, 208), (208, 207), (207, 206), (206, 205), (205, 204), (204, 2011), (2011, 2010), (2010, 110), (204, 203), (203, 202), (202, 201), (201, 200), (200, 2001), (2001, 2000), (2000, 106),
(300, 301), (301, 302), (302, 303), (303, 304), (304, 305), (305, 306), (306, 307), (307, 308), (308, 309), (309, 310), (310, 3021), (3021, 3020), (3020, 224), 
(310, 309), (309, 308), (308, 307), (307, 306), (306, 305), (305, 304), (304, 303), (303, 302), (302, 301), (301, 300), (300, 3011), (3011, 3010), (3010, 208);

- rail_blocks (block_name, section_id)
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

- stops (stop_name, section_id)
('Track 1', 31),
('Track 2', 129),
('Track 3', 213),
('Track 4', 301);

---

This multistack containerized application is composed by: 
* a Postgres database which stores the network topology and train types. 
* a Python FastAPI backend that exposes some RESTful endpoints and a WebSocket.
* a React frontend that renders each train by consuming the WebSocket + minor features (like posting a train CSV on the backend).

---

1. Each section cannot contain more than one wagon at a given time.
2. There can only be one train in a block at any time. A train spanning multiple blocks occupies them all. Even the wagons act the same way, occupying the block/s.
3. Each train can move forwards and backwards along the tracks. Backwards movement (reversing) should prioritize entering horizontal sections if not occupied.
4. Each wagon is strictly binded to its locomotive's movements. 
5. To render each wagon smoothly, a "position_offset" field is passed to the frontend. This field should work in *all* conditions like diagonal travelling, backwards travelling etc.
6. Each Connection object must have an is_active field. This field acts as a traffic light between rail_blocks (signalling block system).
7. Each train should use a path finding algorithm to find the quickest route to the destination, continuously evaluating the section_connections availability. Reversing should be penalized.
8. Trains can only spawn on section 0 (left spawn) or section 141 (right spawn).
9. Trains can only despawn on section 100 (left despawn) or section 41 (right despawn).
10. Trains only enter a rail block if they can also leave it.
11. If a train must stop at section 31 or 129, these two stops must be approached respectively from section 30 and 128 (from the left).
12. If a train must stop at section 213 or 301, these two stops must be approached respectively from section 214 and 302 (from the right).
13. If two trains are "racing", the one with the higher priority_index should pass first.
14. The loaded csv can have a desired_stop_id. If the desired_stop_id is provided, the train should target that stop, sleep for 5 seconds and then target the despawn location. if no desired_stop_id is provided then the train is transit only, targets despawn point immediately.

Let's take for example the rail block 'B' composed by sections 2, 3 and 1000. 2 and 3 are horizontal sections, 1000 is a diagonal section. The explicit section connections (from_section_id, to_section_id) are: (2, 3), (2, 1000), (1000, 2), (3, 2). As we can see (3, 1000) and (1000, 3) are not available because in our visual representation of the network topology, this 2 connections are basically a V-shaped track turn.
A train that enters the 'B' block from the 'A' block can take the section connection (2, 1000). However a train that enters the 'B' block from the 'C' block cannot take (2, 1000). Note that (3, 1000) is already not available, so no problem with that one. The strategy to avoid V-shaped turns is to use a sql table made up of: (from_section_id, to_section_id, exclude_previous_block_name). 
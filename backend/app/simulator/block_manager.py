# generated sample code, must review

class BlockManager:
    def __init__(self, db_connection):
        self.db = db_connection
        
        # Load block configuration once
        self.block_sections = self.load_block_structure()
        # {block_id: [section_ids in order]}
        
        self.section_to_block = self.build_section_mapping()
        # {section_id: block_id}
        
        # Runtime state (in-memory)
        self.block_occupancy = {}  # {block_id: train_id or None}
    
    def load_block_structure(self):
        """Load which sections belong to which blocks"""
        result = self.db.query(
            "SELECT block_id, section_id, section_order "
            "FROM block_sections ORDER BY block_id, section_order"
        )
        
        blocks = {}
        for row in result:
            if row['block_id'] not in blocks:
                blocks[row['block_id']] = []
            blocks[row['block_id']].append(row['section_id'])
        
        return blocks
    
    def build_section_mapping(self):
        """Reverse mapping: section -> block"""
        mapping = {}
        for block_id, sections in self.block_sections.items():
            for section_id in sections:
                mapping[section_id] = block_id
        return mapping
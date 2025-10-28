# generated sample code, must review

class Train:
    def update(self, delta_time, block_manager):
        # Check if we can proceed
        if not block_manager.can_enter_next_block(
            self.train_id, 
            self.current_section_id
        ):
            # Block ahead is occupied - brake
            self.brake(delta_time)
            self.is_moving = False
            return
        
        # Accelerate to cruising speed
        if self.speed < self.cruising_speed:
            self.accelerate(delta_time)
            self.is_moving = True
        
        # Move forward
        section_length = self.get_section_length(self.current_section_id)
        self.position_offset += (self.speed * delta_time) / section_length
        
        # Check if entering new section
        if self.position_offset >= 1.0:
            old_section = self.current_section_id
            next_section = block_manager.get_next_section(
                self.current_section_id, 
                self.train_id
            )
            
            if next_section is None:
                # End of track
                self.brake(delta_time)
                return
            
            # Move to next section
            self.current_section_id = next_section
            self.position_offset -= 1.0
            
            # Update database
            self.db.execute(
                "UPDATE trains SET current_section_id = %s WHERE train_id = %s",
                (next_section, self.train_id)
            )
            
            # Update block occupancy
            old_block = block_manager.get_block_for_section(old_section)
            new_block = block_manager.get_block_for_section(next_section)
            
            if old_block != new_block:
                # Entering new block
                block_manager.occupy_block(self.train_id, new_block)
                
                # Try to release old block (if tail has cleared)
                block_manager.release_block(self.train_id, old_block)
    
    def accelerate(self, delta_time):
        acceleration = 20.0  # pixels/s²
        self.speed = min(
            self.speed + acceleration * delta_time, 
            self.cruising_speed
        )
    
    def brake(self, delta_time):
        deceleration = 30.0  # pixels/s²
        self.speed = max(self.speed - deceleration * delta_time, 0.0)
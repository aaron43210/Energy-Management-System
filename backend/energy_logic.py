# =============================================================================
# Energy Control Rules Engine
# =============================================================================
# This file implements the core business logic for automatic energy management.
#
# The auto_control() function applies these rules:
#   - If room is OCCUPIED: turn Light ON (person needs light)
#   - If room is EMPTY: turn Light OFF and AC OFF (save energy)
#
# This logic is triggered whenever occupancy status changes.
# It's a pure function - given same input, always produces same output.
# Easy to test and maintain.
# =============================================================================


def auto_control(rooms, room_id):
    """
    Automatically controls lights and AC based on room occupancy.
    
    Parameters:
        rooms: Dictionary containing all room states
        room_id: ID of the room to control
    
    Returns:
        True if control was applied successfully
        False if room was not found
    
    Control Logic:
        - Room OCCUPIED: Turn light ON
        - Room EMPTY: Turn light OFF and AC OFF
    """
    # Check if room exists in our system
    if room_id not in rooms:
        print(f"Room '{room_id}' not found")
        return False

    # Get the current state of the room
    room_state = rooms[room_id]
    
    # Check if room is occupied
    is_occupied = room_state.get("occupied", False)
    
    if is_occupied:
        # Room is occupied - turn on light if it's off
        light_is_off = not room_state.get("light", False)
        if light_is_off:
            room_state["light"] = True
            print(f"{room_id}: Light ON")
    else:
        # Room is empty - turn off light and AC to save energy
        light_is_on = room_state.get("light", False)
        if light_is_on:
            room_state["light"] = False
            print(f"{room_id}: Light OFF")
        
        ac_is_on = room_state.get("ac", False)
        if ac_is_on:
            room_state["ac"] = False
            print(f"{room_id}: AC OFF")
            
    return True

# Energy Control Rules Engine
# This file implements the core business logic for automatic energy management.
# The auto_control() function applies rules:
#   - If room is OCCUPIED: turn Light ON
#   - If room is EMPTY: turn Light OFF and AC OFF
# This logic is triggered whenever occupancy status changes.
# Pure function with no side effects - easy to test and maintain.

from typing import Dict, Any


def auto_control(rooms: Dict[str, Any], room_id: str) -> bool:
    if room_id not in rooms:
        print(f"Room '{room_id}' not found")
        return False

    room_state = rooms[room_id]
    
    if room_state.get("occupied", False):
        if not room_state.get("light", False):
            room_state["light"] = True
            print(f"{room_id}: Light ON")
    else:
        if room_state.get("light", False):
            room_state["light"] = False
            print(f"{room_id}: Light OFF")
        if room_state.get("ac", False):
            room_state["ac"] = False
            print(f"{room_id}: AC OFF")
            
    return True

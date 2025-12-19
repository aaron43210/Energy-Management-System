# Room Configuration and State Management
# This file manages the state of all rooms in the system.
# It defines:
#   - Room names (Classroom, Lab, Library, Office)
#   - Default state structure for each room (occupancy, lights, AC, process info)
#   - Factory functions to create fresh room state copies
# Ensures each room is independent and maintains proper state separation.

import copy
from typing import List, Dict, Any

ROOM_NAMES: List[str] = [
    "Classroom",
    "Lab",
    "Library",
    "Office"
]

DEFAULT_ROOM_STATE = {
    "occupied": False,
    "light": False,
    "ac": False,
    "ai_mode": "webcam",
    "cctv_ip": "",
    "cctv_username": "",
    "cctv_password": "",
    "cctv_channel": "0",
    "rtsp_url": "",
    "process": None,
    "stop_event": None
}


def get_room_config() -> Dict[str, Any]:
    return copy.deepcopy(DEFAULT_ROOM_STATE)


def get_initial_rooms_state() -> Dict[str, Dict[str, Any]]:
    return {name: get_room_config() for name in ROOM_NAMES}

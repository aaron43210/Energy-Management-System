# =============================================================================
# Room Configuration and State Management Module
# =============================================================================
# This file manages the state of all rooms in the Energy Management System.
# 
# It defines:
#   - ROOM_NAMES: List of room names (Classroom, Lab, Library, Office)
#   - DEFAULT_ROOM_STATE: Template for each room's initial state
#   - Functions to create room configurations
#
# Each room tracks:
#   - occupied: Whether people are detected in the room
#   - light: Whether lights are on/off
#   - ac: Whether AC is on/off
#   - ai_mode: Detection mode (webcam or cctv)
#   - CCTV connection details (IP, username, password, channel)
#   - process: Thread running AI detection
#   - stop_event: Event to signal thread termination
# =============================================================================

import copy

# List of all rooms in the system
ROOM_NAMES = [
    "Classroom",
    "Lab", 
    "Library",
    "Office"
]

# Default state template for each room
# All rooms start with everything off and no connections
DEFAULT_ROOM_STATE = {
    "occupied": False,       # Is room currently occupied?
    "light": False,          # Is light on?
    "ac": False,             # Is AC on?
    "ai_mode": "webcam",     # Detection mode: "webcam" or "cctv"
    "cctv_ip": "",           # CCTV camera IP address
    "cctv_username": "",     # CCTV login username
    "cctv_password": "",     # CCTV login password
    "cctv_channel": "0",     # CCTV channel number
    "rtsp_url": "",          # Full RTSP stream URL
    "process": None,         # Thread running AI detection
    "stop_event": None       # Event to stop the thread
}


def get_room_config():
    """
    Returns a fresh copy of the default room configuration.
    
    Uses deepcopy to ensure each room has independent state.
    This prevents accidental sharing of mutable objects between rooms.
    """
    # Return a deep copy so each room has its own independent state
    return copy.deepcopy(DEFAULT_ROOM_STATE)


def get_initial_rooms_state():
    """
    Creates initial state dictionary for all rooms.
    
    Returns a dictionary where:
        - Keys are room names from ROOM_NAMES list
        - Values are independent copies of DEFAULT_ROOM_STATE
    
    Example return value:
        {
            "Classroom": {occupied: False, light: False, ...},
            "Lab": {occupied: False, light: False, ...},
            ...
        }
    """
    # Create dictionary with room name as key and fresh config as value
    rooms_state = {}
    for room_name in ROOM_NAMES:
        rooms_state[room_name] = get_room_config()
    return rooms_state

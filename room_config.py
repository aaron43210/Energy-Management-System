# ---------------------------------
# ROOM CONFIGURATION FILE
# ---------------------------------
# This file stores room-wise camera
# and energy state information.
# ---------------------------------

import time

ROOMS = {
    "Classroom": {
        "rtsp": "rtsp://user:pass@192.168.1.101:554/Streaming/Channels/101",
        "power": "OFF",
        "last_seen": time.time()
    },
    "Lab": {
        "rtsp": "rtsp://user:pass@192.168.1.102:554/Streaming/Channels/101",
        "power": "OFF",
        "last_seen": time.time()
    }
}
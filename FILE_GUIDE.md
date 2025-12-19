# Project File Guide

## Backend Files (Python)

### `backend/api.py`
The main server that handles all HTTP requests from the frontend. It defines REST API endpoints for:
- Getting room status (GET /api/rooms)
- Updating occupancy (POST /api/occupancy)
- Managing AI detection (POST /api/ai/{room_id}/start, /stop)
- CCTV control (POST /api/cctv/connect, /disconnect)
- Video streaming (GET /api/stream/{room_id})
- Webcam demo (POST /api/webcam/test/start, /stop, /status)

**Why it matters:** This is the bridge between frontend and backend logic. Every user action in the UI goes through these endpoints.

### `backend/room_config.py`
Manages the state of all rooms in the system. Defines:
- Room names (Classroom, Lab, Library, Office)
- Default state for each room (occupied, light, ac, process info)
- Factory functions to create independent room states

**Why it matters:** Ensures each room maintains its own state without interfering with others.

### `backend/energy_logic.py`
The core business logic that decides when to turn lights and AC on/off. Rules:
- Room OCCUPIED → Light ON
- Room EMPTY → Light OFF, AC OFF

**Why it matters:** This is the "smart" part - the algorithm that controls energy based on occupancy.

### `backend/person_detect.py`
Loads the YOLOv8 AI model and provides person detection. Uses lazy-loading to:
- Load model only once when first needed
- Reuse for all frames (efficient)
- Detect people in images with configurable confidence threshold

**Why it matters:** This is how the system "sees" people. Without this, the system can't detect occupancy.

### `backend/cctv_stream.py`
Handles live RTSP camera streams from professional CCTV cameras. Features:
- Opens and maintains RTSP connection
- Runs YOLO detection on each frame in background thread
- Draws bounding boxes around detected persons
- Converts frames to MJPEG for web viewing
- Triggers energy control based on occupancy

**Why it matters:** This enables production deployment with real security cameras.

### `backend/webcam_energy.py`
Processes video from device webcam for testing/demos. Features:
- Captures frames from device camera
- Runs YOLO detection
- Displays visual feedback (bounding boxes, person count)
- Sends occupancy updates to API
- Shows live information on camera window

**Why it matters:** Makes it easy to demo the system without expensive CCTV hardware.

### `backend/multi_room_energy.py`
Orchestrates the AI monitoring threads. Manages:
- Starting background threads for each room
- Choosing between RTSP or webcam based on configuration
- Stopping threads gracefully

**Why it matters:** Controls the lifecycle of all AI processes - starts/stops them as needed.

### `backend/__init__.py`
Package initialization file. Exports the FastAPI app so the server can start.

**Why it matters:** Simple but essential - tells Python this directory is a package and what to export.

---

## Frontend Files (React/JavaScript)

### `frontend/src/main.jsx`
Entry point for the React application. Renders the App component into the HTML page.

**Why it matters:** First file that loads - sets up the React rendering system.

### `frontend/src/App.jsx`
Root React component. Simply renders the Dashboard.

**Why it matters:** Top-level component that holds the entire UI.

### `frontend/src/api.js`
Service layer for backend communication. Exports functions for:
- fetchRooms() - get all room status
- sendOccupancy() - update occupancy
- startAi(), stopAi() - manage AI processes
- connectCctv(), disconnectCctv() - manage CCTV
- getStreamUrl() - get video stream URL

**Why it matters:** Centralizes all API calls. If backend endpoints change, only this file needs updating.

### `frontend/src/Dashboard.jsx`
Main dashboard component. Features:
- Auto-refreshes room status every 1 second
- Shows all rooms as cards
- Provides 3 tabs: Dashboard, Webcam Test, CCTV Real Mode
- Handles auto-refresh toggle and refresh rate settings
- Shows connection errors if backend is down

**Why it matters:** Core UI that users interact with. Manages real-time data updates.

### `frontend/src/RoomCard.jsx`
Display component for a single room. Shows:
- Room name
- Occupancy status (OCCUPIED/EMPTY)
- Light state (ON/OFF)
- AC state (ON/OFF)
- AI monitoring status

**Why it matters:** Visualizes the state of each room in an easy-to-read card format.

### `frontend/src/WebcamTestMode.jsx`
Demo mode for testing with device camera. Features:
- Start/stop buttons for camera detection
- Real-time status monitoring
- Instructions for using the demo

**Why it matters:** Lets users test the entire system without professional CCTV hardware. Perfect for demos.

### `frontend/src/CctvRealMode.jsx`
Production mode for real CCTV cameras. Features:
- Configure camera IP, username, password
- Connect/disconnect from cameras
- Display live video stream with detection overlays
- Show real-time person count and occupancy

**Why it matters:** Enables deployment in real buildings with security cameras.

---

## How Everything Connects

```
User opens browser → main.jsx renders App.jsx
         ↓
   App renders Dashboard.jsx
         ↓
   Dashboard imports api.js to fetch data
         ↓
   api.js makes HTTP calls to backend
         ↓
   backend/api.py handles the requests
         ↓
   api.py uses room_config.py for state
   api.py uses energy_logic.py to control energy
   api.py uses multi_room_energy.py to manage AI processes
         ↓
   multi_room_energy.py spawns threads
   Threads run person_detect.py (AI detection)
   Threads run webcam_energy.py or cctv_stream.py
         ↓
   Detected occupancy sent back to API
   API returns data to frontend
   Dashboard displays updated room status
```

## Summary for Your Professor

This is a complete Energy Management System that:
1. **Detects people** using YOLOv8 AI in real-time
2. **Tracks occupancy** for multiple rooms independently
3. **Controls energy** automatically (lights/AC on when occupied, off when empty)
4. **Provides UI** for real-time monitoring and manual control
5. **Supports two modes:**
   - Demo with webcam (for testing)
   - Production with CCTV cameras (for real buildings)

The architecture is modular - each file has a specific responsibility, making it easy to understand, test, and modify.

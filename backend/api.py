# =============================================================================
# API Server - Main Entry Point for Energy Management System
# =============================================================================
# This file defines all REST API endpoints that the frontend uses.
#
# Endpoints include:
#   - GET /api/rooms: Get room status (occupancy, lights, AC state)
#   - POST /api/ai/{room_id}/start: Start AI detection for a room
#   - POST /api/ai/{room_id}/stop: Stop AI detection for a room
#   - POST /api/cctv/connect: Connect to CCTV camera
#   - POST /api/cctv/disconnect: Disconnect from CCTV camera
#   - GET /api/stream/{room_id}: Stream video with detection overlays
#   - POST /api/webcam/test/start: Start webcam demo mode
#   - POST /api/webcam/test/stop: Stop webcam demo mode
#   - POST /api/video/upload: Upload and analyze video file
#
# All endpoints return JSON responses and handle errors appropriately.
# =============================================================================

import cv2
import numpy as np
from contextlib import asynccontextmanager

import os
import shutil
from pathlib import Path
from tempfile import NamedTemporaryFile

from fastapi import FastAPI, HTTPException, UploadFile, File, Form
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

# Import local modules
from .room_config import get_initial_rooms_state
from .energy_logic import auto_control
from .multi_room_energy import start_ai_process, stop_ai_process
from .person_detect import count_people
from .cctv_stream import (
    create_stream_processor,
    get_stream_processor,
    cleanup_stream_processor,
    cleanup_all_processors
)
from .webcam_stream import (
    get_webcam_processor,
    start_webcam_stream,
    stop_webcam_stream
)


# =============================================================================
# Lifespan Context Manager
# =============================================================================
# Handles startup and shutdown events for the FastAPI application.
# On shutdown, cleans up all running processes and stream processors.
# =============================================================================

@asynccontextmanager
async def lifespan(app):
    """
    Lifespan context manager for FastAPI application.
    
    Startup: Prints welcome message
    Shutdown: Stops all AI processes and cleans up resources
    """
    # Startup
    print("Energy AI Management Backend starting up...")
    
    yield  # Application runs here
    
    # Shutdown
    print("Shutting down server and stopping processes...")
    global webcam_test_process
    
    # Clean up all CCTV stream processors
    cleanup_all_processors()
    
    # Stop webcam test process if running
    if webcam_test_process is not None:
        try:
            webcam_test_process.terminate()
            webcam_test_process.wait(timeout=3)
        except Exception as e:
            print(f"Error stopping webcam: {e}")
        webcam_test_process = None
    
    # Stop AI processes for all rooms
    for room_id in rooms_state:
        stop_ai_process(rooms_state, room_id)
    
    print("All processes stopped")


# =============================================================================
# FastAPI Application Setup
# =============================================================================

# Create FastAPI application
app = FastAPI(
    title="Energy AI Management Backend",
    version="1.0.0",
    description="Energy management with AI person detection",
    lifespan=lifespan
)

# Add CORS middleware to allow frontend to connect
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],      # Allow all origins
    allow_credentials=True,
    allow_methods=["*"],       # Allow all methods
    allow_headers=["*"],       # Allow all headers
)


# =============================================================================
# Global State Variables
# =============================================================================

# Dictionary storing the state of all rooms
# Keys are room names, values are state dictionaries
rooms_state = get_initial_rooms_state()

# Reference to webcam test process (if running)
webcam_test_process = None

# Storage for uploaded videos (session_id -> file_path)
_uploaded_videos = {}

# Storage for video stream occupancy state
# session_id -> {occupied, person_count, light, ac, room_id}
_video_occupancy_state = {}


# =============================================================================
# Request/Response Models (Pydantic)
# =============================================================================
# These classes define the structure of request and response data.
# Pydantic handles validation automatically.
# =============================================================================

class RoomState(BaseModel):
    """Response model for a single room's state."""
    id: str
    occupied: bool
    light: bool
    ac: bool
    rtsp_url: str
    is_running: bool


class AllRoomsResponse(BaseModel):
    """Response model for all rooms."""
    rooms: list


class OccupancyUpdate(BaseModel):
    """Request model for occupancy update."""
    room_id: str
    occupied: bool


class RtspUpdateRequest(BaseModel):
    """Request model for RTSP URL update."""
    room_id: str
    rtsp_url: str


class CctvConfigRequest(BaseModel):
    """Request model for CCTV configuration."""
    room_id: str
    cctv_ip: str
    cctv_username: str
    cctv_password: str
    cctv_channel: str = "0"


class AiModeRequest(BaseModel):
    """Request model for AI mode change."""
    room_id: str
    ai_mode: str


# =============================================================================
# Helper Functions
# =============================================================================

def _save_upload_to_temp(upload_file):
    """
    Saves an uploaded file to a temporary location.
    
    Parameters:
        upload_file: The uploaded file from FastAPI
    
    Returns:
        Path to the saved temporary file
    """
    # Get file extension from original filename
    suffix = Path(upload_file.filename or "upload").suffix or ".mp4"
    
    # Create temporary file
    tmp_file = NamedTemporaryFile(delete=False, suffix=suffix)
    
    try:
        # Copy uploaded content to temp file
        shutil.copyfileobj(upload_file.file, tmp_file)
    finally:
        tmp_file.close()
    
    return tmp_file.name


def _analyze_video_file(video_path, room_id, frame_skip=5):
    """
    Analyzes a video file for person detection.
    
    Parameters:
        video_path: Path to the video file
        room_id: ID of the room for simulation
        frame_skip: Process every Nth frame (default 5)
    
    Returns:
        Dictionary with analysis results including:
        - frames_total: Total frames in video
        - frames_analyzed: Number of frames analyzed
        - fps: Frames per second
        - duration_seconds: Video duration
        - occupied_frames: Frames with people detected
        - occupancy_ratio: Ratio of occupied frames
        - events: List of occupancy change events
    """
    # Validate frame_skip
    if frame_skip < 1:
        raise HTTPException(status_code=400, detail="frame_skip must be >= 1")

    # Open video file
    cap = cv2.VideoCapture(video_path)
    if not cap.isOpened():
        raise HTTPException(status_code=400, detail="Could not read uploaded video")

    # Get video properties
    fps = cap.get(cv2.CAP_PROP_FPS) or 30.0
    total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT)) or 0
    duration_seconds = total_frames / fps if fps else 0.0

    # Initialize simulation state
    sim_state = {room_id: {"occupied": False, "light": False, "ac": False}}
    events = []
    occupied_frames = 0
    frames_analyzed = 0
    previous_occupied = None
    frame_index = 0

    try:
        # Process each frame
        while True:
            ret, frame = cap.read()
            if not ret or frame is None:
                break

            # Skip frames for performance
            if frame_skip > 1 and frame_index % frame_skip != 0:
                frame_index += 1
                continue

            # Run person detection
            people_count = count_people(frame)
            occupied = people_count > 0

            # Count occupied frames
            if occupied:
                occupied_frames += 1

            # Update simulation state
            sim_state[room_id]["occupied"] = occupied
            
            # Record event if occupancy changed
            if previous_occupied is None or occupied != previous_occupied:
                auto_control(sim_state, room_id)
                events.append({
                    "frame_index": frame_index,
                    "time_seconds": round(frame_index / fps, 2) if fps else 0.0,
                    "occupied": occupied,
                    "light": sim_state[room_id]["light"],
                    "ac": sim_state[room_id]["ac"],
                    "person_count": people_count
                })
                previous_occupied = occupied

            frames_analyzed += 1
            frame_index += 1
            
    finally:
        cap.release()

    # Calculate occupancy ratio
    occupancy_ratio = (occupied_frames / frames_analyzed) if frames_analyzed else 0.0

    return {
        "room_id": room_id,
        "frames_total": total_frames,
        "frames_analyzed": frames_analyzed,
        "fps": round(float(fps), 2),
        "duration_seconds": round(duration_seconds, 2),
        "occupied_frames": occupied_frames,
        "occupancy_ratio": round(occupancy_ratio, 3),
        "events": events
    }


def _generate_video_stream_with_detection(video_path, session_id):
    """
    Generator that streams video frames with YOLO person detection overlays.
    
    Yields MJPEG frames for browser streaming.
    
    Parameters:
        video_path: Path to video file
        session_id: Session identifier for tracking state
    """
    # Open video file
    cap = cv2.VideoCapture(video_path)
    
    if not cap.isOpened():
        return
    
    # Initialize occupancy state for this session
    room_id = _video_occupancy_state.get(session_id, {}).get("room_id", "UploadedVideo")
    _video_occupancy_state[session_id] = {
        "occupied": False,
        "person_count": 0,
        "light": False,
        "ac": False,
        "room_id": room_id
    }
    
    frame_count = 0
    
    while True:
        ret, frame = cap.read()
        
        if not ret:
            # Loop back to start when video ends
            cap.set(cv2.CAP_PROP_POS_FRAMES, 0)
            continue
        
        # Run person detection
        people_count = count_people(frame)
        occupied = people_count > 0
        
        # Update occupancy state
        _video_occupancy_state[session_id]["person_count"] = people_count
        _video_occupancy_state[session_id]["occupied"] = occupied
        
        # Simulate energy control when occupancy changes
        if occupied != _video_occupancy_state[session_id].get("occupied_prev"):
            sim_state = {room_id: {"occupied": occupied, "light": False, "ac": False}}
            auto_control(sim_state, room_id)
            _video_occupancy_state[session_id]["light"] = sim_state[room_id]["light"]
            _video_occupancy_state[session_id]["ac"] = sim_state[room_id]["ac"]
            _video_occupancy_state[session_id]["occupied_prev"] = occupied
        
        # Draw detection boxes using YOLO
        from ultralytics import YOLO
        from pathlib import Path as PathlibPath
        MODEL_PATH = PathlibPath(__file__).resolve().parent.parent / "yolov8n.pt"
        model = YOLO(MODEL_PATH)
        results = model(frame, conf=0.4, classes=[0], verbose=False)
        
        # Draw bounding boxes for each detected person
        # Draw bounding boxes for each detected person
        if results[0] and results[0].boxes:
            for box in results[0].boxes:
                x1, y1, x2, y2 = map(int, box.xyxy[0])
                confidence = box.conf[0]
                cv2.rectangle(frame, (x1, y1), (x2, y2), (0, 255, 0), 2)
                label = f"Person {confidence:.2f}"
                cv2.putText(frame, label, (x1, y1 - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 2)
        
        # Draw overlay with status information
        cv2.rectangle(frame, (0, 0), (400, 90), (0, 0, 0), -1)
        cv2.putText(frame, f"People: {people_count}", (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 255), 2)
        
        # Draw occupancy status
        status_color = (0, 0, 255) if people_count > 0 else (0, 255, 0)
        occupancy_text = "OCCUPIED" if people_count > 0 else "EMPTY"
        cv2.putText(frame, occupancy_text, (10, 60), cv2.FONT_HERSHEY_SIMPLEX, 0.8, status_color, 2)
        
        # Draw power status
        light_color = (0, 255, 0) if _video_occupancy_state[session_id]["light"] else (0, 0, 255)
        light_text = "💡 ON" if _video_occupancy_state[session_id]["light"] else "💡 OFF"
        cv2.putText(frame, light_text, (10, 90), cv2.FONT_HERSHEY_SIMPLEX, 0.7, light_color, 2)
        
        # Encode frame as JPEG for streaming
        ret, buffer = cv2.imencode('.jpg', frame)
        if ret:
            frame_bytes = buffer.tobytes()
            yield (b'--frame\r\n'
                   b'Content-Type: image/jpeg\r\n\r\n' + frame_bytes + b'\r\n')
        
        frame_count += 1
    
    cap.release()


# =============================================================================
# Response Models for Video Analysis
# =============================================================================

class VideoAnalysisEvent(BaseModel):
    """Model for a single video analysis event."""
    frame_index: int
    time_seconds: float
    occupied: bool
    light: bool
    ac: bool
    person_count: int


class VideoAnalysisResponse(BaseModel):
    """Response model for video analysis results."""
    room_id: str
    frames_total: int
    frames_analyzed: int
    fps: float
    duration_seconds: float
    occupied_frames: int
    occupancy_ratio: float
    events: list


# =============================================================================
# API Endpoints
# =============================================================================

@app.get("/")
def root():
    """
    Root endpoint - health check.
    
    Returns:
        Message confirming backend is running
    """
    return {"message": "Energy Management Backend Running", "version": "1.0.0"}


@app.get("/api/rooms", response_model=AllRoomsResponse)
def get_rooms_status():
    """
    Get status of all rooms.
    
    Returns:
        List of all rooms with their current state
    """
    response_rooms = []
    
    for room_id, state in rooms_state.items():
        # Check if AI process is running
        process = state.get("process")
        is_running = process.is_alive() if process else False
        
        # Build room state response
        response_rooms.append(
            RoomState(
                id=room_id,
                occupied=state["occupied"],
                light=state["light"],
                ac=state["ac"],
                rtsp_url=state["rtsp_url"],
                is_running=is_running
            )
        )
    
    return {"rooms": response_rooms}


@app.post("/api/occupancy")
def update_occupancy(data: OccupancyUpdate):
    """
    Update room occupancy status.
    
    Called by AI detection processes when occupancy changes.
    Triggers auto_control to update lights and AC.
    
    Parameters:
        data: OccupancyUpdate with room_id and occupied status
    
    Returns:
        Updated room state
    """
    # Check if room exists
    if data.room_id not in rooms_state:
        raise HTTPException(status_code=404, detail="Room not found")
    
    # Update occupancy
    rooms_state[data.room_id]["occupied"] = data.occupied
    
    # Apply energy control rules
    auto_control(rooms_state, data.room_id)
    
    return {
        "status": "updated",
        "room_id": data.room_id,
        "occupied": data.occupied
    }


# =============================================================================
# Video Upload Endpoints
# =============================================================================

@app.post("/api/video/upload", response_model=VideoAnalysisResponse)
async def upload_video(
    file: UploadFile = File(...),
    room_id: str = Form("UploadedVideo"),
    frame_skip: int = Form(5)
):
    """
    Upload and analyze a video file for person detection.
    
    Parameters:
        file: Video file to upload
        room_id: Room ID to use for simulation (default "UploadedVideo")
        frame_skip: Process every Nth frame (default 5)
    
    Returns:
        Analysis results including occupancy events and statistics
    """
    temp_path = None
    
    try:
        # Save uploaded file to temp location
        temp_path = _save_upload_to_temp(file)
        
        # Generate session ID for streaming
        import uuid
        session_id = str(uuid.uuid4())
        _uploaded_videos[session_id] = temp_path
        
        # Analyze the video
        result = _analyze_video_file(temp_path, room_id, frame_skip)
        result["session_id"] = session_id
        
        return result
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error analyzing video: {str(e)}")


@app.get("/api/video/stream/{session_id}")
def stream_uploaded_video(session_id: str):
    """
    Stream uploaded video with YOLO detection overlays as MJPEG.
    
    Parameters:
        session_id: Session ID from video upload
    
    Returns:
        MJPEG video stream
    """
    # Check if session exists
    if session_id not in _uploaded_videos:
        raise HTTPException(status_code=404, detail="Video session not found")
    
    video_path = _uploaded_videos[session_id]
    
    # Check if file still exists
    if not os.path.exists(video_path):
        raise HTTPException(status_code=404, detail="Video file not found")
    
    return StreamingResponse(
        _generate_video_stream_with_detection(video_path, session_id),
        media_type="multipart/x-mixed-replace; boundary=frame"
    )


@app.get("/api/video/status/{session_id}")
def get_video_stream_status(session_id: str):
    """
    Get current occupancy status for a video stream.
    
    Parameters:
        session_id: Session ID from video upload
    
    Returns:
        Current occupancy state for the video stream
    """
    # Check if session exists
    if session_id not in _video_occupancy_state:
        raise HTTPException(status_code=404, detail="Video session not found")
    
    state = _video_occupancy_state[session_id]
    
    return {
        "session_id": session_id,
        "occupied": state.get("occupied", False),
        "person_count": state.get("person_count", 0),
        "light": state.get("light", False),
        "ac": state.get("ac", False),
        "room_id": state.get("room_id", "UploadedVideo")
    }


@app.post("/api/video/cleanup/{session_id}")
def cleanup_video_session(session_id: str):
    """
    Clean up uploaded video file after done.
    
    Parameters:
        session_id: Session ID to clean up
    
    Returns:
        Status message
    """
    if session_id in _uploaded_videos:
        video_path = _uploaded_videos[session_id]
        
        # Try to delete the file
        try:
            if os.path.exists(video_path):
                os.remove(video_path)
        except Exception as e:
            print(f"Error cleaning up video: {e}")
        
        # Remove from storage
        del _uploaded_videos[session_id]
    
    return {"status": "cleaned up"}


# =============================================================================
# AI Process Control Endpoints
# =============================================================================

@app.post("/api/ai/{room_id}/start")
def start_room_ai(room_id: str):
    """
    Start AI detection process for a room.
    
    Parameters:
        room_id: ID of the room to start monitoring
    
    Returns:
        Status message
    """
    # Check if room exists
    if room_id not in rooms_state:
        raise HTTPException(status_code=404, detail="Room not found")
    
    # Start AI process
    start_ai_process(rooms_state, room_id, camera_index=0)
    
    return {"status": f"AI started for {room_id}"}


@app.post("/api/ai/{room_id}/stop")
def stop_room_ai(room_id: str):
    """
    Stop AI detection process for a room.
    
    Parameters:
        room_id: ID of the room to stop monitoring
    
    Returns:
        Status message
    """
    # Check if room exists
    if room_id not in rooms_state:
        raise HTTPException(status_code=404, detail="Room not found")
    
    # Stop AI process
    stop_ai_process(rooms_state, room_id)
    
    return {"status": f"AI stopped for {room_id}"}


# =============================================================================
# CCTV Connection Endpoints
# =============================================================================

@app.post("/api/cctv/connect")
def connect_cctv(data: CctvConfigRequest):
    """
    Connect to a CCTV camera via RTSP.
    
    Builds RTSP URL from provided credentials and starts stream processing.
    
    Parameters:
        data: CctvConfigRequest with IP, username, password, channel
    
    Returns:
        Connection status and RTSP URL
    """
    # Check if room exists
    if data.room_id not in rooms_state:
        raise HTTPException(status_code=404, detail="Room not found")
    
    try:
        # Build RTSP URL from credentials
        rtsp_url = (
            f"rtsp://{data.cctv_username}:{data.cctv_password}@"
            f"{data.cctv_ip}:554/Streaming/Channels/{data.cctv_channel}"
        )
        
        # Store RTSP URL in room state
        rooms_state[data.room_id]["rtsp_url"] = rtsp_url
        
        # Create stream processor
        processor = create_stream_processor(rtsp_url, data.room_id)
        
        # Try to connect
        if not processor.connect():
            raise HTTPException(status_code=502, detail="Could not connect to camera")
        
        # Define callback for occupancy changes
        def occupancy_callback(room_id, is_occupied):
            if room_id in rooms_state:
                rooms_state[room_id]["occupied"] = is_occupied
                auto_control(rooms_state, room_id)
        
        # Set callback and start processing
        processor.occupancy_callback = occupancy_callback
        processor.start_processing()
        
        return {
            "status": "connected",
            "room_id": data.room_id,
            "rtsp_url": rtsp_url,
            "message": f"Connected to {data.room_id} camera"
        }
    
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error: {str(e)}")


@app.post("/api/cctv/disconnect")
def disconnect_cctv(data: dict):
    """
    Disconnect from a CCTV camera.
    
    Parameters:
        data: Dictionary with room_id
    
    Returns:
        Disconnection status
    """
    room_id = data.get("room_id")
    
    # Validate room_id
    if not room_id or room_id not in rooms_state:
        raise HTTPException(status_code=404, detail="Room not found")
    
    try:
        # Stop and clean up stream processor
        cleanup_stream_processor(room_id)
        
        # Reset room state
        rooms_state[room_id]["rtsp_url"] = ""
        rooms_state[room_id]["occupied"] = False
        auto_control(rooms_state, room_id)
        
        return {
            "status": "disconnected",
            "room_id": room_id,
            "message": f"Disconnected from {room_id}"
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/cctv/status/{room_id}")
def get_cctv_status(room_id: str):
    """
    Get CCTV connection status for a room.
    
    Parameters:
        room_id: ID of the room to check
    
    Returns:
        Connection status and person count
    """
    # Check if room exists
    if room_id not in rooms_state:
        raise HTTPException(status_code=404, detail="Room not found")
    
    # Get stream processor
    processor = get_stream_processor(room_id)
    
    # Return not connected if no processor
    if processor is None:
        return {
            "room_id": room_id,
            "connected": False,
            "person_count": 0,
            "occupied": False
        }
    
    # Get person count and status
    person_count = processor.get_person_count()
    is_occupied = rooms_state[room_id]["occupied"]
    
    return {
        "room_id": room_id,
        "connected": processor.is_running,
        "person_count": person_count,
        "occupied": is_occupied,
        "light": rooms_state[room_id]["light"],
        "ac": rooms_state[room_id]["ac"]
    }


# =============================================================================
# CCTV Stream Endpoint
# =============================================================================

def generate_annotated_stream(room_id):
    """
    Generator that yields MJPEG frames from CCTV stream.
    
    Parameters:
        room_id: ID of the room to stream
    
    Yields:
        MJPEG frame bytes
    """
    processor = get_stream_processor(room_id)
    
    # Generate placeholder if no processor
    if processor is None:
        placeholder = np.zeros((480, 640, 3), dtype=np.uint8)
        cv2.putText(
            placeholder,
            "Camera Not Connected",
            (100, 240),
            cv2.FONT_HERSHEY_SIMPLEX,
            1.5,
            (0, 0, 255),
            2
        )
        ret, buffer = cv2.imencode('.jpg', placeholder)
        frame_bytes = buffer.tobytes()
        yield (b'--frame\r\n'
               b'Content-Type: image/jpeg\r\n\r\n' + frame_bytes + b'\r\n')
        return
    
    # Stream frames while processor is running
    while processor.is_running:
        try:
            frame_bytes = processor.get_annotated_frame()
            
            if frame_bytes:
                yield (b'--frame\r\n'
                       b'Content-Type: image/jpeg\r\n\r\n' + frame_bytes + b'\r\n')
            else:
                import time
                time.sleep(0.01)
        
        except Exception as e:
            print(f"Stream error for {room_id}: {e}")
            break


@app.get("/api/stream/{room_id}")
def stream_room(room_id: str):
    """
    Stream MJPEG video from CCTV with YOLO detection.
    
    Parameters:
        room_id: ID of the room to stream
    
    Returns:
        MJPEG video stream
    """
    # Check if room exists
    if room_id not in rooms_state:
        raise HTTPException(status_code=404, detail="Room not found")
    
    # Check if CCTV is connected
    processor = get_stream_processor(room_id)
    if processor is None:
        raise HTTPException(status_code=503, detail="CCTV not connected")
    
    return StreamingResponse(
        generate_annotated_stream(room_id),
        media_type="multipart/x-mixed-replace; boundary=frame"
    )


# =============================================================================
# WEBCAM TEST MODE - Demo Endpoints
# =============================================================================
# These endpoints allow testing the system with a local webcam
# instead of CCTV cameras. Great for demos and development.
# =============================================================================

@app.post("/api/webcam/test/start")
def start_webcam_test():
    """
    Start webcam test mode with live stream and energy control.
    
    Creates a "Webcam" room and starts streaming from the default camera.
    
    Returns:
        Status message
    """
    global webcam_test_process
    
    try:
        # Use "Webcam" as the room for test mode
        room_id = "Webcam"
        
        # Initialize webcam room in state if not exists
        if room_id not in rooms_state:
            from .room_config import get_room_config
            rooms_state[room_id] = get_room_config()
        
        # Start the streaming processor
        print("Starting webcam stream processor...")
        start_webcam_stream(camera_index=0, room_id=room_id)
        processor = get_webcam_processor()
        
        # Define callback for occupancy changes
        def occupancy_callback(room_id, occupied, light, ac):
            if room_id in rooms_state:
                rooms_state[room_id]["occupied"] = occupied
                rooms_state[room_id]["light"] = light
                rooms_state[room_id]["ac"] = ac
        
        # Set callback
        processor.occupancy_callback = occupancy_callback
        
        # Mark as running
        webcam_test_process = processor
        print(f"Webcam streaming started with energy control. is_running={processor.is_running}")
        
        return {"status": "Webcam test started"}
        
    except Exception as e:
        print(f"Error starting webcam: {e}")
        return {"status": "error", "detail": str(e)}


@app.post("/api/webcam/test/stop")
def stop_webcam_test():
    """
    Stop webcam test mode.
    
    Returns:
        Status message
    """
    try:
        print("Stopping webcam stream...")
        stop_webcam_stream()
        
        global webcam_test_process
        webcam_test_process = None
        
        print("Webcam stream stopped")
        return {"status": "Webcam test stopped"}
        
    except Exception as e:
        print(f"Error stopping webcam: {e}")
        return {"status": "error", "detail": str(e)}


@app.get("/api/webcam/test/status")
def get_webcam_test_status():
    """
    Get current webcam test status.
    
    Returns:
        Running status and person count
    """
    try:
        processor = get_webcam_processor()
        
        if processor and processor.is_running:
            return {
                "status": "running",
                "person_count": processor.get_person_count(),
                "occupied": processor.get_person_count() > 0
            }
        
        return {"status": "stopped"}
        
    except Exception as e:
        print(f"Error getting status: {e}")
        return {"status": "stopped"}


def generate_webcam_stream():
    """
    Generator that yields MJPEG frames from webcam.
    
    Yields:
        MJPEG frame bytes
    """
    import time
    
    processor = get_webcam_processor()
    
    while True:
        frame_bytes = processor.get_annotated_frame()
        
        if frame_bytes is None:
            time.sleep(0.01)
            continue
        
        yield (b'--frame\r\n'
               b'Content-Type: image/jpeg\r\n'
               b'Content-Length: ' + str(len(frame_bytes)).encode() + b'\r\n'
               b'\r\n' + frame_bytes + b'\r\n')


@app.get("/api/webcam/stream")
def webcam_stream():
    """
    Stream live webcam video with detection overlays as MJPEG.
    
    Returns:
        MJPEG video stream
    """
    processor = get_webcam_processor()
    
    # Start streaming if not already running
    if not processor.is_running:
        processor.start_streaming()
    
    return StreamingResponse(
        generate_webcam_stream(),
        media_type="multipart/x-mixed-replace; boundary=frame"
    )

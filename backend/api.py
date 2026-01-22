# API Server - Main entry point for the Energy Management System
# This file defines all REST API endpoints that the frontend uses to:
#   - Get room status (occupancy, lights, AC state)
#   - Start/stop AI detection processes
#   - Connect/disconnect CCTV cameras
#   - Stream video with detection overlays
#   - Manage webcam demo mode
# All endpoints return JSON responses and handle errors appropriately.

import cv2
import numpy as np
from typing import Dict, Any, List
from contextlib import asynccontextmanager

import os
import shutil
from pathlib import Path
from tempfile import NamedTemporaryFile

from fastapi import FastAPI, HTTPException, UploadFile, File, Form
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

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

# Lifespan context manager for startup/shutdown events
@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    print("Energy AI Management Backend starting up...")
    yield
    # Shutdown
    print("Shutting down server and stopping processes...")
    global webcam_test_process
    
    cleanup_all_processors()
    
    if webcam_test_process is not None:
        try:
            webcam_test_process.terminate()
            webcam_test_process.wait(timeout=3)
        except Exception as e:
            print(f"Error stopping webcam: {e}")
        webcam_test_process = None
    
    for room_id in rooms_state:
        stop_ai_process(rooms_state, room_id)
    
    print("All processes stopped")

app = FastAPI(
    title="Energy AI Management Backend",
    version="1.0.0",
    description="Energy management with AI person detection",
    lifespan=lifespan
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

rooms_state: Dict[str, Dict[str, Any]] = get_initial_rooms_state()
webcam_test_process = None

# Global storage for uploaded video streams
_uploaded_videos: Dict[str, str] = {}  # session_id -> file_path
_video_occupancy_state: Dict[str, Dict[str, Any]] = {}  # session_id -> {occupied, person_count, light, ac, room_id}


class RoomState(BaseModel):
    id: str
    occupied: bool
    light: bool
    ac: bool
    rtsp_url: str
    is_running: bool


class AllRoomsResponse(BaseModel):
    rooms: List[RoomState]


class OccupancyUpdate(BaseModel):
    room_id: str
    occupied: bool


class RtspUpdateRequest(BaseModel):
    room_id: str
    rtsp_url: str


class CctvConfigRequest(BaseModel):
    room_id: str
    cctv_ip: str
    cctv_username: str
    cctv_password: str
    cctv_channel: str = "0"


class AiModeRequest(BaseModel):
    room_id: str
    ai_mode: str


def _save_upload_to_temp(upload_file: UploadFile) -> str:
    suffix = Path(upload_file.filename or "upload").suffix or ".mp4"
    tmp_file = NamedTemporaryFile(delete=False, suffix=suffix)
    try:
        shutil.copyfileobj(upload_file.file, tmp_file)
    finally:
        tmp_file.close()
    return tmp_file.name


def _analyze_video_file(video_path: str, room_id: str, frame_skip: int = 5) -> dict:
    if frame_skip < 1:
        raise HTTPException(status_code=400, detail="frame_skip must be >= 1")

    cap = cv2.VideoCapture(video_path)
    if not cap.isOpened():
        raise HTTPException(status_code=400, detail="Could not read uploaded video")

    fps = cap.get(cv2.CAP_PROP_FPS) or 30.0
    total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT)) or 0
    duration_seconds = total_frames / fps if fps else 0.0

    sim_state = {room_id: {"occupied": False, "light": False, "ac": False}}
    events: List[dict] = []
    occupied_frames = 0
    frames_analyzed = 0
    previous_occupied = None
    frame_index = 0

    try:
        while True:
            ret, frame = cap.read()
            if not ret or frame is None:
                break

            if frame_skip > 1 and frame_index % frame_skip != 0:
                frame_index += 1
                continue

            people_count = count_people(frame)
            occupied = people_count > 0

            if occupied:
                occupied_frames += 1

            sim_state[room_id]["occupied"] = occupied
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


def _generate_video_stream_with_detection(video_path: str, session_id: str):
    """Stream video frames with YOLO person detection overlays."""
    cap = cv2.VideoCapture(video_path)
    
    if not cap.isOpened():
        return
    
    # Initialize occupancy state
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
            cap.set(cv2.CAP_PROP_POS_FRAMES, 0)  # Loop back to start
            continue
        
        # Run person detection
        people_count = count_people(frame)
        occupied = people_count > 0
        
        # Update occupancy state
        _video_occupancy_state[session_id]["person_count"] = people_count
        _video_occupancy_state[session_id]["occupied"] = occupied
        
        # Simulate energy control
        if occupied != _video_occupancy_state[session_id].get("occupied_prev"):
            sim_state = {room_id: {"occupied": occupied, "light": False, "ac": False}}
            auto_control(sim_state, room_id)
            _video_occupancy_state[session_id]["light"] = sim_state[room_id]["light"]
            _video_occupancy_state[session_id]["ac"] = sim_state[room_id]["ac"]
            _video_occupancy_state[session_id]["occupied_prev"] = occupied
        
        # Draw detection boxes
        from ultralytics import YOLO
        from pathlib import Path as PathlibPath
        MODEL_PATH = PathlibPath(__file__).resolve().parent.parent / "yolov8n.pt"
        model = YOLO(MODEL_PATH)
        results = model(frame, conf=0.4, classes=[0], verbose=False)
        
        # Annotate frame
        if results[0] and results[0].boxes:
            for box in results[0].boxes:
                x1, y1, x2, y2 = map(int, box.xyxy[0])
                confidence = box.conf[0]
                cv2.rectangle(frame, (x1, y1), (x2, y2), (0, 255, 0), 2)
                label = f"Person {confidence:.2f}"
                cv2.putText(frame, label, (x1, y1 - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 2)
        
        # Draw overlay with status
        cv2.rectangle(frame, (0, 0), (400, 90), (0, 0, 0), -1)
        cv2.putText(frame, f"People: {people_count}", (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 255), 2)
        status_color = (0, 0, 255) if people_count > 0 else (0, 255, 0)
        occupancy_text = "OCCUPIED" if people_count > 0 else "EMPTY"
        cv2.putText(frame, occupancy_text, (10, 60), cv2.FONT_HERSHEY_SIMPLEX, 0.8, status_color, 2)
        
        # Draw power status
        light_color = (0, 255, 0) if _video_occupancy_state[session_id]["light"] else (0, 0, 255)
        light_text = "💡 ON" if _video_occupancy_state[session_id]["light"] else "💡 OFF"
        cv2.putText(frame, light_text, (10, 90), cv2.FONT_HERSHEY_SIMPLEX, 0.7, light_color, 2)
        
        # Encode frame
        ret, buffer = cv2.imencode('.jpg', frame)
        if ret:
            frame_bytes = buffer.tobytes()
            yield (b'--frame\r\n'
                   b'Content-Type: image/jpeg\r\n\r\n' + frame_bytes + b'\r\n')
        
        frame_count += 1
    
    cap.release()


class VideoAnalysisEvent(BaseModel):
    frame_index: int
    time_seconds: float
    occupied: bool
    light: bool
    ac: bool
    person_count: int


class VideoAnalysisResponse(BaseModel):
    room_id: str
    frames_total: int
    frames_analyzed: int
    fps: float
    duration_seconds: float
    occupied_frames: int
    occupancy_ratio: float
    events: List[VideoAnalysisEvent]


# Shutdown handler now in lifespan context manager above


@app.get("/")
def root():
    return {"message": "Energy Management Backend Running", "version": "1.0.0"}


@app.get("/api/rooms", response_model=AllRoomsResponse)
def get_rooms_status():
    response_rooms = []
    for room_id, state in rooms_state.items():
        process = state.get("process")
        response_rooms.append(
            RoomState(
                id=room_id,
                occupied=state["occupied"],
                light=state["light"],
                ac=state["ac"],
                rtsp_url=state["rtsp_url"],
                is_running=process.is_alive() if process else False
            )
        )
    return {"rooms": response_rooms}


@app.post("/api/occupancy")
def update_occupancy(data: OccupancyUpdate):
    if data.room_id not in rooms_state:
        raise HTTPException(status_code=404, detail="Room not found")
    
    rooms_state[data.room_id]["occupied"] = data.occupied
    auto_control(rooms_state, data.room_id)
    
    return {
        "status": "updated",
        "room_id": data.room_id,
        "occupied": data.occupied
    }


@app.post("/api/video/upload", response_model=VideoAnalysisResponse)
async def upload_video(
    file: UploadFile = File(...),
    room_id: str = Form("UploadedVideo"),
    frame_skip: int = Form(5)
):
    temp_path = None
    try:
        temp_path = _save_upload_to_temp(file)
        # Store the path for streaming
        import uuid
        session_id = str(uuid.uuid4())
        _uploaded_videos[session_id] = temp_path
        
        result = _analyze_video_file(temp_path, room_id, frame_skip)
        result["session_id"] = session_id
        return result
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error analyzing video: {str(e)}")


@app.get("/api/video/stream/{session_id}")
def stream_uploaded_video(session_id: str):
    """Stream uploaded video with YOLO detection overlays as MJPEG."""
    if session_id not in _uploaded_videos:
        raise HTTPException(status_code=404, detail="Video session not found")
    
    video_path = _uploaded_videos[session_id]
    if not os.path.exists(video_path):
        raise HTTPException(status_code=404, detail="Video file not found")
    
    return StreamingResponse(
        _generate_video_stream_with_detection(video_path, session_id),
        media_type="multipart/x-mixed-replace; boundary=frame"
    )


@app.get("/api/video/status/{session_id}")
def get_video_stream_status(session_id: str):
    """Get current occupancy status for a video stream."""
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
    """Clean up uploaded video file after done."""
    if session_id in _uploaded_videos:
        video_path = _uploaded_videos[session_id]
        try:
            if os.path.exists(video_path):
                os.remove(video_path)
        except Exception as e:
            print(f"Error cleaning up video: {e}")
        del _uploaded_videos[session_id]
    return {"status": "cleaned up"}


@app.post("/api/ai/{room_id}/start")
def start_room_ai(room_id: str):
    if room_id not in rooms_state:
        raise HTTPException(status_code=404, detail="Room not found")
    
    start_ai_process(rooms_state, room_id, camera_index=0)
    return {"status": f"AI started for {room_id}"}


@app.post("/api/ai/{room_id}/stop")
def stop_room_ai(room_id: str):
    if room_id not in rooms_state:
        raise HTTPException(status_code=404, detail="Room not found")
    
    stop_ai_process(rooms_state, room_id)
    return {"status": f"AI stopped for {room_id}"}


@app.post("/api/cctv/connect")
def connect_cctv(data: CctvConfigRequest):
    if data.room_id not in rooms_state:
        raise HTTPException(status_code=404, detail="Room not found")
    
    try:
        rtsp_url = (
            f"rtsp://{data.cctv_username}:{data.cctv_password}@"
            f"{data.cctv_ip}:554/Streaming/Channels/{data.cctv_channel}"
        )
        
        rooms_state[data.room_id]["rtsp_url"] = rtsp_url
        processor = create_stream_processor(rtsp_url, data.room_id)
        
        if not processor.connect():
            raise HTTPException(status_code=502, detail="Could not connect to camera")
        
        def occupancy_callback(room_id: str, is_occupied: bool):
            if room_id in rooms_state:
                rooms_state[room_id]["occupied"] = is_occupied
                auto_control(rooms_state, room_id)
        
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
    room_id = data.get("room_id")
    if not room_id or room_id not in rooms_state:
        raise HTTPException(status_code=404, detail="Room not found")
    
    try:
        cleanup_stream_processor(room_id)
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
    if room_id not in rooms_state:
        raise HTTPException(status_code=404, detail="Room not found")
    
    processor = get_stream_processor(room_id)
    
    if processor is None:
        return {
            "room_id": room_id,
            "connected": False,
            "person_count": 0,
            "occupied": False
        }
    
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


def generate_annotated_stream(room_id: str):
    processor = get_stream_processor(room_id)
    
    if processor is None:
        placeholder = cv2.zeros((480, 640, 3), dtype=np.uint8)
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
    """Stream MJPEG video from CCTV with YOLO detection."""
    if room_id not in rooms_state:
        raise HTTPException(status_code=404, detail="Room not found")
    
    processor = get_stream_processor(room_id)
    if processor is None:
        raise HTTPException(status_code=503, detail="CCTV not connected")
    
    return StreamingResponse(
        generate_annotated_stream(room_id),
        media_type="multipart/x-mixed-replace; boundary=frame"
    )


# ============================================================================
# WEBCAM TEST MODE - Demo endpoints
# ============================================================================

@app.post("/api/webcam/test/start")
def start_webcam_test():
    """Start webcam test mode with live stream and energy control."""
    global webcam_test_process
    
    try:
        # Use "Webcam" as the room for webcam test mode
        room_id = "Webcam"
        
        # Initialize webcam room in state if not exists
        if room_id not in rooms_state:
            from .room_config import get_room_config
            rooms_state[room_id] = get_room_config()
        
        # Start the streaming processor
        print("Starting webcam stream processor...")
        start_webcam_stream(camera_index=0, room_id=room_id)
        processor = get_webcam_processor()
        
        # Set up callback to update room state when occupancy changes
        def occupancy_callback(room_id: str, occupied: bool, light: bool, ac: bool):
            if room_id in rooms_state:
                rooms_state[room_id]["occupied"] = occupied
                rooms_state[room_id]["light"] = light
                rooms_state[room_id]["ac"] = ac
        
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
    """Stop webcam test mode."""
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
    """Get current webcam test status."""
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
    """Generate MJPEG stream frames from webcam."""
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
    """Stream live webcam video with detection overlays as MJPEG."""
    processor = get_webcam_processor()
    
    # Start streaming if not already running
    if not processor.is_running:
        processor.start_streaming()
    
    return StreamingResponse(
        generate_webcam_stream(),
        media_type="multipart/x-mixed-replace; boundary=frame"
    )

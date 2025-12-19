# API Server - Main entry point for the Energy Management System
# This file defines all REST API endpoints that the frontend uses to:
#   - Get room status (occupancy, lights, AC state)
#   - Start/stop AI detection processes
#   - Connect/disconnect CCTV cameras
#   - Stream video with detection overlays
#   - Manage webcam demo mode
# All endpoints return JSON responses and handle errors appropriately.

import cv2
from typing import Dict, Any, List

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from .room_config import get_initial_rooms_state
from .energy_logic import auto_control
from .multi_room_energy import start_ai_process, stop_ai_process
from .cctv_stream import (
    create_stream_processor,
    get_stream_processor,
    cleanup_stream_processor,
    cleanup_all_processors
)

app = FastAPI(
    title="Energy AI Management Backend",
    version="1.0.0",
    description="Energy management with AI person detection"
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


@app.on_event("shutdown")
def shutdown_event():
    global webcam_test_process
    
    print("Shutting down server and stopping processes...")
    
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
        placeholder = cv2.putText(
            cv2.zeros((480, 640, 3), cv2.CV_8UC3),
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
    """Start webcam test mode with visual feedback."""
    global webcam_test_process
    
    if webcam_test_process is not None and webcam_test_process.is_alive():
        return {"status": "Webcam test already running"}
    
    from threading import Event
    stop_event = Event()
    
    try:
        from .webcam_energy import run_webcam_energy_ai
        webcam_test_process = start_ai_process(rooms_state, "Classroom", camera_index=0)
        return {"status": "Webcam test started"}
    except Exception as e:
        return {"status": "error", "detail": str(e)}


@app.post("/api/webcam/test/stop")
def stop_webcam_test():
    """Stop webcam test mode."""
    global webcam_test_process
    
    if webcam_test_process is None or not webcam_test_process.is_alive():
        return {"status": "Webcam test not running"}
    
    try:
        stop_ai_process(rooms_state, "Classroom")
        webcam_test_process = None
        return {"status": "Webcam test stopped"}
    except Exception as e:
        return {"status": "error", "detail": str(e)}


@app.get("/api/webcam/test/status")
def get_webcam_test_status():
    """Get current webcam test status."""
    global webcam_test_process
    
    if webcam_test_process is None or not webcam_test_process.is_alive():
        return {"status": "stopped"}
    
    classroom_state = rooms_state.get("Classroom", {})
    return {
        "status": "running",
        "occupied": classroom_state.get("occupied", False),
        "light": classroom_state.get("light", False)
    }

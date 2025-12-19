# CCTV Stream Processing Module
# This file handles real-time RTSP camera stream processing.
# Main features:
#   - RTSPStreamProcessor class manages a single camera connection
#   - Runs YOLO detection on each frame in a background thread
#   - Draws bounding boxes around detected persons
#   - Provides MJPEG-encoded frames for web streaming
#   - Tracks occupancy changes and triggers energy control
# Used for production CCTV deployments with professional security cameras.

import cv2
import numpy as np
import threading
from typing import Optional, Callable, Dict
from ultralytics import YOLO
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
MODEL_PATH = BASE_DIR / "yolov8n.pt"

class RTSPStreamProcessor:
    """
    Processes an RTSP stream to detect persons and determine room occupancy.
    """
    def __init__(self, rtsp_url: str, room_id: str):
        self.rtsp_url = rtsp_url
        self.room_id = room_id
        self.model = YOLO(MODEL_PATH)
        self.cap = None
        self.current_frame = None
        self.person_count = 0
        self.is_running = False
        self.processing_thread = None
        self.lock = threading.Lock()
        self.occupancy_callback = None
        self.previous_occupancy = None
        
    def connect(self) -> bool:
        """
        Connect to the RTSP stream.
        
        Returns:
            True if connection is successful, False otherwise.
        """
        try:
            self.cap = cv2.VideoCapture(self.rtsp_url)
            self.cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)
            
            ret, frame = self.cap.read()
            if not ret or frame is None:
                self.cap.release()
                self.cap = None
                print(f" Failed to connect to stream: {self.room_id}")
                return False
            
            print(f"✅ Connected to stream: {self.room_id}")
            return True
        except Exception as e:
            print(f" Error connecting to stream: {e}")
            return False
    
    def start_processing(self, occupancy_callback: Optional[Callable] = None):
        """
        Start processing the stream in a separate thread.
        
        Args:
            occupancy_callback: Optional callback function to be called when occupancy changes.
        """
        if self.is_running:
            print(f"Stream already processing for {self.room_id}")
            return
        
        if self.cap is None:
            if not self.connect():
                return

        self.occupancy_callback = occupancy_callback
        self.is_running = True
        self.processing_thread = threading.Thread(
            target=self._process_stream,
            daemon=True
        )
        self.processing_thread.start()
        print(f"🚀 Started stream processing for {self.room_id}")
    
    def stop_processing(self):
        """Stop processing the stream."""
        self.is_running = False
        
        if self.processing_thread:
            self.processing_thread.join(timeout=5)
        
        if self.cap:
            self.cap.release()
            self.cap = None
        
        self.current_frame = None
        print(f"Stopped stream processing for {self.room_id}")
    
    def _process_stream(self):
        """
        Main loop for processing stream frames.
        """
        while self.is_running:
            try:
                ret, frame = self.cap.read()
                
                if not ret or frame is None:
                    print(f"⚠️ Lost frame from {self.room_id}, attempting reconnect...")
                    if not self.connect():
                        self.is_running = False
                        break
                    continue
                
                results = self.model(frame, conf=0.5, classes=[0], verbose=False)
                
                person_count = len(results[0].boxes) if results[0] else 0
                
                self._update_occupancy(person_count)
                
                with self.lock:
                    self.current_frame = self._annotate_frame(frame, results, person_count)
            
            except Exception as e:
                print(f" Error processing frame for {self.room_id}: {e}")
                continue

    def _update_occupancy(self, person_count: int):
        """
        Update occupancy status and trigger callback if it changed.
        """
        with self.lock:
            self.person_count = person_count
            is_occupied = person_count > 0
            
            if is_occupied != self.previous_occupancy:
                self.previous_occupancy = is_occupied
                if self.occupancy_callback:
                    self.occupancy_callback(self.room_id, is_occupied)
                    print(f"📊 {self.room_id}: {'Occupied' if is_occupied else 'Empty'} "
                          f"({self.person_count} people)")

    def _annotate_frame(self, frame: np.ndarray, results, person_count: int) -> np.ndarray:
        """
        Annotate frame with YOLO detection boxes and person count overlay.
        
        Args:
            frame: Original video frame
            results: YOLO detection results
            person_count: Number of detected persons
        
        Returns:
            Annotated frame with visualization
        """
        annotated_frame = frame.copy()
        
        self._draw_bounding_boxes(annotated_frame, results)
        self._draw_overlay(annotated_frame, person_count)
        
        return annotated_frame

    def _draw_bounding_boxes(self, frame: np.ndarray, results):
        """Draw bounding boxes for detected persons."""
        if results[0] and results[0].boxes:
            for box in results[0].boxes:
                x1, y1, x2, y2 = map(int, box.xyxy[0])
                confidence = box.conf[0]
                
                # Draw box
                cv2.rectangle(frame, (x1, y1), (x2, y2), (0, 255, 0), 2)
                
                # Draw confidence label
                label = f"Person {confidence:.2f}"
                label_size, _ = cv2.getTextSize(label, cv2.FONT_HERSHEY_SIMPLEX, 0.5, 1)
                cv2.rectangle(
                    frame,
                    (x1, y1 - label_size[1] - 4),
                    (x1 + label_size[0], y1),
                    (0, 255, 0),
                    -1
                )
                cv2.putText(
                    frame,
                    label,
                    (x1, y1 - 2),
                    cv2.FONT_HERSHEY_SIMPLEX,
                    0.5,
                    (0, 0, 0),
                    1
                )

    def _draw_overlay(self, frame: np.ndarray, person_count: int):
        """Draw occupancy status and person count overlay."""
        occupancy_status = "OCCUPIED" if person_count > 0 else "EMPTY"
        count_text = f"{self.room_id} | People: {person_count}"
        
        # Background for text
        cv2.rectangle(frame, (0, 0), (400, 60), (0, 0, 0), -1)
        
        # Person count
        cv2.putText(
            frame,
            count_text,
            (10, 30),
            cv2.FONT_HERSHEY_SIMPLEX,
            1,
            (0, 255, 255),
            2
        )
        
        # Occupancy status
        status_color = (0, 0, 255) if person_count > 0 else (0, 255, 0)  # Red for occupied, Green for empty
        cv2.putText(
            frame,
            occupancy_status,
            (10, 55),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.7,
            status_color,
            2
        )

    def get_annotated_frame(self) -> Optional[bytes]:
        """
        Get the latest annotated frame as JPEG bytes for streaming.
        
        Returns:
            JPEG-encoded frame bytes, or None if no frame available
        """
        with self.lock:
            if self.current_frame is None:
                return None
            
            ret, buffer = cv2.imencode('.jpg', self.current_frame)
            if ret:
                return buffer.tobytes()
        return None
    
    def get_person_count(self) -> int:
        """Get current person count from latest frame."""
        with self.lock:
            return self.person_count


# Global stream processors dictionary
_stream_processors: Dict[str, RTSPStreamProcessor] = {}
_processors_lock = threading.Lock()


def create_stream_processor(rtsp_url: str, room_id: str) -> RTSPStreamProcessor:
    """
    Create or retrieve a stream processor for a room.
    
    Args:
        rtsp_url: RTSP camera URL
        room_id: Room identifier
    
    Returns:
        RTSPStreamProcessor instance
    """
    with _processors_lock:
        if room_id in _stream_processors:
            _stream_processors[room_id].stop_processing()
        
        processor = RTSPStreamProcessor(rtsp_url, room_id)
        _stream_processors[room_id] = processor
        return processor


def get_stream_processor(room_id: str) -> Optional[RTSPStreamProcessor]:
    """Get existing stream processor for a room."""
    with _processors_lock:
        return _stream_processors.get(room_id)


def cleanup_stream_processor(room_id: str):
    """Stop and remove stream processor for a room."""
    with _processors_lock:
        if room_id in _stream_processors:
            _stream_processors[room_id].stop_processing()
            del _stream_processors[room_id]


def cleanup_all_processors():
    """Stop and remove all stream processors."""
    with _processors_lock:
        for processor in list(_stream_processors.values()):
            processor.stop_processing()
        _stream_processors.clear()

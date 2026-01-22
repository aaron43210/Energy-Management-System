# Webcam Stream Processor
# Handles real-time webcam stream processing with YOLO detection
# Provides MJPEG-encoded frames for web streaming to browser

import cv2
import numpy as np
import threading
from typing import Optional
from ultralytics import YOLO
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
MODEL_PATH = BASE_DIR / "yolov8n.pt"

class WebcamStreamProcessor:
    """
    Processes webcam stream to detect persons and provide live video feed
    """
    def __init__(self, camera_index: int = 0, room_id: str = "Webcam"):
        self.camera_index = camera_index
        self.room_id = room_id  # Track which room this webcam is for
        self.model = YOLO(MODEL_PATH)
        self.cap = None
        self.current_frame = None
        self.person_count = 0
        self.is_running = False
        self.processing_thread = None
        self.lock = threading.Lock()
        
        # Energy control state
        self.light_on = False
        self.ac_on = False
        self.occupied = False
        self.occupancy_callback = None  # Callback when occupancy changes
        
        # Performance optimization settings
        self.frame_skip = 3  # Process every Nth frame for YOLO (higher = faster, less accurate)
        self.frame_count = 0
        self.jpeg_quality = 60  # JPEG quality (lower = faster)
        self.target_fps = 25  # Target FPS for smoother streaming
        self.resize_factor = 0.6  # Resize frames to 60% for faster processing
        
    def connect(self) -> bool:
        """Connect to webcam"""
        try:
            self.cap = cv2.VideoCapture(self.camera_index)
            self.cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)
            # Optimize camera settings for performance
            self.cap.set(cv2.CAP_PROP_FPS, 30)  # Request 30 FPS from camera
            self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)  # Lower resolution for faster processing
            self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
            
            ret, frame = self.cap.read()
            if not ret or frame is None:
                self.cap.release()
                self.cap = None
                print(f"❌ Failed to connect to camera index {self.camera_index}")
                return False
            
            print(f"✅ Connected to webcam at index {self.camera_index}")
            print(f"   Performance mode: process every {self.frame_skip} frames, JPEG quality {self.jpeg_quality}%")
            return True
        except Exception as e:
            print(f"❌ Error connecting to webcam: {e}")
            return False
    
    def start_streaming(self):
        """Start streaming in a separate thread"""
        if self.is_running:
            print("Webcam stream already running")
            return
        
        if self.cap is None:
            if not self.connect():
                return

        self.is_running = True
        self.processing_thread = threading.Thread(
            target=self._process_stream,
            daemon=True
        )
        self.processing_thread.start()
        print("🚀 Started webcam stream processing")
    
    def stop_streaming(self):
        """Stop streaming"""
        self.is_running = False
        
        if self.processing_thread:
            self.processing_thread.join(timeout=5)
        
        if self.cap:
            self.cap.release()
            self.cap = None
        
        self.current_frame = None
        print("Stopped webcam stream")
    
    def _process_stream(self):
        """Main loop for processing stream frames"""
        import time
        last_frame_time = time.time()
        target_frame_time = 1.0 / self.target_fps
        
        while self.is_running:
            try:
                # FPS limiting
                current_time = time.time()
                elapsed = current_time - last_frame_time
                if elapsed < target_frame_time:
                    time.sleep(target_frame_time - elapsed)
                last_frame_time = time.time()
                
                ret, frame = self.cap.read()
                
                if not ret or frame is None:
                    print("⚠️ Lost frame from webcam, attempting reconnect...")
                    if not self.connect():
                        self.is_running = False
                        break
                    continue
                
                self.frame_count += 1
                
                # Only run YOLO detection on every Nth frame for better performance
                if self.frame_count % self.frame_skip == 0:
                    # Optionally resize frame for faster YOLO processing
                    if self.resize_factor < 1.0:
                        h, w = frame.shape[:2]
                        new_w, new_h = int(w * self.resize_factor), int(h * self.resize_factor)
                        detection_frame = cv2.resize(frame, (new_w, new_h))
                    else:
                        detection_frame = frame
                    
                    # Run YOLO detection on (possibly resized) frame
                    results = self.model(detection_frame, conf=0.4, classes=[0], verbose=False)
                    person_count = len(results[0].boxes) if results[0] else 0
                    
                    # Determine occupancy and apply energy control
                    is_occupied = person_count > 0
                    
                    with self.lock:
                        self.person_count = person_count
                        
                        # Check if occupancy changed
                        if is_occupied != self.occupied:
                            self.occupied = is_occupied
                            
                            # Apply energy control logic
                            if is_occupied:
                                self.light_on = True
                                self.ac_on = True
                                print("=" * 60)
                                print(f"🟢 {self.room_id}: PERSON DETECTED")
                                print(f"⚡ POWER ON - LIGHT: ON | AC: ON")
                                print("=" * 60)
                            else:
                                self.light_on = False
                                self.ac_on = False
                                print("=" * 60)
                                print(f"🔴 {self.room_id}: ROOM EMPTY")
                                print(f"⚡ POWER OFF - LIGHT: OFF | AC: OFF")
                                print("=" * 60)
                            
                            # Call occupancy callback if set
                            if self.occupancy_callback:
                                self.occupancy_callback(self.room_id, is_occupied, self.light_on, self.ac_on)
                        
                        self.current_frame = self._annotate_frame(frame, results, person_count, detection_frame)
                else:
                    # For skipped frames, just update the frame without re-running detection
                    with self.lock:
                        if self.current_frame is not None:
                            # Keep using previous detection results
                            pass
            
            except Exception as e:
                print(f"❌ Error processing webcam frame: {e}")
                continue

    def _annotate_frame(self, frame: np.ndarray, results, person_count: int, detection_frame=None) -> np.ndarray:
        """Annotate frame with YOLO detection boxes and person count"""
        annotated_frame = frame.copy()
        
        # Calculate scale factor if frame was resized for detection
        scale_factor = 1.0
        if detection_frame is not None and self.resize_factor < 1.0:
            scale_factor = 1.0 / self.resize_factor
        
        # Draw bounding boxes (scaled back to original frame size if needed)
        if results[0] and results[0].boxes:
            for box in results[0].boxes:
                x1, y1, x2, y2 = map(int, box.xyxy[0])
                
                # Scale coordinates back to original frame size
                x1, y1 = int(x1 * scale_factor), int(y1 * scale_factor)
                x2, y2 = int(x2 * scale_factor), int(y2 * scale_factor)
                
                confidence = box.conf[0]
                
                cv2.rectangle(annotated_frame, (x1, y1), (x2, y2), (0, 255, 0), 2)
                
                label = f"Person {confidence:.2f}"
                label_size, _ = cv2.getTextSize(label, cv2.FONT_HERSHEY_SIMPLEX, 0.5, 1)
                cv2.rectangle(
                    annotated_frame,
                    (x1, y1 - label_size[1] - 4),
                    (x1 + label_size[0], y1),
                    (0, 255, 0),
                    -1
                )
                cv2.putText(
                    annotated_frame,
                    label,
                    (x1, y1 - 2),
                    cv2.FONT_HERSHEY_SIMPLEX,
                    0.5,
                    (0, 0, 0),
                    1
                )
        
        # Draw overlay with person count and energy status
        occupancy_status = "OCCUPIED" if person_count > 0 else "EMPTY"
        count_text = f"People: {person_count}"
        
        # Black background for overlay
        overlay_height = 120
        cv2.rectangle(annotated_frame, (0, 0), (400, overlay_height), (0, 0, 0), -1)
        
        # Person count
        cv2.putText(
            annotated_frame,
            count_text,
            (10, 30),
            cv2.FONT_HERSHEY_SIMPLEX,
            1,
            (0, 255, 255),
            2
        )
        
        # Occupancy status
        status_color = (0, 0, 255) if person_count > 0 else (0, 255, 0)
        cv2.putText(
            annotated_frame,
            occupancy_status,
            (10, 60),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.8,
            status_color,
            2
        )
        
        # Light status (using instance variable)
        light_color = (0, 255, 0) if self.light_on else (0, 0, 255)
        light_text = "💡 LIGHT: ON" if self.light_on else "💡 LIGHT: OFF"
        cv2.putText(
            annotated_frame,
            light_text,
            (10, 90),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.7,
            light_color,
            2
        )
        
        # AC status (using instance variable)
        ac_color = (0, 255, 0) if self.ac_on else (0, 0, 255)
        ac_text = "❄️ AC: ON" if self.ac_on else "❄️ AC: OFF"
        cv2.putText(
            annotated_frame,
            ac_text,
            (220, 90),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.7,
            ac_color,
            2
        )
        
        return annotated_frame

    def get_annotated_frame(self) -> Optional[bytes]:
        """Get latest frame as JPEG bytes for streaming"""
        with self.lock:
            if self.current_frame is None:
                return None
            
            # Use lower JPEG quality for faster encoding and smaller file size
            encode_params = [cv2.IMWRITE_JPEG_QUALITY, self.jpeg_quality]
            ret, buffer = cv2.imencode('.jpg', self.current_frame, encode_params)
            if ret:
                return buffer.tobytes()
        return None
    
    def get_person_count(self) -> int:
        """Get current person count"""
        with self.lock:
            return self.person_count


# Global webcam processor
_webcam_processor: Optional[WebcamStreamProcessor] = None
_processor_lock = threading.Lock()


def get_webcam_processor(camera_index: int = 0, room_id: str = "Webcam") -> WebcamStreamProcessor:
    """Get or create webcam processor"""
    global _webcam_processor
    with _processor_lock:
        if _webcam_processor is None:
            _webcam_processor = WebcamStreamProcessor(camera_index, room_id)
        return _webcam_processor


def start_webcam_stream(camera_index: int = 0, room_id: str = "Webcam"):
    """Start webcam streaming"""
    processor = get_webcam_processor(camera_index, room_id)
    processor.start_streaming()


def stop_webcam_stream():
    """Stop webcam streaming"""
    global _webcam_processor
    with _processor_lock:
        if _webcam_processor:
            _webcam_processor.stop_streaming()
            _webcam_processor = None

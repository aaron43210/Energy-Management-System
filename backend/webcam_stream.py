# =============================================================================
# Webcam Stream Processor Module
# =============================================================================
# This file handles real-time webcam stream processing with YOLO detection.
#
# Main features:
#   - WebcamStreamProcessor class manages local webcam capture
#   - Runs YOLO person detection on frames
#   - Draws bounding boxes around detected persons
#   - Provides MJPEG-encoded frames for web streaming
#   - Tracks occupancy changes and controls energy (lights, AC)
#
# Performance optimizations:
#   - Frame skipping: Only run YOLO every Nth frame
#   - Frame resizing: Smaller frames for faster detection
#   - JPEG quality: Lower quality for faster encoding
#
# Used for demo/testing without professional CCTV hardware.
# =============================================================================

import cv2
import numpy as np
import threading
from ultralytics import YOLO
from pathlib import Path

# Path to YOLO model file
BASE_DIR = Path(__file__).resolve().parent.parent
MODEL_PATH = BASE_DIR / "yolov8n.pt"


class WebcamStreamProcessor:
    """
    Processes webcam stream to detect persons and provide live video feed.
    
    This class handles:
        - Connecting to local webcam
        - Running YOLO person detection
        - Drawing detection overlays on frames
        - Providing frames for web streaming
        - Tracking occupancy and controlling energy devices
    
    Attributes:
        camera_index: Index of the webcam to use (usually 0)
        room_id: Identifier for the room being monitored
        model: YOLO detection model
        cap: OpenCV video capture object
        current_frame: Latest processed frame with annotations
        person_count: Number of people detected
        is_running: Whether stream processing is active
        processing_thread: Background thread for processing
        lock: Thread lock for safe access to shared data
        light_on: Whether the light is on
        ac_on: Whether the AC is on
        occupied: Whether the room is occupied
        occupancy_callback: Function to call when occupancy changes
    """
    
    def __init__(self, camera_index=0, room_id="Webcam"):
        """
        Initialize the webcam stream processor.
        
        Parameters:
            camera_index: Index of the webcam to use (default 0)
            room_id: Identifier for the room being monitored
        """
        # Store configuration
        self.camera_index = camera_index
        self.room_id = room_id
        
        # Load YOLO model
        self.model = YOLO(MODEL_PATH)
        
        # Video capture (None until connected)
        self.cap = None
        
        # Current processed frame
        self.current_frame = None
        
        # Detection results
        self.person_count = 0
        
        # Processing state
        self.is_running = False
        self.processing_thread = None
        
        # Thread safety lock
        self.lock = threading.Lock()
        
        # Energy control state
        self.light_on = False
        self.ac_on = False
        self.occupied = False
        self.occupancy_callback = None
        
        # Performance optimization settings
        self.frame_skip = 3           # Process every Nth frame for YOLO
        self.frame_count = 0          # Counter for frame skipping
        self.jpeg_quality = 60        # JPEG quality (lower = faster)
        self.target_fps = 25          # Target FPS for streaming
        self.resize_factor = 0.6      # Resize frames to 60% for faster processing
        
    def connect(self):
        """
        Connect to webcam.
        
        Opens the video capture and configures camera settings.
        
        Returns:
            True if connection successful
            False if connection failed
        """
        try:
            # Open video capture
            self.cap = cv2.VideoCapture(self.camera_index)
            
            # Configure camera settings
            self.cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)  # Minimize latency
            self.cap.set(cv2.CAP_PROP_FPS, 30)         # Request 30 FPS
            self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)   # Lower resolution
            self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
            
            # Test the connection
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
        """
        Start streaming in a separate thread.
        
        Connects to camera if not already connected, then starts
        the processing thread.
        """
        # Check if already running
        if self.is_running:
            print("Webcam stream already running")
            return
        
        # Connect if not connected
        if self.cap is None:
            if not self.connect():
                return

        # Mark as running
        self.is_running = True
        
        # Create and start processing thread
        self.processing_thread = threading.Thread(
            target=self._process_stream,
            daemon=True
        )
        self.processing_thread.start()
        
        print("🚀 Started webcam stream processing")
    
    def stop_streaming(self):
        """
        Stop streaming.
        
        Signals the processing thread to stop, waits for it,
        and releases the camera.
        """
        # Signal thread to stop
        self.is_running = False
        
        # Wait for thread to finish
        if self.processing_thread:
            self.processing_thread.join(timeout=5)
        
        # Release camera
        if self.cap:
            self.cap.release()
            self.cap = None
        
        # Clear current frame
        self.current_frame = None
        
        print("Stopped webcam stream")
    
    def _process_stream(self):
        """
        Main loop for processing stream frames.
        
        This runs in a background thread and:
            1. Limits FPS for smooth streaming
            2. Reads frames from camera
            3. Runs YOLO detection (with frame skipping)
            4. Updates energy controls based on occupancy
            5. Annotates frames for streaming
        """
        import time
        
        # FPS limiting variables
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
                
                # Read frame from camera
                ret, frame = self.cap.read()
                
                # Handle connection loss
                if not ret or frame is None:
                    print("⚠️ Lost frame from webcam, attempting reconnect...")
                    if not self.connect():
                        self.is_running = False
                        break
                    continue
                
                # Increment frame counter
                self.frame_count += 1
                
                # Only run YOLO detection on every Nth frame (performance optimization)
                if self.frame_count % self.frame_skip == 0:
                    # Optionally resize frame for faster YOLO processing
                    if self.resize_factor < 1.0:
                        h, w = frame.shape[:2]
                        new_w = int(w * self.resize_factor)
                        new_h = int(h * self.resize_factor)
                        detection_frame = cv2.resize(frame, (new_w, new_h))
                    else:
                        detection_frame = frame
                    
                    # Run YOLO detection
                    results = self.model(detection_frame, conf=0.4, classes=[0], verbose=False)
                    
                    # Count detected persons
                    person_count = len(results[0].boxes) if results[0] else 0
                    
                    # Determine if room is occupied
                    is_occupied = person_count > 0
                    
                    with self.lock:
                        # Update person count
                        self.person_count = person_count
                        
                        # Check if occupancy changed
                        if is_occupied != self.occupied:
                            self.occupied = is_occupied
                            
                            # Apply energy control logic
                            if is_occupied:
                                # Room occupied - turn on lights and AC
                                self.light_on = True
                                self.ac_on = True
                                print("=" * 60)
                                print(f"🟢 {self.room_id}: PERSON DETECTED")
                                print(f"⚡ POWER ON - LIGHT: ON | AC: ON")
                                print("=" * 60)
                            else:
                                # Room empty - turn off lights and AC
                                self.light_on = False
                                self.ac_on = False
                                print("=" * 60)
                                print(f"🔴 {self.room_id}: ROOM EMPTY")
                                print(f"⚡ POWER OFF - LIGHT: OFF | AC: OFF")
                                print("=" * 60)
                            
                            # Call occupancy callback if set
                            if self.occupancy_callback:
                                self.occupancy_callback(
                                    self.room_id, 
                                    is_occupied, 
                                    self.light_on, 
                                    self.ac_on
                                )
                        
                        # Annotate frame with detection results
                        self.current_frame = self._annotate_frame(
                            frame, 
                            results, 
                            person_count, 
                            detection_frame
                        )
                else:
                    # For skipped frames, keep using previous detection results
                    with self.lock:
                        if self.current_frame is not None:
                            pass  # Keep previous frame
            
            except Exception as e:
                print(f"❌ Error processing webcam frame: {e}")
                continue

    def _annotate_frame(self, frame, results, person_count, detection_frame=None):
        """
        Annotate frame with YOLO detection boxes and person count.
        
        Parameters:
            frame: Original video frame (full size)
            results: YOLO detection results
            person_count: Number of detected persons
            detection_frame: Resized frame used for detection (for scaling boxes)
        
        Returns:
            Annotated frame with bounding boxes and status overlay
        """
        # Create copy to avoid modifying original
        annotated_frame = frame.copy()
        
        # Calculate scale factor if frame was resized for detection
        scale_factor = 1.0
        if detection_frame is not None and self.resize_factor < 1.0:
            scale_factor = 1.0 / self.resize_factor
        
        # Draw bounding boxes (scaled back to original frame size if needed)
        if results[0] and results[0].boxes:
            for box in results[0].boxes:
                # Get box coordinates
                x1, y1, x2, y2 = map(int, box.xyxy[0])
                
                # Scale coordinates back to original frame size
                x1 = int(x1 * scale_factor)
                y1 = int(y1 * scale_factor)
                x2 = int(x2 * scale_factor)
                y2 = int(y2 * scale_factor)
                
                confidence = box.conf[0]
                
                # Draw rectangle around person
                cv2.rectangle(annotated_frame, (x1, y1), (x2, y2), (0, 255, 0), 2)
                
                # Draw confidence label
                label = f"Person {confidence:.2f}"
                label_size, _ = cv2.getTextSize(label, cv2.FONT_HERSHEY_SIMPLEX, 0.5, 1)
                
                # Draw label background
                cv2.rectangle(
                    annotated_frame,
                    (x1, y1 - label_size[1] - 4),
                    (x1 + label_size[0], y1),
                    (0, 255, 0),
                    -1
                )
                
                # Draw label text
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
        
        # Draw person count
        cv2.putText(
            annotated_frame,
            count_text,
            (10, 30),
            cv2.FONT_HERSHEY_SIMPLEX,
            1,
            (0, 255, 255),
            2
        )
        
        # Draw occupancy status
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
        
        # Draw light status
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
        
        # Draw AC status
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

    def get_annotated_frame(self):
        """
        Get latest frame as JPEG bytes for streaming.
        
        Returns:
            JPEG-encoded frame bytes, or None if no frame available
        """
        with self.lock:
            # Check if we have a frame
            if self.current_frame is None:
                return None
            
            # Encode with lower quality for faster streaming
            encode_params = [cv2.IMWRITE_JPEG_QUALITY, self.jpeg_quality]
            ret, buffer = cv2.imencode('.jpg', self.current_frame, encode_params)
            
            if ret:
                return buffer.tobytes()
                
        return None
    
    def get_person_count(self):
        """
        Get current person count.
        
        Returns:
            Number of people detected
        """
        with self.lock:
            return self.person_count


# =============================================================================
# Global Webcam Processor Management
# =============================================================================
# These functions provide a singleton-style interface to the webcam processor.
# Only one webcam processor is active at a time.
# =============================================================================

# Global webcam processor instance
_webcam_processor = None

# Lock for thread-safe access
_processor_lock = threading.Lock()


def get_webcam_processor(camera_index=0, room_id="Webcam"):
    """
    Get or create webcam processor.
    
    Creates a new processor if one doesn't exist.
    
    Parameters:
        camera_index: Index of webcam to use
        room_id: Room identifier
    
    Returns:
        WebcamStreamProcessor instance
    """
    global _webcam_processor
    
    with _processor_lock:
        if _webcam_processor is None:
            _webcam_processor = WebcamStreamProcessor(camera_index, room_id)
        return _webcam_processor


def start_webcam_stream(camera_index=0, room_id="Webcam"):
    """
    Start webcam streaming.
    
    Gets or creates processor and starts streaming.
    
    Parameters:
        camera_index: Index of webcam to use
        room_id: Room identifier
    """
    processor = get_webcam_processor(camera_index, room_id)
    processor.start_streaming()


def stop_webcam_stream():
    """
    Stop webcam streaming.
    
    Stops the processor and clears the global reference.
    """
    global _webcam_processor
    
    with _processor_lock:
        if _webcam_processor:
            _webcam_processor.stop_streaming()
            _webcam_processor = None

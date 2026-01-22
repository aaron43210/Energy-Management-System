# =============================================================================
# CCTV Stream Processing Module
# =============================================================================
# This file handles real-time RTSP camera stream processing.
#
# Main features:
#   - RTSPStreamProcessor class manages a single camera connection
#   - Runs YOLO detection on each frame in a background thread
#   - Draws bounding boxes around detected persons
#   - Provides MJPEG-encoded frames for web streaming
#   - Tracks occupancy changes and triggers energy control
#
# Used for production CCTV deployments with professional security cameras.
# =============================================================================

import cv2
import numpy as np
import threading
from ultralytics import YOLO
from pathlib import Path

# Path to YOLO model file
BASE_DIR = Path(__file__).resolve().parent.parent
MODEL_PATH = BASE_DIR / "yolov8n.pt"


class RTSPStreamProcessor:
    """
    Processes an RTSP stream to detect persons and determine room occupancy.
    
    This class handles:
        - Connecting to RTSP camera streams
        - Running YOLO person detection on frames
        - Drawing detection overlays on frames
        - Providing frames for web streaming
        - Tracking and reporting occupancy changes
    
    Attributes:
        rtsp_url: URL of the RTSP camera stream
        room_id: Identifier for the room being monitored
        model: YOLO detection model
        cap: OpenCV video capture object
        current_frame: Latest processed frame with annotations
        person_count: Number of people detected
        is_running: Whether stream processing is active
        processing_thread: Background thread for processing
        lock: Thread lock for safe access to shared data
        occupancy_callback: Function to call when occupancy changes
        previous_occupancy: Last known occupancy state
    """
    
    def __init__(self, rtsp_url, room_id):
        """
        Initialize the RTSP stream processor.
        
        Parameters:
            rtsp_url: URL of the RTSP camera stream
            room_id: Identifier for the room being monitored
        """
        # Store configuration
        self.rtsp_url = rtsp_url
        self.room_id = room_id
        
        # Load YOLO model for person detection
        self.model = YOLO(MODEL_PATH)
        
        # Video capture object (None until connected)
        self.cap = None
        
        # Current processed frame (None until first frame)
        self.current_frame = None
        
        # Detection results
        self.person_count = 0
        
        # Processing state
        self.is_running = False
        self.processing_thread = None
        
        # Thread safety lock
        self.lock = threading.Lock()
        
        # Occupancy tracking
        self.occupancy_callback = None
        self.previous_occupancy = None
        
    def connect(self):
        """
        Connect to the RTSP stream.
        
        Opens the video capture and verifies the connection by reading
        a test frame.
        
        Returns:
            True if connection is successful
            False if connection failed
        """
        try:
            # Open video capture with RTSP URL
            self.cap = cv2.VideoCapture(self.rtsp_url)
            
            # Set buffer size to 1 for minimal latency
            self.cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)
            
            # Test the connection by reading a frame
            ret, frame = self.cap.read()
            
            if not ret or frame is None:
                # Connection failed - clean up
                self.cap.release()
                self.cap = None
                print(f" Failed to connect to stream: {self.room_id}")
                return False
            
            print(f"✅ Connected to stream: {self.room_id}")
            return True
            
        except Exception as e:
            print(f" Error connecting to stream: {e}")
            return False
    
    def start_processing(self, occupancy_callback=None):
        """
        Start processing the stream in a separate thread.
        
        Parameters:
            occupancy_callback: Optional function to call when occupancy changes
                               Function signature: callback(room_id, is_occupied)
        """
        # Check if already running
        if self.is_running:
            print(f"Stream already processing for {self.room_id}")
            return
        
        # Connect if not already connected
        if self.cap is None:
            if not self.connect():
                return

        # Store the callback
        self.occupancy_callback = occupancy_callback
        
        # Mark as running
        self.is_running = True
        
        # Create and start processing thread
        self.processing_thread = threading.Thread(
            target=self._process_stream,
            daemon=True
        )
        self.processing_thread.start()
        
        print(f"🚀 Started stream processing for {self.room_id}")
    
    def stop_processing(self):
        """
        Stop processing the stream.
        
        Signals the processing thread to stop, waits for it to finish,
        and releases the video capture.
        """
        # Signal thread to stop
        self.is_running = False
        
        # Wait for thread to finish
        if self.processing_thread:
            self.processing_thread.join(timeout=5)
        
        # Release video capture
        if self.cap:
            self.cap.release()
            self.cap = None
        
        # Clear current frame
        self.current_frame = None
        
        print(f"Stopped stream processing for {self.room_id}")
    
    def _process_stream(self):
        """
        Main loop for processing stream frames.
        
        This runs in a background thread and:
            1. Reads frames from the camera
            2. Runs YOLO detection
            3. Updates occupancy status
            4. Annotates frames for streaming
        """
        while self.is_running:
            try:
                # Read a frame from the camera
                ret, frame = self.cap.read()
                
                # Handle connection loss
                if not ret or frame is None:
                    print(f"⚠️ Lost frame from {self.room_id}, attempting reconnect...")
                    if not self.connect():
                        self.is_running = False
                        break
                    continue
                
                # Run YOLO detection (class 0 = person, confidence 0.5)
                results = self.model(frame, conf=0.5, classes=[0], verbose=False)
                
                # Count detected persons
                person_count = len(results[0].boxes) if results[0] else 0
                
                # Update occupancy status
                self._update_occupancy(person_count)
                
                # Annotate frame with detection boxes and overlay
                with self.lock:
                    self.current_frame = self._annotate_frame(frame, results, person_count)
            
            except Exception as e:
                print(f" Error processing frame for {self.room_id}: {e}")
                continue

    def _update_occupancy(self, person_count):
        """
        Update occupancy status and trigger callback if it changed.
        
        Parameters:
            person_count: Number of people detected in current frame
        """
        with self.lock:
            # Update person count
            self.person_count = person_count
            
            # Determine if room is occupied
            is_occupied = person_count > 0
            
            # Check if occupancy status changed
            if is_occupied != self.previous_occupancy:
                # Update previous state
                self.previous_occupancy = is_occupied
                
                # Call callback if registered
                if self.occupancy_callback:
                    self.occupancy_callback(self.room_id, is_occupied)
                    
                    # Log the change
                    status = "Occupied" if is_occupied else "Empty"
                    print(f"📊 {self.room_id}: {status} ({self.person_count} people)")

    def _annotate_frame(self, frame, results, person_count):
        """
        Annotate frame with YOLO detection boxes and person count overlay.
        
        Parameters:
            frame: Original video frame
            results: YOLO detection results
            person_count: Number of detected persons
        
        Returns:
            Annotated frame with visualization
        """
        # Create a copy to avoid modifying original
        annotated_frame = frame.copy()
        
        # Draw bounding boxes
        self._draw_bounding_boxes(annotated_frame, results)
        
        # Draw status overlay
        self._draw_overlay(annotated_frame, person_count)
        
        return annotated_frame

    def _draw_bounding_boxes(self, frame, results):
        """
        Draw bounding boxes for detected persons.
        
        Parameters:
            frame: Frame to draw on
            results: YOLO detection results
        """
        # Check if there are detection results
        if results[0] and results[0].boxes:
            # Draw box for each detected person
            for box in results[0].boxes:
                # Get box coordinates
                x1, y1, x2, y2 = map(int, box.xyxy[0])
                confidence = box.conf[0]
                
                # Draw rectangle around person
                cv2.rectangle(frame, (x1, y1), (x2, y2), (0, 255, 0), 2)
                
                # Draw confidence label
                label = f"Person {confidence:.2f}"
                label_size, _ = cv2.getTextSize(label, cv2.FONT_HERSHEY_SIMPLEX, 0.5, 1)
                
                # Draw label background
                cv2.rectangle(
                    frame,
                    (x1, y1 - label_size[1] - 4),
                    (x1 + label_size[0], y1),
                    (0, 255, 0),
                    -1
                )
                
                # Draw label text
                cv2.putText(
                    frame,
                    label,
                    (x1, y1 - 2),
                    cv2.FONT_HERSHEY_SIMPLEX,
                    0.5,
                    (0, 0, 0),
                    1
                )

    def _draw_overlay(self, frame, person_count):
        """
        Draw occupancy status and person count overlay.
        
        Parameters:
            frame: Frame to draw on
            person_count: Number of people detected
        """
        # Determine occupancy status
        occupancy_status = "OCCUPIED" if person_count > 0 else "EMPTY"
        count_text = f"{self.room_id} | People: {person_count}"
        
        # Draw black background for text
        cv2.rectangle(frame, (0, 0), (400, 60), (0, 0, 0), -1)
        
        # Draw person count
        cv2.putText(
            frame,
            count_text,
            (10, 30),
            cv2.FONT_HERSHEY_SIMPLEX,
            1,
            (0, 255, 255),
            2
        )
        
        # Draw occupancy status
        # Red for occupied, Green for empty
        status_color = (0, 0, 255) if person_count > 0 else (0, 255, 0)
        cv2.putText(
            frame,
            occupancy_status,
            (10, 55),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.7,
            status_color,
            2
        )

    def get_annotated_frame(self):
        """
        Get the latest annotated frame as JPEG bytes for streaming.
        
        Returns:
            JPEG-encoded frame bytes, or None if no frame available
        """
        with self.lock:
            # Check if we have a frame
            if self.current_frame is None:
                return None
            
            # Encode frame as JPEG
            ret, buffer = cv2.imencode('.jpg', self.current_frame)
            
            if ret:
                return buffer.tobytes()
                
        return None
    
    def get_person_count(self):
        """
        Get current person count from latest frame.
        
        Returns:
            Number of people detected
        """
        with self.lock:
            return self.person_count


# =============================================================================
# Global Stream Processors Management
# =============================================================================
# These functions manage multiple RTSPStreamProcessor instances,
# one for each room that has a connected CCTV camera.
# =============================================================================

# Dictionary to store stream processors by room_id
_stream_processors = {}

# Lock for thread-safe access to processors dictionary
_processors_lock = threading.Lock()


def create_stream_processor(rtsp_url, room_id):
    """
    Create or retrieve a stream processor for a room.
    
    If a processor already exists for the room, it is stopped and replaced.
    
    Parameters:
        rtsp_url: RTSP camera URL
        room_id: Room identifier
    
    Returns:
        RTSPStreamProcessor instance
    """
    with _processors_lock:
        # Stop existing processor if any
        if room_id in _stream_processors:
            _stream_processors[room_id].stop_processing()
        
        # Create new processor
        processor = RTSPStreamProcessor(rtsp_url, room_id)
        _stream_processors[room_id] = processor
        
        return processor


def get_stream_processor(room_id):
    """
    Get existing stream processor for a room.
    
    Parameters:
        room_id: Room identifier
    
    Returns:
        RTSPStreamProcessor instance, or None if not found
    """
    with _processors_lock:
        return _stream_processors.get(room_id)


def cleanup_stream_processor(room_id):
    """
    Stop and remove stream processor for a room.
    
    Parameters:
        room_id: Room identifier
    """
    with _processors_lock:
        if room_id in _stream_processors:
            _stream_processors[room_id].stop_processing()
            del _stream_processors[room_id]


def cleanup_all_processors():
    """
    Stop and remove all stream processors.
    
    Called during application shutdown.
    """
    with _processors_lock:
        # Stop each processor
        for processor in list(_stream_processors.values()):
            processor.stop_processing()
        
        # Clear the dictionary
        _stream_processors.clear()

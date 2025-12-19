"""
ARCHITECTURE & CODEBASE GUIDE

Industrial-grade Energy AI Management System
=============================================

## Project Structure

energy_ai/
├── backend/                  # FastAPI server (Python)
│   ├── __init__.py          # Package initialization
│   ├── api.py               # Main FastAPI application with all endpoints
│   ├── room_config.py       # Room state initialization and management
│   ├── energy_logic.py      # Energy control business logic (pure functions)
│   ├── person_detect.py     # YOLO-based person detection module
│   ├── webcam_energy.py     # Webcam AI processing subprocess
│   ├── cctv_stream.py       # RTSP/CCTV stream processing
│   └── multi_room_energy.py # Multi-room process orchestration
├── frontend/                 # React + Vite application (JavaScript)
│   ├── src/
│   │   ├── api.js           # Backend API service layer
│   │   ├── App.jsx          # Root React component
│   │   ├── main.jsx         # Entry point
│   │   ├── Dashboard.jsx    # Main dashboard component
│   │   ├── RoomCard.jsx     # Individual room component
│   │   ├── CctvRealMode.jsx # CCTV mode component
│   │   ├── WebcamTestMode.jsx # Webcam demo component
│   │   ├── App.css          # Main styling
│   │   ├── styles.css       # Component styles
│   │   └── index.css        # Global styles
│   ├── public/              # Static assets
│   ├── index.html           # HTML entry point
│   ├── package.json         # Dependencies
│   ├── vite.config.js       # Vite configuration
│   └── eslint.config.js     # Linting rules
├── yolov8n.pt               # YOLO v8 Nano model weights
├── README.md                # Project overview
└── .gitignore               # Git ignore rules


## Architecture Patterns

### 1. Backend Architecture

**Layered Design:**
- API Layer (api.py) - Handles HTTP requests/responses
- Business Logic (energy_logic.py) - Pure functions, easily testable
- Data Layer (room_config.py) - State management and initialization
- AI/Detection Layer (person_detect.py, cctv_stream.py) - ML operations
- Process Management (multi_room_energy.py, webcam_energy.py) - Background tasks

**Data Flow:**
```
HTTP Request → FastAPI Endpoint → Business Logic → State Update → Response
                                        ↓
                              AI Process (background)
                                        ↓
                          Occupancy Detection → Energy Control
```

### 2. Frontend Architecture

**Component Hierarchy:**
```
App
└── Dashboard (state management)
    ├── RoomCard (each room)
    │   └── Room controls
    ├── CctvRealMode (CCTV integration)
    │   └── Stream viewer
    └── WebcamTestMode (demo mode)
        └── Test controls
```

**State Management:**
- React hooks (useState, useEffect, useCallback)
- Centralized API service (api.js)
- Component-level state where appropriate


## Key Files Explained

### backend/api.py
- FastAPI application factory
- CORS configuration for frontend access
- Global state management (rooms_state)
- API endpoints organized by functionality:
  * Health checks
  * Room status endpoints
  * Occupancy management
  * AI process control
  * CCTV connection/management
  * MJPEG video streaming

### backend/energy_logic.py
- Pure function: auto_control(rooms, room_id)
- No side effects, easily testable
- Implements business rules:
  * Light ON when occupied
  * Light/AC OFF when vacant
- Can be used in multiple contexts (API, scripts, tests)

### backend/room_config.py
- Defines available rooms (ROOM_NAMES)
- Default state template (_DEFAULT_ROOM_STATE)
- Factory functions for state initialization
- Ensures state independence via deep copy

### backend/person_detect.py
- Singleton YOLO model loading (lazy initialization)
- count_people() function for frame analysis
- Configurable confidence threshold
- Handles missing model file gracefully

### backend/cctv_stream.py
- RTSPStreamProcessor class for RTSP handling
- Frame capture from camera streams
- YOLO detection on each frame
- MJPEG encoding for web streaming
- Threading for concurrent processing
- Occupancy change callbacks

### backend/webcam_energy.py
- Subprocess for webcam demonstration
- Real-time detection visualization
- API updates for occupancy changes
- Press ESC to exit gracefully

### frontend/src/api.js
- Centralized API service layer
- Error handling and request formatting
- Organized endpoints by function
- Base URL auto-detection (local/remote)

### frontend/src/Dashboard.jsx
- Main UI component
- Room polling and state management
- Mode switching (webcam/CCTV)
- Controls and status display


## Development Workflow

1. **Backend Development:**
   - Modify backend files
   - Run tests: `python -m backend.module_name`
   - Restart server with --reload for hot reload

2. **Frontend Development:**
   - Modify React components
   - Vite automatically hot-reloads
   - Run lint: `npm run lint`

3. **API Addition:**
   - Add endpoint to api.py
   - Create Pydantic model if needed
   - Document with docstrings
   - Add frontend API function in api.js


## Error Handling Strategy

**Backend:**
- HTTPException for API errors (400, 404, 500)
- Try-except blocks for resource cleanup
- Graceful degradation for missing resources

**Frontend:**
- Try-catch in async operations
- User-friendly error messages
- Fallback UI states

**Process Management:**
- Graceful shutdown handlers
- Resource cleanup in finally blocks
- Process termination with timeout


## Testing Approach

**Unit Tests:**
- energy_logic.py: Pure function tests
- room_config.py: State initialization tests
- person_detect.py: Model loading tests

**Integration Tests:**
- API endpoint functionality
- Frontend-backend communication
- Multi-room orchestration

**Run Tests:**
```bash
python -m backend.energy_logic
python -m backend.person_detect
python -m backend.room_config
```


## Performance Considerations

1. **YOLO Model:**
   - Loaded once (singleton pattern)
   - Confidence threshold tunable
   - Frame skipping for high-load scenarios

2. **Streaming:**
   - MJPEG format for wide compatibility
   - Frame buffering to prevent lag
   - Threading for non-blocking operations

3. **Database:**
   - Currently uses in-memory state
   - Could migrate to persistent database for production

4. **API:**
   - CORS enabled for frontend
   - Async operations where applicable
   - Connection pooling ready


## Security Considerations

1. **CCTV Credentials:**
   - Transmitted via HTTPS in production
   - Should use environment variables
   - Never hardcode in version control

2. **API Security:**
   - CORS configured for known origins
   - Input validation via Pydantic
   - Rate limiting (to be added)

3. **Frontend Security:**
   - No sensitive data in localStorage
   - HTTPS in production
   - Content Security Policy headers


## Scalability Path

**Current:**
- Single backend instance
- In-memory state
- 4 rooms fixed

**Future Enhancements:**
- Database (PostgreSQL/MongoDB)
- Multi-instance deployment (load balancer)
- Caching layer (Redis)
- Message queue (RabbitMQ/Kafka)
- Microservices architecture
- Kubernetes orchestration


## Deployment

**Development:**
```bash
# Terminal 1: Backend
uvicorn backend.api:app --reload --port 8002

# Terminal 2: Frontend
cd frontend && npm run dev
```

**Production:**
```bash
# Backend
uvicorn backend.api:app --host 0.0.0.0 --port 8002 --workers 4

# Frontend
cd frontend && npm run build
# Serve dist/ folder with static hosting
```


## Contributing Guidelines

1. Follow existing code style
2. Add docstrings to all functions
3. Keep functions focused and testable
4. Update this documentation
5. Test locally before committing
6. Use meaningful commit messages


## Support

For issues or questions:
1. Check docstrings in code
2. Review API endpoint documentation
3. Check component prop documentation
4. Review error messages in console

"""

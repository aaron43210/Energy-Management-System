# Energy AI Management System

Industrial-grade energy management application with real-time AI person detection for smart buildings.

## Overview

This application automatically controls room lighting and AC based on real-time person detection using YOLOv8. It supports two operational modes:

- **Webcam Mode**: Real-time detection from local webcam (testing/demo)
- **CCTV Mode**: Integration with RTSP cameras for production deployment

## Architecture

```
energy_ai/
├── backend/                    # FastAPI server
│   ├── api.py                 # Main API endpoints
│   ├── room_config.py         # Room state management
│   ├── energy_logic.py        # Energy control rules
│   ├── person_detect.py       # YOLO detection
│   ├── webcam_energy.py       # Webcam processing
│   ├── cctv_stream.py         # RTSP processing
│   ├── multi_room_energy.py   # Multi-room orchestration
│   ├── test_api.py            # API endpoint tests
│   └── test_detection.py      # YOLO detection tests
├── frontend/                   # React + Vite
│   ├── src/
│   │   ├── api.js             # API service
│   │   ├── App.jsx            # Root component
│   │   ├── Dashboard.jsx      # Main dashboard
│   │   └── RoomCard.jsx       # Room component
│   └── package.json
├── yolov8n.pt                 # YOLO model
├── start.sh                   # Convenience startup script
└── README.md
```

## Quick Start

### Prerequisites
- Python 3.10+
- Node.js 18+
- Webcam or RTSP camera (optional)

### Option 1: Using Startup Script (Recommended)
```bash
# First time setup
python3 -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate
pip install -r requirements.txt
cd frontend && npm install && cd ..

# Start both servers with one command
./start.sh
```

### Option 2: Manual Startup

#### Backend
```bash
source .venv/bin/activate  # On Windows: .venv\Scripts\activate
uvicorn backend.api:app --port 8002 --reload
```

#### Frontend (new terminal)
```bash
cd frontend
npm run dev
```

Access at `http://localhost:5173`

## Key Features

✅ Real-time YOLO person detection  
✅ Multi-room occupancy tracking  
✅ Automatic light/AC control  
✅ Live MJPEG streaming  
✅ REST API  
✅ Web dashboard  
✅ Video upload analysis  
✅ Comprehensive testing  

## API Endpoints

- `GET /` - Health check
- `GET /api/rooms` - Room status
- `POST /api/occupancy` - Update occupancy
- `POST /api/ai/{room_id}/start` - Start detection
- `POST /api/cctv/connect` - Connect to camera
- `GET /api/stream/{room_id}` - Video stream
- `GET /api/webcam/test/status` - Webcam status
- `POST /api/webcam/test/start` - Start webcam mode
- `POST /api/video/upload` - Upload video for analysis

## Testing

### Run All Tests
```bash
# Test API endpoints
.venv/bin/python backend/test_api.py

# Test YOLO detection
.venv/bin/python backend/test_detection.py
```

### Manual Testing
```bash
# Check backend health
curl http://localhost:8002/

# Get room status
curl http://localhost:8002/api/rooms

# Update room occupancy
curl -X POST http://localhost:8002/api/occupancy \
  -H "Content-Type: application/json" \
  -d '{"room_id":"Classroom","occupied":true}'
```

## Troubleshooting

### Backend won't start
- Ensure Python 3.10+ is installed: `python3 --version`
- Check virtual environment is activated: `which python` should show `.venv/bin/python`
- Reinstall dependencies: `pip install -r requirements.txt`
- Check port 8002 is not in use: `lsof -i :8002`

### Frontend won't start
- Ensure Node.js 18+ is installed: `node --version`
- Reinstall dependencies: `cd frontend && rm -rf node_modules && npm install`
- Check port 5173 is not in use: `lsof -i :5173`

### YOLO model not found
- Ensure `yolov8n.pt` exists in project root
- Download if missing: The model will auto-download on first use

### Can't access the dashboard
- Verify backend is running: `curl http://localhost:8002/`
- Verify frontend is running: `curl http://localhost:5173/`
- Check browser console for errors (F12)
- Try a different browser

### Webcam not working
- Grant camera permissions in browser/system settings
- Check if another app is using the camera
- Try different camera index in webcam mode

## Documentation

- **Architecture**: See `ARCHITECTURE.md` for detailed system design
- **Quick Start**: See `QUICKSTART.md` for setup instructions
- **Verification**: See `VERIFICATION.md` for quality assurance details
- **Backend**: See docstrings in `backend/*.py`
- **Frontend**: See comments in `frontend/src/*.jsx`
- **API**: RESTful endpoints with JSON schemas

## Configuration

Copy `.env.example` to `.env` and customize:
```bash
cp .env.example .env
```

## Production Deployment

```bash
# Backend
uvicorn backend.api:app --host 0.0.0.0 --port 8002 --workers 4

# Frontend
cd frontend && npm run build
# Serve dist/ folder with nginx or similar
```

## License

© 2025 Energy AI Management System


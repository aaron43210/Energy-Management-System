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
│   └── multi_room_energy.py   # Multi-room orchestration
├── frontend/                   # React + Vite
│   ├── src/
│   │   ├── api.js             # API service
│   │   ├── App.jsx            # Root component
│   │   ├── Dashboard.jsx      # Main dashboard
│   │   └── RoomCard.jsx       # Room component
│   └── package.json
├── yolov8n.pt                 # YOLO model
└── README.md
```

## Quick Start

### Prerequisites
- Python 3.10+
- Node.js 18+
- Webcam or RTSP camera

### Backend
```bash
pip install -r requirements.txt
uvicorn backend.api:app --port 8002 --reload
```

### Frontend
```bash
cd frontend
npm install
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

## API Endpoints

- `GET /api/rooms` - Room status
- `POST /api/occupancy` - Update occupancy
- `POST /api/ai/{room_id}/start` - Start detection
- `POST /api/cctv/connect` - Connect to camera
- `GET /api/stream/{room_id}` - Video stream

## Documentation

- Backend: See docstrings in `backend/*.py`
- Frontend: See comments in `frontend/src/*.jsx`
- API: RESTful endpoints with JSON schemas

## License

© 2025 Energy AI Management System

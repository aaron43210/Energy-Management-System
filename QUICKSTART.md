# Quickstart Guide

## Complete Setup & Run Instructions

### 1. First Time Setup (One-time)
```bash
# Navigate to project root
cd /Users/aaronr/Desktop/energy_ai

# Create virtual environment (if not already done)
python3 -m venv .venv

# Activate virtual environment
source .venv/bin/activate

# Install backend dependencies
pip install -r requirements.txt

# Install frontend dependencies
cd frontend
npm install
cd ..
```

---

### 2. To Run Backend
```bash
# From project root, activate venv
source .venv/bin/activate

# Start backend server
uvicorn backend.api:app --port 8002 --reload
```
Backend will be running at: `http://127.0.0.1:8002`

---

### 3. To Run Frontend (New Terminal)
```bash
# From project root, activate venv (optional for frontend)
source .venv/bin/activate

# Navigate to frontend and start dev server
cd frontend
npm run dev
```
Frontend will be running at: `http://127.0.0.1:5173`

---

## Quick Copy-Paste Commands

### Terminal 1 (Backend):
```bash
cd /Users/aaronr/Desktop/energy_ai
source .venv/bin/activate
uvicorn backend.api:app --port 8002 --reload
```

### Terminal 2 (Frontend):
```bash
cd /Users/aaronr/Desktop/energy_ai/frontend
npm run dev
```

---

## That's it!

- Backend API running on port **8002**
- Frontend UI running on port **5173**
- Open browser to `http://127.0.0.1:5173` to see the dashboard

Both will auto-reload when you make code changes (hot reload enabled).

---

## Troubleshooting

### Backend won't start?
- Make sure Python 3.8+ is installed
- Check `.venv` is activated (you should see `(.venv)` in terminal)
- Try: `pip install -r requirements.txt` again

### Frontend won't start?
- Make sure Node.js 18+ is installed
- Run `npm install` in the `frontend` directory
- Check port 5173 isn't already in use

### Can't access the dashboard?
- Open `http://127.0.0.1:5173` in your browser
- Make sure both backend and frontend are running
- Check backend shows "Application startup complete"

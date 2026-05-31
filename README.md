# 🚦 Smart Traffic AI — Full-Stack System

AI-powered adaptive traffic management using YOLOv8, Flask, Socket.IO,
and a live web dashboard.

---

## Project structure

```
smart-traffic-ai/
├── backend/
│   ├── app.py               ← Flask + Socket.IO entry point
│   ├── detector.py          ← YOLOv8 vehicle detection
│   ├── signal_controller.py ← Adaptive signal timing (threaded)
│   ├── emergency.py         ← Emergency-vehicle detection
│   ├── database.py          ← SQLAlchemy models & helpers
│   └── utils.py             ← Shared helpers (frame encoding, paths)
├── frontend/                ← (reserved for React upgrade)
├── models/
│   └── yolov8n.pt           ← Downloaded automatically on first run
├── videos/                  ← Place your MP4 / JPEG traffic files here
├── static/
│   ├── css/style.css
│   └── js/dashboard.js
├── templates/
│   └── index.html
└── requirements.txt
```

---

## Quick start

```bash
# 1. Create virtual environment
python -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate

# 2. Install dependencies
pip install -r requirements.txt

# 3. Add traffic videos (optional — system works with static images too)
# Copy north_traffic.mp4 / east_traffic.mp4 … to videos/

# 4. Run
python backend/app.py
# Open http://localhost:5000
```

---

## How it works

1. **Click ▶ Start** in the dashboard.
2. The backend spins up one detection thread per direction (N/E/S/W).
3. Each thread reads frames from the corresponding video file, runs
   YOLOv8 inference, and counts vehicles.
4. `TrafficSignalController` runs a separate cycle thread that grants
   green time proportional to vehicle counts.
5. Results stream to the browser via Socket.IO — live frames, signal
   states, and counts update in real time.
6. All events are persisted to SQLite (`traffic.db`).

---

## Configuration

| Variable          | Default                    | Description                  |
|-------------------|----------------------------|------------------------------|
| `SECRET_KEY`      | `dev-secret-change-me`     | Flask session secret         |
| `DATABASE_URL`    | `sqlite:///traffic.db`     | SQLAlchemy DB URI            |

Set via environment variables or a `.env` file in the project root.

---

## Upgrade path

| Phase | What to add                              |
|-------|------------------------------------------|
| ✅ 1  | YOLOv8 + video feed ← *you are here*    |
| ✅ 2  | Flask dashboard + SQLite DB              |
| ✅ 3  | Emergency priority + analytics           |
| 🔜 4  | LSTM prediction + Docker + cloud deploy  |

---

## Author
Somesh — Smart AI-based Traffic Management System
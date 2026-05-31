from itertools import count
import os
import cv2
import time
import base64
import threading

from flask import Flask, render_template, jsonify
from flask_socketio import SocketIO

from detector import VehicleDetector
from signal_controller import calculate_green_time


# =====================================================
# FLASK SETUP
# =====================================================

BASE_DIR = os.path.dirname(
    os.path.dirname(os.path.abspath(__file__))
)

app = Flask(

    __name__,

    template_folder=os.path.join(
        BASE_DIR,
        "templates"
    ),

    static_folder=os.path.join(
        BASE_DIR,
        "static"
    )
)

socketio = SocketIO(
    app,
    cors_allowed_origins="*"
)


# =====================================================
# MODE
# =====================================================

# OPTIONS:
# "image"
# "video"

MODE = "images"


# =====================================================
# MEDIA SOURCES
# =====================================================

MEDIA_SOURCES = {

    "north": {
        "image": os.path.join(
            BASE_DIR,
            "media",
            "images",
            "north.jpg"
        )
    },

    "east": {
        "image": os.path.join(
            BASE_DIR,
            "media",
            "images",
            "east.jpg"
        )
    },

    "south": {
        "image": os.path.join(
            BASE_DIR,
            "media",
            "images",
            "south.jpg"
        )
    },

    "west": {
        "image": os.path.join(
            BASE_DIR,
            "media",
            "images",
            "west.jpg"
        )
    }
}


# =====================================================
# GLOBALS
# =====================================================

system_running = False

detector = VehicleDetector()

latest_data = {

    "north": {},
    "east": {},
    "south": {},
    "west": {}
}

event_logs = []
traffic_history = []


# =====================================================
# ENCODE FRAME
# =====================================================

def encode_frame(frame):

    _, buffer = cv2.imencode(
        ".jpg",
        frame
    )

    return base64.b64encode(
        buffer
    ).decode("utf-8")


# =====================================================
# PROCESS IMAGE
# =====================================================

def process_image(direction, image_path):

    frame = cv2.imread(image_path)

    if frame is None:

        print(f"[ERROR] Cannot read image: {image_path}")

        return

    annotated, count, detections = detector.detect(frame)

    green_time = calculate_green_time(count)

    frame_base64 = encode_frame(annotated)

    signal_state = "GREEN"

    socketio.emit(

        f"frame_{direction}",

        {
            "image": frame_base64,

            "count": count,

            "signal": signal_state,

            "green_sec": green_time,

            "emergency": False
        }
    )

    # Store latest data
    latest_data[direction] = {

        "count": count,

        "green_time": green_time,

        "signal": signal_state
    }

    # Add log
    event_logs.append({

        "timestamp": time.strftime("%H:%M:%S"),

        "direction": direction.upper(),

        "vehicle_count": count,

        "green_time": green_time,

        "emergency": False
    })


# =====================================================
# PROCESS VIDEO
# =====================================================

def process_video(direction, video_path):

    global system_running

    cap = cv2.VideoCapture(video_path)

    if not cap.isOpened():

        print(f"[ERROR] Cannot open video: {video_path}")

        return

    while system_running:

        ret, frame = cap.read()

        # Restart video if ended
        if not ret:

            cap.set(
                cv2.CAP_PROP_POS_FRAMES,
                0
            )

            continue

        # YOLO DETECTION
        annotated, count, detections = detector.detect(frame)

        green_time = calculate_green_time(count)

        # Determine busiest direction
        busiest_direction = max(

            latest_data,

            key=lambda d:
            latest_data[d].get("count", 0)
        )

        signal_state = (

            "GREEN"

            if direction == busiest_direction

            else "RED"
        )

        # Encode image
        frame_base64 = encode_frame(annotated)

        # Store latest data
        latest_data[direction] = {

            "count": count,

            "green_time": green_time,

            "signal": signal_state
        }

        # Emergency detection placeholder
        emergency = False

        # SOCKET EMIT
        socketio.emit(

            f"frame_{direction}",

            {
                "image": frame_base64,

                "count": count,

                "signal": signal_state,

                "green_sec": green_time,

                "emergency": emergency
            }
        )

        # Event log
        event_logs.append({

            "timestamp": time.strftime("%H:%M:%S"),

            "direction": direction.upper(),

            "vehicle_count": count,

            "green_time": green_time,

            "emergency": emergency
        })

        # Limit logs
        if len(event_logs) > 50:

            event_logs.pop(0)

        socketio.sleep(0.03)

    cap.release()


# =====================================================
# START PROCESSING
# =====================================================

def start_processing():

    global system_running

    if system_running:
        return

    system_running = True

    print("[INFO] IMAGE MODE STARTED")

    for direction, source in MEDIA_SOURCES.items():

        image_path = source["image"]

        print(f"[INFO] Loading image: {image_path}")

        frame = cv2.imread(image_path)

        if frame is None:

            print(f"[ERROR] Cannot load image: {image_path}")

            continue

        # YOLO detection
        annotated, count, detections = detector.detect(frame)

        # Encode image
        frame_base64 = encode_frame(annotated)

        print(f"[SUCCESS] Sending image for {direction}")

        # Emit frame
        socketio.emit(

            f"frame_{direction}",

            {
                "image": frame_base64,
                "count": count,
                "signal": "GREEN",
                "green_sec": 20,
                "emergency": False
            }
        )
        traffic_history.append({

    "direction": direction.capitalize(),

    "count": count,

    "hour": time.strftime("%H")
})
    

# =====================================================
# STOP PROCESSING
# =====================================================

def stop_processing():

    global system_running

    system_running = False

    print("[INFO] System stopped")


# =====================================================
# ROUTES
# =====================================================

@app.route("/")
def index():

    return render_template("index.html")


@app.route("/api/start", methods=["POST"])
def api_start():

    start_processing()

    return jsonify({

        "status": "started"
    })


@app.route("/api/stop", methods=["POST"])
def api_stop():

    stop_processing()

    return jsonify({

        "status": "stopped"
    })


@app.route("/api/logs")
def api_logs():

    return jsonify(event_logs)


@app.route("/api/status")
def api_status():

    return jsonify({

        "running": system_running,

        "latest": latest_data
    })
@app.route("/api/summary")
def api_summary():

    summary = {}

    # Aggregate counts
    for item in traffic_history:

        key = (
            item["direction"],
            item["hour"]
        )

        if key not in summary:

            summary[key] = {
                "total": 0,
                "samples": 0
            }

        summary[key]["total"] += item["count"]

        summary[key]["samples"] += 1

    # Convert to frontend format
    result = []

    for (direction, hour), values in summary.items():

        avg = (
            values["total"] /
            values["samples"]
        )

        result.append({

            "direction": direction,

            "hour": hour,

            "avg_count": round(avg, 2)
        })

    return jsonify(result)

# =====================================================
# MAIN
# =====================================================

if __name__ == "__main__":

    socketio.run(

        app,

        host="0.0.0.0",

        port=5000,

        debug=True,

        allow_unsafe_werkzeug=True
    )
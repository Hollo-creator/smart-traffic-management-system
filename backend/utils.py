import os
import cv2
import base64
import numpy as np
from datetime import datetime


# ------------------------------------------------------------------ #
# Frame / image helpers                                                #
# ------------------------------------------------------------------ #

def frame_to_base64(frame: np.ndarray, quality: int = 75) -> str:
    """Encode a BGR frame as a base64 JPEG string for Socket.IO streaming."""
    _, buf = cv2.imencode(".jpg", frame, [cv2.IMWRITE_JPEG_QUALITY, quality])
    return base64.b64encode(buf).decode("utf-8")


def resize_frame(frame: np.ndarray, width: int = 640) -> np.ndarray:
    """Resize frame to a fixed width while keeping aspect ratio."""
    h, w = frame.shape[:2]
    scale  = width / w
    new_h  = int(h * scale)
    return cv2.resize(frame, (width, new_h))


def draw_signal_overlay(frame: np.ndarray, direction: str,
                        signal: str, count: int, green_sec: int) -> np.ndarray:
    """Draw a coloured HUD bar at the bottom of a frame."""
    h, w = frame.shape[:2]
    bar_h = 50
    overlay = frame.copy()

    colour = (0, 200, 0) if signal == "green" else (0, 0, 220)
    cv2.rectangle(overlay, (0, h - bar_h), (w, h), colour, -1)
    cv2.addWeighted(overlay, 0.5, frame, 0.5, 0, frame)

    text = (f"{direction} — {signal.upper()}  |  "
            f"Vehicles: {count}  |  Green: {green_sec}s")
    cv2.putText(frame, text, (10, h - 15),
                cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 2)
    return frame


# ------------------------------------------------------------------ #
# Path helpers                                                         #
# ------------------------------------------------------------------ #

BASE_DIR    = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
VIDEOS_DIR  = os.path.join(BASE_DIR, "videos")
MODELS_DIR  = os.path.join(BASE_DIR, "models")
STATIC_DIR  = os.path.join(BASE_DIR, "static")


def video_path(filename: str) -> str:
    return os.path.join(VIDEOS_DIR, filename)


def model_path(filename: str = "yolov8n.pt") -> str:
    return os.path.join(MODELS_DIR, filename)


# ------------------------------------------------------------------ #
# Timestamp                                                            #
# ------------------------------------------------------------------ #

def now_str() -> str:
    return datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S UTC")
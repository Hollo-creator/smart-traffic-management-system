import cv2
import numpy as np

# HSV colour range for emergency lights (red & blue flashing)
# Tune these if your lighting conditions differ
EMERGENCY_HSV_RANGES = [
    # Red (wraps around 0°)
    (np.array([0,   160, 100]), np.array([10,  255, 255])),
    (np.array([170, 160, 100]), np.array([180, 255, 255])),
    # Blue
    (np.array([100, 150,  80]), np.array([130, 255, 255])),
]

# Minimum contour area to avoid noise triggering
MIN_FLASH_AREA = 200

# Sirens / audio detection placeholder
# (real implementation would use a trained audio classifier)
SIREN_KEYWORDS = ["ambulance", "fire truck", "police"]


def detect_emergency_lights(frame: np.ndarray) -> bool:
    """
    Return True if probable emergency-vehicle light patterns are found
    in the given frame using HSV colour segmentation.
    """
    hsv   = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)
    mask  = np.zeros(hsv.shape[:2], dtype=np.uint8)

    for lo, hi in EMERGENCY_HSV_RANGES:
        mask = cv2.bitwise_or(mask, cv2.inRange(hsv, lo, hi))

    # Morphological cleanup
    kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (5, 5))
    mask   = cv2.morphologyEx(mask, cv2.MORPH_OPEN,  kernel)
    mask   = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, kernel)

    contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL,
                                   cv2.CHAIN_APPROX_SIMPLE)
    significant = [c for c in contours if cv2.contourArea(c) > MIN_FLASH_AREA]
    return len(significant) > 0


def classify_emergency_from_detections(detections: list) -> bool:
    """
    Check YOLOv8 detection labels for known emergency vehicle names.
    Useful when using a model fine-tuned on emergency vehicles.
    """
    for det in detections:
        name = det.get("class_name", "").lower()
        if any(kw in name for kw in SIREN_KEYWORDS):
            return True
    return False


class EmergencyDetector:
    """
    Stateful detector that combines colour-based light detection
    with optional label-based detection.
    It requires N consecutive positive frames before triggering,
    reducing false positives from ordinary brake lights.
    """

    def __init__(self, confirmation_frames: int = 3):
        self.confirmation_frames = confirmation_frames
        self._positive_streak = 0

    def update(self, frame: np.ndarray, detections: list) -> bool:
        """
        Call once per frame.  Returns True when emergency is confirmed.
        """
        light_hit = detect_emergency_lights(frame)
        label_hit = classify_emergency_from_detections(detections)

        if light_hit or label_hit:
            self._positive_streak += 1
        else:
            self._positive_streak = max(0, self._positive_streak - 1)

        return self._positive_streak >= self.confirmation_frames

    def reset(self):
        self._positive_streak = 0
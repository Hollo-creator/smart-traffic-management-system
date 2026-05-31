import time
import threading
from datetime import datetime


# =====================================================
# DIRECTIONS
# =====================================================

DIRECTIONS = [
    "North",
    "East",
    "South",
    "West"
]


# =====================================================
# SIGNAL TIMING CONSTANTS
# =====================================================

MIN_GREEN = 10
MAX_GREEN = 60
BASE_GREEN = 15

RED_BUFFER = 3


# =====================================================
# TRAFFIC THRESHOLDS
# =====================================================

HIGH_TRAFFIC = 40
MEDIUM_TRAFFIC = 20


# =====================================================
# GREEN TIME CALCULATION
# =====================================================

def compute_green_duration(
    vehicle_count: int,
    emergency: bool = False
) -> int:

    """
    Adaptive green timing
    """

    # Emergency vehicle priority
    if emergency:

        return MAX_GREEN

    # Heavy traffic
    if vehicle_count > HIGH_TRAFFIC:

        duration = BASE_GREEN + 30

    # Medium traffic
    elif vehicle_count > MEDIUM_TRAFFIC:

        duration = BASE_GREEN + 15

    # Normal traffic
    else:

        duration = BASE_GREEN

    return max(
        MIN_GREEN,
        min(MAX_GREEN, duration)
    )


# =====================================================
# MAIN TRAFFIC SIGNAL CONTROLLER
# =====================================================

class TrafficSignalController:

    """
    Intelligent traffic controller
    """

    def __init__(self, socketio=None):

        self.socketio = socketio

        # Vehicle counts
        self.counts = {

            d: 0

            for d in DIRECTIONS
        }

        # Emergency states
        self.emergency = {

            d: False

            for d in DIRECTIONS
        }

        # Signal states
        self.state = {

            d: "red"

            for d in DIRECTIONS
        }

        # Green timings
        self.timings = {

            d: BASE_GREEN

            for d in DIRECTIONS
        }

        self.active_dir = None

        self._lock = threading.Lock()

        self._running = False

        self._thread = None


    # =================================================
    # UPDATE COUNTS
    # =================================================

    def update_count(

        self,

        direction: str,

        count: int,

        emergency: bool = False

    ):

        with self._lock:

            self.counts[direction] = count

            self.emergency[direction] = emergency

            self.timings[direction] = (

                compute_green_duration(

                    count,

                    emergency
                )
            )


    # =================================================
    # GET STATUS
    # =================================================

    def get_status(self) -> dict:

        with self._lock:

            return {

                "active_direction": self.active_dir,

                "timestamp": datetime.utcnow().isoformat(),

                "directions": {

                    d: {

                        "signal": self.state[d],

                        "count": self.counts[d],

                        "green_sec": self.timings[d],

                        "emergency": self.emergency[d]

                    }

                    for d in DIRECTIONS
                }
            }


    # =================================================
    # START CONTROLLER
    # =================================================

    def start(self):

        if self._running:

            return

        self._running = True

        self._thread = threading.Thread(

            target=self._cycle_loop,

            daemon=True
        )

        self._thread.start()

        print("[INFO] Signal controller started")


    # =================================================
    # STOP CONTROLLER
    # =================================================

    def stop(self):

        self._running = False

        print("[INFO] Signal controller stopped")


    # =================================================
    # SET GREEN SIGNAL
    # =================================================

    def _set_green(self, direction: str):

        with self._lock:

            for d in DIRECTIONS:

                self.state[d] = (

                    "green"

                    if d == direction

                    else "red"
                )

            self.active_dir = direction

        # Emit live update
        if self.socketio:

            self.socketio.emit(

                "signal_update",

                self.get_status()
            )


    # =================================================
    # ALL RED
    # =================================================

    def _all_red(self):

        with self._lock:

            for d in DIRECTIONS:

                self.state[d] = "red"

            self.active_dir = None

        if self.socketio:

            self.socketio.emit(

                "signal_update",

                self.get_status()
            )


    # =================================================
    # NEXT DIRECTION LOGIC
    # =================================================

    def _next_direction(self) -> str:

        with self._lock:

            # Emergency override
            for d in DIRECTIONS:

                if self.emergency[d]:

                    return d

            # Highest traffic priority
            return max(

                DIRECTIONS,

                key=lambda d:
                self.counts[d]
            )


    # =================================================
    # MAIN SIGNAL LOOP
    # =================================================

    def _cycle_loop(self):

        while self._running:

            direction = self._next_direction()

            with self._lock:

                green_time = self.timings[direction]

            # Activate signal
            self._set_green(direction)

            print(

                f"[SIGNAL] GREEN → {direction} "

                f"for {green_time}s "

                f"({self.counts[direction]} vehicles)"
            )

            # Green phase
            time.sleep(green_time)

            # Red buffer
            self._all_red()

            time.sleep(RED_BUFFER)


# =====================================================
# COMPATIBILITY FUNCTION
# =====================================================

def calculate_green_time(vehicle_count):

    """
    Compatibility helper for app.py
    """

    return compute_green_duration(
        vehicle_count
    )
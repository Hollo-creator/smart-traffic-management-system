from datetime import datetime
from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()


# ------------------------------------------------------------------ #
# Models                                                               #
# ------------------------------------------------------------------ #

class TrafficLog(db.Model):
    """One row per detection event (per direction, per frame)."""
    __tablename__ = "traffic_log"

    id          = db.Column(db.Integer, primary_key=True)
    timestamp   = db.Column(db.DateTime, default=datetime.utcnow, index=True)
    direction   = db.Column(db.String(10), nullable=False)
    count       = db.Column(db.Integer,   nullable=False)
    green_sec   = db.Column(db.Integer,   nullable=False)
    emergency   = db.Column(db.Boolean,   default=False)

    def to_dict(self):
        return {
            "id":        self.id,
            "timestamp": self.timestamp.isoformat(),
            "direction": self.direction,
            "count":     self.count,
            "green_sec": self.green_sec,
            "emergency": self.emergency,
        }


class SignalEvent(db.Model):
    """Records every green-phase transition."""
    __tablename__ = "signal_event"

    id          = db.Column(db.Integer, primary_key=True)
    timestamp   = db.Column(db.DateTime, default=datetime.utcnow, index=True)
    direction   = db.Column(db.String(10), nullable=False)
    duration    = db.Column(db.Integer,    nullable=False)   # seconds
    triggered_by_emergency = db.Column(db.Boolean, default=False)

    def to_dict(self):
        return {
            "id":        self.id,
            "timestamp": self.timestamp.isoformat(),
            "direction": self.direction,
            "duration":  self.duration,
            "emergency": self.triggered_by_emergency,
        }


# ------------------------------------------------------------------ #
# Helper functions                                                     #
# ------------------------------------------------------------------ #

def log_traffic(direction: str, count: int, green_sec: int,
                emergency: bool = False):
    """Insert a TrafficLog row and commit."""
    row = TrafficLog(
        direction=direction,
        count=count,
        green_sec=green_sec,
        emergency=emergency,
    )
    db.session.add(row)
    db.session.commit()
    return row


def log_signal_event(direction: str, duration: int,
                     emergency: bool = False):
    """Insert a SignalEvent row and commit."""
    row = SignalEvent(
        direction=direction,
        duration=duration,
        triggered_by_emergency=emergency,
    )
    db.session.add(row)
    db.session.commit()
    return row


def get_recent_logs(limit: int = 100):
    return (
        TrafficLog.query
        .order_by(TrafficLog.timestamp.desc())
        .limit(limit)
        .all()
    )


def get_hourly_summary():
    """
    Return average vehicle count grouped by direction & hour.
    Uses raw SQL for simplicity (works on SQLite & Postgres).
    """
    sql = """
        SELECT
            direction,
            strftime('%H', timestamp) AS hour,
            AVG(count)               AS avg_count
        FROM traffic_log
        GROUP BY direction, hour
        ORDER BY direction, hour
    """
    rows = db.session.execute(db.text(sql)).fetchall()
    return [{"direction": r[0], "hour": r[1], "avg_count": round(r[2], 1)}
            for r in rows]
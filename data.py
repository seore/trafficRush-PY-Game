# data.py
import json, os

SAVE_FILE = "data.json"

DEFAULT_DATA = {
    "coins": 0,
    "xp": 0,
    "level": 1,
    "selected_vehicle": "compact",
    "vehicles": {
        "compact": {"unlocked": True, "acceleration": 1, "speed": 1, "magnet": 1, "duration": 1},
        "sport":   {"unlocked": False,"acceleration": 0, "speed": 0, "magnet": 0, "duration": 0},
        "van":     {"unlocked": False,"acceleration": 0, "speed": 0, "magnet": 0, "duration": 0}
    },
    "achievements": {
        "coins_100": False,
        "missions_10": False,
        "distance_5000": False
    },
    "stats": {
        "total_coins": 0,
        "missions_played": 0,
        "distance_total": 0.0
    }
}

def load_data():
    if os.path.exists(SAVE_FILE):
        try:
            with open(SAVE_FILE, "r") as f:
                return json.load(f)
        except Exception:
            pass
    save_data(DEFAULT_DATA)
    return DEFAULT_DATA.copy()

def save_data(data):
    with open(SAVE_FILE, "w") as f:
        json.dump(data, f, indent=2)

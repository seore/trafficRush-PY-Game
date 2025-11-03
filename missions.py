from dataclasses import dataclass

class MissionDef:
    name: str
    kind: str
    target: int
    reward: int
    desc: str

MISSION_SELETS = [
    dict(name="Endurance 60", kind="survive", target=60, reward=400, desc="Survive for 60 seconds."),
    dict(name="Coin Collector 20", kind="coins", target=20, reward=300, desc="Collect 20 coins in one run."),
    dict(name="Combo x6", kind="combo", target=6, reward=350, desc="Reach a near-miss combo of x6."),
    dict(name="Endurance 90", kind="survive", target=90, reward=650, desc="Survive for 90 seconds."),
    dict(name="Coin Collector 35", kind="coins", target=35, reward=520, desc="Collect 35 coins in one run."),
    dict(name="Combo x8", kind="combo", target=8, reward=600, desc="Hit a near-miss combo of x8."),
]

def generate_difficulty(diff_name: str):
    if diff_name == "Esay":
        return MISSION_SELETS[:3]
    elif diff_name == "Hard":
        return MISSION_SELETS[3:]
    return MISSION_SELETS[:3] + MISSION_SELETS[3:4]
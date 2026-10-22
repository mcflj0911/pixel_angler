"""Save slots: three games kept side by side as JSON in the saves folder. A slot holds the economy, the game clock and the people
the angler has met. Loading fills the economy that is already in use, so the fishing scene keeps its reference to it."""
import json
from pathlib import Path

from weather import DAY_FRAMES

SAVE_DIR = Path(__file__).resolve().parent.parent / "saves"
SLOTS = (1, 2, 3)
SET_FIELDS = ("owned", "wardrobe", "sponsors", "claimed")  # Sets are kept as sorted lists in the file


def slot_path(slot):
    return SAVE_DIR / f"slot{slot}.json"


def save(economy, clock, met, slot):
    """Writes the slot. A write that fails is ignored, so the game carries on without a save."""
    data = {key: sorted(value) if key in SET_FIELDS else value for key, value in vars(economy).items()}
    data["_clock"] = clock
    data["_met"] = sorted(met)
    try:
        SAVE_DIR.mkdir(exist_ok=True)
        slot_path(slot).write_text(json.dumps(data, indent=1), encoding="utf-8")
        return True
    except OSError:
        return False


def load(economy, slot):
    """Fills the economy from the slot. Returns (clock, met) for the game to take up, or None if the slot is empty or unreadable."""
    try:
        data = json.loads(slot_path(slot).read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None
    clock = data.pop("_clock", 0)
    met = set(data.pop("_met", []))
    for key, value in data.items():
        setattr(economy, key, set(value) if key in SET_FIELDS else value)
    return clock, met


def summary(slot):
    """A line for the title screen: the money and day of the slot, or that it is empty."""
    try:
        data = json.loads(slot_path(slot).read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return f"Slot {slot}: empty"
    day = data.get("_clock", 0) // DAY_FRAMES + 1
    return f"Slot {slot}: day {day}   ${data.get('money', 0)}   caught {data.get('total_caught', 0)}"

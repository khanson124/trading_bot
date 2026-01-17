import json
import os
from datetime import datetime, timezone

STATE_PATH = os.path.join("logs", "state.json")

def _load_state():
    if not os.path.exists(STATE_PATH):
        return {}
    with open(STATE_PATH, "r", encoding="utf-8") as f:
        return json.load(f)

def _save_state(state: dict):
    os.makedirs("logs", exist_ok=True)
    with open(STATE_PATH, "w", encoding="utf-8") as f:
        json.dump(state, f, indent=2)

def already_traded_today(symbol: str) -> bool:
    state = _load_state()
    key = f"{symbol}_last_trade_date"
    last = state.get(key)
    today = datetime.now(timezone.utc).date().isoformat()
    return last == today

def mark_traded_today(symbol: str):
    state = _load_state()
    key = f"{symbol}_last_trade_date"
    state[key] = datetime.now(timezone.utc).date().isoformat()
    _save_state(state)

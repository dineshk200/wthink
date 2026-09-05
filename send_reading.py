"""
ThingSpeak single-update sender with SIMULATED DRIFT PATTERN.
No fetching from ThingSpeak -- state (current value + trend) is kept in
state.json inside this repo, which the GitHub Actions workflow commits
back after every run.

Pattern: each field moves in the same direction (up/down/flat) for a
run of 3-4 readings, then picks a new direction -- similar to a real
drifting sensor rather than pure random noise each time.
"""

import json
import os
import random
from datetime import datetime
import requests

WRITE_API_KEY = "1PB3KHDRUTOQIZCH"     # your ThingSpeak Write API key
WRITE_URL = "https://api.thingspeak.com/update"
STATE_FILE = "state.json"

# name: (min, max, step_size, decimal_places)
FIELD_CONFIG = {
    "field1": (7.10, 7.65, 0.02, 2),    # pH
    "field3": (0.30, 0.40, 0.004, 6),
    "field4": (25, 40, 1.2, 6),
}

def load_state():
    if os.path.exists(STATE_FILE):
        with open(STATE_FILE, "r") as f:
            return json.load(f)
    return {}

def save_state(state):
    with open(STATE_FILE, "w") as f:
        json.dump(state, f, indent=2)

def init_field_state(min_v, max_v):
    return {
        "value": round((min_v + max_v) / 2, 6),
        "direction": random.choice([-1, 0, 1]),
        "remaining": random.randint(3, 4),
    }

def next_value(field_name, state, min_v, max_v, step_size, decimals):
    fs = state.get(field_name, init_field_state(min_v, max_v))

    # time to pick a new direction / run length
    if fs["remaining"] <= 0:
        fs["direction"] = random.choice([-1, 0, 1])  # down, flat, up
        fs["remaining"] = random.randint(3, 4)

    move = fs["direction"] * step_size * random.uniform(0.7, 1.3)
    new_value = fs["value"] + move

    # if it hits an edge, clamp and force a direction change next time
    if new_value >= max_v:
        new_value = max_v
        fs["remaining"] = 0
    elif new_value <= min_v:
        new_value = min_v
        fs["remaining"] = 0
    else:
        fs["remaining"] -= 1

    new_value = round(new_value, decimals)
    fs["value"] = new_value
    state[field_name] = fs
    return new_value

def main():
    state = load_state()

    field1 = next_value("field1", state, *FIELD_CONFIG["field1"])
    field2 = 0
    field3 = next_value("field3", state, *FIELD_CONFIG["field3"])
    field4 = next_value("field4", state, *FIELD_CONFIG["field4"])
    field5 = 25   # constant temperature

    save_state(state)

    # force exactly 6 decimal places for field3/field4 (e.g. 0.340000, not 0.34)
    field3_str = f"{field3:.6f}"
    field4_str = f"{field4:.6f}"

    params = {
        "api_key": WRITE_API_KEY,
        "field1": field1,
        "field2": field2,
        "field3": field3_str,
        "field4": field4_str,
        "field5": field5,
    }

    response = requests.get(WRITE_URL, params=params, timeout=15)
    ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    if response.status_code == 200 and response.text != "0":
        print(f"[{ts}] Sent OK | entry_id={response.text} | "
              f"field1={field1} field2={field2} field3={field3_str} field4={field4_str} field5={field5}")
    else:
        print(f"[{ts}] ThingSpeak returned: {response.text} "
              f"(0 usually means rate limit hit or wrong API key)")

if __name__ == "__main__":
    main()

"""
ThingSpeak multi-channel sender with SIMULATED DRIFT PATTERN.
Each channel has its own API key and its own independent drift state
(kept in state.json), so every channel shows different readings
in the same format.
"""

import json
import os
import random
import time
from datetime import datetime
import requests

WRITE_URL = "https://api.thingspeak.com/update"
STATE_FILE = "state.json"

# name -> write API key. Add more channels here if needed.
CHANNELS = {
    "channel1": "1PB3KHDRUTOQIZCH",
    "channel2": "IDTILLJTR5XX1C0Q",
}

# name: (min, max, step_size, decimal_places)
FIELD_CONFIG = {
    "field1": (7.10, 7.65, 0.02, 2),    # pH
    "field3": (0.02, 0.04, 0.0006, 6),
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
        "value": round(random.uniform(min_v, max_v), 6),
        "direction": random.choice([-1, 0, 1]),
        "remaining": random.randint(3, 4),
    }

def next_value(field_name, state, min_v, max_v, step_size, decimals):
    fs = state.get(field_name, init_field_state(min_v, max_v))

    if fs["remaining"] <= 0:
        fs["direction"] = random.choice([-1, 0, 1])
        fs["remaining"] = random.randint(3, 4)

    move = fs["direction"] * step_size * random.uniform(0.7, 1.3)
    new_value = fs["value"] + move

    if new_value >= max_v:
        new_value = max_v - random.uniform(0.00001, step_size)
        fs["remaining"] = 0
    elif new_value <= min_v:
        new_value = min_v + random.uniform(0.00001, step_size)
        fs["remaining"] = 0
    else:
        fs["remaining"] -= 1

    new_value = round(new_value, decimals)
    fs["value"] = new_value
    state[field_name] = fs
    return new_value

def send_channel(name, api_key, all_state):
    if api_key.startswith("PUT_"):
        print(f"[{name}] API key not set, skipping.")
        return

    ch_state = all_state.setdefault(name, {})

    field1 = next_value("field1", ch_state, *FIELD_CONFIG["field1"])
    field3 = next_value("field3", ch_state, *FIELD_CONFIG["field3"])
    field4 = next_value("field4", ch_state, *FIELD_CONFIG["field4"])

    params = {
        "api_key": api_key,
        "field1": field1,
        "field2": 0,
        "field3": f"{field3:.6f}",
        "field4": f"{field4:.6f}",
        "field5": 25,
    }

    try:
        response = requests.get(WRITE_URL, params=params, timeout=15)
        ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        if response.status_code == 200 and response.text != "0":
            print(f"[{ts}] [{name}] Sent OK | entry_id={response.text} | "
                  f"f1={field1} f3={params['field3']} f4={params['field4']}")
        else:
            print(f"[{ts}] [{name}] ThingSpeak returned: {response.text}")
    except requests.exceptions.RequestException as e:
        print(f"[{name}] Network error: {e}")

def main():
    state = load_state()
    for i, (name, key) in enumerate(CHANNELS.items()):
        if i > 0:
            time.sleep(2)   # small gap between channels
        send_channel(name, key, state)
    save_state(state)

if __name__ == "__main__":
    main()

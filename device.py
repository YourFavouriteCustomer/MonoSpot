import json
from typing import Any

import tinytuya
import os

from dotenv import load_dotenv

TUYA_CLOUD = None
ORIGINAL_STATE = ""

load_dotenv()

def get_cloud():
    global TUYA_CLOUD
    if TUYA_CLOUD is None:
        TUYA_CLOUD = tinytuya.Cloud(
            apiRegion=os.getenv('TUYA_API_REGION'),
            apiKey=os.getenv('TUYA_API_KEY'),
            apiSecret=os.getenv('TUYA_API_SECRET')
        )
    return TUYA_CLOUD


def make_scene_units(palette: list[list[int | float | Any]]):
    scene_units = list()
    for color in palette:
        h, s, v, area = color
        unit = {
            "bright": 0,
            "temperature": 0,
            "h": h,
            "s": s,
            "v": v,
            "unit_change_mode": "gradient",
            "unit_gradient_duration": 100 - area,
            "unit_switch_duration": 0
        }
        scene_units.append(unit)

    return scene_units


def send_new_scene(device_id: str, palette: list[list[int | float | Any]]):
    c = get_cloud()
    commands = {
        "commands": [
            {"code": "switch_led", "value": True},
            {"code": "scene_data_v2", "value":
                {"scene_num": 8,
                 "scene_units": make_scene_units(palette)
                 }
             },
        ]
    }

    result = c.sendcommand(device_id, commands)
    print(result)


def get_original_state(device_id: str):
    global ORIGINAL_STATE
    c = get_cloud()
    data = c.getstatus(device_id)
    if data["success"] is not True:
        raise Exception("Original state not received")
    ORIGINAL_STATE = data["result"]

    # The return response is bad: scene_data_v2 and colour_data_v2 should have JSON in values,
    # but they are returned as strings. It's necessary to convert them to proper types.
    i = 0
    while i < len(ORIGINAL_STATE):
        state = ORIGINAL_STATE[i]
        value = state["value"]
        if isinstance(value, str):
            if value.startswith("AA") or value == "": # Also, filtering out garbage data and empty strings
                del ORIGINAL_STATE[i]
                continue
            try:
                state["value"] = json.loads(value)
            except json.JSONDecodeError:
                pass
        i += 1


def send_original_state(device_id: str):
    global ORIGINAL_STATE
    c = get_cloud()
    command = {"commands": ORIGINAL_STATE}
    result = c.sendcommand(device_id, command)
    print(result)
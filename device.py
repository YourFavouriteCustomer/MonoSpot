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

    # The return response is bad: scene_data_v2 and colour_data_v2 should have JSON in values,
    # but they are returned as strings. It is necessary to convert them to proper types.
    status_map = {}
    for state in data["result"]:
        code = state["code"]
        value = state["value"]
        if isinstance(value, str):
            if value.startswith("AA") or value == "":
                continue
            try:
                value = json.loads(value)
            except json.JSONDecodeError:
                pass
        status_map[code] = value

    if status_map.get("switch_led") is False:
        ORIGINAL_STATE = [{"code": "switch_led", "value": False}]
        return

    mode_codes = {
        "white": ["switch_led", "work_mode", "bright_value_v2", "temp_value_v2"],
        "colour": ["switch_led", "work_mode", "colour_data_v2"],
        "scene": ["switch_led", "work_mode", "scene_data_v2"],
    }
    work_mode = str(status_map.get("work_mode", ""))
    allowed_codes = mode_codes.get(work_mode, ["switch_led", "work_mode"])

    ORIGINAL_STATE = [
        {"code": code, "value": status_map[code]}
        for code in allowed_codes
        if code in status_map
    ]


def send_original_state(device_id: str):
    global ORIGINAL_STATE
    c = get_cloud()
    command = {"commands": ORIGINAL_STATE}
    result = c.sendcommand(device_id, command)
    print(result)
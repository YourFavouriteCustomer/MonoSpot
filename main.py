from typing import Any

import aiohttp
import spotipy
from spotipy.oauth2 import SpotifyOAuth
import os
from dotenv import load_dotenv
import piexif

import ast
from color_extractor import get_palette, convert_to_rgb
from device import send_new_scene, get_original_state, send_original_state

import asyncio

load_dotenv()

pause_event = asyncio.Event()
pause_event.set()

status = None
previous_status = None
image_id = "0"
current_palette = None
timeout = 2

scope = "user-read-playback-state"
sp = spotipy.Spotify(auth_manager=SpotifyOAuth(scope=scope, client_id=os.getenv('SPOTIFY_CLIENT_ID'),
                                               client_secret=os.getenv('SPOTIFY_CLIENT_SECRET'),
                                               redirect_uri=os.getenv('REDIRECT_URI')))


async def spotify_loop():
    """Continuously fetches the current playing song and updates the light color."""
    global status, timeout
    while True:
        await pause_event.wait()
        await get_spotify_track()
        if status is None:
            timeout = 5
        else:
            timeout = 2
        await asyncio.sleep(timeout)


async def fetch_spotify_data() -> dict | None:
    max_retries = 5
    for attempt in range(max_retries):
        try:
            result = await asyncio.to_thread(sp.current_playback)
            if result is not None:
                return result
            else:
                return None
        except spotipy.SpotifyException as e:
            print(f"Spotify API Error: {e}. Retrying in {2 ** attempt} seconds...")
        except Exception as e:
            print(f"Unexpected Error: {e}. Retrying in {2 ** attempt} seconds...")

        await asyncio.sleep(2 ** attempt)

    return None


async def get_spotify_track():
    global status, previous_status, image_id, current_palette
    result = await fetch_spotify_data()
    device_id = os.getenv('TUYA_DEVICE_ID')
    if device_id is None:
        raise ValueError("TUYA_DEVICE_ID not set")

    # Haven't played anything in a while or local files are being played
    if result is None or result["item"] is None or result["item"]["is_local"] is False:
        status = None
    else:
        status = result["is_playing"]

        if len(result["item"]["album"]["images"]) > 0:
            # [1] gives 300x300px. If you want to save on space, go with [0]. If you want higher quality album art, go with [2]
            image_url = result["item"]["album"]["images"][1]["url"]
            new_image_id = image_url.split("/")[-1]
            image_path = f"./images/{new_image_id}.jpg"

            if not os.path.isfile(image_path):
                await get_image(image_path, image_url, result)

            artist, title, palette = get_metadata(image_path)
            current_palette = palette

            if image_id != new_image_id:
                print(f"{artist} - {title}", end="  ")
                await asyncio.to_thread(send_new_scene, device_id, palette)
                image_id = new_image_id

    if status != previous_status:
        if status is True and previous_status is not True and current_palette is not None:
            await asyncio.to_thread(send_new_scene, device_id, current_palette)
        elif status is not True and previous_status is True:
            await asyncio.to_thread(send_original_state, device_id)
        previous_status = status


async def get_image(image_path: str, image_url: str, result: dict):
    pause_event.clear()

    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(image_url) as response:
                response.raise_for_status()
                image_data = await response.read()

        with open(image_path, 'wb') as handler:
            handler.write(image_data)

        artist = get_artists(result["item"]["album"]["artists"])
        name = result["item"]["album"]["name"]
        palette = get_palette(image_path)
        palette = bonus_for_vibrance(palette)
        add_metadata(image_path, artist, name, palette)
    finally:
        pause_event.set()


def get_artists(artists: list[dict]):
    artists = [artist["name"] for artist in artists]
    string = ", ".join(artists)
    return string


def add_metadata(image_path: str, artist: str, name: str, palette: list[list[int | float | Any]]):
    exif_dict = piexif.load(image_path)

    exif_dict["0th"][piexif.ImageIFD.Artist] = artist.encode("utf-8")
    exif_dict["0th"][piexif.ImageIFD.ImageDescription] = name.encode("utf-8")

    string = "["
    for i in range(min(len(palette), 8)):
        h, s, v, area = palette[i]
        if round(area) < 1:
            break
        string += f"[{round(h)}, {round(s)}, {round(v)}, {round(area)}], "
    string += "]"

    exif_dict["Exif"][piexif.ExifIFD.UserComment] = string.encode("utf-8")

    exif_bytes = piexif.dump(exif_dict)
    piexif.insert(exif_bytes, image_path)


def get_metadata(image_path: str) -> tuple[str, str, list[list[int | float | Any]]]:
    exif_dict = piexif.load(image_path)

    artist = exif_dict["0th"].get(piexif.ImageIFD.Artist, b"").decode("utf-8")
    title = exif_dict["0th"].get(piexif.ImageIFD.ImageDescription, b"").decode("utf-8")
    comment = exif_dict["Exif"].get(piexif.ExifIFD.UserComment, b"").decode("utf-8")
    palette = ast.literal_eval(comment) if comment else []

    return artist, title, palette


def bonus_for_vibrance(palette: list[list[int | float | Any]]):
    actual_area = 0
    for color in palette:
        lowering_coefficient = 0.8
        saturation = color[1] ** lowering_coefficient + 0.01
        value = color[2] ** lowering_coefficient + 0.01
        bonus = saturation * value
        color[3] *= bonus
        actual_area += color[3]

    if actual_area == 0:
        return palette
    for color in palette:
        color[3] /= actual_area / 100

    palette.sort(key=lambda x: x[3], reverse=True)

    return palette

async def main():
    os.makedirs("images", exist_ok=True)

    device_id = os.getenv('TUYA_DEVICE_ID')
    if device_id:
        await asyncio.to_thread(get_original_state, device_id)

    await spotify_loop()


if __name__ == "__main__":
    asyncio.run(main())

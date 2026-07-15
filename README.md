# LightSpot - Spotify to Tuya Light Sync

Syncs Tuya smart lights with your currently playing Spotify track by extracting colors from album art.

## How It Works

- Polls Spotify API for the currently playing track
- Downloads album art and extracts dominant colors using MeanShift clustering
- Sends color scene to Tuya device via cloud API
- Caches color palettes in image EXIF data for faster subsequent loads
- Restores original light state when playback is paused or local files are played

## Requirements

- Python 3.10+
- Spotify Developer account (for API credentials)
- Tuya IoT platform account (for device control)

### Python Dependencies

```
spotipy
aiohttp
tinytuya
piexif
opencv-python
scikit-learn
numpy
python-dotenv
```

Install with:
```bash
pip install -r requirements.txt
```

## Setup

### 1. Spotify API

1. Go to [Spotify Developer Dashboard](https://developer.spotify.com/dashboard)
2. Create a new app
3. Add a redirect URI (e.g., `http://127.0.0.1:8888`)
4. Add your Client ID and Client Secret to `.env` file

### 2. Tuya API

1. Go to [Tuya IoT Platform](https://iot.tuya.com/)
2. Create a cloud project
3. Get your API Key, API Secret, and Device ID
4. Note your region (e.g., `eu`, `us`, `cn`)
5. Add them to your `.env` file

### 3. Install dependencies

Install with:
```bash
pip install -r requirements.txt
```

## Usage

```bash
python main.py
```

The script will:
1. Create an `images/` directory for caching album art
2. Fetch your Tuya device's current state
3. Start polling Spotify for track changes

## Limitations

- Local files: Lights restore to original state (no album art available from Spotify API)
- Requires active internet connection for both Spotify and Tuya APIs
- First-time Spotify authentication requires browser interaction
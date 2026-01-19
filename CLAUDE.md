# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Accent is a smart e-paper picture frame. A Python/Flask server generates and serves images to an ESP32 client that displays them on Waveshare e-paper displays. The device wakes periodically, fetches a new image, displays it, then deep sleeps to conserve power.

## Build Commands

### Server
```bash
cd server
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt  # Also builds the C dithering extension
python main.py                   # Runs on localhost:8080
```

### Client (ESP32)
```bash
cd client
pio run -e release --upload-port /dev/cu.usbserial-XXXXX -t upload
pio device monitor --baud 115200  # View serial output
```

### Display Configuration
Set display type in `client/platformio.ini` build_flags:
- `DISPLAY_GDEW075Z08` - 7.5" 800x480 3-color (default)
- `DISPLAY_GDEW075Z09` - 7.5" 640x384 3-color
- `DISPLAY_GDEH075Z90` - 7.5" 880x528 3-color
- `DISPLAY_GDEY1248Z51` - 12.48" 1304x984 3-color
- `DISPLAY_GDEY073D46` - 7.3" 800x480 7-color

## Architecture

### Client (C++/Arduino)
- `Client.cpp` - Main loop: wake → connect WiFi → download image → display → query sleep time → deep sleep
- `Display.cpp` - GxEPD2 library wrapper for e-paper rendering
- `Network.cpp` - WiFi connection, HTTP client, WiFi setup AP server
- `Power.cpp` - Deep sleep management

The client streams image data directly to the display buffer (1KB chunks) rather than loading the full image into RAM.

### Server (Python/Flask)
- `main.py` - Flask routes and request handling
- `schedule.py` - Determines which content to show based on cron schedule
- `epd.py` - Image conversion: dithering, color quantization, bit packing for e-paper
- `response.py` - Encodes responses as GIF (browser preview) or binary EPD format
- `dithering_extension/` - C extension for Floyd-Steinberg dithering (performance critical)

Content generators (all implement `image(user, width, height, variant)`):
- `artwork.py` - Random artwork from `assets/artwork/`
- `city.py` - Dynamic scene with weather/time/sun layers
- `weather.py` - OpenWeather API integration
- `google_calendar.py` - Calendar event display
- `wittgenstein.py` - Philosophy quotes

### Image Pipeline
1. Request arrives with `width`, `height`, `variant` (color mode)
2. Schedule determines content type based on time/cron
3. Content generator creates PIL Image
4. Dithering reduces to e-paper palette (C extension)
5. Bit packing: 2 bits/pixel for BWR, 4 bits/pixel for 7-color
6. Streamed to client as binary EPD or GIF for testing

### Key Endpoints
- `/epd?width=800&height=480&variant=bwr` - Binary image for e-paper
- `/gif?width=800&height=480&variant=bwr` - GIF preview for browser testing
- `/next` - Milliseconds until next scheduled refresh
- `/hello/<key>` - User settings web UI

## Client-Server Communication

- Client authenticates via Basic Auth header with WiFi MAC address (colons removed)
- Server looks up user data in Firestore by MAC address
- Currently using hardcoded test user (Cambridge, MA) with Firebase disabled

## WiFi Setup Flow

On first boot or GPIO10-to-GND reset:
1. Device creates "AccentSetup" WiFi AP at IP 1.2.3.4
2. User connects and visits `http://1.2.3.4/go`
3. Submits WiFi credentials via form
4. Device saves to NVS, restarts, connects to network

## Static Image Generation

`server/client_image.py` converts GIF images to C headers for client-side error/setup screens:
```bash
python client_image.py assets/error.gif ../client/include/ErrorImage.h
```

## Server

A Flask server that generates and serves images to ESP32 devices driving Waveshare e-paper displays.

Entry point: [`main.py`](main.py)

### Prerequisites

- Python 3.13+
- A C compiler (for the dithering extension)

### Setup

1. Create and activate a virtual environment:

```bash
cd server
python -m venv .venv
source .venv/bin/activate
```

2. Install dependencies (this also builds the dithering C extension):

```bash
pip install -r requirements.txt
```

### Running the Server

```bash
source .venv/bin/activate
python main.py
```

The server will start on port 8080 and be available at:
- http://127.0.0.1:8080 (localhost)
- http://<your-local-ip>:8080 (for ESP32 devices on your network)

### Endpoints

| Endpoint | Description |
|----------|-------------|
| `/epd` | E-paper display format (for ESP32 client) |
| `/gif` | GIF format (for browser preview) |
| `/next` | Returns milliseconds until next image refresh |
| `/wittgenstein` | Philosophy quotes |
| `/city` | City/weather images |
| `/artwork` | Artwork images |
| `/calendar` | Google Calendar events |
| `/hello/<key>` | User settings page |

Query parameters for image endpoints:
- `width` - Display width in pixels
- `height` - Display height in pixels
- `variant` - Display color variant (e.g., `bwr` for black/white/red)

### Regular Flow

```
┌────────────┐       ┌────────────┐       ┌────────────┐
│   Client   │       │ App Engine │       │ Firestore  │
└─────┬──────┘       └─────┬──────┘       └─────┬──────┘
      │                    │                    │
      ├───┐                │                    │
      │   │ Wake           │                    │
      │◀──┘                │                    │
      │                    │                    │
      │  /epd (Key, Size)  │                    │
      ├───────────────────▶├─┐ Schedule (User)  │
      │                    │ ├─────────────────▶├─┐
      │                    │ │                  │ │
      │                    │ │    User Data     │ │
      │   Content Image    │ │◁ ─ ─ ─ ─ ─ ─ ─ ─ ┼─┘
      │◁ ─ ─ ─ ─ ─ ─ ─ ─ ─ ┼─┘                  │
      │                    │                    │
      ├───┐                │                    │
      │   │ Display        │                    │
      │◀──┘                │                    │
      │                    │                    │
      │    /next (Key)     │                    │
      ├───────────────────▶├─┐ Schedule (User)  │
      │                    │ ├─────────────────▶├─┐
      │                    │ │                  │ │
      │                    │ │    User Data     │ │
      │     Sleep Time     │ │◁ ─ ─ ─ ─ ─ ─ ─ ─ ┼─┘
      │◁ ─ ─ ─ ─ ─ ─ ─ ─ ─ ┼─┘                  │
      │                    │                    │
      ├───┐                │                    │
      │   │ Sleep          │                    │
      │◀──┘                │                    │
      │                    │                    │
```

### New User Flow

```
┌────────────┐       ┌────────────┐       ┌────────────┐       ┌────────────┐
│   Client   │       │ App Engine │       │ Firestore  │       │  Browser   │
└─────┬──────┘       └─────┬──────┘       └─────┬──────┘       └─────┬──────┘
      │                    │                    │                    │
      ├───┐                │                    │                    │
      │   │ Wake           │                    │                    │
      │◀──┘                │                    │                    │
      │                    │                    │                    │
      │  /epd (Key, Size)  ├─┐ Schedule (User)  │                    │
      ├───────────────────▶│ ├─────────────────▶├─┐                  │
      │                    │ │                  │ │                  │
      │                    │ │      Error       │ │                  │
      │ Settings URL Image │ │x ─ ─ ─ ─ ─ ─ ─ ─ ┼─┘                  │
      │◁ ─ ─ ─ ─ ─ ─ ─ ─ ─ ┼─┘                  │                    │
      │                    │                    │                    │
      ├───┐                │                    │                    │
      │   │ Display        │                    │                    │
      │◀──┘                │                    │       Settings URL │
      │                    │                    │     ○─────────────▶├─┐
      ├───┐                │                    │                    │ │
      │   │ Sleep          │                    │     User Data      │ │
      │◀──┘                │                    │◁ ─ ─ ─ ─ ─ ─ ─ ─ ─ ┼─┘
      │                    │                    │                    │
   ┌──┴────────────────────┴────────────────────┴────────────────────┴──┐
   │                                                                    │
   │                            Regular Flow                            │
   │                                                                    │
   └──┬────────────────────┬────────────────────┬────────────────────┬──┘
      │                    │                    │                    │
```

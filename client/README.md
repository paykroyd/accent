## Client

ESP32 firmware that fetches images from the server and displays them on a Waveshare e-paper display.

Entry point: [`Client.cpp`](src/Client.cpp)

### Prerequisites

- [PlatformIO](https://platformio.org/) (install via `brew install platformio` or from platformio.org)
- ESP32 dev board connected via USB
- Waveshare e-paper display (7.5" 800x480 3-color by default)

### Configuration

1. Update the server IP address in `src/Client.cpp`:

```cpp
const String kBaseUrl = "http://<YOUR_SERVER_IP>:8080";
```

2. If using a different display, uncomment the appropriate line in `platformio.ini`:

```ini
build_flags =
    ; -DDISPLAY_GDEW075Z09   ; 7.5" 640x384 3-color
    -DDISPLAY_GDEW075Z08    ; 7.5" 800x480 3-color (default)
    ; -DDISPLAY_GDEH075Z90   ; 7.5" 880x528 3-color
    ; -DDISPLAY_GDEY1248Z51  ; 12.48" 1304x984 3-color
    ; -DDISPLAY_GDEY073D46   ; 7.3" 800x480 7-color
```

### Building and Flashing

1. Find your ESP32's serial port:

```bash
ls /dev/cu.usb*
```

2. Build and upload the firmware:

```bash
cd client
pio run -e release --upload-port /dev/cu.usbserial-XXXXX -t upload
```

3. Monitor serial output (optional):

```bash
pio device monitor --baud 115200 --port /dev/cu.usbserial-XXXXX
```

### WiFi Setup

On first boot (or after a WiFi reset), the device will:

1. Create an access point named **AccentSetup**
2. Display the setup URL on the e-paper display
3. Connect to the AP and visit `http://1.2.3.4/go` to enter WiFi credentials
4. The device will restart and connect to your network

### Resetting WiFi

To clear stored WiFi credentials and trigger the setup flow again, connect GPIO pin 10 to GND during boot.

### Regular Flow

```
┌────────────┐       ┌────────────┐       ┌────────────┐
│   Server   │       │   ESP32    │       │  Display   │
└─────┬──────┘       └─────┬──────┘       └─────┬──────┘
      │                    │                    │
      │                    ├───┐                │
      │                    │   │ Wake           │
      │                    │◀──┘                │
      │                    │                    │
      │                    ├───┐                │
      │                    │   │ Connect Wifi   │
      │                    │◀──┘                │
      │  /epd (Key, Size)  │                    │
    ┌─┤◀───────────────────┤                    │
    │ │                    │                    │
    │ │       Image        │                    │
    └─┼ ─ ─ ─ ─ ─ ─ ─ ─ ─ ▷│                    │
      │                    │    Show (Image)    │
      │                    ├───────────────────▶├─┐
      │                    │                    │ │
      │                    │                    │ │
      │                    │◁ ─ ─ ─ ─ ─ ─ ─ ─ ─ ┼─┘
      │    /next (Key)     │                    │
    ┌─┤◀───────────────────┤                    │
    │ │                    │                    │
    │ │     Sleep Time     │                    │
    └─┼ ─ ─ ─ ─ ─ ─ ─ ─ ─ ▷│                    │
      │                    │                    │
      │                    ├───┐                │
      │                    │   │ Sleep          │
      │                    │◀──┘                │
      │                    │                    │

```

### New Wifi Flow

```
┌────────────┐       ┌────────────┐       ┌────────────┐
│  Browser   │       │   ESP32    │       │  Display   │
└─────┬──────┘       └─────┬──────┘       └─────┬──────┘
      │                    │                    │
      │                    ├───┐                │
      │                    │   │ Wake           │
      │                    │◀──┘                │
      │                    │                    │
      │                    ├───┐                │
      │                    │   │ Connect Wifi   │
      │                    │x──┘                │
      │                    │                    │
      │                    │   Show (AP URL)    │
      │                    ├───────────────────▶├─┐
      │                    │                    │ │
      │                    │                    │ │
      │                    │◁ ─ ─ ─ ─ ─ ─ ─ ─ ─ ┼─┘
      │                    │                    │
      │                    ├───┐                │
      │                    │   │ Start AP       │
      │  AP URL            │◀──┘                │
    ┌─┤◀────────○          │                    │
    │ │                    │                    │
    │ │  Wifi Credentials  │                    │
    └─┤─ ─ ─ ─ ─ ─ ─ ─ ─ ─▷│                    │
      │                    │                    │
      │                    ├───┐                │
      │                    │   │ Restart        │
      │                    │◀──┘                │
      │                    │                    │
   ┌──┴────────────────────┴────────────────────┴──┐
   │                                               │
   │                 Regular Flow                  │
   │                                               │
   └──┬────────────────────┬────────────────────┬──┘
      │                    │                    │
```

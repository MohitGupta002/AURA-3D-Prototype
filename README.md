# 🧠 AURA-3D Prototype

> **Control 3D objects in Blender using hand gestures** — captured by a webcam, processed with MediaPipe AI, and streamed to Blender in real-time via UDP.

![Python](https://img.shields.io/badge/Python-3.10+-blue?logo=python&logoColor=white)
![Blender](https://img.shields.io/badge/Blender-4.x-orange?logo=blender&logoColor=white)
![MediaPipe](https://img.shields.io/badge/MediaPipe-0.10+-green?logo=google&logoColor=white)
![License](https://img.shields.io/badge/License-MIT-yellow)

---

## 🔄 How It Works

```
┌─────────────────────────────┐                    ┌──────────────────────────────┐
│                             │    UDP packets     │                              │
│  WEBCAM + MediaPipe AI      │  ─────────────►   │  BLENDER                     │
│  (aura_npu.py)              │   JSON over UDP    │  (gesture_bridge.py)         │
│                             │   localhost:9090   │                              │
│  • Hand landmark detection  │                    │  • UDP Listener              │
│  • Gesture classification   │                    │  • Coordinate Mapping        │
│  • Real-time tracking       │                    │  • Lerp Smoothing            │
│                             │                    │  • Action Dispatch           │
└─────────────────────────────┘                    └──────────────────────────────┘
```

1. A **webcam** captures your hand movements
2. **MediaPipe AI** detects 21 hand landmarks and classifies gestures
3. Gesture data is sent as **JSON over UDP** to Blender
4. **Blender** receives the data and translates it into 3D actions — moving, scaling, recoloring objects, and orbiting the camera

---

## 📁 Project Structure

```
AURA-3D Prototype/
│
├── aura_main.py               # ⭐ Master Controller — launch everything from here
├── aura_npu.py                # Webcam → MediaPipe → UDP sender
├── config.py                  # Shared configuration (port, lerp, gestures)
├── diagnose_aura.py           # System diagnostic tool
├── requirements               # Python dependencies
│
├── blender_scripts/           # Scripts that run INSIDE Blender
│   ├── startup_aura.py        # Auto-loader for Blender startup
│   ├── scene_setup.py         # Scene preparation (adds Suzanne model)
│   ├── gesture_bridge.py      # ⭐ Main bridge — gesture → 3D action
│   ├── udp_server.py          # Standalone UDP listener
│   └── modal_listener.py      # Non-blocking loop demo
│
├── external/                  # Scripts that run OUTSIDE Blender
│   └── test_sender.py         # Simulates gesture data for testing
│
├── npu_pipeline/              # AI pipeline components
│   ├── hand_landmarker.task   # MediaPipe hand landmark model
│   ├── main.py                # Standalone gesture demo
│   ├── test_camera.py         # Camera test utility
│   └── requirements.txt       # Pipeline-specific dependencies
│
└── docs/
    └── protocol.md            # UDP protocol specification
```

---

## ✅ Prerequisites

| Requirement | Version | Notes |
|-------------|---------|-------|
| **Python** | 3.10+ | For webcam tracking pipeline |
| **Blender** | 4.x | For 3D model manipulation |
| **Webcam** | Any | Built-in or USB camera |
| **OS** | Windows 10/11 | Tested on Windows |

---

## 🛠️ Setup

### 1. Clone the Repository
```bash
git clone https://github.com/Mohitgupta002/AURA-3D-Prototype.git
cd AURA-3D-Prototype
```

### 2. Create Virtual Environment & Install Dependencies
```bash
python -m venv venv
.\venv\Scripts\activate        # Windows
pip install -r requirements
```

### 3. Download Hand Landmark Model (if not included)
```bash
python -c "import urllib.request; urllib.request.urlretrieve('https://storage.googleapis.com/mediapipe-models/hand_landmarker/hand_landmarker/float16/latest/hand_landmarker.task', 'npu_pipeline/hand_landmarker.task')"
```

---

## 🚀 How to Run

### Option A: Interactive Launcher (Recommended)
```bash
python aura_main.py
```
This opens a menu where you can:
1. **Launch Blender** — auto-loads the scene and gesture bridge
2. **Start NPU Pipeline** — opens webcam and starts tracking
3. **Run Simulation** — sends test gesture data without a webcam

### Option B: Command Line
```bash
python aura_main.py --blender --npu    # Launch both at once
python aura_main.py --blender          # Blender only
python aura_main.py --npu              # Camera only
python aura_main.py --sim              # Simulation only
```

### Inside Blender
1. Press **N** in the 3D Viewport → select **"Aura-3D"** tab
2. Click **"Start Bridge"**
3. Your hand gestures will now control the 3D model!

---

## 🖐️ Gesture Controls

| Gesture | Detection | Blender Action |
|---------|-----------|----------------|
| ✋ **Open Hand** | Hand open, fingers extended | **Translate** object |
| 🤏 **Pinch** | Thumb + Index finger close | **Scale** object |
| ✊ **Fist** | All fingers curled | **Cycle color** |
| 🖐️ **Palm** | Open palm facing camera | **Orbit camera** |

---

## 📡 UDP Protocol

Every packet is a JSON string sent over UDP to `localhost:9090`:

```json
{
    "gesture":    "MOVE",
    "xyz":        [0.5, 0.2, 0.0],
    "confidence": 0.95
}
```

| Field | Type | Range | Description |
|-------|------|-------|-------------|
| `gesture` | string | `MOVE`, `PINCH`, `FIST`, `PALM` | Detected hand gesture |
| `xyz` | float[3] | `0.0 – 1.0` | Normalized hand position |
| `confidence` | float | `0.0 – 1.0` | AI confidence score |

---

## ⚙️ Configuration

All settings are in `config.py`:

```python
HOST = "127.0.0.1"       # Network address
PORT = 9090              # UDP port
LERP_FACTOR = 0.15       # Smoothing (0=frozen, 1=instant)
TIMER_INTERVAL = 0.016   # Poll rate (~60 Hz)
WORLD_MIN = -5.0         # 3D movement bounds
WORLD_MAX = 5.0
```

---

## 🛠 Troubleshooting

| Problem | Solution |
|---------|----------|
| Camera not opening | Close other apps using webcam (Zoom, Teams, etc.) |
| No movement in Blender | Ensure "Start Bridge" is clicked AND `aura_npu.py` is running |
| "Address already in use" | Change `PORT` in `config.py` or close previous sessions |
| Object doesn't move | Click on Suzanne to make her the **active object** |
| MediaPipe import error | Ensure `mediapipe>=0.10.14` is installed in venv |

---

## 🧪 Tech Stack

- **MediaPipe Tasks API** — Hand landmark detection (21 keypoints)
- **OpenCV** — Camera capture and visualization
- **Blender Python API (bpy)** — 3D scene manipulation
- **UDP Sockets** — Low-latency gesture data streaming
- **Linear Interpolation (Lerp)** — Smooth, cinematic movement

---

## 📄 License

MIT License — Part of the **Aura-3D** project.

---

Built with 🐍 Python, 🎨 Blender, and 🤖 MediaPipe AI.

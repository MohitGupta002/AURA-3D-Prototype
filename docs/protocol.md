# Aura-3D Communication Protocol

## Overview
All communication between the **NPU Gesture Pipeline** (external) and the **Blender Bridge** uses **UDP datagrams** containing UTF-8 encoded JSON.

| Parameter | Value |
|-----------|-------|
| Transport | UDP |
| Host | `127.0.0.1` (localhost) |
| Port | `5005` |
| Encoding | UTF-8 JSON |
| Max Payload | 1024 bytes |

## Message Schema

```json
{
  "gesture": "<GESTURE_NAME>",
  "xyz": [<x>, <y>, <z>]
}
```

### Fields

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `gesture` | `string` | ✅ | Recognised gesture name (see table below) |
| `xyz` | `float[3]` | ✅ | Normalised screen-space coordinates `[0.0 … 1.0]` |

### Supported Gestures

| Gesture | Blender Action | Description |
|---------|---------------|-------------|
| `PINCH` | `transform.resize` | Scale the active object |
| `FIST` | Change material color | Swap/cycle diffuse color |
| `PALM` | Rotate camera | Orbit camera around origin |
| `MOVE_UP` | Translate +Z | Move active object up |
| `MOVE_DOWN` | Translate -Z | Move active object down |

## Example Messages

```json
{"gesture": "PINCH", "xyz": [0.5, 0.3, 0.0]}
{"gesture": "FIST", "xyz": [0.0, 0.0, 0.0]}
{"gesture": "MOVE_UP", "xyz": [0.5, 0.5, 0.0]}
```

## Notes
- `xyz` values are **normalised** (0.0 = left/bottom, 1.0 = right/top)
- The Blender bridge maps these to World Space `[-5.0 … +5.0]` via `coord_mapper.py`
- All coordinate updates are smoothed with Linear Interpolation (Lerp, `t = 0.15`)

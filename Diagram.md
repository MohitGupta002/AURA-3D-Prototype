# 📐 Project Aura — System Diagrams

A comprehensive collection of UML and architecture diagrams for the Aura-3D gesture-controlled 3D sculpting system.

---

## 1. Use Case Diagram

```mermaid
graph TB
    subgraph Actors
        User["🧑 User"]
        Blender["🟠 Blender"]
        Camera["📷 Webcam"]
    end

    subgraph "Aura-3D System"
        UC1["✋ Air-Draw Shapes via Pinch Gesture"]
        UC2["🖐️ Move 3D Object via Palm Gesture"]
        UC3["✊ Change Object Color via Fist"]
        UC4["🤏 Scale Object via Pinch"]
        UC5["☝️ Erase Last Shape via Point"]
        UC6["🚀 Launch Full System"]
        UC7["🔧 Configure Network Settings"]
        UC8["🧪 Run Test Simulation"]
        UC9["📊 View Shape Classification HUD"]
    end

    User --> UC1
    User --> UC2
    User --> UC3
    User --> UC4
    User --> UC5
    User --> UC6
    User --> UC7
    User --> UC8
    User --> UC9

    UC1 --> Camera
    UC2 --> Camera
    UC3 --> Camera
    UC4 --> Camera
    UC5 --> Camera

    UC1 --> Blender
    UC2 --> Blender
    UC3 --> Blender
    UC4 --> Blender
    UC5 --> Blender
```

---

## 2. System Architecture Diagram

```mermaid
graph LR
    subgraph "NPU Pipeline (aura_npu.py)"
        CAM["📷 Webcam\nOpenCV"]
        MP["🤖 MediaPipe\nHand Landmarker"]
        SC["🔷 Shape Classifier\nv8b"]
        GD["✋ Gesture Detector\nPinch/Fist/Palm/Point"]
    end

    subgraph "Communication"
        UDP["📡 UDP Socket\n127.0.0.1:9090"]
    end

    subgraph "Blender Scripts"
        GB["🌉 Gesture Bridge\ngesture_bridge.py"]
        SS["🎬 Scene Setup\nscene_setup.py"]
        SA["🚀 Startup Aura\nstartup_aura.py"]
        US["🔌 UDP Server\nudp_server.py"]
    end

    subgraph "Blender 3D"
        VP["🖥️ 3D Viewport"]
        NP["📋 N-Panel UI"]
    end

    CAM --> MP
    MP --> GD
    MP --> SC
    GD --> UDP
    SC --> UDP
    UDP --> GB
    GB --> VP
    SA --> SS
    SA --> GB
    US --> NP
```

---

## 3. Class Diagram

```mermaid
classDiagram
    class AuraMain {
        +ROOT_DIR: str
        +BLENDER_PATH: str
        +VENV_PYTHON: str
        +launch_blender()
        +launch_npu()
        +launch_simulation()
        +show_config()
        +clean_port(port)
        +main()
    }

    class AuraNPU {
        +PINCH_START_THRESH: float
        +PINCH_END_THRESH: float
        +MIN_DRAW_POINTS: int
        +MIN_DRAW_TIME: float
        +send_gesture(gesture, xyz, confidence)
        +send_draw_2d(shape, center, size)
        +send_erase()
        +get_distance(p1, p2)
        +classify_shape(points)
        +main()
    }

    class ShapeClassifier {
        +AUTO_CORRECT_THRESHOLD: float
        +CANVAS: int
        +_smooth_points(pts, window)
        +_resample(pts, n)
        +_make_template(shape_name, n)
        +_hu_match(contour, candidates)
        +classify_shape(points)
    }

    class Config {
        +HOST: str
        +PORT: int
        +BUFFER_SIZE: int
        +LERP_FACTOR: float
        +TIMER_INTERVAL: float
        +GESTURE_MOVE: str
        +GESTURE_OPEN: str
        +GESTURE_PINCH: str
        +GESTURE_FIST: str
        +GESTURE_PALM: str
    }

    class GestureBridge {
        +CONFIDENCE_THRESHOLD: float
        +PALM_MOVE_SCALE: float
        +lerp(current, target, factor)
        +lerp_vec(current, target, factor)
        +screen_to_world(value)
        +handle_move(obj, target)
        +handle_pinch(obj, target)
        +handle_fist(obj, target)
        +handle_palm(obj, target)
        +handle_draw_2d(payload)
        +handle_erase()
    }

    class AURA_OT_StartBridge {
        +bl_idname: str
        +bl_label: str
        +execute(context)
    }

    class AURA_OT_StopBridge {
        +bl_idname: str
        +bl_label: str
        +execute(context)
    }

    class AURA_PT_MainPanel {
        +bl_label: str
        +bl_category: str
        +draw(context)
    }

    class SceneSetup {
        +enable_developer_extras()
        +clear_default_objects()
        +add_suzanne(location, rotation, size)
        +setup_viewport()
    }

    class StartupAura {
        +_resolve_project_dirs()
        +_load_module_from_file(name, filepath)
        +run_aura()
    }

    class TestSender {
        +build_sequence()
        +interactive_mode(host, port)
        +main()
    }

    AuraMain --> AuraNPU : launches
    AuraMain --> GestureBridge : launches via Blender
    AuraNPU --> ShapeClassifier : uses
    AuraNPU --> Config : reads
    GestureBridge --> Config : reads
    GestureBridge --> AURA_OT_StartBridge : registers
    GestureBridge --> AURA_OT_StopBridge : registers
    GestureBridge --> AURA_PT_MainPanel : registers
    StartupAura --> SceneSetup : loads
    StartupAura --> GestureBridge : loads
    TestSender --> Config : reads
```

---

## 4. Sequence Diagram — Air-Drawing a Shape

```mermaid
sequenceDiagram
    actor User
    participant Camera as Webcam
    participant MP as MediaPipe
    participant NPU as aura_npu.py
    participant SC as ShapeClassifier
    participant UDP as UDP Socket
    participant Bridge as GestureBridge
    participant Blender as Blender 3D

    User->>Camera: Pinch fingers together
    Camera->>MP: Send RGB frame
    MP->>NPU: Return hand landmarks
    NPU->>NPU: Detect PINCH (dist < 0.045)
    NPU->>NPU: Start recording draw_points[]

    loop While pinching
        User->>Camera: Move hand
        Camera->>MP: Frame
        MP->>NPU: Landmarks
        NPU->>NPU: Append index_tip (x,y)
    end

    User->>Camera: Release pinch
    NPU->>NPU: Stop recording (dist > 0.085)

    NPU->>SC: classify_shape(draw_points)
    SC->>SC: 1. Smooth (moving average)
    SC->>SC: 2. Resample (64 uniform pts)
    SC->>SC: 3. Compute metrics (circ, verts, aspect)
    SC->>SC: 4. Decision tree v8b
    SC->>SC: 5. Hu moment refinement
    SC-->>NPU: Return (SQUARE, center, size, 0.85)

    NPU->>UDP: send_draw_2d("SQUARE", center, size)
    UDP->>Bridge: JSON payload received
    Bridge->>Bridge: handle_draw_2d(payload)
    Bridge->>Blender: _spawn_square(name, pos, size)
    Blender-->>User: 3D square appears in viewport
```

---

## 5. Sequence Diagram — Gesture Control Flow

```mermaid
sequenceDiagram
    actor User
    participant NPU as aura_npu.py
    participant UDP as UDP Socket
    participant Bridge as GestureBridge
    participant Blender as Blender 3D

    alt PALM Gesture
        User->>NPU: Open palm
        NPU->>UDP: {"gesture":"PALM", "xyz":[...]}
        UDP->>Bridge: Dispatch
        Bridge->>Blender: handle_palm() → Move + Orbit camera
    end

    alt FIST Gesture
        User->>NPU: Close fist
        NPU->>UDP: {"gesture":"FIST", "xyz":[...]}
        UDP->>Bridge: Dispatch
        Bridge->>Blender: handle_fist() → Cycle color palette
    end

    alt PINCH Gesture (non-drawing)
        User->>NPU: Pinch fingers
        NPU->>UDP: {"gesture":"PINCH", "xyz":[...]}
        UDP->>Bridge: Dispatch
        Bridge->>Blender: handle_pinch() → Scale object
    end

    alt POINT Gesture
        User->>NPU: Point index finger
        NPU->>UDP: {"action":"ERASE"}
        UDP->>Bridge: Dispatch
        Bridge->>Blender: handle_erase() → Delete last shape
    end
```

---

## 6. Activity Diagram — Shape Classification v8b

```mermaid
flowchart TD
    A["Start: receive draw_points"] --> B{"len >= MIN_DRAW_POINTS?"}
    B -- No --> Z["Return None"]
    B -- Yes --> C["Stage 1: Smooth\n(moving average, window=5)"]
    C --> D["Stage 2: Resample\n(64 uniform points)"]
    D --> E["Compute Metrics:\ncirc, verts, aspect,\nlinearity, solidity"]
    E --> F{"Shape Closed?\n(gap < 45% diagonal)"}

    F -- No/Open --> G{"linearity > 0.85?"}
    G -- Yes --> H["LINE"]
    G -- No --> I{"linearity > 0.5?"}
    I -- Yes --> J{"verts >= 4?"}
    J -- Yes --> K["ARROW"]
    J -- No --> L["ARC"]
    I -- No --> M["CURVE"]

    F -- Yes/Closed --> N{"circ > 0.75?"}
    N -- Yes --> O{"aspect > 1.45?"}
    O -- Yes --> P["OVAL"]
    O -- No --> Q["CIRCLE"]

    N -- No --> R{"solidity < 0.55?"}
    R -- Yes --> S["STAR"]

    R -- No --> T{"circ < 0.55?"}
    T -- Yes --> U["Trust Vertex Count"]
    U --> U1{"verts?"}
    U1 -- 3 --> U2["TRIANGLE"]
    U1 -- 4 --> U3["SQUARE / RECTANGLE"]
    U1 -- 5 --> U4["PENTAGON"]
    U1 -- 6 --> U5["HEXAGON"]
    U1 -- 7+ --> U6["HEXAGON / RECTANGLE"]

    T -- No --> V["Ambiguous Zone\n0.55 ≤ circ ≤ 0.75"]
    V --> W["Hu Moment Template\nMatching Decides"]
    W --> X["Best match from\ncandidates list"]

    H & K & L & M & P & Q & S & U2 & U3 & U4 & U5 & U6 & X --> Y["Return\n(shape, center, size, confidence)"]
```

---

## 7. Component Diagram

```mermaid
graph TB
    subgraph "Master Controller"
        MC["aura_main.py\n(Interactive Menu / CLI)"]
    end

    subgraph "NPU Pipeline"
        NPU["aura_npu.py\n(Camera + Hand Tracking\n+ Shape Classifier v8b)"]
        HL["hand_landmarker.task\n(MediaPipe TFLite Model)"]
    end

    subgraph "Shared Configuration"
        CFG["config.py\n(HOST, PORT, Gestures,\nLERP, Thresholds)"]
    end

    subgraph "Blender Addon"
        SA["startup_aura.py\n(Auto-loader)"]
        SS["scene_setup.py\n(Scene Init + Suzanne)"]
        GB["gesture_bridge.py\n(Gesture Handlers\n+ Shape Spawners\n+ Blender Operators + UI)"]
        US["udp_server.py\n(Standalone UDP Server)"]
        ML["modal_listener.py\n(Modal Operator)"]
    end

    subgraph "Testing"
        TS["test_sender.py\n(Simulated Gestures\n+ Interactive Mode)"]
    end

    MC -->|"subprocess"| NPU
    MC -->|"subprocess"| SA
    MC -->|"subprocess"| TS
    NPU --> HL
    NPU -->|"UDP"| GB
    TS -->|"UDP"| GB
    SA --> SS
    SA --> GB
    NPU -.->|"imports"| CFG
    GB -.->|"imports"| CFG
    TS -.->|"imports"| CFG
    US -.->|"imports"| CFG
```

---

## 8. Data Flow Diagram

```mermaid
graph LR
    subgraph "Input"
        W["📷 Webcam Frame\n(BGR Image)"]
    end

    subgraph "Processing"
        RGB["Convert to RGB"]
        MP["MediaPipe\nHand Landmarker"]
        LM["21 Hand\nLandmarks"]
        PD["Pinch Distance\nCalculation"]
        GR["Gesture\nRecognition"]
        DP["Draw Points\nCollection"]
        SM["Smooth\n(Moving Average)"]
        RS["Resample\n(64 Uniform Points)"]
        DT["Decision Tree\nv8b Classifier"]
        HU["Hu Moment\nRefinement"]
    end

    subgraph "Output"
        UDP_G["UDP: Gesture Packet\n{gesture, xyz, confidence}"]
        UDP_D["UDP: DRAW_2D Packet\n{shape, center, size}"]
        UDP_E["UDP: ERASE Packet"]
    end

    subgraph "3D Result"
        B3D["Blender 3D\nViewport Update"]
    end

    W --> RGB --> MP --> LM
    LM --> PD --> GR
    PD --> DP
    DP --> SM --> RS --> DT --> HU

    GR --> UDP_G
    HU --> UDP_D
    GR -->|"POINT"| UDP_E

    UDP_G --> B3D
    UDP_D --> B3D
    UDP_E --> B3D
```

---

## 9. Deployment Diagram

```mermaid
graph TB
    subgraph "User's Machine"
        subgraph "Console 1: Master Controller"
            MC["python aura_main.py"]
        end

        subgraph "Console 2: NPU Pipeline"
            VENV["Python 3.10 venv"]
            NPU["aura_npu.py"]
            CAM["USB Webcam\n(OpenCV VideoCapture)"]
            TF["TensorFlow Lite\n+ MediaPipe Tasks"]
        end

        subgraph "Window: Blender"
            BL["Blender 3.x/4.x"]
            ADDON["Aura-3D Addon\n(gesture_bridge.py)"]
            VIEW["3D Viewport\n+ N-Panel"]
        end

        subgraph "Network (Loopback)"
            UDP["UDP 127.0.0.1:9090"]
        end
    end

    MC -->|"subprocess\n(new console)"| NPU
    MC -->|"subprocess\n(new window)"| BL
    VENV --> NPU
    NPU --> CAM
    NPU --> TF
    NPU -->|"send"| UDP
    UDP -->|"recv"| ADDON
    ADDON --> VIEW
    BL --> ADDON
```

---

## 10. State Diagram — Drawing FSM

```mermaid
stateDiagram-v2
    [*] --> Idle

    Idle --> Drawing : Pinch detected\n(dist < 0.045)
    Drawing --> Drawing : Hand moving\n(append point)
    Drawing --> Classifying : Pinch released\n(dist > 0.085)
    Drawing --> TooQuick : Released too fast\n(< 0.8s)

    TooQuick --> Idle : After status display

    Classifying --> ShapeDetected : classify_shape() succeeds
    Classifying --> NotRecognized : classify_shape() returns None

    ShapeDetected --> Sending : send_draw_2d()
    Sending --> Idle : After status display

    NotRecognized --> Idle : After "Not recognized" display

    Idle --> Erasing : Point gesture detected
    Erasing --> Idle : send_erase() + cooldown

    Idle --> GestureControl : Non-drawing gesture
    GestureControl --> Idle : Gesture ends

    state GestureControl {
        [*] --> MOVE
        MOVE --> PINCH : Pinch dist < 0.05
        MOVE --> FIST : Fist dist < 0.2
        MOVE --> PALM : Index above knuckle
        PINCH --> MOVE
        FIST --> MOVE
        PALM --> MOVE
    }
```

---

## 11. Shape Spawning Map

```mermaid
graph TB
    subgraph "Shape Classification (NPU)"
        C["CIRCLE"] 
        O["OVAL"]
        S["SQUARE"]
        R["RECTANGLE"]
        T["TRIANGLE"]
        D["DIAMOND"]
        ST["STAR"]
        P["PENTAGON"]
        H["HEXAGON"]
        L["LINE"]
        A["ARROW"]
        ARC["ARC"]
        CRV["CURVE"]
    end

    subgraph "Blender 3D Spawners"
        SC["_spawn_circle()\nTorus mesh"]
        SO["_spawn_oval()\nScaled torus"]
        SS["_spawn_square()\nPlane mesh"]
        SR["_spawn_rectangle()\nScaled plane"]
        STR["_spawn_triangle()\nbmesh vertices"]
        SD["_spawn_diamond()\nRotated plane"]
        SST["_spawn_star()\nbmesh 5-point"]
        SP["_spawn_polygon()\nbmesh n-gon"]
        SL["_spawn_line()\nCylinder stretched"]
        SA["_spawn_arrow()\nCone + Cylinder"]
    end

    C --> SC
    O --> SO
    S --> SS
    R --> SR
    T --> STR
    D --> SD
    ST --> SST
    P -->|"sides=5"| SP
    H -->|"sides=6"| SP
    L --> SL
    A --> SA
    ARC --> SL
    CRV --> SL
```

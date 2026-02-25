from fastapi import FastAPI
import cv2
import mediapipe as mp
import threading

app = FastAPI()

mp_hands = mp.solutions.hands
hands = mp_hands.Hands(
    min_detection_confidence=0.7,
    min_tracking_confidence=0.7
)

cap = cv2.VideoCapture(0)

latest_gesture = {
    "action": "IDLE",
    "dx": 0.0,
    "dy": 0.0,
    "dz": 0.0
}

def camera_loop():
    global latest_gesture

    prev_x, prev_y = None, None

    while True:
        ret, frame = cap.read()
        if not ret:
            continue

        frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        results = hands.process(frame_rgb)

        if results.multi_hand_landmarks:
            hand_landmarks = results.multi_hand_landmarks[0]

            h, w, _ = frame.shape
            cx = int(hand_landmarks.landmark[9].x * w)
            cy = int(hand_landmarks.landmark[9].y * h)

            if prev_x is not None and prev_y is not None:
                dx = (cx - prev_x) / 100.0
                dy = (cy - prev_y) / 100.0

                latest_gesture = {
                    "action": "MOVE",
                    "dx": float(dx),
                    "dy": float(-dy),
                    "dz": 0.0
                }

            prev_x, prev_y = cx, cy
        else:
            latest_gesture = {
                "action": "IDLE",
                "dx": 0.0,
                "dy": 0.0,
                "dz": 0.0
            }

@app.get("/gesture")
def get_gesture():
    return latest_gesture

if __name__ == "__main__":
    t = threading.Thread(target=camera_loop, daemon=True)
    t.start()

    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
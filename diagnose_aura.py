# Aura-3D Diagnostic Tool
import os
import sys

def test_camera():
    print("Checking OpenCV camera access...")
    try:
        import cv2
        for i in range(3):
            cap = cv2.VideoCapture(i)
            if cap.isOpened():
                ret, frame = cap.read()
                if ret:
                    print(f"  ✔ Camera {i} is working. Found frame size: {frame.shape[1]}x{frame.shape[0]}")
                    cap.release()
                    return True
                cap.release()
        print("  ✖ No working cameras found at indices 0-2.")
    except Exception as e:
        print(f"  ✖ OpenCV Error: {e}")
    return False

def test_mediapipe():
    print("Checking MediaPipe availability...")
    try:
        from mediapipe.tasks.python import BaseOptions
        from mediapipe.tasks.python.vision import HandLandmarker, HandLandmarkerOptions, RunningMode

        ROOT_DIR = os.path.dirname(os.path.realpath(__file__))
        MODEL_PATH = os.path.join(ROOT_DIR, "npu_pipeline", "hand_landmarker.task")

        if not os.path.exists(MODEL_PATH):
            print(f"  ✖ Hand landmarker model not found at: {MODEL_PATH}")
            return False

        options = HandLandmarkerOptions(
            base_options=BaseOptions(model_asset_path=MODEL_PATH),
            running_mode=RunningMode.VIDEO,
            num_hands=1,
        )
        landmarker = HandLandmarker.create_from_options(options)
        landmarker.close()
        print("  ✔ MediaPipe Tasks API initialized successfully.")
        print(f"  ✔ Model loaded from: {MODEL_PATH}")
        return True
    except Exception as e:
        print(f"  ✖ MediaPipe Error: {e}")
    return False

if __name__ == "__main__":
    print("═"*40)
    print("  Aura-3D Diagnostic Report")
    print("═"*40)
    print(f"Python: {sys.version}")
    print(f"CWD: {os.getcwd()}")
    
    cam_ok = test_camera()
    mp_ok = test_mediapipe()
    
    print("═"*40)
    if cam_ok and mp_ok:
        print("  🎉 ALL SYSTEMS GREEN.")
    else:
        print("  🚨 PROBLEMS DETECTED.")
    print("═"*40)
    input("Press Enter to close diagnostic.")

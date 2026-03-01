# ============================================================
#  Aura-3D  ·  Master Controller
#  ──────────────────────────────────────────────────────────
#  The universal launcher for Project Aura. Use this to
#  start Blender, the NPU pipeline, or the simulation.
# ============================================================

import os
import sys
import subprocess
import argparse
import time

if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

# ── Paths ───────────────────────────────────────────────────
ROOT_DIR = os.path.dirname(os.path.realpath(__file__))
BLENDER_PATH = r"D:\Blender\blender.exe"
VENV_PYTHON = os.path.join(ROOT_DIR, "venv", "Scripts", "python.exe")

def print_header(title):
    print("\n" + "="*60)
    print(f"  Aura-3D  -  {title}")
    print("="*60)

def clean_port(port=9090):
    """Kills any process holding the target port to prevent WinError 10048."""
    print(f"[Aura] Checking port {port}...")
    try:
        # Find PID using the port
        output = subprocess.check_output(f'netstat -ano | findstr :{port}', shell=True).decode()
        for line in output.strip().split('\n'):
            if 'LISTENING' in line or 'UDP' in line:
                pid = line.strip().split()[-1]
                if pid != '0':
                    print(f"[Aura] Cleaning up old process (PID {pid}) on port {port}...")
                    subprocess.run(f'taskkill /F /PID {pid}', shell=True, capture_output=True)
    except:
        pass # Port is likely free or no process found

def launch_blender():
    clean_port()
    print_header("Launching Blender")
    startup_script = os.path.join(ROOT_DIR, "blender_scripts", "startup_aura.py")
    scripts_dir = os.path.join(ROOT_DIR, "blender_scripts")
    
    # Use --python-expr to avoid Blender splitting paths with spaces.
    # Pre-inject sys.path and __file__ so the startup script can find
    # config.py and all other project modules.
    expr = (
        f"import sys; "
        f"sys.path.insert(0, r'{ROOT_DIR}'); "
        f"sys.path.insert(0, r'{scripts_dir}'); "
        f"__file__ = r'{startup_script}'; "
        f"exec(open(r'{startup_script}').read())"
    )
    cmd = [BLENDER_PATH, "--python-expr", expr]
    
    print(f"[Aura] Running Blender with startup script...")
    subprocess.Popen(cmd)
    print("[Aura] Blender is starting in a separate window.")
    print("[Aura] Remember to click 'Start Bridge' in the N-panel (Aura-3D tab).")

def launch_npu():
    clean_port()
    print_header("Starting NPU Pipeline")
    npu_script = os.path.join(ROOT_DIR, "aura_npu.py")
    
    if not os.path.exists(VENV_PYTHON):
        print(f"Error: Virtual environment not found at {VENV_PYTHON}")
        return

    # Quote paths for cmd /k. Windows cmd needs outer quotes if there are multiple quoted parts.
    # Format: cmd /k ""Path 1" "Path 2""
    full_cmd = f'cmd /k ""{VENV_PYTHON}" "{npu_script}""'
    print(f"[Aura] Running: {full_cmd}")
    subprocess.Popen(full_cmd, creationflags=subprocess.CREATE_NEW_CONSOLE, cwd=ROOT_DIR)
    print("[Aura] NPU Bridge (Webcam) started in a new console.")

def launch_simulation():
    print_header("Running Simulation")
    sim_script = os.path.join(ROOT_DIR, "external", "test_sender.py")
    
    cmd = [sys.executable, sim_script, "--loop", "--fps", "30"]
    print(f"[Aura] Running: {' '.join(cmd)}")
    subprocess.Popen(cmd, creationflags=subprocess.CREATE_NEW_CONSOLE)
    print("[Aura] Test sender started in a new console.")

def show_config():
    print_header("Current Configuration")
    try:
        import config
        print(f"  Host        : {config.HOST}")
        print(f"  Port        : {config.PORT}")
        print(f"  Lerp Factor : {config.LERP_FACTOR}")
        print(f"  Gate        : 0.5 (Confidence Threshold)")
        print(f"  Status      : Unified and Ready")
    except ImportError:
        print("❌ Error: Could not load config.py from root.")
    print("═"*60)

def main():
    parser = argparse.ArgumentParser(description="Aura-3D Master Controller")
    parser.add_argument("--blender", action="store_true", help="Launch Blender with pre-loaded bridge")
    parser.add_argument("--npu", action="store_true", help="Start the webcam gesture pipeline")
    parser.add_argument("--sim", action="store_true", help="Start the test simulation sender")
    parser.add_argument("--config", action="store_true", help="Show current system configuration")
    
    if len(sys.argv) == 1:
        # Interactive mode if no args
        while True:
            os.system('cls' if os.name == 'nt' else 'clear')
            print_header("Universal Launcher")
            print("  [1] Launch Blender (Bridge Auto-load)")
            print("  [2] Start NPU Pipeline (Webcam tracking)")
            print("  [3] Run Test Simulation (Dummy data)")
            print("  [4] Show Configuration")
            print("  [q] Quit")
            print("═"*60)
            
            choice = input("\nSelect an option: ").strip().lower()
            
            if choice == '1': launch_blender()
            elif choice == '2': launch_npu()
            elif choice == '3': launch_simulation()
            elif choice == '4': show_config()
            elif choice == 'q': break
            
            if choice in ['1', '2', '3', '4']:
                input("\nPress Enter to continue...")
    else:
        args = parser.parse_args()
        if args.config: show_config()
        if args.blender: launch_blender()
        if args.npu: launch_npu()
        if args.sim: launch_simulation()

if __name__ == "__main__":
    main()

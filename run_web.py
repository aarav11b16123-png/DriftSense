import subprocess
import sys
import os
import time

def start():
    root = os.path.abspath(os.path.dirname(__file__))
    backend_dir = os.path.join(root, "web", "backend")
    frontend_dir = os.path.join(root, "web", "frontend")

    print("==================================================")
    print(" 🚀 Launching DriftSense AI Observability Platform")
    print("==================================================")
    print(f"[*] Starting FastAPI Web Backend on port 8001...")
    backend_proc = subprocess.Popen(
        [sys.executable, "-m", "uvicorn", "main:app", "--port", "8001", "--reload"],
        cwd=backend_dir
    )

    time.sleep(1)

    print(f"[*] Starting React Frontend on port 5173...")
    frontend_proc = subprocess.Popen(
        "npm run dev",
        shell=True,
        cwd=frontend_dir
    )

    print("\n[+] DriftSense Web is running:")
    print("    👉 Frontend UI: http://localhost:5173")
    print("    👉 Backend API: http://localhost:8001/docs\n")
    print("Press Ctrl+C to stop both servers.")

    try:
        backend_proc.wait()
        frontend_proc.wait()
    except KeyboardInterrupt:
        print("\nStopping DriftSense servers...")
        backend_proc.terminate()
        frontend_proc.terminate()

if __name__ == "__main__":
    start()

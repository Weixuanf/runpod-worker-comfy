import subprocess
import signal
import threading
from app.common import COMFYUI_PORT, restart_error, COMFYUI_PATH
import os 

# Global variable to track the subprocess status
is_subprocess_running = False
# Subprocess handle
subprocess_handle = None

def stream_output(process, stream_type, logError=False):
    """
    Forward the output of the subprocess to the console.
    
    :param process: The subprocess handle
    :param stream_type: Type of the stream ('stdout' or 'stderr')
    """
    global restart_error
    stream = process.stdout if stream_type == 'stdout' else process.stderr
    for line in iter(stream.readline, ''):
        print(line.strip())
        if stream_type == 'stderr':
            # Append errors to the global string, separating them with a newline character
            restart_error += line.strip() + "\n"

def start_comfyui_subprocess():
    global is_subprocess_running
    global subprocess_handle
    
    if is_subprocess_running:
        print("Subprocess is already running.")
        return

    # Define the environment variables for the subprocess
    # env_vars = {}
    # Set a specific environment variable for the subprocess
    # env_vars["LD_PRELOAD"] = "path_to_libtcmalloc.so"  # Update this path as necessary

    # Start the subprocess and redirect its output and error
    venv_path = f"{COMFYUI_PATH}/venv/bin/python3"
    print("👉💼venv path", venv_path, 'exists', os.path.exists(venv_path), "comfyui main.py exists:",os.path.exists(f"{COMFYUI_PATH}/main.py"))
    subprocess_handle = subprocess.Popen(
        [venv_path if os.path.exists(venv_path) else "python3", "-u", f"{COMFYUI_PATH}/main.py", "--disable-auto-launch", "--disable-metadata", "--port", COMFYUI_PORT],
        # env=env_vars,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        bufsize=1,
        universal_newlines=True,
        text=True
    )
    is_subprocess_running = True

    # Start threads to read the subprocess's output and error streams
    stdout_thread = threading.Thread(target=stream_output, args=(subprocess_handle, 'stdout'))
    stderr_thread = threading.Thread(target=stream_output, args=(subprocess_handle, 'stderr'))
    stdout_thread.start()
    stderr_thread.start()

def stop_comfyui_subprocess():
    global is_subprocess_running
    global subprocess_handle
    
    if subprocess_handle:
        try:
            # Terminate the subprocess
            subprocess_handle.terminate()
            # Wait for the subprocess to terminate
            subprocess_handle.wait(timeout=5)
        except subprocess.TimeoutExpired:
            # Force kill if not terminated within timeout
            os.kill(subprocess_handle.pid, signal.SIGKILL)
        finally:
            subprocess_handle = None
            is_subprocess_running = False
            print("Subprocess stopped.")

def restart():
    print("Restarting the subprocess...")
    stop_comfyui_subprocess()
    start_comfyui_subprocess()

def start_aiohttp_server_subprocess():
    aiohttp_server_subprocess_handle = subprocess.Popen(
        ["python3", "-u", "app/server.py"],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        bufsize=1,
        universal_newlines=True,
        text=True
    )

    # Start threads to read the aiohttp server subprocess's output and error streams
    stdout_thread = threading.Thread(target=stream_output, args=(aiohttp_server_subprocess_handle, 'stdout'))
    stderr_thread = threading.Thread(target=stream_output, args=(aiohttp_server_subprocess_handle, 'stderr'))
    stdout_thread.start()
    stderr_thread.start()


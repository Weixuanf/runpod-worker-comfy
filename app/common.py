import os
import subprocess
import threading

from app.ddb_utils import updateRunJobLogsThread
from app.logUtils import append_comfyui_log
CONTAINER_ROOT = os.path.dirname(os.path.dirname(__file__))
COMFYUI_PATH = os.environ.get("COMFYUI_PATH", "/comfyui")  
COMFYUI_LOG_PATH = '/comfyui.log'
print(f'👉COMFYUI_PATH: {COMFYUI_PATH}')
COMFYUI_PORT = "8080"
COMFYUI_MODEL_PATH = f'{COMFYUI_PATH}/models'
EXTRA_MODEL_PATH = os.environ.get("EXTRA_MODEL_PATH", "/runpod-volume/comfyui/models")
COMFY_HOST = f"127.0.0.1:{COMFYUI_PORT}"
COMFY_HOST_URL = f"http://{COMFY_HOST}"
HASHED_FILENAME_PREFIX = "sha256_"
# Time to wait between API check attempts in milliseconds
COMFY_API_AVAILABLE_INTERVAL_MS = 50
# Maximum number of API check attempts
COMFY_API_AVAILABLE_MAX_RETRIES = 500
# Time to wait between poll attempts in milliseconds
COMFY_POLLING_INTERVAL_MS = 250
# Maximum number of poll attempts
COMFY_POLLING_MAX_RETRIES = 500
# Host where ComfyUI is running
# Enforce a clean state after each job is done
# see https://docs.runpod.io/docs/handler-additional-controls#refresh-worker
REFRESH_WORKER = os.environ.get("REFRESH_WORKER", "false").lower() == "true"


# for scanner
IS_SCANNER_WORKER = os.environ.get('IS_SCANNER_WORKER', False)
restart_error = ""


def stream_output(process, stream_type, logError=False):
    stream = process.stdout if stream_type == 'stdout' else process.stderr
    count = 0
    for line in iter(stream.readline, ''):
        if count < 10 or count % 10 == 0: 
            print(line.strip())
            append_comfyui_log(line.strip())
        count = count + 1

def start_subprocess(cmd):
    # Start the subprocess and redirect its output and error
    subprocess_handle = subprocess.Popen(
        cmd,
        # env=env_vars,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        bufsize=1,
        universal_newlines=True,
        text=True
    )

    # Start threads to read the subprocess's output and error streams
    stdout_thread = threading.Thread(target=stream_output, args=(subprocess_handle, 'stdout'))
    stderr_thread = threading.Thread(target=stream_output, args=(subprocess_handle, 'stderr'))
    stdout_thread.start()
    stderr_thread.start()
    # Wait for the subprocess to complete
    subprocess_handle.wait()

    # Wait also for all output to be processed (output threads to complete)
    stdout_thread.join()
    stderr_thread.join()
import subprocess
import signal
import threading
from app.common import COMFYUI_LOG_PATH, COMFYUI_PORT, restart_error, COMFYUI_PATH
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

import subprocess
import logging
import sys

def start_comfyui_subprocess():
    print('🚀 Starting ComfyUI subprocess...')
    global is_subprocess_running
    global subprocess_handle
    
    if is_subprocess_running:
        print("Subprocess is already running.")
        return

    # Define the environment variables for the subprocess
    # env_vars = {}

    # Set up logging
    logger = logging.getLogger('ComfyUI')
    logger.setLevel(logging.DEBUG)

    # Create handlers
    console_handler = logging.StreamHandler(sys.stdout)
    file_handler = logging.FileHandler(COMFYUI_LOG_PATH)

    # Set levels
    console_handler.setLevel(logging.DEBUG)
    file_handler.setLevel(logging.DEBUG)

    # Create formatters and add them to handlers
    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    console_handler.setFormatter(formatter)
    file_handler.setFormatter(formatter)

    # Add handlers to the logger
    logger.addHandler(console_handler)
    logger.addHandler(file_handler)

    # Command to run
    command = ['python3', 'main.py', '--port', COMFYUI_PORT]

    # Start the subprocess
    process = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE)

    # Stream the logs
    for line in iter(process.stdout.readline, b''):
        logger.info(line.decode().strip())
    for line in iter(process.stderr.readline, b''):
        logger.error(line.decode().strip())

    # Wait for the process to complete
    process.stdout.close()
    process.stderr.close()
    process.wait()


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


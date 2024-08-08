import subprocess
import logging
import sys
import threading
import time

COMFYUI_LOG_PATH = '/comfyui.log'
COMFYUI_PORT = '8080'

# Flag to indicate if the subprocess is running
is_subprocess_running = False
subprocess_handle = None

def stream_subprocess_output(process, logger):
    """Function to stream subprocess output."""
    def stream_pipe(pipe, log_level):
        with pipe:
            for line in iter(pipe.readline, ''):
                if line:
                    logger.log(log_level, line.strip())

    stdout_thread = threading.Thread(target=stream_pipe, args=(process.stdout, logging.INFO))
    stderr_thread = threading.Thread(target=stream_pipe, args=(process.stderr, logging.ERROR))

    stdout_thread.start()
    stderr_thread.start()

    stdout_thread.join()
    stderr_thread.join()

def start_comfyui_subprocess():
    print('🚀 Starting ComfyUI subprocess...')
    global is_subprocess_running
    global subprocess_handle
    
    if is_subprocess_running:
        print("Subprocess is already running.")
        return

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
    formatter = logging.Formatter('%(asctime)s %(message)s')
    # console_handler.setFormatter(formatter)
    file_handler.setFormatter(formatter)

    # Add handlers to the logger
    logger.addHandler(console_handler)
    logger.addHandler(file_handler)

    # Command to run
    command = ['python3', '-u', 'main.py', '--port', COMFYUI_PORT, '--listen']

    # Start the subprocess
    process = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, universal_newlines=True)

    # Mark the subprocess as running
    is_subprocess_running = True
    subprocess_handle = process

    # Start a thread to stream the subprocess output
    threading.Thread(target=stream_subprocess_output, args=(process, logger), daemon=True).start()


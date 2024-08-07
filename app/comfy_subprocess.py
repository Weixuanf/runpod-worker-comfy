import subprocess
import logging
import sys
import threading

COMFYUI_LOG_PATH = '/comfyui.log'
COMFYUI_PORT = '8080'

# Flag to indicate if the subprocess is running
is_subprocess_running = False
subprocess_handle = None

def stream_subprocess_output(process, logger):
    """Function to stream subprocess output."""
    for line in iter(process.stdout.readline, b''):
        logger.info(line.decode().strip())
    for line in iter(process.stderr.readline, b''):
        logger.error(line.decode().strip())
    process.stdout.close()
    process.stderr.close()

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

    # Mark the subprocess as running
    is_subprocess_running = True
    subprocess_handle = process

    # Start a thread to stream the subprocess output
    threading.Thread(target=stream_subprocess_output, args=(process, logger), daemon=True).start()

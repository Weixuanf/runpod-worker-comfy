import subprocess
import threading
from app.common import COMFYUI_LOG_PATH


def append_comfyui_log(log:str):
    with open(COMFYUI_LOG_PATH, "a") as f:
        f.write("\n" + log + "\n")

def clear_comfyui_log():
    with open(COMFYUI_LOG_PATH, "w") as f:
        f.write("")



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
import subprocess
import threading
import time
import boto3
from app.common import COMFYUI_LOG_PATH, get_job_item
from app.s3_utils import upload_log_to_s3

# S3 Configuration
S3_BUCKET = 'your-s3-bucket-name'
S3_LOG_KEY = 'path/to/log/file/in/s3.log'

s3_client = boto3.client('s3')


def append_comfyui_log(log: str):    
    with open(COMFYUI_LOG_PATH, "a") as f:
        f.write("\n" + log + "\n")


def clear_comfyui_log():
    with open(COMFYUI_LOG_PATH, "w") as f:
        f.write("")

def start_append_log_thread(log: str):
    print(log)
    def append_continuously():
        while True:
            log = input()
            append_comfyui_log(log)

    append_thread = threading.Thread(target=append_continuously)
    append_thread.daemon = True
    append_thread.start()

def start_continuous_s3_log_upload_thread(intervalMS: int = 500):
    clear_comfyui_log()
    job = get_job_item()
    job_id = job.get('id', None)
    log_key = job.get('log_key', 'unknown')
    if not job_id:
        raise ValueError("Job ID not found in job item")

    def upload_continuously():
        while True:
            upload_log_to_s3(log_key)
            time.sleep(intervalMS / 1000)

    upload_thread = threading.Thread(target=upload_continuously)
    upload_thread.daemon = True
    upload_thread.start()


def end_job_upload_comfyui_log(log: str):
    append_comfyui_log(log + "\n<EOF>")
    upload_log_to_s3()


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
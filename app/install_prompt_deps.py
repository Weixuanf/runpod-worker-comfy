import hashlib
import os
import shutil
import subprocess
import threading

from app.ddb_utils import updateRunJobLogsThread
from .logUtils import append_comfyui_log
from .common import HASHED_FILENAME_PREFIX, MODEL_PATHS,COMFYUI_PATH

DISK_MODEL_PATH = os.path.join(COMFYUI_PATH, 'models')
TEMP_MODEL_PATH = '/'

civitai_token = os.environ.get('CIVITAI_API_KEY',"none")
downloaded_model_paths = set()
job_id = None
def install_prompt_deps(prompt,deps, new_job_id):
    global job_id, downloaded_model_paths
    job_id = new_job_id
    models = deps.get('models',{})
    for filename in models:
        model = models.get(filename)
        filehash = model.get('fileHash')
        folderName = model.get('fileFolder')
        download_url = model.get('downloadUrl')
        if download_url.startswith('https://civitai.com/'):
            download_url += f'?token={civitai_token}'
        elif not download_url.startswith('https://huggingface.co/'):
            raise ValueError('download_url not supported',download_url)
        if not filehash or not folderName or not download_url:
            raise ValueError('filehash or folderName or download_url not found in model',model)
        model_exists = False
        for model_path in MODEL_PATHS:
            base_name, extension = os.path.splitext(filename)
            hash_file_path = os.path.join(model_path, folderName, HASHED_FILENAME_PREFIX+ filehash + extension)
            if os.path.exists(hash_file_path):
                print(f"👌Model file {filename} exists in {hash_file_path}")
                model_exists = True
                # update the prompt with the hash_file_path
                for key in prompt:
                    prompt_node = prompt[key]
                    inputs = prompt_node.get('inputs')
                    if inputs:
                        for key in inputs:
                            if inputs[key] == filename:
                                inputs[key] = HASHED_FILENAME_PREFIX + filehash + extension
                print(f"🧙 re-prompt with hash:{prompt}")
        if not model_exists:
            temp_path = os.path.join(TEMP_MODEL_PATH, filename)
            file_path = os.path.join(DISK_MODEL_PATH, folderName, filename)
            downloaded_model_paths.add(file_path)
            print(f"⬇️Start downloading from {download_url} to {temp_path}")
            start_subprocess(['wget','-O',temp_path, download_url, '--progress=bar:force'])
            print(f"🌳Downloaded. moving from {temp_path} to {file_path}")
            shutil.move(temp_path, file_path)
            print(f"👌Moved to {file_path}")
            
    return prompt
                
def rename_file_with_hash():
    copy = downloaded_model_paths.copy()
    for filepath in copy:
        if os.path.exists(filepath):
            print(f"#️⃣calculating hash for", filepath)
            base_name, extension = os.path.splitext(filepath)
            calc_hash = calculate_sha256(filepath)
            directory = os.path.dirname(filepath)  # Get the directory of the file
            hash_file_name = HASHED_FILENAME_PREFIX + calc_hash + extension
            os.rename(filepath, os.path.join(directory, hash_file_name))
            print(f"👌Renamed {filepath} to {hash_file_name}")
            downloaded_model_paths.remove(filepath)
        else:
            print(f"File not found: {filepath}")
            downloaded_model_paths.remove(filepath)
            
def calculate_sha256(file_path):
    sha256_hash = hashlib.sha256()  # Create a new SHA-256 hash object
    try:
        with open(file_path, "rb") as f:  # Open the file in binary mode
            for chunk in iter(lambda: f.read(4096), b""):  # Read in 4096 byte chunks
                sha256_hash.update(chunk)  # Update the hash with the chunk
    except FileNotFoundError:
        return None
    except Exception as e:
        return None

    return sha256_hash.hexdigest() 

def stream_output(process, stream_type, logError=False):
    stream = process.stdout if stream_type == 'stdout' else process.stderr
    count = 0
    for line in iter(stream.readline, ''):
        if count < 10 or count % 10 == 0: 
            print(line.strip())
            append_comfyui_log(line.strip())
            updateRunJobLogsThread({"id": job_id, "status": "INSTALLING"})
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
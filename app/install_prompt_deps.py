import hashlib
import logging
import os
import shutil
import subprocess
import threading

from app.ddb_utils import updateRunJobLogsThread
from .logUtils import append_comfyui_log
from .common import COMFYUI_MODEL_PATH, EXTRA_MODEL_PATH, HASHED_FILENAME_PREFIX,COMFYUI_PATH

TEMP_MODEL_PATH = '/'

civitai_token = os.environ.get('CIVITAI_API_KEY',"none")
downloaded_model_paths = set()
job = None
def install_prompt_deps(prompt,deps, new_job):
    global job, downloaded_model_paths
    downloaded_model_paths.clear()
    job = new_job
    models = deps.get('models',{})
    for filename in models:
        model = models.get(filename)
        filehash = model.get('fileHash', model.get('hash'))
        folder = model.get('fileFolder', model.get('folder'))
        download_url = model.get('downloadUrl', model.get('url'))
        if download_url.startswith('https://civitai.com/'):
            download_url += f'?token={civitai_token}'
        elif not download_url.startswith('https://huggingface.co/'):
            raise ValueError('download_url not supported',download_url)
        if not folder or not download_url:
            raise ValueError('folderName or download_url not found in model',model)
        model_exists = False
        # Check if model cache exists in the EXTRA_MODEL_PATH
        if filehash:
            base_name, extension = os.path.splitext(filename)
            hash_file_path = os.path.join(EXTRA_MODEL_PATH, folder, HASHED_FILENAME_PREFIX+ filehash + extension)
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
            # temp_path = os.path.join(TEMP_MODEL_PATH, filename)
            file_path = os.path.join(COMFYUI_MODEL_PATH, folder, filename)
            downloaded_model_paths.add(file_path)
            print(f"⬇️Start downloading from {download_url} to {file_path}")
            start_subprocess(['wget','-O',file_path, download_url, '--progress=bar:force'])
            
    return prompt
                
def rename_file_with_hash():
    global downloaded_model_paths
    copy = downloaded_model_paths.copy()
    
    for filepath in copy:
        if os.path.exists(filepath):
            print(f"#️⃣calculating hash for", filepath)
            base_name, extension = os.path.splitext(filepath)
            calc_hash = calculate_sha256(filepath)
            hash_file_name = HASHED_FILENAME_PREFIX + calc_hash + extension
            # Calculate the relative path from base_path to full_path
            model_rel_path = os.path.relpath(filepath, COMFYUI_MODEL_PATH)
            model_rel_folder = os.path.dirname(model_rel_path)
            new_model_path = os.path.join(EXTRA_MODEL_PATH, model_rel_folder, hash_file_name)
            print('🌳 moving and renaming model from', filepath, 'to', new_model_path)
            try:
                os.makedirs(os.path.dirname(new_model_path), exist_ok=True)
                shutil.move(filepath, new_model_path)
                print(f"👌Renamed {filepath} to {hash_file_name}")
            except Exception as e:
                logging.error(f"❌Error moving model: {e}", exc_info=True)
            
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
            updateRunJobLogsThread({"id": job['id'], **job, "status": "INSTALLING"})
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
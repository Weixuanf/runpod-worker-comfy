import json
import os
import subprocess
import signal
import threading
import requests
from .common import MODEL_PATHS,COMFY_HOST_URL,CONTAINER_ROOT
from .manager_copy import run_script

DISK_MODEL_PATH = 'models'

try:
    os.makedirs(os.path.join(CONTAINER_ROOT, DISK_MODEL_PATH), exist_ok=True)
except Exception as e:
    print('❌❌ Error creating /models folder',e)

civitai_token = os.environ.get('CIVITAI_API_KEY',"none")

def install_prompt_deps(prompt,deps):
    models = deps.get('models')
    if models:
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
                hash_filename = os.path.join(model_path, folderName, filehash + extension)
                print(f"hashed filepath: {hash_filename}")
                if os.path.exists(hash_filename):
                    print(f"👌Model file {filename} exists in {hash_filename}")
                    model_exists = True
                    # update the prompt with the hash_filename
                    for key in prompt:
                        prompt_node = prompt[key]
                        inputs = prompt_node.get('inputs')
                        if inputs:
                            for key in inputs:
                                if inputs[key] == filename:
                                    inputs[key] = hash_filename
            if not model_exists:
                print(f"⬇️Start downloading {filename} from {download_url}")
                start_subprocess(['wget','-O',f'{DISK_MODEL_PATH}/{filename}', download_url, '--progress=bar:force'])
    return prompt
                

def stream_output(process, stream_type, logError=False):
    stream = process.stdout if stream_type == 'stdout' else process.stderr
    count = 0
    for line in iter(stream.readline, ''):
        if count < 10 or count % 10 == 0: 
            print(line.strip())
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
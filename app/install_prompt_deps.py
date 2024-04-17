import os
import subprocess
import threading
from .common import MODEL_PATHS,COMFY_HOST_URL,CONTAINER_ROOT,COMFYUI_PATH

DISK_MODEL_PATH = os.path.join(COMFYUI_PATH, 'models')

civitai_token = os.environ.get('CIVITAI_API_KEY',"none")

def install_prompt_deps(prompt,deps):
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
            hash_file_path = os.path.join(model_path, folderName, filehash + extension)
            if os.path.exists(hash_file_path):
                print(f"👌Model file {filename} exists in {hash_file_path}")
                model_exists = True
        if not model_exists:
            hash_file_path = os.path.join(DISK_MODEL_PATH, folderName, filehash + extension)
            print(f"⬇️Start downloading from {download_url} to {hash_file_path}")
            start_subprocess(['wget','-O',hash_file_path, download_url, '--progress=bar:force'])
        # update the prompt with the hash_file_path
        for key in prompt:
            prompt_node = prompt[key]
            inputs = prompt_node.get('inputs')
            if inputs:
                for key in inputs:
                    if inputs[key] == filename:
                        inputs[key] = filehash + extension
        print(f"🧙 re-prompt with hash:{prompt}")
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
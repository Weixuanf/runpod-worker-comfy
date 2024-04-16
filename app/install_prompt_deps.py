import os

import requests
from common import MODEL_PATHS,COMFY_HOST_URL
from manager_copy import run_script

DISK_MODEL_PATH = '/models'

try:
    os.makedirs(DISK_MODEL_PATH, exist_ok=True)
except Exception as e:
    print('❌❌ Error creating /models folder',e)

civitai_token = os.getenv('CIVITAI_API_KEY')

def install_prompt_deps(prompt:str,deps):
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
            for model_path in MODEL_PATHS:
                base_name, extension = os.path.splitext(filename)
                hash_filename = os.path.join(model_path, folderName, filehash + extension)
                print('🔍🔍filehash filename',hash_filename)
                if os.path.exists(hash_filename):
                    print(f"👌Model file {hash_filename} exists")
                else:
                    run_script(['wget', '-O',f'{DISK_MODEL_PATH}/{filename}', download_url])
                prompt.replace(filename,hash_filename)
    # refresh server file lists
    requests.get(f'{COMFY_HOST_URL}/object_info')
                
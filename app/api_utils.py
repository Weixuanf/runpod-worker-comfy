import logging
import os
from app.logUtils import start_subprocess


supported_pt_extensions = ['.ckpt', '.pt', '.bin', '.pth', '.safetensors', '.pkl']

def list_models(directory, extensions: list):
    files = {}
    for dirpath, _, filenames in os.walk(directory):
        for filename in filenames:
            ext = '.' + os.path.splitext(filename)[-1]
            if extensions and ext not in extensions:
                continue
            filepath = os.path.join(dirpath, filename)
            relative_path = os.path.relpath(filepath, directory)
            files[relative_path] = {
                "relPath": relative_path,
                "size": os.path.getsize(filepath)
            }
    return files

def install_models(model_deps, dir):
    for filename in model_deps:
        model = model_deps.get(filename)
        filehash = model.get('fileHash', model.get('hash'))
        folder = model.get('fileFolder', model.get('folder'))
        download_url = model.get('downloadUrl', model.get('url'))
        # if download_url.startswith('https://civitai.com/'):
        #     download_url += f'?token={civitai_token}'
        
        if not folder or not download_url:
            raise ValueError('folderName or download_url not found in model',model)
        
        file_path = os.path.join(dir, folder, filename)
        
        print(f"⬇️Start downloading model from {download_url} to {file_path}")
        start_subprocess(['wget','-O',file_path, download_url, '--progress=bar:force'])

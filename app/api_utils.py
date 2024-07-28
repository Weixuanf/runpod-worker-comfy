import logging
import os
from app.logUtils import start_subprocess


def list_models(directory, extensions: list = None):
    files = {}
    for dirpath, _, filenames in os.walk(directory):
        for filename in filenames:
            print(f"filename: {filename}")
            ext = os.path.splitext(filename)[1]
            if extensions and ext not in extensions:
                continue
            filepath = os.path.join(dirpath, filename)
            relative_path = os.path.relpath(filepath, directory)
            size_bytes = os.path.getsize(filepath)
            size_kb = size_bytes / 1024
            size_mb = size_kb / 1024
            files[relative_path] = {
                "path": relative_path,
                "sizeB": size_bytes,
                "sizeKB": size_kb
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
            raise ValueError('folderName or download_url not found in model', model)
        
        file_path = os.path.join(dir, folder, filename)
        
        # Create the directory if it doesn't exist
        os.makedirs(os.path.dirname(file_path), exist_ok=True)
        
        print(f"⬇️ Start downloading model from {download_url} to {file_path}")
        start_subprocess(['wget', '-O', file_path, download_url, '--progress=bar:force'])

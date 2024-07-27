import os
from app.logUtils import start_subprocess


def list_models(directory):
    result = []
    dirs = {}
    for dirpath, subdirs, filenames in os.walk(directory, followlinks=True, topdown=True):
        subdirs[:] = [d for d in subdirs]
        for file_name in filenames:
            relative_path = os.path.relpath(os.path.join(dirpath, file_name), directory)
            result.append(relative_path)

        for d in subdirs:
            path = os.path.join(dirpath, d)
            try:
                dirs[path] = os.path.getmtime(path)
            except FileNotFoundError:
                print(f"Warning: Unable to access {path}. Skipping this path.")
                continue

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

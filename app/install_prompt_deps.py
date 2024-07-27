import hashlib
import logging
import os
import shutil
from app.logUtils import start_subprocess
from .common import COMFYUI_MODEL_PATH, EXTRA_MODEL_PATH, HASHED_FILENAME_PREFIX,COMFYUI_PATH

TEMP_MODEL_PATH = '/'

civitai_token = os.environ.get('CIVITAI_API_KEY',"none")
downloaded_model_paths = {}
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
        origin_name_file_path = os.path.join(EXTRA_MODEL_PATH, folder, filename)
        if(model.get('keepName', False) and os.path.exists(origin_name_file_path)):
            print(f"👌Model file {filename} exists in {origin_name_file_path}")
            model_exists = True
            continue
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
            file_path = os.path.join(COMFYUI_MODEL_PATH, folder, filename)
            model['file_path'] = file_path
            downloaded_model_paths[file_path] = model
            print(f"⬇️Start downloading model from {download_url} to {file_path}")
            start_subprocess(['wget','-O',file_path, download_url, '--progress=bar:force'])
    install_prompt_images(prompt,deps)
    return prompt

def install_prompt_images(prompt,deps):
    images = deps.get('images',{})
    for filename in images:
        image = images.get(filename)
        download_url = image.get('url')
        if not download_url:
            continue
        #save image to input folder
        image_path = os.path.join(COMFYUI_PATH, 'input', filename)
        print(f"⬇️Start downloading image from {download_url} to {image_path}")
        start_subprocess(['wget','-O',image_path, download_url, '--progress=bar:force'])

                
def rename_file_with_hash():
    global downloaded_model_paths
    copy = downloaded_model_paths.copy()
    
    for key in list(copy.keys()):
        model = copy[key]
        filepath = key
        if filepath and os.path.exists(filepath):
            
            # Calculate the relative path for the new directory without the hash name yet
            model_rel_path = os.path.relpath(filepath, COMFYUI_MODEL_PATH)
            model_rel_folder = os.path.dirname(model_rel_path)
            temp_model_path = os.path.join(EXTRA_MODEL_PATH, model_rel_folder, os.path.basename(filepath))
            
            try:
                # Ensure the target directory exists
                os.makedirs(os.path.dirname(temp_model_path), exist_ok=True)
                # Move the file to the new directory
                print(f"🚚 Moving file", filepath, 'to', temp_model_path)
                shutil.move(filepath, temp_model_path)
                print(f"👌 Moved {filepath} to {temp_model_path}")
                if model.get('keepName', False):
                    print(f"👌 Keeping original file name {filepath}")
                    continue
                # After moving, calculate the hash
                print(f"#️⃣ Calculating hash for", temp_model_path)
                base_name, extension = os.path.splitext(temp_model_path)
                calc_hash = calculate_sha256(temp_model_path)
                hash_file_name = HASHED_FILENAME_PREFIX + calc_hash + extension
                new_model_path = os.path.join(os.path.dirname(temp_model_path), hash_file_name)
                
                # Rename the file based on the hash
                os.rename(temp_model_path, new_model_path)
                print(f"🏷️ Renamed to {new_model_path}")
                
                del downloaded_model_paths[filepath]

            except Exception as e:
                logging.error(f"❌Error moving or renaming model: {e}", exc_info=True)
        else:
            print(f"File not found: {filepath}")
            del downloaded_model_paths[filepath]
            
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

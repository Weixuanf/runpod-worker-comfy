import os
import traceback

COMFYUI_PATH = os.environ.get("COMFYUI_PATH", "/comfyui")  #network volume
COMFYUI_MODEL_PATH = f'{COMFYUI_PATH}/models'

def encode_path(path):
    # Replace '@' with '@@' to avoid conflicts
    # Replace slashes and backslashes with '@'
    return path.replace('@', '@@').replace('/', '@').replace('\\', '@')

def decode_path(encoded_path):
    # Replace '@@' with '@'
    # Replace '@' with the os-specific path separator
    return encoded_path.replace('@@', '@').replace('@', os.sep)

def clear_directory(dir_path):
    for filename in os.listdir(dir_path):
        file_path = os.path.join(dir_path, filename)
        if os.path.isfile(file_path) or os.path.islink(file_path):
            os.remove(file_path)

def create_safetensors_files(base_dir):
    for root, dirs, files in os.walk(base_dir):
        # Calculate the relative path from the base directory
        rel_path = os.path.relpath(root, base_dir)
        if rel_path == ".":
            continue  # Skip the base directory itself

        # Clear the contents of the current directory, only remove files
        clear_directory(root)

        encoded_path = encode_path(rel_path)
        safetensors_filename = f"{encoded_path}.safetensors"
        safetensors_filepath = os.path.join(root, safetensors_filename)
        # Create the .safetensors file in the current directory
        try:
            with open(safetensors_filepath, 'w') as f:
                f.write(rel_path)  # Create an empty file
        except Exception as e:
            print(f"❌🔴Error creating {safetensors_filepath}: {e}")
            traceback.print_exc()

input_image_path = os.path.join(COMFYUI_PATH, 'input')
def create_images_files(base_dir):
    for root, dirs, files in os.walk(base_dir):
        # Calculate the relative path from the base directory
        rel_path = os.path.relpath(root, base_dir)
        if rel_path == ".":
            continue  # Skip the base directory itself

        # Clear the contents of the current directory, only remove files
        clear_directory(root)
        
        encoded_path = encode_path(rel_path)
        safetensors_filename = f"{encoded_path}.png"
        safetensors_filepath = os.path.join(root, safetensors_filename)
        # Create the .safetensors file in the current directory
        try:
            with open(safetensors_filepath, 'w') as f:
                f.write(rel_path)  # Create an empty file
        except Exception as e:
            print(f"❌🔴Error creating {safetensors_filepath}: {e}")
            traceback.print_exc()


#put extra model folders
os.makedirs(f'{COMFYUI_MODEL_PATH}/ipadapter', exist_ok=True)
os.makedirs(f'{COMFYUI_MODEL_PATH}/animatediff_models', exist_ok=True)
os.makedirs(f'{COMFYUI_MODEL_PATH}/animatediff_motion_lora', exist_ok=True)
create_safetensors_files(COMFYUI_MODEL_PATH)
create_images_files(input_image_path)
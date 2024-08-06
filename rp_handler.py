import subprocess
import traceback
import runpod
import datetime
import json
import urllib.request
import urllib.parse
import time
import os
import requests
import base64
from io import BytesIO
from dotenv import load_dotenv
from app.api_utils import install_models, list_models
from app.ddb_utils import finishJobWithError, start_tunnel_thread, updateRunJob, updateRunJobLogsThread, updateRunJobLogs
from app.install_prompt_deps import install_prompt_deps, rename_file_with_hash
from app.logUtils import append_comfyui_log, append_log_thread, start_continuous_s3_log_upload_thread
from app.s3_utils import upload_file_to_s3
from concurrent.futures import ThreadPoolExecutor, as_completed
load_dotenv()
from app.common import COMFY_API_AVAILABLE_INTERVAL_MS, COMFY_HOST, COMFY_HOST_URL, COMFY_POLLING_INTERVAL_MS, COMFYUI_PATH, COMFYUI_LOG_PATH, COMFYUI_PORT, COMFY_POLLING_MAX_RETRIES, COMFY_API_AVAILABLE_MAX_RETRIES, EXTRA_MODEL_PATH, REFRESH_WORKER, get_job_item, restart_error, set_job_item
import logging
logging.basicConfig(level=logging.ERROR, format='%(asctime)s - %(levelname)s - %(message)s')

def validate_input(job_input):
    # Validate if job_input is provided
    if job_input is None:
        return None, "Please provide input"

    # Check if input is a string and try to parse it as JSON
    if isinstance(job_input, str):
        try:
            job_input = json.loads(job_input)
        except json.JSONDecodeError:
            return None, "Invalid JSON format in input"

    # Validate 'workflow' in input
    workflow = job_input.get("prompt")
    if workflow is None:
        return None, "Missing 'workflow' parameter"

    # Return validated data and no error
    return job_input, None


def check_server(url, retries=50, delay=500):
    """
    Check if a server is reachable via HTTP GET request
    - url (str): The URL to check
    - retries (int, optional): The number of times to attempt connecting to the server. Default is 50
    - delay (int, optional): The time in milliseconds to wait between retries. Default is 500
    """

    for i in range(retries):
        try:
            response = requests.get(url)

            # If the response status code is 200, the server is up and running
            if response.status_code == 200:
                print(f"runpod-worker-comfy - API is reachable")
                return True
        except requests.RequestException as e:
            # If an exception occurs, the server may not be ready
            pass

        # Wait for the specified delay before retrying
        time.sleep(delay / 1000)

    print(
        f"runpod-worker-comfy - Failed to connect to server at {url} after {retries} attempts."
    )
    return False


def upload_images(images):
    """
    Upload a list of base64 encoded images to the ComfyUI server using the /upload/image endpoint.

    Args:
        images (list): A list of dictionaries, each containing the 'name' of the image and the 'image' as a base64 encoded string.
        server_address (str): The address of the ComfyUI server.

    Returns:
        list: A list of responses from the server for each image upload.
    """
    if not images:
        return {"status": "success", "message": "No images to upload", "details": []}

    responses = []
    upload_errors = []

    print(f"runpod-worker-comfy - image(s) upload")

    for image in images:
        name = image["name"]
        image_data = image["image"]
        blob = base64.b64decode(image_data)

        # Prepare the form data
        files = {
            "image": (name, BytesIO(blob), "image/png"),
            "overwrite": (None, "true"),
        }

        # POST request to upload the image
        response = requests.post(f"http://{COMFY_HOST}/upload/image", files=files)
        if response.status_code != 200:
            upload_errors.append(f"Error uploading {name}: {response.text}")
        else:
            responses.append(f"Successfully uploaded {name}")

    if upload_errors:
        print(f"runpod-worker-comfy - image(s) upload with errors")
        return {
            "status": "error",
            "message": "Some images failed to upload",
            "details": upload_errors,
        }

    print(f"runpod-worker-comfy - image(s) upload complete")
    return {
        "status": "success",
        "message": "All images uploaded successfully",
        "details": responses,
    }


def queue_workflow(workflow):
    """
    Queue a workflow to be processed by ComfyUI

    Args:
        workflow (dict): A dictionary containing the workflow to be processed

    Returns:
        dict: The JSON response from ComfyUI after processing the workflow
    """

    # The top level element "prompt" is required by ComfyUI
    data = json.dumps({"prompt": workflow}).encode("utf-8")

    req = urllib.request.Request(f"http://{COMFY_HOST}/prompt", data=data)
    return json.loads(urllib.request.urlopen(req).read())


def get_history(prompt_id):
    """
    Retrieve the history of a given prompt using its ID

    Args:
        prompt_id (str): The ID of the prompt whose history is to be retrieved

    Returns:
        dict: The history of the prompt, containing all the processing steps and results
    """
    with urllib.request.urlopen(f"http://{COMFY_HOST}/history/{prompt_id}") as response:
        return json.loads(response.read())


def base64_encode(img_path):
    """
    Returns base64 encoded image.

    Args:
        img_path (str): The path to the image

    Returns:
        str: The base64 encoded image
    """
    with open(img_path, "rb") as image_file:
        encoded_string = base64.b64encode(image_file.read()).decode("utf-8")
        return f"{encoded_string}"

def process_image(image_path):
    """ Determine processing type based on environment and process the image """
    if not os.path.exists(image_path):
        print(f"Error: File does not exist - {image_path}")
        return None
    
    if os.environ.get("AWS_ACCESS_KEY_ID", False):
        # Adjust the bucket name as per your configuration
        return upload_file_to_s3(image_path)
    else:
        return base64_encode(image_path)

from typing import Dict, List, TypedDict

class Image(TypedDict):
    filename: str
    subfolder: str
    type: str
    format: str

Outputs = Dict[str, dict[str, List[Image]]]

def process_output_images(outputs: Outputs):
    """
    Args:
        outputs (dict): A dictionary containing the outputs from image generation,
                        typically includes node IDs and their respective output data.
        job_id (str): The unique identifier for the job.
    Returns:
        dict: { "images": [image] } or { "error": "messaage" }
    - It first determines the output path for the images from an environment variable,
      defaulting to "/comfyui/output" if not set.
    - It then iterates through the outputs to find the filenames of the generated images.
    """
    print('process output', outputs)
    if not outputs:
        print("runpod-worker-comfy - no outputs found")
        return {
            "error": "No outputs found",
        }

    output_images = []
    """ example outputs: {
        "10": {
            "gifs": [
                {
                    "filename": "readme_00001.gif",
                    "subfolder": "AnimateDiff",
                    "type": "temp",
                    "format": "image/gif"
                }
            ]
        }
    }
    """
    for node_id, node_output in outputs.items():
        for output_type, output in node_output.items():
            for image in output:
                if not isinstance(image, dict) or "filename" not in image:
                    continue
                try:
                    subfolder = image.get("subfolder", "")
                    type = image.get("type", "output")
                    image_path = os.path.join(COMFYUI_PATH, type, subfolder, image.get("filename"))
                    if image_path not in output_images and type == "output": # only process output images, no temp images
                        output_images.append(image_path)
                except Exception as e:
                    print(f"Error processing output in: node [{node_id}] {image} - {e}")
                    print(traceback.format_exc())
            
    # Path correction if needed
    # output_images = [f"{COMFYUI_PATH}/{type}/{filename}" for filename in output_images]
    print(f"output image path: {output_images}")
    results = []
    # Process images in parallel
    with ThreadPoolExecutor() as executor:
        future_to_image = {executor.submit(process_image, img_path): img_path for img_path in output_images}
        for future in as_completed(future_to_image):
            img_path = future_to_image[future]
            try:
                result = future.result()
                if result is not None:
                    results.append(result)
                print(f"Image processed: {result}")
            except Exception as exc:
                print(f"{img_path} generated an exception: {exc}")
    print(f"🗂️🌩️ All Images processed: {results}")
    return {
        "images": results
    }

def handler(job):
    print(f"🧪🧪handler received job", job['id'])
    job_input = job["input"]
    job_item = job_input.get('jobItem', {})
    job_item = {**job_item, 'id': job['id']}

    if job_input.get('object_info', False):
        print('📡 Getting object_info....')
        server_online = check_server(
            f"http://{COMFY_HOST}",
            COMFY_API_AVAILABLE_MAX_RETRIES, # 15sec
            COMFY_API_AVAILABLE_INTERVAL_MS,
        )
        if not server_online:
            return {"error": "ComfyUI API is not available, please try again later."}
        resp = requests.get(f'{COMFY_HOST_URL}/object_info')
        dict_resp = json.loads(resp.text)
        return {'data': resp.text}
    if job_input.get('list_models', False):
        print('📡 Listing models....')
        supported_pt_extensions = ['.ckpt', '.pt', '.bin', '.pth', '.safetensors', '.pkl']
        models_data1 = list_models(EXTRA_MODEL_PATH, 'volume')
        models_data2 = list_models(os.path.join(COMFYUI_PATH, 'models'), 'native')
        return {'data': {
            **models_data1,
            **models_data2,
        }}

    if job_input.get('install_models', False):
        print('📡 Installing models....')
        models_data = install_models(job_input.get('install_models'), EXTRA_MODEL_PATH)
        return {'data': models_data}
        
    if job_input.get('comfyui', False):
        print('📡 Starting up comfyui....')
        server_online = check_server(
            f"http://{COMFY_HOST}",
            COMFY_API_AVAILABLE_MAX_RETRIES, # 15sec
            COMFY_API_AVAILABLE_INTERVAL_MS,
        )
        if not server_online:
            return {"error": "ComfyUI API is not available, please try again later."}
        p = subprocess.Popen(["cloudflared", "tunnel", "--url", f"http://127.0.0.1:{COMFYUI_PORT}"], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        tunnel_url = None
        for line in p.stderr:
            l = line.decode()
            if "trycloudflare.com " in l:
                print("👉This is the URL to access ComfyUI:", l[l.find("http"):], end='')
                tunnel_url = True
                break
        if tunnel_url:
            # Sleep for 600 seconds
            time.sleep(1200)
            return {'session': 'finished'}
        return {'error': 'Error local tunneling comfyui'}

    set_job_item({**job_item, "startedAt": datetime.datetime.now().isoformat()})
    start_continuous_s3_log_upload_thread()
    # Make sure that the input is valid
    validated_data, error_message = validate_input(job_input)
    if error_message:
        return {"error": error_message}

    # Extract validated data
    prompt = validated_data["prompt"]
    deps = validated_data.get("deps")
    time_start = time.perf_counter()
    if deps:
        try:
            prompt = install_prompt_deps(prompt, deps, job_item)
        except Exception as e:
            append_comfyui_log('❌Error install_prompt_deps:', str(e))
            set_job_item({"status": "FAIL", "finishedAt": datetime.datetime.now().isoformat()})
            updateRunJobLogs(get_job_item())
            return {"error": f"Error installing prompt dependencies: {str(e)}"}
    set_job_item({"install_finished_at": datetime.datetime.now().isoformat()})
    append_log_thread('🦄Finished installing, waiting for server...')
    # Make sure that the ComfyUI API is available
    server_online = check_server(
        f"http://{COMFY_HOST}",
        COMFY_API_AVAILABLE_MAX_RETRIES, # 15sec
        COMFY_API_AVAILABLE_INTERVAL_MS,
    )
    if not server_online:
        set_job_item({"status": "FAIL", "finishedAt": datetime.datetime.now().isoformat(), error: "ComfyUI API is not available, please try again later."})
        return {"error": "ComfyUI API is not available, please try again later."}
    append_log_thread('🦄Server is online, starting workflow...')
    
    # refresh server file lists
    requests.get(f'{COMFY_HOST_URL}/object_info')

    # Queue the workflow
    try:
        queued_workflow = queue_workflow(prompt)
        prompt_id = queued_workflow["prompt_id"]
        start_tunnel_thread(job_item)
        print(f"runpod-worker-comfy queued workflow with ID {prompt_id}")
    except Exception as e:
        print('❌Error queue_workflow:', str(e))
        updateRunJobLogs({"id": job["id"], 
                **job_item,
                "status": "FAIL", 
                "finishedAt": datetime.datetime.now().isoformat(),
                "error": f"Error queuing workflow: {str(e)}",
                "duration": time.perf_counter() - time_start,
            })
        return {"error": f"Error queuing workflow: {str(e)}"}

    # Poll for completion
    print(f"⌛️ wait until image generation is complete")
    retries = 0
    error = None
    images_result = {}
    try:
        while retries < COMFY_POLLING_MAX_RETRIES:
            history = get_history(prompt_id)
            
            # Exit the loop if we have found the history
            if prompt_id in history and history[prompt_id].get("outputs"):
                print('🎨🖼️ Image generated history[prompt_id]:', history[prompt_id])
                images_result = process_output_images(history[prompt_id].get("outputs"))
                if images_result.get("error"):
                    error = images_result["error"]
                break
            else:
                # Wait before trying again
                time.sleep(COMFY_POLLING_INTERVAL_MS / 1000)
                retries += 1
        else:
            error = "Max retries reached while waiting for image generation"
    except Exception as e: 
        error = "error waiting for image generation"
        print('❌Error polling for completion:', str(e))

    set_job_item({
        "status": "FAIL" if error else "SUCCESS", 
        "finishedAt": datetime.datetime.now().isoformat(),
        "output": images_result.get("images", None),
        "error": error,
        "duration": time.perf_counter() - time_start,
    })
    updateRunJob(get_job_item())
    # disable hash renaming
    # rename_file_with_hash()
    return {**get_job_item(), "refresh_worker": REFRESH_WORKER}

if __name__ == "__main__":
    runpod.serverless.start({"handler": handler})

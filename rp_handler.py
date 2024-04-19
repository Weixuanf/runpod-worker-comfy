import asyncio
from decimal import Decimal
import runpod
import datetime
from runpod.serverless.utils import rp_upload
import json
import urllib.request
import urllib.parse
import time
import os
import requests
import base64
from io import BytesIO
from app.clearCustomNodesFolder import clear_except_allowed_folder
from dotenv import load_dotenv
from app.comfy_subprocess import restart, start_aiohttp_server_subprocess, start_comfyui_subprocess
from app.ddb_utils import finishJobWithError, updateRunJob, updateRunJobLogs
from app.install_prompt_deps import install_prompt_deps
from app.logUtils import clear_comfyui_log
from app.s3_utils import upload_file_to_s3
load_dotenv()
from app.common import COMFY_API_AVAILABLE_INTERVAL_MS, COMFY_HOST, COMFY_HOST_URL, COMFY_POLLING_INTERVAL_MS, COMFYUI_PATH, COMFYUI_LOG_PATH, IS_SCANNER_WORKER, COMFY_POLLING_MAX_RETRIES, COMFY_API_AVAILABLE_MAX_RETRIES, REFRESH_WORKER, restart_error

def validate_input(job_input):
    """
    Validates the input for the handler function.

    Args:
        job_input (dict): The input data to validate.

    Returns:
        tuple: A tuple containing the validated data and an error message, if any.
               The structure is (validated_data, error_message).
    """
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

    Args:
    - url (str): The URL to check
    - retries (int, optional): The number of times to attempt connecting to the server. Default is 50
    - delay (int, optional): The time in milliseconds to wait between retries. Default is 500

    Returns:
    bool: True if the server is reachable within the given number of retries, otherwise False
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


def process_output_images(outputs, job_id):
    """
    This function takes the "outputs" from image generation and the job ID,
    then determines the correct way to return the image, either as a direct URL
    to an AWS S3 bucket or as a base64 encoded string, depending on the
    environment configuration.

    Args:
        outputs (dict): A dictionary containing the outputs from image generation,
                        typically includes node IDs and their respective output data.
        job_id (str): The unique identifier for the job.

    Returns:
        dict: A dictionary with the status ('success' or 'error') and the message,
              which is either the URL to the image in the AWS S3 bucket or a base64
              encoded string of the image. In case of error, the message details the issue.

    The function works as follows:
    - It first determines the output path for the images from an environment variable,
      defaulting to "/comfyui/output" if not set.
    - It then iterates through the outputs to find the filenames of the generated images.
    - After confirming the existence of the image in the output folder, it checks if the
      AWS S3 bucket is configured via the BUCKET_ENDPOINT_URL environment variable.
    - If AWS S3 is configured, it uploads the image to the bucket and returns the URL.
    - If AWS S3 is not configured, it encodes the image in base64 and returns the string.
    - If the image file does not exist in the output folder, it returns an error status
      with a message indicating the missing image file.
    """

    # The path where ComfyUI stores the generated images
    COMFY_OUTPUT_PATH = os.environ.get("COMFY_OUTPUT_PATH", f"{COMFYUI_PATH}/output")

    output_images = {}

    for node_id, node_output in outputs.items():
        if "images" in node_output:
            for image in node_output["images"]:
                output_images = image["filename"]

    print(f"runpod-worker-comfy - image generation is done")

    # expected image output folder
    local_image_path = f"{COMFY_OUTPUT_PATH}/{output_images}"

    print(f"runpod-worker-comfy - {local_image_path}")

    # The image is in the output folder
    if os.path.exists(local_image_path):
        if os.environ.get("AWS_ACCESS_KEY_ID", False):
            # URL to image in AWS S3
            image = upload_file_to_s3(local_image_path)
            print(
                "runpod-worker-comfy - the image was generated and uploaded to AWS S3"
            )
        else:
            # base64 image
            image = base64_encode(local_image_path)
            print(
                "runpod-worker-comfy - the image was generated and converted to base64"
            )

        return {
            "images": [image],
        }
    else:
        print("runpod-worker-comfy - the image does not exist in the output folder")
        return {
            "error": f"the image does not exist in the specified output folder: {local_image_path}",
        }

def handler(job):
    print(f"🧪🧪handler received job")
    job_input = job["input"]

    # Make sure that the input is valid
    validated_data, error_message = validate_input(job_input)
    if error_message:
        return {"error": error_message}

    # Extract validated data
    prompt = validated_data["prompt"]
    deps = validated_data.get("deps")
    time_start = time.perf_counter()
    clear_comfyui_log()
    asyncio.create_task(asyncio.to_thread(updateRunJob, {"id": job["id"], "status": "INSTALLING_DEPS", "startedAt": datetime.datetime.now().replace(microsecond=0).isoformat()}))
    if deps:
        prompt = install_prompt_deps(prompt, deps)
    time_finish_install = time.perf_counter()
    # Make sure that the ComfyUI API is available
    server_online = check_server(
        f"http://{COMFY_HOST}",
        30, # 15sec
        500,
    )
    if not server_online:
        finishJobWithError(job["id"], "ComfyUI API is not available, please try again later.")
        return {"error": "ComfyUI API is not available, please try again later."}
    # refresh server file lists
    requests.get(f'{COMFY_HOST_URL}/object_info')

    # Queue the workflow
    try:
        queued_workflow = queue_workflow(prompt)
        prompt_id = queued_workflow["prompt_id"]
        print(f"runpod-worker-comfy queued workflow with ID {prompt_id}")
    except Exception as e:
        finishJobWithError(job["id"], f"Error queuing workflow: {str(e)}")
        return {"error": f"Error queuing workflow: {str(e)}"}

    # Poll for completion
    print(f"runpod-worker-comfy - wait until image generation is complete")
    retries = 0
    
    try:
        while retries < COMFY_POLLING_MAX_RETRIES:
            # update log in ddb
            if retries % 5 == 0:
                updateRunJobLogs({"id": job["id"], "status": "RUNNING"})

            history = get_history(prompt_id)

            # Exit the loop if we have found the history
            if prompt_id in history and history[prompt_id].get("outputs"):
                print('✅ Image generated history[prompt_id]:', history[prompt_id])
                break
            else:
                # Wait before trying again
                time.sleep(COMFY_POLLING_INTERVAL_MS / 1000)
                retries += 1
        else:
            finishJobWithError(job["id"], "Max retries reached while waiting for image generation")
            return {"error": "Max retries reached while waiting for image generation"}
    except Exception as e:
        finishJobWithError(job["id"], "error waiting for image generation")
        return {"error": "error waiting for image generation"}

    # Get the generated image and return it as URL in an AWS bucket or as base64
    images_result = process_output_images(history[prompt_id].get("outputs"), job["id"])

    error = None
    if images_result.get("error"):
        error = images_result["error"]

    updateRunJob({"id": job["id"], 
        "status": "FAIL" if error else "SUCCESS", 
        "finishedAt": datetime.datetime.now().replace(microsecond=0).isoformat(),
        "output": images_result.get("images", None),
        "error": error,
        "duration": Decimal(str(time.perf_counter() - time_start)),
        "installDuration": Decimal(str(time_finish_install - time_start)),
    })
    return {**images_result, "refresh_worker": REFRESH_WORKER}

if __name__ == "__main__":
    # print("Starting comfyui...")
    # start_comfyui_subprocess()
    if IS_SCANNER_WORKER: 
        print("Starting aiohttp server...")
        start_aiohttp_server_subprocess()
    runpod.serverless.start({"handler": handler})

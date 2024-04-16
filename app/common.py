import os
CONTAINER_ROOT = os.path.dirname(os.path.dirname(__file__))
COMFYUI_PATH = os.path.join(CONTAINER_ROOT, 'comfyui')
print(f'👉COMFYUI_PATH: {COMFYUI_PATH}')
COMFYUI_PORT = "8080"
MODEL_PATHS = [f'{COMFYUI_PATH}/models']
COMFY_HOST = f"127.0.0.1:{COMFYUI_PORT}"
COMFY_HOST_URL = f"http://{COMFY_HOST}"
# Time to wait between API check attempts in milliseconds
COMFY_API_AVAILABLE_INTERVAL_MS = 50
# Maximum number of API check attempts
COMFY_API_AVAILABLE_MAX_RETRIES = 500
# Time to wait between poll attempts in milliseconds
COMFY_POLLING_INTERVAL_MS = 250
# Maximum number of poll attempts
COMFY_POLLING_MAX_RETRIES = 500
# Host where ComfyUI is running
# Enforce a clean state after each job is done
# see https://docs.runpod.io/docs/handler-additional-controls#refresh-worker
REFRESH_WORKER = os.environ.get("REFRESH_WORKER", "false").lower() == "true"


# for scanner
IS_SCANNER_WORKER = os.environ.get('IS_SCANNER_WORKER', False)
restart_error = ""

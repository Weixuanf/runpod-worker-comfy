from app.common import COMFYUI_LOG_PATH


def append_comfyui_log(log:str):
    with open(COMFYUI_LOG_PATH, "a") as f:
        f.write("\n" + log + "\n")

def clear_comfyui_log():
    with open(COMFYUI_LOG_PATH, "w") as f:
        f.write("")
#!/usr/bin/env bash

echo "Symlinking files from Network Volume"
rm -rf /workspace && \
  ln -s /runpod-volume /workspace

comfyui_path="/workspace/comfyui_0.1"
comfy_log_path="/comfyui.log"

echo "Starting ComfyUI API"
source /workspace/comfyui_0.1/venv/bin/activate
TCMALLOC="$(ldconfig -p | grep -Po "libtcmalloc.so.\d" | head -n 1)"
export LD_PRELOAD="${TCMALLOC}"
export PYTHONUNBUFFERED=true
cd $comfyui_path
python3 main.py --port 8080 >> "${comfy_log_path}" 2>&1 &
deactivate


echo "Starting RunPod Handler"
# Serve the API and don't shutdown the container
if [ "$SERVE_API_LOCALLY" == "true" ]; then
    python3 -u /rp_handler.py --rp_serve_api
else
    python3 -u /rp_handler.py
fi

touch "$comfy_log_path"
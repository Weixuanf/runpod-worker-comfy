#!/usr/bin/env bash

echo "Symlinking files from Network Volume"
rm -rf /workspace && \
  ln -s /runpod-volume /workspace

comfyui_path="/comfyui"
comfy_log_path="/comfyui.log"

echo "Starting ComfyUI API"
TCMALLOC="$(ldconfig -p | grep -Po "libtcmalloc.so.\d" | head -n 1)"
export LD_PRELOAD="${TCMALLOC}"
export PYTHONUNBUFFERED=true
cd $comfyui_path


# Serve the API and don't shutdown the container
if [ "$SERVE_API_LOCALLY" == "true" ]; then
    python3 -u /rp_handler.py --rp_serve_api
else
    python3 -u /rp_handler.py
fi

touch "$comfy_log_path"

#!/usr/bin/env bash

echo "Symlinking files from Network Volume"
rm -rf /workspace && \
  ln -s /runpod-volume /workspace
  
# Use libtcmalloc for better memory management
TCMALLOC="$(ldconfig -p | grep -Po "libtcmalloc.so.\d" | head -n 1)"
export LD_PRELOAD="${TCMALLOC}"

# echo "runpod-worker-comfy: Starting ComfyUI"
# python3 /comfyui/main.py --disable-auto-launch --disable-metadata &

echo "runpod-worker-comfy: Starting RunPod Handler"

# Serve the API and don't shutdown the container
if [ "$SERVE_API_LOCALLY" == "true" ]; then
    python3 -u /rp_handler.py --rp_serve_api
else
    python3 -u /rp_handler.py
fi
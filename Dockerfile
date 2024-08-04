# Use Nvidia CUDA base image
FROM nvidia/cuda:11.8.0-cudnn8-runtime-ubuntu22.04 as base

# Prevents prompts from packages asking for user input during installation
ENV DEBIAN_FRONTEND=noninteractive
# Prefer binary wheels over source distributions for faster pip installations
ENV PIP_PREFER_BINARY=1
# Ensures output from python is printed immediately to the terminal without buffering
ENV PYTHONUNBUFFERED=1 

# Install Python, git and other necessary tools
RUN apt-get update && apt-get install -y \
    python3.10 \
    python3-pip \
    git \
    wget \
    libgl1 \
    libglib2.0-0 \
    curl

# Clean up to reduce image size
RUN apt-get autoremove -y && apt-get clean -y && rm -rf /var/lib/apt/lists/*
RUN pip3 install --no-cache-dir torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu121
RUN  pip install --no-cache-dir xformers --no-deps
RUN  pip install insightface

# Clone ComfyUI repository
# RUN git clone --branch master --single-branch --depth 1 https://github.com/comfyanonymous/ComfyUI /comfyui
RUN git clone --branch master --single-branch https://github.com/comfyanonymous/ComfyUI /comfyui

# RUN git clone --branch main --single-branch --depth 1 https://github.com/ltdrdata/ComfyUI-Manager /comfyui/custom_nodes/ComfyUI-Manager

# Change working directory to ComfyUI
WORKDIR /comfyui

# Install ComfyUI dependencies
RUN pip3 install -r requirements.txt

# Go back to the root
WORKDIR /
RUN pip3 install -r requirements.txt
# RUN pip3 install runpod requests boto3 nanoid
# Install cloudflared
RUN wget https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-linux-amd64.deb \
    && dpkg -i cloudflared-linux-amd64.deb

# Set the DEPS_JSON environment variable to pass comfyui snapshot
ARG DEPS_JSON
ENV DEPS_JSON=${DEPS_JSON}

ADD scripts/manager_copy.py scripts/install_custom_nodes_BASIC.py scripts/deps.json ./scripts/

ADD scripts/put_files_in_models_folder.py ./scripts/
RUN python3 /scripts/put_files_in_models_folder.py

RUN python3 /scripts/install_custom_nodes_BASIC.py

# Add the start and the handler
ADD start.sh rp_handler.py test_input.json ./
ADD extra_model_paths.yaml /comfyui/
ADD app/ /app/

EXPOSE 8080

RUN chmod +x /start.sh

# Start the container
CMD /start.sh

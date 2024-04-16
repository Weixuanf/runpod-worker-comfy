from app.manager_copy import gitclone_install


CUSTOM_NODES_REPO = [
    # "https://github.com/WASasquatch/was-node-suite-comfyui",
    # "https://github.com/ltdrdata/ComfyUI-Impact-Pack",
    "https://github.com/Kosinkadink/ComfyUI-VideoHelperSuite",
    # "https://github.com/ssitu/ComfyUI_UltimateSDUpscale",
    # "https://github.com/rgthree/rgthree-comfy",
    "https://github.com/cubiq/ComfyUI_IPAdapter_plus",
    # "https://github.com/jags111/efficiency-nodes-comfyui",
    "https://github.com/Kosinkadink/ComfyUI-AnimateDiff-Evolved",
    "https://github.com/Fannovel16/comfyui_controlnet_aux",
    # "https://github.com/ZHO-ZHO-ZHO/ComfyUI-BRIA_AI-RMBG"
]

def install_custom_nodes():
    gitclone_install(CUSTOM_NODES_REPO)

install_custom_nodes()
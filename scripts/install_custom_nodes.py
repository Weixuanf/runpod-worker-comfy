from manager_copy import gitclone_install


CUSTOM_NODES_REPO = [
    "https://github.com/ltdrdata/ComfyUI-Impact-Pack",
    "https://github.com/Kosinkadink/ComfyUI-VideoHelperSuite",
    "https://github.com/ssitu/ComfyUI_UltimateSDUpscale",
    "https://github.com/rgthree/rgthree-comfy",
    "https://github.com/cubiq/ComfyUI_IPAdapter_plus",
    # "https://github.com/jags111/efficiency-nodes-comfyui",
    "https://github.com/Kosinkadink/ComfyUI-AnimateDiff-Evolved",
    "https://github.com/Fannovel16/comfyui_controlnet_aux",
    "https://github.com/huchenlei/ComfyUI-layerdiffuse",
    "https://github.com/kijai/ComfyUI-SUPIR",
    "https://github.com/cubiq/ComfyUI_essentials",
    "https://github.com/kijai/ComfyUI-KJNodes",
    "https://github.com/Kosinkadink/ComfyUI-Advanced-ControlNet",
    "https://github.com/pythongosssss/ComfyUI-WD14-Tagger",
    "https://github.com/WASasquatch/was-node-suite-comfyui",
    "https://github.com/pythongosssss/ComfyUI-Custom-Scripts",
    "https://github.com/RockOfFire/ComfyUI_Comfyroll_CustomNodes",
    "https://github.com/giriss/comfy-image-saver",
    # "https://github.com/ZHO-ZHO-ZHO/ComfyUI-BRIA_AI-RMBG"
]


gitclone_install(CUSTOM_NODES_REPO)



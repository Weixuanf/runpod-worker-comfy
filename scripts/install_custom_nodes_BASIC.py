import json
import subprocess
from manager_copy import gitclone_install
import os

plugins_json = os.environ.get("DEPS_JSON", None)

COMFYUI_PATH = os.environ.get("COMFYUI_PATH", "/comfyui") 

if plugins_json:
    plugins = json.loads(plugins_json)
else:
    if not os.path.exists("./scripts/deps.json"):
        raise Exception("❌deps.json not found")
    with open("./scripts/deps.json", "r") as f:
        plugins = json.load(f)

comfyui_commit = plugins.get("comfyui")
custom_nodes = plugins.get("git_custom_nodes", {})


# Checkout specific commit for comfyui
if comfyui_commit:
    print(f"🦄Updating ComfyUI repository...")
    
    update_result = subprocess.run(["git", "pull"], cwd=COMFYUI_PATH, capture_output=True, text=True)
    if update_result.returncode != 0:
        raise Exception(f"❌Git pull failed: {update_result.stderr}")
    
    print(f"🦄Checking out ComfyUI to commit: {comfyui_commit}")
    result = subprocess.run(["git", "checkout", comfyui_commit], cwd=COMFYUI_PATH, capture_output=True, text=True)
    if result.returncode != 0:
        raise Exception(f"❌Git checkout failed: {result.stderr}")
    
gitclone_install(custom_nodes)
        


# BASIC_CUSTOM_NODES_REPO = {
#     "https://github.com/ltdrdata/ComfyUI-Impact-Pack": 'aad58a99bf6dfb2fededea82a011c1e72418bff4',
#     "https://github.com/Kosinkadink/ComfyUI-VideoHelperSuite": '1f46b5c3ae9b4e30f721bee83d9cb7b9f270d8cd',
#     "https://github.com/ssitu/ComfyUI_UltimateSDUpscale": '233f8b8ef999c35d1bdf98741632234977e6719f',
#     "https://github.com/rgthree/rgthree-comfy": 'd233e0fa5e8abd181d9180986db93036a719b925',
#     "https://github.com/cubiq/ComfyUI_IPAdapter_plus": '7d8adaec730bff243cc3026eed5111695cc5ed4e',
#     "https://github.com/Kosinkadink/ComfyUI-AnimateDiff-Evolved": '72482e70f73336a3dd61cbf9cc7d973137e9b33d',
#     "https://github.com/Fannovel16/comfyui_controlnet_aux":'589af18adae7ff50009a0e021781dd1aa39c32e3',
#     "https://github.com/huchenlei/ComfyUI-layerdiffuse": 'c5f1c0aa45592d2f48764472db3f7d2da622b6f1',
#     "https://github.com/cubiq/ComfyUI_essentials": '4f2f11ca3c6f89e385bae8af739861f495e60540',
#     "https://github.com/kijai/ComfyUI-SUPIR": 'bbb2bd7e8f241100c3ff6d8aa49dda512fef0d55',
#     "https://github.com/kijai/ComfyUI-KJNodes": '2fb0ee4934a240ddf75e63bc4f780ac6a61e2ac8',
#     "https://github.com/Kosinkadink/ComfyUI-Advanced-ControlNet": 'bf16347fd09ec14f8e6e9d5b5f31bb7561395275',
#     "https://github.com/pythongosssss/ComfyUI-WD14-Tagger": '4f1a857ff1a73ad2b4cbaf1f487e6aeaf802d226',
#     "https://github.com/WASasquatch/was-node-suite-comfyui": '43039ea455fc4a4f99f38048273f72a75a0523c0',
#     "https://github.com/pythongosssss/ComfyUI-Custom-Scripts": 'edc5321bfd3d8f77cace0a69b46e129d99b53c3d',
#     "https://github.com/RockOfFire/ComfyUI_Comfyroll_CustomNodes": 'd78b780ae43fcf8c6b7c6505e6ffb4584281ceca',
#     "https://github.com/giriss/comfy-image-saver": '65e6903eff274a50f8b5cd768f0f96baf37baea1', 
# }





import os
import re
import sys
import threading
import locale
import subprocess  # don't remove this
from tqdm.auto import tqdm
from urllib.parse import urlparse
from datetime import datetime
import platform
import subprocess
import time
import git
from git.remote import RemoteProgress

COMFYUI_PATH = "/comfyui"  #network volume
pip_downgrade_blacklist = ['torch', 'torchsde', 'torchvision', 'transformers', 'safetensors', 'kornia']
custom_nodes_path = os.path.join(COMFYUI_PATH, "custom_nodes")

class GitProgress(RemoteProgress):
    def __init__(self):
        super().__init__()
        self.pbar = tqdm()

    def update(self, op_code, cur_count, max_count=None, message=''):
        self.pbar.total = max_count
        self.pbar.n = cur_count
        self.pbar.pos = 0
        self.pbar.refresh()

def gitclone_install(files: dict[str, str]):
    for url,node in files.items():
        commit_hash = node.get('hash', None)
        print(f"Installing: {url} 👉 commit: {commit_hash}")
        # if not is_valid_url(url):
        #     print(f"Invalid git url: '{url}'")
        #     return False

        if url.endswith("/"):
            url = url[:-1]
        
        print(f"Download: git clone '{url}'")
        repo_name = os.path.splitext(os.path.basename(url))[0]
        repo_path = os.path.join(custom_nodes_path, repo_name)
        if repo_name == "ComfyUI-Manager":
            print(f"🦄 Skipping ComfyUI-Manager")
            continue

        # Clone the repository from the remote URL
        if None:
        # if platform.system() == 'Windows':
            res = run_script([sys.executable, git_script_path, "--clone", custom_nodes_path, url])
            if res != 0:
                return False
        else:
            repo = git.Repo.clone_from(url, repo_path, recursive=True, progress=GitProgress())

            # Checkout to the specified commit hash if it's not None
            if commit_hash is not None:
                repo.git.checkout(commit_hash)
                print(f"🦄Checkout to commit hash: {commit_hash}")

            repo.git.clear_cache()
            repo.close()

        if not execute_install_script(url, repo_path):
            print('🦄❌ Failed to install {url}')
            raise Exception(f"Failed to install {url}")
            return False


    print("Installation was successful.")
    return True

def run_script(cmd, cwd='.'):
    if len(cmd) > 0 and cmd[0].startswith("#"):
        print(f"[ComfyUI-Manager] Unexpected behavior: `{cmd}`")
        return 0

    process = subprocess.Popen(cmd, cwd=cwd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, bufsize=1)

    stdout_thread = threading.Thread(target=handle_stream, args=(process.stdout, ""))
    stderr_thread = threading.Thread(target=handle_stream, args=(process.stderr, "[!]"))

    stdout_thread.start()
    stderr_thread.start()

    stdout_thread.join()
    stderr_thread.join()

    return process.wait()


def handle_stream(stream, prefix):
    stream.reconfigure(encoding=locale.getpreferredencoding(), errors='replace')
    for msg in stream:
        if prefix == '[!]' and ('it/s]' in msg or 's/it]' in msg) and ('%|' in msg or 'it [' in msg):
            if msg.startswith('100%'):
                print('\r' + msg, end="", file=sys.stderr),
            else:
                print('\r' + msg[:-1], end="", file=sys.stderr),
        else:
            if prefix == '[!]':
                print(prefix, msg, end="", file=sys.stderr)
            else:
                print(prefix, msg, end="")

def execute_install_script(url, repo_path, lazy_mode=False, instant_execution=False):
    install_script_path = os.path.join(repo_path, "install.py")
    requirements_path = os.path.join(repo_path, "requirements.txt")

    if lazy_mode:
        install_cmd = ["#LAZY-INSTALL-SCRIPT",  sys.executable]
        try_install_script(url, repo_path, install_cmd)
    else:
        if os.path.exists(requirements_path):
            print("Install: pip packages")
            with open(requirements_path, "r") as requirements_file:
                for line in requirements_file:
                    package_name = line.strip()
                    if package_name and not package_name.startswith('#'):
                        install_cmd = [sys.executable, "-m", "pip", "install", package_name]
                        if package_name.strip() != "" and not package_name.startswith('#'):
                            if not try_install_script(url, repo_path, install_cmd, instant_execution=instant_execution):
                                print(f"🦄❌ Error: Failed to pip install {package_name} in {repo_path}")
                                return False

        if os.path.exists(install_script_path):
            print(f"Install: install script")
            install_cmd = [sys.executable, "install.py"]
            if not try_install_script(url, repo_path, install_cmd, instant_execution=instant_execution):
                print(f"🦄❌ Error: Failed to install install.py in {repo_path}")
                return False
    return True

def try_install_script(url, repo_path, install_cmd, instant_execution=False):
    if len(install_cmd) == 5 and install_cmd[2:4] == ['pip', 'install']:
        if is_blacklisted(install_cmd[4]):
            print(f"[ComfyUI-Manager] skip black listed pip installation: '{install_cmd[4]}'")
            return True

    print(f"\n## ComfyUI-Manager: EXECUTE => {install_cmd}")
    code = run_script(install_cmd, cwd=repo_path)

    if code != 0:
        if url is None:
            url = os.path.dirname(repo_path)
        print(f"install script failed: {url}")
        return False
    return True

def is_blacklisted(name):
    name = name.strip()

    pattern = r'([^<>!=]+)([<>!=]=?)(.*)'
    match = re.search(pattern, name)

    if match:
        name = match.group(1)

    if name in pip_downgrade_blacklist:
        return True
        # pips = get_installed_packages()

        # if match is None:
        #     if name in pips:
        #         return True
        # elif match.group(2) in ['<=', '==', '<']:
        #     if name in pips:
        #         if StrictVersion(pips[name]) >= StrictVersion(match.group(3)):
        #             return True

    return False

def get_installed_packages():
    global pip_map

    if pip_map is None:
        try:
            result = subprocess.check_output([sys.executable, '-m', 'pip', 'list'], universal_newlines=True)

            pip_map = {}
            for line in result.split('\n'):
                x = line.strip()
                if x:
                    y = line.split()
                    if y[0] == 'Package' or y[0].startswith('-'):
                        continue

                    pip_map[y[0]] = y[1]
        except subprocess.CalledProcessError as e:
            print(f"[ComfyUI-Manager] Failed to retrieve the information of installed pip packages.")
            return set()

    return pip_map

def install_pip_packages(packages: dict):
    for package in packages:
        print(f"\n\n 🦄Installing pip package: {package}")
        run_script([sys.executable, "-m", "pip", "install", package])
            

import os
import subprocess
# bake models into docker image
def install_models_to_docker_image(snapshot: dict):
    models = snapshot.get('models', {})
    for path, model in models.items():
        file_path = os.path.join(COMFYUI_PATH, 'models', path)
        url = model.get('url')
        type = model.get('type', 'native')
        if type != 'native':
            continue
        if not url:
            raise ValueError('❌🦄 Error: download url not found for model', path)
        
        # Ensure the directory exists
        os.makedirs(os.path.dirname(file_path), exist_ok=True)
        
        print(f"\n ⬇️Downloading model: {url} to {file_path}")
        
        # Download the model using wget
        try:
            # '--progress=bar:force' shows the progress bar
            subprocess.run(['wget', '--progress=bar:force', '-O', file_path, url], check=True)
            print(f"👌 Successfully downloaded model to {file_path}")
        except subprocess.CalledProcessError as e:
            print(f"❌ Error downloading model: {path} from {url}")
            raise e

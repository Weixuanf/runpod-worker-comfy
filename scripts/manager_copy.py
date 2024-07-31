import os
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
                            try_install_script(url, repo_path, install_cmd, instant_execution=instant_execution)

        if os.path.exists(install_script_path):
            print(f"Install: install script")
            install_cmd = [sys.executable, "install.py"]
            try_install_script(url, repo_path, install_cmd, instant_execution=instant_execution)

    return True

def try_install_script(url, repo_path, install_cmd, instant_execution=False):
    print(f"\n## ComfyUI-Manager: EXECUTE => {install_cmd}")
    code = run_script(install_cmd, cwd=repo_path)

    if code != 0:
        if url is None:
            url = os.path.dirname(repo_path)
        print(f"install script failed: {url}")
        return False

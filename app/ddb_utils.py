import threading
import requests
from .common import COMFYUI_LOG_PATH, COMFYUI_PORT
import datetime
import os 
import subprocess

#prompt job
def updateRunJob(item):
    try:
        url = os.environ.get("UPDATE_RUNJOB_API_URL", None)
        if url is None:
            raise ValueError("RUNJOB_API_URL environment variable not set")
        
        api_key = os.environ.get("UPDATE_RUNJOB_API_KEY", "")
        response = requests.post(url, json=item, headers={"Content-Type": "application/json", "Authorization": f"Bearer {api_key}"})
        
        # Check if the request was successful
        if response.status_code == 200:
            return response.json()
        else:
            print(f"❌🔴Error updating job item: {response.status_code} - {response.text}")
            return None
    except Exception as e:
        print("❌🔴Error updating job item:", e)
        return None

def updateRunJobLogs(item):
    with open(COMFYUI_LOG_PATH, 'r', encoding='utf-8') as f:
        content = f.read()
        if (item.get('finishedAt') is not None):
            print('🦄finished job, comfy logs:', content)
        return updateRunJob({
            **item,
            'logs': content
        })

def updateRunJobLogsThread(item):
    thread = threading.Thread(target=updateRunJobLogs, args=(item,))
    thread.start()

def finishJobWithError(id, error):
    return updateRunJob({
        'id': id,
        'error': error,
        'status': 'FAIL',
        "finishedAt": datetime.datetime.now().replace(microsecond=0).isoformat(),
    })

def run_tunnel(job_item):
    print("🚇Starting cloudflared tunnel...")
    p = subprocess.Popen(
        ["cloudflared", "tunnel", "--url", f"http://127.0.0.1:{COMFYUI_PORT}"],
        stdout=subprocess.PIPE, stderr=subprocess.PIPE
    )
    tunnel_url = None
    for line in p.stderr:
        l = line.decode()
        if "trycloudflare.com " in l:
            print("👉This is the URL to access ComfyUI:", l[l.find("http"):], end='')
            tunnel_url = l[l.find("http"):]
            print('tunnel url', tunnel_url)
            updateRunJob({
                **job_item,
                "tunnel": tunnel_url
            })
            break

def start_tunnel_thread(job_item):
    tunnel_thread = threading.Thread(target=run_tunnel, args=(job_item,))
    tunnel_thread.start()


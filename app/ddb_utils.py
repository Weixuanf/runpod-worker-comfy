import threading
import requests
from .common import COMFYUI_LOG_PATH
import datetime
import os 

#prompt job
def updateRunJob(item):
    try:
        id = item['id']  # Extract the primary key from the item
        
        # Define the URL
        url = os.environ.get("UPDATE_RUNJOB_API_URL", None)
        if url is None:
            raise ValueError("RUNJOB_API_URL environment variable not set")
        
        # Send the POST request
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
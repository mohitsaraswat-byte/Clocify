import os
import requests
import time
import random
import datetime

# --- CONFIGURATION ---
# We will securely store these in GitHub Secrets later!
API_KEY = os.environ.get("CLOCKIFY_API_KEY")
WORKSPACE_ID = os.environ.get("CLOCKIFY_WORKSPACE_ID")
USER_ID = os.environ.get("CLOCKIFY_USER_ID")
PROJECT_ID = "" # Optional: Add your project ID if you want to track to a specific project

BASE_URL = "https://api.clockify.me/api/v1"
HEADERS = {
    "X-Api-Key": API_KEY,
    "Content-Type": "application/json"
}

def get_running_timer():
    """Fetches the currently running time entry from Clockify, if any."""
    url = f"{BASE_URL}/workspaces/{WORKSPACE_ID}/user/{USER_ID}/time-entries"
    response = requests.get(url, headers=HEADERS, params={"page-size": 5})
    
    if response.status_code == 200:
        entries = response.json()
        for entry in entries:
            # If the end time is None, the timer is currently running
            if entry.get('timeInterval', {}).get('end') is None:
                return entry
    return None

def start_timer():
    """Starts a new time entry."""
    url = f"{BASE_URL}/workspaces/{WORKSPACE_ID}/time-entries"
    now_utc = datetime.datetime.utcnow().strftime('%Y-%m-%dT%H:%M:%SZ')
    payload = {"start": now_utc, "description": "Daily Automation"}
    if PROJECT_ID:
        payload["projectId"] = PROJECT_ID

    response = requests.post(url, headers=HEADERS, json=payload)
    if response.status_code in [200, 201]:
        print("Timer started successfully!")
    else:
        print(f"Error starting timer: {response.text}")

def stop_timer():
    """Stops the currently running time entry."""
    url = f"{BASE_URL}/workspaces/{WORKSPACE_ID}/user/{USER_ID}/time-entries"
    now_utc = datetime.datetime.utcnow().strftime('%Y-%m-%dT%H:%M:%SZ')
    payload = {"end": now_utc}

    response = requests.patch(url, headers=HEADERS, json=payload)
    if response.status_code in [200, 201]:
        print("Timer stopped successfully!")
    else:
        print(f"Error stopping timer: {response.text}")

def main():
    print(f"[{datetime.datetime.utcnow()}] Waking up to check Clockify status...")
    running_entry = get_running_timer()

    if running_entry is None:
        # NO TIMER RUNNING: Assume it is morning and we need to start.
        print("No running timer found. Initiating morning start routine...")
        
        # Random delay between 0 and 15 minutes (0 to 900 seconds)
        delay_seconds = random.randint(0, 900)
        print(f"Randomizing start time: Waiting {delay_seconds // 60} minutes and {delay_seconds % 60} seconds.")
        time.sleep(delay_seconds)
        
        start_timer()

    else:
        # TIMER IS RUNNING: Assume it is evening and we need to stop.
        print("Running timer found. Initiating evening stop routine...")
        start_time_str = running_entry['timeInterval']['start']
        
        # Convert Clockify's UTC start time string into a Python datetime object
        start_time = datetime.datetime.strptime(start_time_str, '%Y-%m-%dT%H:%M:%SZ')
        
        # Calculate random target duration between 8 hours (28800s) and 8 hours 15 mins (29700s)
        target_duration_seconds = random.randint(28800, 29700)
        target_stop_time = start_time + datetime.timedelta(seconds=target_duration_seconds)
        now_utc = datetime.datetime.utcnow()
        
        # Calculate how many seconds are left until we hit our target stop time
        wait_seconds = (target_stop_time - now_utc).total_seconds()
        
        if wait_seconds > 0:
            print(f"Target duration not met yet. Waiting {int(wait_seconds // 60)} minutes and {int(wait_seconds % 60)} seconds before stopping...")
            time.sleep(wait_seconds)
        else:
            print("Target duration already met or exceeded! Stopping immediately.")
        
        stop_timer()

if __name__ == "__main__":
    main()

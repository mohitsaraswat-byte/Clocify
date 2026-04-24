import os
import sys
import requests
import time
import random
import datetime

# ---------------------------------------------------------------------------
# CONFIGURATION — pulled from GitHub Secrets / environment variables
# ---------------------------------------------------------------------------
API_KEY      = os.environ.get("CLOCKIFY_API_KEY")
WORKSPACE_ID = os.environ.get("CLOCKIFY_WORKSPACE_ID")
USER_ID      = os.environ.get("CLOCKIFY_USER_ID")

BASE_URL = "https://api.clockify.me/api/v1"
HEADERS  = {
    "X-Api-Key": API_KEY or "",
    "Content-Type": "application/json",
}

# IST = UTC + 5:30  (no external library needed)
IST = datetime.timezone(datetime.timedelta(hours=5, minutes=30))

# ---------------------------------------------------------------------------
# PROJECT DESCRIPTIONS — one is picked at random for each day's entry
# ---------------------------------------------------------------------------
DESCRIPTION_LIST = [
    "Comic Series - Class 6",
    "Comic Series - Class 7",
    "Comic Series - Class 8",
    "Curios Junior Books (CJ Boo...)",
    "E-Book",
    "Games - PW Games - Class 6",
    "Games - PW Games - Class 7",
    "Games - PW Games - Class 8",
    "Games for books",
    "Interactive Book NCERT based",
]

# ---------------------------------------------------------------------------
# HELPERS
# ---------------------------------------------------------------------------

def validate_env():
    """Abort early if any required secret is missing."""
    missing = [k for k, v in {
        "CLOCKIFY_API_KEY":      API_KEY,
        "CLOCKIFY_WORKSPACE_ID": WORKSPACE_ID,
        "CLOCKIFY_USER_ID":      USER_ID,
    }.items() if not v]

    if missing:
        print(f"[ERROR] Missing environment variable(s): {', '.join(missing)}")
        print("        Add them to your GitHub Secrets and re-run.")
        sys.exit(1)


def now_utc() -> datetime.datetime:
    """Current time as a timezone-aware UTC datetime."""
    return datetime.datetime.now(datetime.timezone.utc)


def now_ist() -> datetime.datetime:
    """Current time in IST."""
    return datetime.datetime.now(IST)


def fmt_utc(dt: datetime.datetime) -> str:
    """Format a UTC datetime for the Clockify API."""
    return dt.astimezone(datetime.timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')


def get_all_projects() -> list:
    """
    Fetch ALL active projects from the workspace (handles pagination).
    Returns an empty list on any error.
    """
    url = f"{BASE_URL}/workspaces/{WORKSPACE_ID}/projects"
    all_projects = []
    page = 1

    while True:
        try:
            resp = requests.get(
                url,
                headers=HEADERS,
                params={"page": page, "page-size": 50, "archived": "false"},
                timeout=15,
            )
            resp.raise_for_status()
        except requests.RequestException as exc:
            print(f"[ERROR] Could not fetch projects (page {page}): {exc}")
            break

        data = resp.json()
        if not data:
            break
        all_projects.extend(data)
        if len(data) < 50:      # last page
            break
        page += 1

    print(f"[INFO] Fetched {len(all_projects)} project(s) from workspace.")
    return all_projects


def find_project_id(projects: list, name: str) -> str | None:
    """Return the Clockify project ID that matches 'name', or None."""
    for p in projects:
        if p.get("name", "").strip() == name.strip():
            return p["id"]
    return None


def get_running_timer() -> dict | None:
    """
    Returns the currently running time-entry dict, or None.
    Uses the official Clockify 'in-progress' filter — reliable and exact.
    """
    url = f"{BASE_URL}/workspaces/{WORKSPACE_ID}/user/{USER_ID}/time-entries"
    try:
        resp = requests.get(
            url,
            headers=HEADERS,
            params={"in-progress": "true", "page-size": 1},
            timeout=15,
        )
        resp.raise_for_status()
    except requests.RequestException as exc:
        print(f"[ERROR] Could not check for running timer: {exc}")
        return None

    entries = resp.json()
    # The API returns a list; if in-progress exists it will be the only item.
    for entry in entries:
        if entry.get("timeInterval", {}).get("end") is None:
            return entry
    return None


def start_timer(description: str, project_id: str | None):
    """Start a new Clockify time entry right now."""
    url = f"{BASE_URL}/workspaces/{WORKSPACE_ID}/time-entries"
    payload: dict = {
        "start": fmt_utc(now_utc()),
        "description": description,
    }
    if project_id:
        payload["projectId"] = project_id

    try:
        resp = requests.post(url, headers=HEADERS, json=payload, timeout=15)
        resp.raise_for_status()
        print(f"[OK] Timer started — project: '{description}'")
    except requests.RequestException as exc:
        print(f"[ERROR] Could not start timer: {exc}")
        if hasattr(exc, "response") and exc.response is not None:
            print(f"       API response: {exc.response.text}")


def stop_timer():
    """Stop the currently running Clockify time entry."""
    url = f"{BASE_URL}/workspaces/{WORKSPACE_ID}/user/{USER_ID}/time-entries"
    payload = {"end": fmt_utc(now_utc())}

    try:
        resp = requests.patch(url, headers=HEADERS, json=payload, timeout=15)
        resp.raise_for_status()
        print("[OK] Timer stopped successfully.")
    except requests.RequestException as exc:
        print(f"[ERROR] Could not stop timer: {exc}")
        if hasattr(exc, "response") and exc.response is not None:
            print(f"       API response: {exc.response.text}")


# ---------------------------------------------------------------------------
# MAIN LOGIC
# ---------------------------------------------------------------------------

def main():
    # 1. Fail fast if secrets are missing
    validate_env()

    ist_now = now_ist()
    ist_hour = ist_now.hour
    print(f"[INFO] Current IST time: {ist_now.strftime('%Y-%m-%d %H:%M:%S %Z')}")

    # ------------------------------------------------------------------
    # MORNING WINDOW  →  10:00 AM – 10:15 AM IST  →  START timer
    # ------------------------------------------------------------------
    if 10 <= ist_hour < 11:
        print("[MODE] Morning detected — will start timer.")

        running = get_running_timer()
        if running:
            print("[SKIP] A timer is already running. Nothing to do.")
            return

        # Random delay: 0 – 15 minutes (matches the 10:00–10:15 AM window)
        delay_seconds = random.randint(0, 900)
        print(f"[WAIT] Sleeping {delay_seconds // 60}m {delay_seconds % 60}s "
              f"before starting...")
        time.sleep(delay_seconds)

        # Pick a random description and match it to a Clockify project
        description = random.choice(DESCRIPTION_LIST)
        projects    = get_all_projects()
        project_id  = find_project_id(projects, description)

        if project_id is None:
            print(f"[WARN] No exact project match for '{description}'. "
                  f"Entry will be created without a project link.")

        start_timer(description, project_id)

    # ------------------------------------------------------------------
    # EVENING WINDOW  →  6:00 PM – 6:15 PM IST  →  STOP timer
    # ------------------------------------------------------------------
    elif 18 <= ist_hour < 19:
        print("[MODE] Evening detected — will stop timer.")

        running = get_running_timer()
        if running is None:
            print("[SKIP] No running timer found. Nothing to stop.")
            return

        # Random delay: 0 – 15 minutes (matches the 6:00–6:15 PM window)
        delay_seconds = random.randint(0, 900)
        print(f"[WAIT] Sleeping {delay_seconds // 60}m {delay_seconds % 60}s "
              f"before stopping...")
        time.sleep(delay_seconds)

        stop_timer()

    # ------------------------------------------------------------------
    # UNEXPECTED TRIGGER TIME — do nothing safely
    # ------------------------------------------------------------------
    else:
        print(f"[WARN] Script triggered outside the expected windows "
              f"(IST hour = {ist_hour}). No action taken.")
        print("       Expected: 10 AM for start, 6 PM for stop.")


if __name__ == "__main__":
    main()

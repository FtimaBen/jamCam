import os
import json
import time
import subprocess
import requests

WORKER = int(os.environ["WORKER"])

CHUNK_FILE = f"chunks/chunk_{WORKER}.json"

if not os.path.exists(CHUNK_FILE):
    print("No chunk for worker", WORKER)
    exit(0)

with open(CHUNK_FILE, "r") as f:
    records = json.load(f)


def run(cmd):
    print(">", " ".join(cmd))
    subprocess.run(cmd, check=True)


def git_commit_push(file_path, message):
    while True:
        try:
            # Update local branch
            run(["git", "pull", "--rebase"])

            # Skip if file disappeared
            if not os.path.exists(file_path):
                return

            run(["git", "add", file_path])

            # Nothing to commit?
            status = subprocess.run(
                ["git", "status", "--porcelain", file_path],
                capture_output=True,
                text=True,
            )

            if status.stdout.strip() == "":
                return

            run(["git", "commit", "-m", message])

            run(["git", "push"])

            return

        except subprocess.CalledProcessError:
            print("Push conflict. Retrying in 5 seconds...")
            time.sleep(5)


session = requests.Session()

for record in records:

    cam_id = record["id"]
    dt = record["datetime"]
    url = record["url"]

    safe_dt = (
        dt.replace(":", "-")
          .replace("/", "-")
          .replace(" ", "_")
    )

    folder = cam_id
    os.makedirs(folder, exist_ok=True)

    filename = os.path.join(folder, safe_dt + ".mp4")

    # Check latest repo state
    run(["git", "pull", "--rebase"])

    if os.path.exists(filename):
        print("Already exists:", filename)
        continue

    print("Downloading", filename)

    try:
        r = session.get(url, stream=True, timeout=180)
        r.raise_for_status()

        with open(filename, "wb") as f:
            for chunk in r.iter_content(1024 * 1024):
                if chunk:
                    f.write(chunk)

    except Exception as e:
        print("Download failed:", e)
        if os.path.exists(filename):
            os.remove(filename)
        continue

    try:
        git_commit_push(
            filename,
            f"Add {cam_id} {safe_dt}"
        )

    except Exception as e:
        print("Git failed:", e)
        continue

    # Free runner disk space.
    # IMPORTANT: don't git add/commit after deleting.
    try:
        os.remove(filename)

        if not os.listdir(folder):
            os.rmdir(folder)

    except Exception:
        pass

print("Worker", WORKER, "finished.")
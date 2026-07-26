import os
import json
import requests
from math import ceil

API_URL = "https://api.tfl.gov.uk/Place/Type/JamCam"

os.makedirs("chunks", exist_ok=True)

print("Downloading TfL JSON...")

r = requests.get(API_URL, timeout=60)
r.raise_for_status()

items = r.json()

records = []
BASE_URL = "https://api.tfl.gov.uk"

for item in items:
    cam_id = item["id"]

    records.append({
        "id": cam_id,
        "datetime": item.get("modified"),
        "latitude": item.get("lat"),
        "longitude": item.get("lon"),
        "url": BASE_URL + item["url"]
    })
    
    cam_id = item.get("id")
    latitude = item.get("lat")
    longitude = item.get("lon")

    modified = item.get("modified")

    video_url = None

    for prop in item.get("additionalProperties", []):

        key = str(prop.get("key", "")).lower()
        value = prop.get("value")

        if key in [
            "videourl",
            "video_url",
            "videourlhd",
            "url",
            "streamurl",
            "video"
        ]:

            if value and str(value).startswith("http"):
                video_url = value
                break

    if video_url is None:
        continue

    records.append(
        {
            "id": cam_id,
            "datetime": modified,
            "latitude": latitude,
            "longitude": longitude,
            "url": video_url,
        }
    )

print(f"Found {len(records)} downloadable videos")

workers = 8
chunk_size = ceil(len(records) / workers)

for worker in range(workers):

    chunk = records[
        worker * chunk_size :
        (worker + 1) * chunk_size
    ]

    filename = f"chunks/chunk_{worker}.json"

    with open(filename, "w") as f:
        json.dump(chunk, f, indent=2)

    print(
        f"Worker {worker}: {len(chunk)} videos"
    )

print("Finished creating chunks.")
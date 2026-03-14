import time
import requests
import sys

base_url = "http://127.0.0.1:5000"
yt_url = "https://www.youtube.com/watch?v=jNQXAC9IVRw"

print("Uploading to /upload with youtube_url...")
try:
    r = requests.post(f"{base_url}/upload", data={"youtube_url": yt_url})
    res = r.json()
except Exception as e:
    print(f"Server not reachable: {e}")
    sys.exit(1)

if not res.get("success"):
    print("Upload failed:", res.get("error"))
    sys.exit(1)

filepath = res["filepath"]
print(f"Downloaded YT to filepath: {filepath}")

payload = {
    "filepath": filepath,
    "ranges": [{"start": 2, "end": 10}],
    "voice_lang": "hi-IN",
    "sub_lang": "hi",
    "gender": "male"
}

print(f"Starting processing task...")
r = requests.post(f"{base_url}/process", json=payload)
res = r.json()
if not res.get("success"):
    print("Process failed:", res.get("error"))
    sys.exit(1)

task_id = res["task_id"]
print(f"Polling status for task: {task_id}")

while True:
    r = requests.get(f"{base_url}/status/{task_id}")
    status = r.json()
    print(status["status"], "-", status.get("message"))
    if status["status"] == "Done":
        result_path = status["result_path"]
        print(f"Done! Result path: {result_path}")
        break
    elif status["status"] == "Error":
        print("Error in task!")
        sys.exit(1)
    time.sleep(3)

print("Verifying final video duration...")
try:
    from moviepy import VideoFileClip
    clip = VideoFileClip(result_path)
    dur = clip.duration
    print(f"Final video duration: {dur} seconds")
    if dur > 1.0:
        print("SUCCESS: Video is valid and has expected duration!")
    else:
        print("FAILURE: Video duration is too short / 0-second glitch still present.")
        sys.exit(1)
except Exception as e:
    print(f"Could not verify duration: {e}")
    sys.exit(1)

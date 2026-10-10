"""Bounded HTTP readiness poll used by CI."""
import sys
import time
import urllib.error
import urllib.request

for attempt in range(90):
    try:
        with urllib.request.urlopen(sys.argv[1], timeout=2) as response:
            if response.status == 200:
                print("HTTP readiness confirmed")
                break
    except (urllib.error.URLError, TimeoutError):
        pass
    time.sleep(1)
else:
    raise SystemExit("HTTP readiness deadline exceeded")

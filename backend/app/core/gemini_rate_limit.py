"""Optional process-wide Gemini request spacing for quota-safe evaluation runs."""
import os
import threading
import time

_lock = threading.Lock()
_last_request = 0.0


def wait_for_gemini_slot() -> None:
    interval = max(0.0, float(os.getenv("GEMINI_MIN_INTERVAL_SECONDS", "0")))
    if not interval:
        return
    global _last_request
    with _lock:
        delay = interval - (time.monotonic() - _last_request)
        if delay > 0:
            time.sleep(delay)
        _last_request = time.monotonic()

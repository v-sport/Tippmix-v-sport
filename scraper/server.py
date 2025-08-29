import threading
import os
from fastapi import FastAPI
from scraper.poller import run_loop


app = FastAPI()

_bg_thread = None


@app.on_event("startup")
def start_poller():
    global _bg_thread
    data_dir = os.environ.get("DATA_DIR", "/workspace/data")
    def _run():
        run_loop(data_dir)
    _bg_thread = threading.Thread(target=_run, daemon=True)
    _bg_thread.start()


@app.get("/health")
def health():
    return {"status": "ok"}


@app.get("/status")
def status():
    return {"poller": "running" if _bg_thread and _bg_thread.is_alive() else "stopped"}


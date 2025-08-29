import threading
import os
from fastapi import FastAPI, HTTPException
import json
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


def _read_json(path: str):
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="not found")


@app.get("/data/timings")
def data_timings():
    data_dir = os.environ.get("DATA_DIR", "/workspace/data")
    return _read_json(os.path.join(data_dir, "timings.json"))


@app.get("/data/matches")
def data_matches():
    data_dir = os.environ.get("DATA_DIR", "/workspace/data")
    return _read_json(os.path.join(data_dir, "matches.json"))


import queue
import threading
import json
import time
from datetime import datetime, timezone

from agents.orchestrator import Orchestrator

_task_queue = queue.Queue()
_results = {}
_results_lock = threading.Lock()

_orchestrator = None
_worker_thread = None


def _get_orchestrator():
    global _orchestrator
    if _orchestrator is None:
        _orchestrator = Orchestrator()
    return _orchestrator


def _worker_loop():
    """Background thread that processes complaints from the queue."""
    print("[queue_worker] Worker thread started.")
    while True:
        try:
            task = _task_queue.get(timeout=1)
        except queue.Empty:
            continue

        if task is None:
            print("[queue_worker] Shutdown signal received.")
            break

        task_id = task["task_id"]
        complaint_text = task["complaint_text"]

        print(f"[queue_worker] Processing task {task_id}...")
        with _results_lock:
            _results[task_id] = {"status": "processing", "task_id": task_id}

        try:
            orchestrator = _get_orchestrator()
            result = orchestrator.process_complaint(complaint_text)
            with _results_lock:
                _results[task_id] = {
                    "status": "complete",
                    "task_id": task_id,
                    "result": result,
                    "completed_at": datetime.now(timezone.utc).isoformat(),
                }
            print(f"[queue_worker] Task {task_id} complete.")

        except Exception as e:
            with _results_lock:
                _results[task_id] = {
                    "status": "failed",
                    "task_id": task_id,
                    "error": str(e),
                    "failed_at": datetime.now(timezone.utc).isoformat(),
                }
            print(f"[queue_worker] Task {task_id} failed: {e}")

        _task_queue.task_done()


def start_worker():
    """Start the background worker thread."""
    global _worker_thread
    if _worker_thread is None or not _worker_thread.is_alive():
        _worker_thread = threading.Thread(target=_worker_loop, daemon=True)
        _worker_thread.start()


def enqueue_complaint(task_id: str, complaint_text: str):
    """Add a complaint to the processing queue."""
    _task_queue.put({"task_id": task_id, "complaint_text": complaint_text})
    with _results_lock:
        _results[task_id] = {"status": "queued", "task_id": task_id}
    print(f"[queue_worker] Task {task_id} enqueued. Queue size: {_task_queue.qsize()}")


def get_result(task_id: str):
    """Poll for the result of a queued task."""
    with _results_lock:
        return _results.get(task_id, {"status": "not_found", "task_id": task_id})


def stop_worker():
    """Send shutdown signal to the worker thread."""
    _task_queue.put(None)


if __name__ == "__main__":
    import uuid

    start_worker()
    time.sleep(1)

    task_id = str(uuid.uuid4())
    enqueue_complaint(
        task_id=task_id,
        complaint_text="My package never arrived and I need a refund immediately.",
    )

    print(f"\nPolling for result of task {task_id}...")
    for _ in range(30):
        result = get_result(task_id)
        status = result.get("status")
        print(f"  Status: {status}")
        if status in ("complete", "failed"):
            break
        time.sleep(2)

    final = get_result(task_id)
    if final.get("status") == "complete":
        print(f"\nFinal status: {final['result'].get('final_status')}")
        print(f"Trace ID: {final['result'].get('trace_id')}")
    else:
        print(f"\nFailed: {final.get('error')}")

    stop_worker()
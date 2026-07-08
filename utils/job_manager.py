"""
Lightweight background job queue for video processing.

Why: the pipeline (download -> analyze -> TTS -> render) can run for many
minutes. Running it inside the HTTP request meant a browser refresh, network
blip, or proxy timeout lost the result. Jobs now run on a single background
worker thread; the API returns a job id immediately and results are persisted
to disk (outputs/<session_id>/job.json) so they survive a server restart.

Design notes:
- One worker thread processes jobs strictly in submission order. Video work is
  CPU/API heavy and Gemini is rate-limited, so serializing jobs is a feature.
- job_id == session_id (the frontend already generates a unique session id per
  submission), which keeps logs, output dirs, and jobs trivially correlated.
- No external broker (Redis/Celery) — deliberate, to keep the app a single
  process anyone can run with `python app.py`.
"""
import json
import queue
import threading
import time
from datetime import datetime
from pathlib import Path

from utils.logger import setup_logger

logger = setup_logger()

STATUS_QUEUED = "queued"
STATUS_RUNNING = "running"
STATUS_COMPLETED = "completed"
STATUS_FAILED = "failed"


class Job:
    def __init__(self, job_id, params):
        self.job_id = job_id
        self.params = params  # everything the runner needs (paths, script, flags)
        self.status = STATUS_QUEUED
        self.stage = "Queued"
        self.error = None
        self.result = None
        self.created_at = datetime.now().isoformat(timespec="seconds")
        self.started_at = None
        self.finished_at = None

    def set_stage(self, stage):
        self.stage = stage

    def to_dict(self, include_result=True):
        data = {
            "job_id": self.job_id,
            "session_id": self.job_id,
            "status": self.status,
            "stage": self.stage,
            "error": self.error,
            "created_at": self.created_at,
            "started_at": self.started_at,
            "finished_at": self.finished_at,
        }
        if include_result:
            data["result"] = self.result
        return data


class JobManager:
    """
    Single-worker FIFO job queue with disk persistence of terminal states.
    """

    def __init__(self, runner, state_root, max_history=100):
        """
        Args:
            runner: callable(job) -> result dict. Raises on failure.
            state_root: base directory containing per-session output dirs;
                        job state is written to <state_root>/<job_id>/job.json
            max_history: max finished jobs kept in memory (disk copies remain)
        """
        self._runner = runner
        self._state_root = Path(state_root)
        self._max_history = max_history
        self._jobs = {}          # job_id -> Job (insertion ordered)
        self._pending = []       # job_ids in queue order (for position display)
        self._lock = threading.Lock()
        self._queue = queue.Queue()
        self._worker = threading.Thread(
            target=self._worker_loop, name="job-worker", daemon=True
        )
        self._worker.start()

    # ---------------- public API ----------------

    def submit(self, job_id, params):
        with self._lock:
            if job_id in self._jobs and self._jobs[job_id].status in (
                STATUS_QUEUED, STATUS_RUNNING
            ):
                raise ValueError(f"Job {job_id} is already {self._jobs[job_id].status}")
            job = Job(job_id, params)
            self._jobs[job_id] = job
            self._pending.append(job_id)
            self._trim_history_locked()
        self._queue.put(job)
        logger.info(f"Job {job_id} queued (position {self.queue_position(job_id)})")
        return job

    def get(self, job_id):
        """Return a Job from memory, falling back to the on-disk record."""
        with self._lock:
            job = self._jobs.get(job_id)
        if job:
            return job
        return self._load_from_disk(job_id)

    def list_jobs(self):
        with self._lock:
            return [j.to_dict(include_result=False) for j in self._jobs.values()]

    def queue_position(self, job_id):
        """1-based position in the pending queue; 0 if not pending."""
        with self._lock:
            try:
                return self._pending.index(job_id) + 1
            except ValueError:
                return 0

    # ---------------- worker ----------------

    def _worker_loop(self):
        while True:
            job = self._queue.get()
            with self._lock:
                if job.job_id in self._pending:
                    self._pending.remove(job.job_id)
            job.status = STATUS_RUNNING
            job.stage = "Starting"
            job.started_at = datetime.now().isoformat(timespec="seconds")
            logger.info(f"Job {job.job_id} started")
            try:
                job.result = self._runner(job)
                job.status = STATUS_COMPLETED
                job.stage = "Complete"
                logger.info(f"Job {job.job_id} completed")
            except Exception as exc:
                job.status = STATUS_FAILED
                job.error = str(exc)
                job.stage = "Failed"
                logger.error(f"Job {job.job_id} failed: {exc}", exc_info=True)
            finally:
                job.finished_at = datetime.now().isoformat(timespec="seconds")
                self._persist(job)
                self._queue.task_done()

    # ---------------- persistence ----------------

    def _job_file(self, job_id):
        return self._state_root / job_id / "job.json"

    def _persist(self, job):
        try:
            path = self._job_file(job.job_id)
            path.parent.mkdir(parents=True, exist_ok=True)
            with open(path, "w", encoding="utf-8") as f:
                json.dump(job.to_dict(), f, indent=2, default=str)
        except Exception as exc:
            logger.warning(f"Could not persist job {job.job_id}: {exc}")

    def _load_from_disk(self, job_id):
        path = self._job_file(job_id)
        if not path.exists():
            return None
        try:
            with open(path, encoding="utf-8") as f:
                data = json.load(f)
            job = Job(data.get("job_id", job_id), params={})
            job.status = data.get("status", STATUS_FAILED)
            job.stage = data.get("stage", "")
            job.error = data.get("error")
            job.result = data.get("result")
            job.created_at = data.get("created_at")
            job.started_at = data.get("started_at")
            job.finished_at = data.get("finished_at")
            return job
        except Exception as exc:
            logger.warning(f"Could not load job {job_id} from disk: {exc}")
            return None

    def _trim_history_locked(self):
        finished = [
            jid for jid, j in self._jobs.items()
            if j.status in (STATUS_COMPLETED, STATUS_FAILED)
        ]
        overflow = len(self._jobs) - self._max_history
        for jid in finished[:max(0, overflow)]:
            del self._jobs[jid]

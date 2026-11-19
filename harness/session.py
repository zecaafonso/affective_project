"""One conversation with the engine. The GUI, the scenario runner and the teacher's tests all go through here."""
import datetime
import time
import traceback

from .contract import normalize
from .logger import SessionLogger


def _name(engine):
    return "%s.%s" % (type(engine).__module__, type(engine).__name__)


class Session:
    def __init__(self, engine, log_dir="logs", log=True):
        self.engine = engine
        self.log_dir = log_dir
        self.history = []
        self.logger = SessionLogger(log_dir, _name(engine)) if log else None
        self._reset_engine()

    def _reset_engine(self):
        try:
            self.engine.reset()
        except Exception:
            self.event("ERROR in engine.reset(): " + traceback.format_exc(limit=2))

    def event(self, text):
        if self.logger:
            self.logger.event(text)

    def send(self, text, audio_path=None, image_path=None, source="user"):
        t0 = time.perf_counter()
        error = None
        try:
            raw = self.engine.process(text, audio_path=audio_path, image_path=image_path)
        except Exception as exc:                      # a crashing engine must not crash the app
            raw = None
            error = "%s: %s" % (type(exc).__name__, exc)
            self.event("ERROR in engine.process(): " + traceback.format_exc(limit=3))
        res = normalize(raw)
        if error:
            res["problems"].append("engine raised " + error)
        entry = dict(res)
        entry.update({"id": len(self.history) + 1, "time": datetime.datetime.now().strftime("%H:%M:%S"),
                      "source": source, "input": text, "audio": audio_path, "image": image_path,
                      "latency_ms": int((time.perf_counter() - t0) * 1000), "error": error})
        self.history.append(entry)
        if self.logger:
            self.logger.write(entry)
        return entry

    def reset(self):
        """Start a new conversation (and a new log file)."""
        self.history = []
        if self.logger:
            self.logger.close()
            self.logger = SessionLogger(self.log_dir, _name(self.engine))
        self._reset_engine()

    def close(self):
        if self.logger:
            self.logger.close()

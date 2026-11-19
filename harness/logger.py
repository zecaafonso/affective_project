"""Plain-text session log: readable by anyone with a text editor."""
import datetime
import os

LINE = "-" * 72


def _fmt(x, signed=True):
    if x is None:
        return "n/a"
    return ("%+.2f" % x) if signed else ("%.2f" % x)


def format_entry(e):
    lines = [LINE,
             "#%d  %s  source=%s" % (e["id"], e["time"], e["source"]),
             "INPUT      : %s" % e["input"]]
    if e.get("audio"):
        lines.append("AUDIO      : %s" % e["audio"])
    if e.get("image"):
        lines.append("IMAGE      : %s" % e["image"])
    if e.get("error"):
        lines.append("ERROR      : %s" % e["error"])
    lines += ["MAP (x,y)   : valence=%s  activity=%s  dominance=%s" % (_fmt(e["valence"]), _fmt(e["activity"]), _fmt(e["dominance"])),
              "CONFIDENCE : %s" % _fmt(e["confidence"], signed=False),
              "LABEL      : %s" % e["label"],
              "ACTION     : %s" % e["action"],
              "FLAGS      : %s" % (", ".join(e["flags"]) if e["flags"] else "-"),
              "LATENCY    : %d ms" % e["latency_ms"],
              "REPLY      : %s" % e["reply"]]
    if e["details"]:
        lines.append("DETAILS    : %s" % e["details"])
    if e["problems"]:
        lines.append("PROBLEMS   : %s" % "; ".join(e["problems"]))
    return "\n".join(lines) + "\n"


class SessionLogger:
    def __init__(self, log_dir, engine_name="engine"):
        os.makedirs(log_dir, exist_ok=True)
        self.start = datetime.datetime.now()
        stamp = self.start.strftime("%Y%m%d_%H%M%S")
        self.path = os.path.join(log_dir, "session_%s.txt" % stamp)
        n = 1
        while os.path.exists(self.path):          # never overwrite another session
            self.path = os.path.join(log_dir, "session_%s_%d.txt" % (stamp, n))
            n += 1
        self.count = 0
        self._f = open(self.path, "w", encoding="utf-8")
        self._w("AFFECTIVE COMPUTING PROJECT - SESSION LOG\n"
                "Session started : %s\nEngine          : %s\nLog file        : %s\n"
                "This is a plain text file. Every message, the map values (x = valence, y = activity),\n"
                "the confidence and the chosen action are written below in order.\n" %
                (self.start.strftime("%Y-%m-%d %H:%M:%S"), engine_name, os.path.abspath(self.path)))

    def _w(self, text):
        self._f.write(text)
        self._f.flush()

    def write(self, entry):
        self.count += 1
        self._w(format_entry(entry))

    def event(self, text):
        self._w(LINE + "\n[%s] %s\n" % (datetime.datetime.now().strftime("%H:%M:%S"), text))

    def close(self):
        if not self._f.closed:
            self._w(LINE + "\nSession ended: %s   messages: %d\n" %
                    (datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"), self.count))
            self._f.close()

"""The engine contract: what every group's Engine must return. Used by the app, the scenario
runner and the teacher's tests, so everybody is measured the same way."""

ACTIONS = ("ANSWER", "ANSWER_EMPATHIC", "ASK_CLARIFICATION", "OFFER_HUMAN", "ESCALATE", "CLOSE_POSITIVE")


def _num(x, lo, hi):
    try:
        x = float(x)
    except (TypeError, ValueError):
        return None
    if x != x:                      # NaN
        return None
    return max(lo, min(hi, x))


def normalize(raw):
    """Turn whatever the engine returned into a clean result dict and list the problems found."""
    problems = []
    if not isinstance(raw, dict):
        return {"valence": 0.0, "activity": 0.0, "dominance": None, "confidence": 0.0, "label": "error",
                "action": "ANSWER", "reply": "", "flags": [], "details": {},
                "problems": ["engine.process() must return a dict"]}
    r = dict(raw)
    if "activity" not in r and "arousal" in r:
        r["activity"] = r["arousal"]
    out = {}
    for key, lo, hi in (("valence", -1, 1), ("activity", -1, 1), ("confidence", 0, 1)):
        v = _num(r.get(key), lo, hi)
        if v is None:
            problems.append("missing or invalid '%s'" % key)
            v = 0.0
        elif float(r[key]) != v:
            problems.append("'%s' outside [%s, %s] (clipped)" % (key, lo, hi))
        out[key] = v
    d = r.get("dominance")
    out["dominance"] = None if d is None else _num(d, -1, 1)
    out["label"] = str(r.get("label", "")) or "unknown"
    if not r.get("label"):
        problems.append("missing 'label'")
    act = r.get("action")
    if act not in ACTIONS:
        problems.append("'action' must be one of %s" % (ACTIONS,))
        act = "ANSWER"
    out["action"] = act
    out["reply"] = str(r.get("reply", ""))
    flags = r.get("flags", [])
    out["flags"] = [str(f) for f in flags] if isinstance(flags, (list, tuple)) else []
    details = r.get("details", {})
    out["details"] = details if isinstance(details, dict) else {"value": str(details)}
    out["problems"] = problems
    return out

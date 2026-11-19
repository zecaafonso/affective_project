# Affective Computing Project - student kit

Everything is Python 3.9+ (standard library only; numpy is allowed). The interface is the **same for every group**.

## Run
    python run_app.py                                     # the interface (needs tkinter)
    python run_scenario.py scenarios/mandatory/M1_calm_faq.json   # same engine, no interface, prints a table
    python tests/test_contract.py                         # checks that your engine respects the contract

On Linux, if you get "No module named tkinter": `sudo apt install python3-tk`.

## What the interface shows
* a **text input** field (Enter or Send); optional buttons to attach an audio file or an image (for groups that use voice or face);
* a **2D affective map**: x = valence, y = activity. Every message is a numbered point, the last one is highlighted.
  If your engine also returns `dominance`, the **3D view** checkbox is enabled (third axis drawn in perspective);
* the conversation, the last estimate (valence, activity, dominance, label, action, flags) and the **confidence**;
* an **expandable "Session log"** panel with every step: input, map values (x, y), confidence, label, action, flags,
  latency, reply and your own `details`. The same log is written to `logs/session_<date>_<time>.txt`
  (plain text, readable by anyone). "Save log as..." copies it elsewhere;
* a **scenario selector** with "Play scenario" (messages are sent one by one) and "Reset session".

## Where you work
Only the folder `engine/` (start with `engine/engine.py`, read its docstring). **Do not edit `harness/`, `run_app.py` or
`run_scenario.py`**: the teacher checks that they are unchanged and runs extra tests through the same interface.

## The engine contract
`Engine.reset()` starts a new conversation. `Engine.process(text, audio_path=None, image_path=None)` returns a dict:

| key | type | meaning |
| --- | --- | --- |
| `valence` | float -1..1 | negative to positive (map x) |
| `activity` | float -1..1 | deactivated to activated (map y); `arousal` is accepted as a synonym |
| `confidence` | float 0..1 | how much you trust the estimate |
| `label` | str | neutral, anger, fear, frustration, sadness, joy, calm, ... |
| `action` | str | `ANSWER`, `ANSWER_EMPATHIC`, `ASK_CLARIFICATION`, `OFFER_HUMAN`, `ESCALATE`, `CLOSE_POSITIVE` |
| `reply` | str | what the assistant says |
| `dominance` | float -1..1, optional | enables the 3D view |
| `flags`, `details` | list, dict, optional | anything useful; `details` is written to the log |

Problems with your output (missing keys, wrong action name, values outside the range) are shown in the interface and in the log.

## Scenarios
`scenarios/mandatory/` has the **4 scenarios that must appear in your video demo** (M1 to M4). `scenarios/practice/`
has 4 more for testing. All groups use the same ones. Each file says what behavior is expected. The teacher will also
test your code with additional messages that you do not see.

## Optional: voice and face (extra points)
`assets/audio/` has sample audio files. Your engine receives `audio_path` / `image_path` when a file is attached.

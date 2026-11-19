"""Start the shared interface:  python run_app.py"""
import os
import sys

ROOT = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, ROOT)

from harness.loader import load_engine      # noqa: E402
from harness.session import Session         # noqa: E402


def main():
    try:
        from harness.gui import App
    except ImportError as exc:
        sys.exit("The interface needs tkinter (%s).\nOn Linux install it with: sudo apt install python3-tk" % exc)
    session = Session(load_engine(ROOT), log_dir=os.path.join(ROOT, "logs"))
    App(session, os.path.join(ROOT, "scenarios"), ROOT).mainloop()


if __name__ == "__main__":
    main()

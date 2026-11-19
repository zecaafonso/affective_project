"""Run a scenario without the interface:  python run_scenario.py scenarios/mandatory/M1_calm_faq.json
Prints each step and writes the same .txt log as the interface."""
import os
import sys

ROOT = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, ROOT)

from harness.loader import load_engine                       # noqa: E402
from harness.scenarios import load_scenario, run_scenario     # noqa: E402
from harness.session import Session                           # noqa: E402


def main(argv):
    if len(argv) < 2:
        sys.exit("usage: python run_scenario.py <scenario.json>")
    sc = load_scenario(argv[1])
    session = Session(load_engine(ROOT), log_dir=os.path.join(ROOT, "logs"))
    print("Scenario %s - %s" % (sc.get("id"), sc.get("title")))

    def show(e):
        print("#%d  %-48s v=%+.2f a=%+.2f conf=%.2f  %-12s %s" % (e["id"], e["input"][:48], e["valence"], e["activity"],
                                                               e["confidence"], e["label"], e["action"]))
    run_scenario(session, sc, ROOT, show)
    path = session.logger.path
    session.close()
    print("Log written to", path)


if __name__ == "__main__":
    main(sys.argv)

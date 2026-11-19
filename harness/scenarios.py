import json
import os


def load_scenario(path):
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def list_scenarios(scenarios_dir):
    """Return [(display name, path)] for every scenario file, mandatory ones first."""
    items = []
    for sub in ("mandatory", "practice"):
        folder = os.path.join(scenarios_dir, sub)
        if not os.path.isdir(folder):
            continue
        for name in sorted(os.listdir(folder)):
            if name.endswith(".json"):
                path = os.path.join(folder, name)
                data = load_scenario(path)
                tag = "MANDATORY" if sub == "mandatory" else "practice"
                items.append(("[%s] %s - %s" % (tag, data.get("id", name[:-5]), data.get("title", "")), path))
    return items


def resolve_media(project_root, rel):
    if not rel:
        return None
    return rel if os.path.isabs(rel) else os.path.join(project_root, rel)


def run_scenario(session, scenario, project_root=".", on_step=None):
    session.event("SCENARIO %s - %s" % (scenario.get("id"), scenario.get("title")))
    entries = []
    for m in scenario["messages"]:
        entry = session.send(m["text"], audio_path=resolve_media(project_root, m.get("audio")),
                             image_path=resolve_media(project_root, m.get("image")),
                             source="scenario:" + str(scenario.get("id")))
        entries.append(entry)
        if on_step:
            on_step(entry)
    return entries

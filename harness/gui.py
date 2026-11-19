"""Tkinter interface shared by every group (do not edit).

Text input, 2D affective map (valence x activity; optional 3D view when the engine returns
dominance), conversation view, metrics and an expandable session log that is also written to a .txt file."""
import os
import shutil
import tkinter as tk
from tkinter import filedialog, messagebox, ttk

from . import HARNESS_VERSION
from .logger import format_entry
from .mapmath import SIZE, MARGIN, project_point
from .scenarios import list_scenarios, load_scenario, resolve_media

LABEL_COLORS = {"anger": "#d62728", "fear": "#9467bd", "frustration": "#ff7f0e", "sadness": "#1f77b4",
                "joy": "#2ca02c", "calm": "#17becf", "neutral": "#7f7f7f", "error": "#000000"}


class App(tk.Tk):
    def __init__(self, session, scenarios_dir, project_root):
        super().__init__()
        self.title("Affective Computing Project - Affective Map (harness %s)" % HARNESS_VERSION)
        self.session = session
        self.project_root = project_root
        self.scenarios = list_scenarios(scenarios_dir)
        self.audio = None
        self.image = None
        self.queue = []
        self.log_open = False
        self._build()
        self.protocol("WM_DELETE_WINDOW", self.on_close)
        self.redraw()

    # ------------------------------------------------------------------ layout
    def _build(self):
        top = ttk.Frame(self)
        top.pack(fill="x", padx=8, pady=6)
        ttk.Label(top, text="Scenario:").pack(side="left")
        self.combo = ttk.Combobox(top, state="readonly", width=48, values=[n for n, _ in self.scenarios])
        self.combo.pack(side="left", padx=4)
        if self.scenarios:
            self.combo.current(0)
        ttk.Button(top, text="Play scenario", command=self.play_scenario).pack(side="left", padx=2)
        ttk.Button(top, text="Reset session", command=self.reset_session).pack(side="left", padx=2)
        self.var3d = tk.BooleanVar(value=False)
        self.chk3d = ttk.Checkbutton(top, text="3D view (needs dominance)", variable=self.var3d, command=self.redraw)
        self.chk3d.pack(side="left", padx=8)
        ttk.Button(top, text="Save log as...", command=self.save_log_as).pack(side="right")

        mid = ttk.Frame(self)
        mid.pack(fill="both", expand=True, padx=8)
        self.canvas = tk.Canvas(mid, width=SIZE, height=SIZE, bg="white", highlightthickness=1, highlightbackground="#999")
        self.canvas.pack(side="left")
        right = ttk.Frame(mid)
        right.pack(side="left", fill="both", expand=True, padx=(8, 0))
        self.chat = tk.Text(right, height=18, width=58, wrap="word", state="disabled")
        self.chat.pack(fill="both", expand=True)
        self.chat.tag_configure("user", foreground="#1a1a1a")
        self.chat.tag_configure("bot", foreground="#0b5394")
        self.chat.tag_configure("note", foreground="#888888")
        metrics = ttk.LabelFrame(right, text="Last estimate")
        metrics.pack(fill="x", pady=6)
        self.vars = {k: tk.StringVar(value="-") for k in ("valence", "activity", "dominance", "label", "action", "flags")}
        for i, (k, title) in enumerate((("valence", "Valence (x)"), ("activity", "Activity (y)"), ("dominance", "Dominance (z)"),
                                        ("label", "Label"), ("action", "Action"), ("flags", "Flags"))):
            ttk.Label(metrics, text=title + ":").grid(row=i // 2, column=(i % 2) * 2, sticky="w", padx=4)
            ttk.Label(metrics, textvariable=self.vars[k]).grid(row=i // 2, column=(i % 2) * 2 + 1, sticky="w", padx=4)
        ttk.Label(metrics, text="Confidence:").grid(row=3, column=0, sticky="w", padx=4)
        self.conf = ttk.Progressbar(metrics, maximum=1.0, length=180)
        self.conf.grid(row=3, column=1, columnspan=2, sticky="w", padx=4, pady=2)
        self.conf_text = tk.StringVar(value="-")
        ttk.Label(metrics, textvariable=self.conf_text).grid(row=3, column=3, sticky="w")

        row = ttk.Frame(self)
        row.pack(fill="x", padx=8, pady=6)
        self.entry = ttk.Entry(row)
        self.entry.pack(side="left", fill="x", expand=True)
        self.entry.bind("<Return>", lambda _e: self.send())
        self.entry.focus_set()
        ttk.Button(row, text="Send", command=self.send).pack(side="left", padx=4)
        ttk.Button(row, text="Audio (optional)...", command=self.pick_audio).pack(side="left", padx=2)
        ttk.Button(row, text="Image (optional)...", command=self.pick_image).pack(side="left", padx=2)
        self.media = tk.StringVar(value="")
        ttk.Label(row, textvariable=self.media).pack(side="left", padx=6)

        self.log_btn = ttk.Button(self, text="\u25b6 Session log (click to expand)", command=self.toggle_log)
        self.log_btn.pack(fill="x", padx=8)
        self.log_frame = ttk.Frame(self)
        self.log_text = tk.Text(self.log_frame, height=14, wrap="none", state="disabled", font=("Courier", 9))
        sb = ttk.Scrollbar(self.log_frame, command=self.log_text.yview)
        self.log_text.configure(yscrollcommand=sb.set)
        sb.pack(side="right", fill="y")
        self.log_text.pack(side="left", fill="both", expand=True)
        self.status = tk.StringVar(value="Ready. Log file: %s" % (self.session.logger.path if self.session.logger else "disabled"))
        self.status_label = ttk.Label(self, textvariable=self.status)
        self.status_label.pack(fill="x", padx=8, pady=(2, 6))

    # ------------------------------------------------------------------ actions
    def pick_audio(self):
        p = filedialog.askopenfilename(title="Choose an audio file", filetypes=[("Audio", "*.wav"), ("All files", "*.*")])
        if p:
            self.audio = p
            self._update_media()

    def pick_image(self):
        p = filedialog.askopenfilename(title="Choose an image", filetypes=[("Images", "*.png *.jpg *.jpeg"), ("All files", "*.*")])
        if p:
            self.image = p
            self._update_media()

    def _update_media(self):
        names = [os.path.basename(x) for x in (self.audio, self.image) if x]
        self.media.set("attached: " + ", ".join(names) if names else "")

    def send(self):
        text = self.entry.get().strip()
        if not text:
            return
        self.entry.delete(0, "end")
        self.submit(text, self.audio, self.image, "user")
        self.audio = self.image = None
        self._update_media()

    def submit(self, text, audio, image, source):
        entry = self.session.send(text, audio_path=audio, image_path=image, source=source)
        self._show(entry)

    def _append(self, widget, text, tag=None):
        widget.configure(state="normal")
        widget.insert("end", text, tag) if tag else widget.insert("end", text)
        widget.see("end")
        widget.configure(state="disabled")

    def _show(self, e):
        self._append(self.chat, "You: %s\n" % e["input"], "user")
        self._append(self.chat, "Assistant [%s]: %s\n\n" % (e["action"], e["reply"]), "bot")
        self.vars["valence"].set("%+.2f" % e["valence"])
        self.vars["activity"].set("%+.2f" % e["activity"])
        self.vars["dominance"].set("n/a" if e["dominance"] is None else "%+.2f" % e["dominance"])
        self.vars["label"].set(e["label"])
        self.vars["action"].set(e["action"])
        self.vars["flags"].set(", ".join(e["flags"]) if e["flags"] else "-")
        self.conf["value"] = e["confidence"]
        self.conf_text.set("%.2f" % e["confidence"])
        self._append(self.log_text, format_entry(e))
        if e["problems"]:
            self.status.set("Engine problems: " + "; ".join(e["problems"]))
        self.redraw()

    def play_scenario(self):
        i = self.combo.current()
        if i < 0 or self.queue:
            return
        name, path = self.scenarios[i]
        sc = load_scenario(path)
        self.session.event("SCENARIO %s - %s" % (sc.get("id"), sc.get("title")))
        self._append(self.chat, "--- scenario: %s ---\n" % name, "note")
        self.queue = list(sc["messages"])
        self.status.set("Playing scenario %s ..." % sc.get("id"))
        self._step(sc.get("id"))

    def _step(self, sid):
        if not self.queue:
            self.status.set("Scenario finished. Log file: %s" % (self.session.logger.path if self.session.logger else ""))
            return
        m = self.queue.pop(0)
        self.submit(m["text"], resolve_media(self.project_root, m.get("audio")),
                    resolve_media(self.project_root, m.get("image")), "scenario:%s" % sid)
        self.after(1500, lambda: self._step(sid))

    def reset_session(self):
        self.queue = []
        self.session.reset()
        for w in (self.chat, self.log_text):
            w.configure(state="normal")
            w.delete("1.0", "end")
            w.configure(state="disabled")
        for v in self.vars.values():
            v.set("-")
        self.conf["value"] = 0
        self.conf_text.set("-")
        self.status.set("New session. Log file: %s" % self.session.logger.path)
        self.redraw()

    def toggle_log(self):
        self.log_open = not self.log_open
        if self.log_open:
            self.log_frame.pack(fill="both", expand=True, padx=8, before=self.status_label)
            self.log_btn.configure(text="\u25bc Session log (click to collapse)")
        else:
            self.log_frame.pack_forget()
            self.log_btn.configure(text="\u25b6 Session log (click to expand)")

    def save_log_as(self):
        if not self.session.logger:
            return
        p = filedialog.asksaveasfilename(defaultextension=".txt", filetypes=[("Text", "*.txt")],
                                         initialfile=os.path.basename(self.session.logger.path))
        if p:
            shutil.copyfile(self.session.logger.path, p)
            self.status.set("Log copied to %s" % p)

    def on_close(self):
        self.session.close()
        self.destroy()

    # ------------------------------------------------------------------ map
    def redraw(self):
        has_dom = any(e["dominance"] is not None for e in self.session.history)
        self.chk3d.state(["!disabled"] if has_dom else ["disabled"])
        three_d = bool(self.var3d.get()) and has_dom
        c = self.canvas
        c.delete("all")
        cx = cy = SIZE / 2
        r = (SIZE - 2 * MARGIN) / 2
        c.create_rectangle(MARGIN, MARGIN, SIZE - MARGIN, SIZE - MARGIN, outline="#bbbbbb")
        c.create_line(MARGIN, cy, SIZE - MARGIN, cy, fill="#555555", arrow="last")
        c.create_line(cx, SIZE - MARGIN, cx, MARGIN, fill="#555555", arrow="last")
        for t in (-1, -0.5, 0.5, 1):
            c.create_line(cx + t * r, cy - 3, cx + t * r, cy + 3, fill="#555555")
            c.create_text(cx + t * r, cy + 14, text="%g" % t, fill="#777777", font=("Helvetica", 8))
            c.create_line(cx - 3, cy - t * r, cx + 3, cy - t * r, fill="#555555")
            c.create_text(cx - 16, cy - t * r, text="%g" % t, fill="#777777", font=("Helvetica", 8))
        q = (("negative, activated\n(tense, angry)", -0.5, 0.55), ("positive, activated\n(excited, happy)", 0.5, 0.55),
             ("negative, deactivated\n(sad, tired)", -0.5, -0.55), ("positive, deactivated\n(calm, relaxed)", 0.5, -0.55))
        for txt, qx, qy in q:
            c.create_text(cx + qx * r, cy - qy * r, text=txt, fill="#bbbbbb", font=("Helvetica", 9))
        c.create_text(SIZE - MARGIN, cy - 12, text="Valence", anchor="e", font=("Helvetica", 10, "bold"))
        c.create_text(cx + 8, MARGIN - 14, text="Activity", anchor="w", font=("Helvetica", 10, "bold"))
        if three_d:
            zx, zy = project_point(0, 0, 1, True)
            c.create_line(cx, cy, zx, zy, fill="#2ca02c", dash=(3, 2), arrow="last")
            c.create_text(zx + 6, zy, text="Dominance", anchor="w", fill="#2ca02c", font=("Helvetica", 9))
        prev = None
        hist = self.session.history
        for i, e in enumerate(hist):
            x, y = project_point(e["valence"], e["activity"], e["dominance"], three_d)
            if prev:
                c.create_line(prev[0], prev[1], x, y, fill="#cccccc")
            last = i == len(hist) - 1
            rad = 8 if last else 4
            col = LABEL_COLORS.get(e["label"], "#555555") if last else "#999999"
            c.create_oval(x - rad, y - rad, x + rad, y + rad, fill=col, outline="black")
            c.create_text(x + rad + 6, y - rad - 4, text=str(e["id"]), font=("Helvetica", 8))
            prev = (x, y)

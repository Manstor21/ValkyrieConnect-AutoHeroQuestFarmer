"""
Graphical interface for the Valkyrie Connect farming bot.

Usage:
    python interfaz_valkyrie.py
"""

from __future__ import annotations

import os
import threading
import time
import tkinter as tk
from tkinter import messagebox

import auto_farmeo_valkyrie
from auto_farmeo_valkyrie import stats
import recorrido_heroes

try:
    import keyboard
except ImportError:
    keyboard = None


GUI_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "gui_templates")
STOP_KEY = "f8"


class App:
    def __init__(self, root: tk.Tk) -> None:
        self.root = root
        self.root.title("Valkyrie Connect - Hero Farming")
        self.root.geometry("420x480")
        self.root.resizable(False, False)
        self.root.configure(bg="#1a1a2e")
        self.running = False
        self.stop_flag = threading.Event()
        self.start_time: float | None = None
        self.elapsed_time = 0
        self._load_images()
        self._build_ui()
        self._register_global_hotkey()
        self._timer_loop()
        self._stats_loop()

    def _register_global_hotkey(self) -> None:
        if keyboard is None:
            print(f"[WARN] 'keyboard' library not installed. "
                  f"Global hotkey ({STOP_KEY.upper()}) unavailable. "
                  f"Install with: pip install keyboard")
            return

        def _on_hotkey() -> None:
            print(f"[HOTKEY] {STOP_KEY.upper()} pressed. Stopping...")
            self.root.after(0, self.stop)

        try:
            keyboard.add_hotkey(STOP_KEY, _on_hotkey)
            print(f"[OK] Global stop hotkey registered: {STOP_KEY.upper()}")
            print("     If unresponsive with game in focus, run this script "
                  "as Administrator (same privilege level as the game).")
        except Exception as e:
            print(f"[WARN] Could not register global hotkey: {e}")

    def _load_images(self) -> None:
        for attr in ("play", "stop", "diamond", "hero", "clock"):
            setattr(self, attr, None)
        if not os.path.isdir(GUI_DIR):
            return
        try:
            from PIL import Image, ImageTk
            mappings = [
                ("play-button.png", "play", None),
                ("stop-button.png", "stop", None),
                ("blue-diamond-icon-removebgpng.png", "diamond", (30, 30)),
                ("hero.png", "hero", (30, 30)),
                ("hourglass-icon.png", "clock", (30, 30)),
            ]
            for filename, attr, size in mappings:
                path = os.path.join(GUI_DIR, filename)
                if os.path.isfile(path):
                    img = Image.open(path)
                    if size:
                        img = img.resize(size, Image.LANCZOS)
                    setattr(self, attr, ImageTk.PhotoImage(img))
        except Exception:
            pass

    def _build_ui(self) -> None:
        btn_frame = tk.Frame(self.root, bg="#1a1a2e")
        btn_frame.pack(pady=(35, 10))

        if self.play:
            self.btn_play = tk.Button(btn_frame, image=self.play, command=self.start,
                bd=0, highlightthickness=0, cursor="hand2", relief="flat",
                bg="#1a1a2e", activebackground="#1a1a2e")
        else:
            self.btn_play = tk.Button(btn_frame, text="PLAY", command=self.start,
                font=("Arial", 14, "bold"), bg="#4CAF50", fg="white",
                padx=30, pady=12, cursor="hand2")
        self.btn_play.pack(side=tk.LEFT, padx=10)

        if self.stop:
            self.btn_stop = tk.Button(btn_frame, image=self.stop, command=self.stop,
                bd=0, highlightthickness=0, cursor="hand2", relief="flat",
                bg="#1a1a2e", activebackground="#1a1a2e", state=tk.DISABLED)
        else:
            self.btn_stop = tk.Button(btn_frame, text="STOP", command=self.stop,
                font=("Arial", 14, "bold"), bg="#f44336", fg="white",
                padx=30, pady=12, cursor="hand2", state=tk.DISABLED)
        self.btn_stop.pack(side=tk.LEFT, padx=10)

        stats_frame = tk.Frame(self.root, bg="#1a1a2e")
        stats_frame.pack(pady=20)

        def _stat_row(icon, label_text, color):
            row = tk.Frame(stats_frame, bg="#16213e", padx=15, pady=8)
            row.pack(pady=5, fill="x", padx=30)
            if icon:
                badge = tk.Label(row, image=icon, bd=0, highlightthickness=0,
                    bg="#2a3a5c", padx=4, pady=4)
                badge.pack(side=tk.LEFT, padx=(0, 10))
            tk.Label(row, text=label_text, font=("Arial", 12),
                fg="#cccccc", bg="#16213e").pack(side=tk.LEFT)
            lbl = tk.Label(row, text="0", font=("Arial", 20, "bold"),
                fg=color, bg="#16213e")
            lbl.pack(side=tk.RIGHT)
            return lbl

        self.label_heroes = _stat_row(self.hero, "Heroes farmed", "#4CAF50")
        self.label_diamonds = _stat_row(self.diamond, "Diamonds", "#FFD700")
        self.label_time = _stat_row(self.clock, "Time", "#ffffff")

        self.status = tk.Label(self.root, text="Stopped",
            font=("Arial", 10), fg="#888888", bg="#1a1a2e")
        self.status.pack(pady=5)

        tk.Label(self.root, text=f"Global stop key: {STOP_KEY.upper()}",
            font=("Arial", 9), fg="#666688", bg="#1a1a2e").pack(pady=(0, 5))

    def _estimate_diamonds(self) -> int:
        return (stats["libros_completados"] * 50 +
                stats["cofre1_abiertos"] * 30 +
                stats["cofre2_abiertos"] * 50 +
                stats["cofre3_abiertos"] * 100)

    def _timer_loop(self) -> None:
        if self.start_time is not None and self.running:
            self.elapsed_time = int(time.time() - self.start_time)
        h, m, s = (self.elapsed_time // 3600,
                    (self.elapsed_time % 3600) // 60,
                    self.elapsed_time % 60)
        self.label_time.config(text=f"{h:02d}:{m:02d}:{s:02d}")
        self.root.after(500, self._timer_loop)

    def _stats_loop(self) -> None:
        if self.running:
            self.label_heroes.config(text=str(stats["heroes_completados"]))
            self.label_diamonds.config(text=str(self._estimate_diamonds()))
        self.root.after(1000, self._stats_loop)

    def start(self) -> None:
        if self.running:
            return
        self.running = True
        self.stop_flag.clear()
        auto_farmeo_valkyrie.stop_event.clear()
        self.start_time = time.time()
        self.elapsed_time = 0
        for key in ("heroes_completados", "libros_completados",
                     "cofre1_abiertos", "cofre2_abiertos", "cofre3_abiertos"):
            stats[key] = 0
        self.label_heroes.config(text="0")
        self.label_diamonds.config(text="0")
        self.label_time.config(text="00:00:00")
        self.btn_play.config(state=tk.DISABLED)
        self.btn_stop.config(state=tk.NORMAL)
        self.status.config(text="Farming...", fg="#4CAF50")

        def _run() -> None:
            try:
                recorrido_heroes.process_all_heroes(stop_event=self.stop_flag)
            except Exception as e:
                print(f"Error: {e}")
            finally:
                self.root.after(0, self._on_finished)

        threading.Thread(target=_run, daemon=True).start()

    def stop(self) -> None:
        if self.running:
            self.stop_flag.set()
            auto_farmeo_valkyrie.stop_event.set()
            self.running = False
            self.btn_play.config(state=tk.NORMAL)
            self.btn_stop.config(state=tk.DISABLED)
            self.status.config(text="Stopped", fg="#FF9800")

    def _bring_to_front(self) -> None:
        self.root.deiconify()
        self.root.state("normal")
        self.root.attributes("-topmost", True)
        self.root.lift()
        self.root.focus_force()
        self.root.after(300, lambda: self.root.attributes("-topmost", False))

    def _on_finished(self) -> None:
        self.running = False
        self.btn_play.config(state=tk.NORMAL)
        self.btn_stop.config(state=tk.DISABLED)
        self.status.config(text="Finished", fg="#888888")

        self._bring_to_front()

        h, m, s = (self.elapsed_time // 3600,
                    (self.elapsed_time % 3600) // 60,
                    self.elapsed_time % 60)
        summary = (
            f"Heroes farmed: {stats['heroes_completados']}\n"
            f"Estimated diamonds: {self._estimate_diamonds()}\n"
            f"Total time: {h:02d}:{m:02d}:{s:02d}"
        )
        messagebox.showinfo("Farming complete", summary, parent=self.root)


if __name__ == "__main__":
    root = tk.Tk()
    App(root)
    try:
        root.mainloop()
    except Exception:
        pass
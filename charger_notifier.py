import tkinter as tk
from tkinter import Label, Button
from PIL import Image, ImageTk, ImageSequence
import openvr
import os
import threading
import pygame
import sys
import random
import ctypes

# ── Theme Definitions ──────────────────────────────────────────────────────────
THEMES = {
    "dark": {
        "bg":              "#1e1e1e",
        "fg":              "#ffffff",
        "button_bg":       "#2d2d2d",
        "button_fg":       "#ffffff",
        "button_active_bg":"#3a3a3a",
        "button_active_fg":"#ffffff",
        "border":          "#444444",
        "accent":          "#5b9bd5",
    },
    "light": {
        "bg":              "#f5f5f0",
        "fg":              "#1a1a1a",
        "button_bg":       "#e0ddd8",
        "button_fg":       "#1a1a1a",
        "button_active_bg":"#ccc9c3",
        "button_active_fg":"#1a1a1a",
        "border":          "#bbbbbb",
        "accent":          "#2a70c8",
    },
}

# Fix for Windows Taskbar Icon
try:
    myappid = 'vr.charger.notifier.v1'
    ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(myappid)
except Exception:
    pass


def resource_path(relative_path):
    try:
        base_path = sys._MEIPASS
    except Exception:
        base_path = os.path.abspath(".")
    return os.path.join(base_path, relative_path)


class AnimatedGIF(Label):
    def __init__(self, master, path, bg_color, *args, **kwargs):
        kwargs['bg'] = bg_color
        super().__init__(master, *args, **kwargs)
        self.path = path
        self.frames = []
        self.load_frames()
        self.index = 0
        self.cancel = None
        self.play()

    def load_frames(self):
        img = Image.open(self.path)
        self.frames = [
            ImageTk.PhotoImage(frame.copy().convert('RGBA'))
            for frame in ImageSequence.Iterator(img)
        ]

    def play(self):
        if not self.frames:
            return
        self.config(image=self.frames[self.index])
        self.index = (self.index + 1) % len(self.frames)
        self.cancel = self.after(100, self.play)

    def stop(self):
        if self.cancel:
            self.after_cancel(self.cancel)
            self.cancel = None

    def update_bg(self, bg_color):
        self.config(bg=bg_color)


CONFIG_PATH = os.path.join(os.path.expanduser("~"), ".vr_charging_status.cfg")

def load_config():
    config = {"mode": "dark", "male_voice": False}
    try:
        with open(CONFIG_PATH, "r") as f:
            for line in f:
                line = line.strip()
                if "=" in line:
                    key, _, val = line.partition("=")
                    config[key.strip()] = val.strip()
        config["male_voice"] = config["male_voice"] == "True"
    except Exception:
        pass
    return config

def save_config(mode, male_voice):
    try:
        with open(CONFIG_PATH, "w") as f:
            f.write(f"mode={mode}\n")
            f.write(f"male_voice={male_voice}\n")
    except Exception:
        pass


class ChargingApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("VR Charging Status")
        self.geometry("400x520")
        self.resizable(False, False)

        # ── Load persisted config ──────────────────────────────────────────────
        cfg = load_config()

        # ── Theme State ────────────────────────────────────────────────────────
        self._mode = cfg["mode"] if cfg["mode"] in THEMES else "dark"
        self._theme = THEMES[self._mode]

        self.configure(bg=self._theme["bg"])

        icon_path = resource_path(os.path.join("assets", "pawicon.ico"))
        if os.path.exists(icon_path):
            self.iconbitmap(icon_path)

        self.cat_charging     = resource_path(os.path.join("assets", "cat5.gif"))
        self.cat_not_charging = resource_path(os.path.join("assets", "cat1.gif"))

        # ── Animated GIF label ─────────────────────────────────────────────────
        self.label = AnimatedGIF(self, self.cat_not_charging, self._theme["bg"])
        self.label.pack(expand=True, fill="both", padx=0, pady=0)

        # ── Button row frame ───────────────────────────────────────────────────
        self.btn_frame = tk.Frame(self, bg=self._theme["bg"])
        self.btn_frame.pack(pady=(8, 16), fill="x", padx=20)

        # Voice toggle button (left)
        self.voice_button = self._make_button(
            self.btn_frame,
            text="🎙 Switch to Male Voice",
            command=self.toggle_voice,
        )
        self.voice_button.pack(side="left", expand=True, fill="x", padx=(0, 6), ipady=4)

        # Dark/light mode toggle button (right)
        self.theme_button = self._make_button(
            self.btn_frame,
            text="Light",
            command=self.toggle_theme,
        )
        self.theme_button.pack(side="right", ipady=4, ipadx=6)

        # ── Audio ──────────────────────────────────────────────────────────────
        pygame.mixer.init()
        self.notif1 = self.load_sound("notif.wav")
        self.notif2 = self.load_sound("notif2.wav")
        self.male_voice = cfg["male_voice"]
        self.load_all_sounds()

        # Apply saved theme & voice state to UI
        self._apply_theme()
        if self.male_voice:
            self.voice_button.config(text="🎙 Switch to Female Voice")

        # ── State ──────────────────────────────────────────────────────────────
        self.remind_index   = 0
        self.was_charging   = None
        self.reminder_timer = None

        self.vr_system = None
        self.vr_thread = threading.Thread(target=self.init_openvr, daemon=True)
        self.vr_thread.start()

        self.after(1000, self.check_charging)

    # ── Helper: create a consistently-styled button ────────────────────────────
    def _make_button(self, parent, text, command, width=None):
        kwargs = dict(
            text=text,
            command=command,
            bg=self._theme["button_bg"],
            fg=self._theme["button_fg"],
            activebackground=self._theme["button_active_bg"],
            activeforeground=self._theme["button_active_fg"],
            relief="flat",
            font=("Segoe UI", 10),
            anchor="center",
            justify="center",
            cursor="hand2",
            bd=0,
            highlightthickness=1,
            highlightbackground=self._theme["border"],
            highlightcolor=self._theme["accent"],
        )
        if width is not None:
            kwargs["width"] = width
        return Button(parent, **kwargs)
    # ── Theme toggle ───────────────────────────────────────────────────────────
    def toggle_theme(self):
        self._mode = "light" if self._mode == "dark" else "dark"
        self._theme = THEMES[self._mode]
        self._apply_theme()

    def _apply_theme(self):
        t = self._theme
        is_dark = self._mode == "dark"

        # Window & frame backgrounds
        self.configure(bg=t["bg"])
        self.btn_frame.configure(bg=t["bg"])

        # Update GIF label background
        self.label.update_bg(t["bg"])

        # Common button style dict
        btn_style = dict(
            bg=t["button_bg"],
            fg=t["button_fg"],
            activebackground=t["button_active_bg"],
            activeforeground=t["button_active_fg"],
            highlightbackground=t["border"],
            highlightcolor=t["accent"],
        )

        self.voice_button.configure(**btn_style)
        self.theme_button.configure(**btn_style)

        # Flip label to reflect the mode you can switch TO
        self.theme_button.configure(text="Light" if is_dark else "Dark")

    # ── Sound helpers ──────────────────────────────────────────────────────────
    def load_sound(self, filename):
        path = resource_path(os.path.join("assets", filename))
        return pygame.mixer.Sound(path) if os.path.exists(path) else None

    def load_group(self, prefix, count):
        sounds = []
        for i in range(1, count + 1):
            name = f"{prefix}{i}{'m' if self.male_voice else ''}.wav"
            sound = self.load_sound(name)
            if sound:
                sounds.append(sound)
        return sounds

    def load_all_sounds(self):
        self.dc_sounds      = self.load_group("dc", 3)
        self.connect_sounds = self.load_group("connect", 3)
        self.remind_sounds  = []
        for i in [1, 2]:
            name  = f"remind{i}{'m' if self.male_voice else ''}.wav"
            sound = self.load_sound(name)
            if sound:
                self.remind_sounds.append(sound)

    def toggle_voice(self):
        self.male_voice = not self.male_voice
        self.voice_button.config(
            text="🎙 Switch to Female Voice" if self.male_voice else "🎙 Switch to Male Voice"
        )
        self.load_all_sounds()

    # ── Notification playback ──────────────────────────────────────────────────
    def play_with_notif(self, sound, is_connect=False):
        notif = self.notif2 if is_connect else self.notif1
        if not notif or not sound:
            if sound:
                sound.play()
            return
        channel = pygame.mixer.find_channel()
        if not channel:
            sound.play()
            return
        channel.play(notif)

        def play_after_notif():
            if not channel.get_busy():
                sound.play()
            else:
                self.after(50, play_after_notif)

        self.after(50, play_after_notif)

    # ── Reminder loop ──────────────────────────────────────────────────────────
    def start_reminder_loop(self):
        self.cancel_reminder()
        if self.remind_sounds:
            self.reminder_timer = self.after(180_000, self.play_reminder)

    def cancel_reminder(self):
        if self.reminder_timer:
            self.after_cancel(self.reminder_timer)
            self.reminder_timer = None
        self.remind_index = 0

    def play_reminder(self):
        if not self.was_charging and self.remind_sounds:
            sound = self.remind_sounds[self.remind_index]
            self.play_with_notif(sound, is_connect=False)
            self.remind_index = (self.remind_index + 1) % len(self.remind_sounds)
            self.reminder_timer = self.after(180_000, self.play_reminder)

    # ── VR ─────────────────────────────────────────────────────────────────────
    def init_openvr(self):
        try:
            openvr.init(openvr.VRApplication_Background)
            self.vr_system = openvr.VRSystem()
        except Exception as e:
            print(f"VR Init failed: {e}")
            self.vr_system = None

    def check_charging(self):
        if self.vr_system is not None:
            is_charging = False
            for device_index in range(openvr.k_unMaxTrackedDeviceCount):
                try:
                    device_class = self.vr_system.getTrackedDeviceClass(device_index)
                    if device_class == openvr.TrackedDeviceClass_HMD:
                        is_charging = self.vr_system.getBoolTrackedDeviceProperty(
                            device_index, openvr.Prop_DeviceIsCharging_Bool
                        )
                        break
                except Exception:
                    continue

            if self.was_charging is not None:
                if self.was_charging and not is_charging:
                    if self.dc_sounds:
                        self.play_with_notif(random.choice(self.dc_sounds), is_connect=False)
                    self.start_reminder_loop()
                elif not self.was_charging and is_charging:
                    if self.connect_sounds:
                        self.play_with_notif(random.choice(self.connect_sounds), is_connect=True)
                    self.cancel_reminder()

            if is_charging:
                self.cancel_reminder()

            self.was_charging = is_charging

            new_gif = self.cat_charging if is_charging else self.cat_not_charging
            if self.label.path != new_gif:
                self.label.stop()
                self.label.destroy()
                self.label = AnimatedGIF(self, new_gif, self._theme["bg"])
                self.label.pack(expand=True, fill="both")

        self.after(3000, self.check_charging)

    def on_closing(self):
        save_config(self._mode, self.male_voice)
        if self.vr_system:
            openvr.shutdown()
        self.cancel_reminder()
        self.destroy()


if __name__ == "__main__":
    app = ChargingApp()
    app.protocol("WM_DELETE_WINDOW", app.on_closing)
    app.mainloop()
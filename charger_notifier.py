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
import json
import shutil

def get_base_path():
    if getattr(sys, 'frozen', False):
        return os.path.dirname(sys.executable)
    return os.path.dirname(os.path.abspath(__file__))

def resource_path(relative_path):
    try:
        base_path = sys._MEIPASS
    except Exception:
        base_path = os.path.abspath(".")
    return os.path.join(base_path, relative_path)

EXE_LOCATION = get_base_path()
CONFIG_PATH = os.path.join(EXE_LOCATION, "vr_charging_settings.cfg")
MANIFEST_NAME = "manifest.vrmanifest"
PERMANENT_MANIFEST_PATH = os.path.normpath(os.path.join(EXE_LOCATION, MANIFEST_NAME))

THEMES = {
    "dark": {
        "bg": "#1e1e1e", "fg": "#ffffff", "button_bg": "#2d2d2d",
        "button_fg": "#ffffff", "button_active_bg": "#3a3a3a",
        "button_active_fg": "#ffffff", "border": "#444444", "accent": "#5b9bd5",
    },
    "light": {
        "bg": "#f5f5f0", "fg": "#1a1a1a", "button_bg": "#e0ddd8",
        "button_fg": "#1a1a1a", "button_active_bg": "#ccc9c3",
        "button_active_fg": "#1a1a1a", "border": "#bbbbbb", "accent": "#2a70c8",
    },
}

try:
    myappid = 'vr.charger.notifier.v1'
    ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(myappid)
except Exception:
    pass

def register_vr_manifest():
    bundled_manifest = resource_path(MANIFEST_NAME)

    if not os.path.exists(PERMANENT_MANIFEST_PATH):
        try:
            if os.path.exists(bundled_manifest):
                shutil.copy2(bundled_manifest, PERMANENT_MANIFEST_PATH)
        except:
            return

    config_path = r"C:\Program Files (x86)\Steam\config\appconfig.json"
    if not os.path.exists(config_path):
        return

    try:
        with open(config_path, 'r', encoding='utf-8') as f:
            data = json.load(f)

        if "manifest_paths" not in data:
            data["manifest_paths"] = []

        if PERMANENT_MANIFEST_PATH not in data["manifest_paths"]:
            data["manifest_paths"].append(PERMANENT_MANIFEST_PATH)
            with open(config_path, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=4)
    except:
        pass

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
        if not self.frames: return
        self.config(image=self.frames[self.index])
        self.index = (self.index + 1) % len(self.frames)
        self.cancel = self.after(100, self.play)

    def stop(self):
        if self.cancel:
            self.after_cancel(self.cancel)
            self.cancel = None

    def update_bg(self, bg_color):
        self.config(bg=bg_color)

def load_config():
    config = {"mode": "dark", "male_voice": False}
    try:
        if os.path.exists(CONFIG_PATH):
            with open(CONFIG_PATH, "r") as f:
                for line in f:
                    line = line.strip()
                    if "=" in line:
                        key, _, val = line.partition("=")
                        config[key.strip()] = val.strip()
            config["male_voice"] = (config["male_voice"] == "True")
    except:
        pass
    return config

def save_config(mode, male_voice):
    try:
        with open(CONFIG_PATH, "w") as f:
            f.write(f"mode={mode}\n")
            f.write(f"male_voice={male_voice}\n")
    except:
        pass

class ChargingApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("VR Charging Status - Modified by Uppy")
        self.geometry("400x520")
        self.resizable(False, False)

        cfg = load_config()
        self._mode = cfg["mode"] if cfg["mode"] in THEMES else "dark"
        self._theme = THEMES[self._mode]
        self.configure(bg=self._theme["bg"])

        icon_path = resource_path(os.path.join("assets", "pawicon.ico"))
        if os.path.exists(icon_path):
            self.iconbitmap(icon_path)

        self.cat_charging     = resource_path(os.path.join("assets", "cat5.gif"))
        self.cat_not_charging = resource_path(os.path.join("assets", "cat1.gif"))

        self.label = AnimatedGIF(self, self.cat_not_charging, self._theme["bg"])
        self.label.pack(expand=True, fill="both")

        self.btn_frame = tk.Frame(self, bg=self._theme["bg"])
        self.btn_frame.pack(pady=(8, 16), fill="x", padx=20)

        self.voice_button = self._make_button(
            self.btn_frame,
            text="🎙 Switch to Male Voice",
            command=self.toggle_voice,
        )
        self.voice_button.pack(side="left", expand=True, fill="x", padx=(0, 6), ipady=4)

        self.theme_button = self._make_button(
            self.btn_frame,
            text="Light",
            command=self.toggle_theme,
        )
        self.theme_button.pack(side="right", ipady=4, ipadx=6)

        pygame.mixer.init()
        self.notif1 = self.load_sound("notif.wav")
        self.notif2 = self.load_sound("notif2.wav")
        self.male_voice = cfg["male_voice"]
        self.load_all_sounds()

        self._apply_theme()
        if self.male_voice:
            self.voice_button.config(text="🎙 Switch to Female Voice")

        self.remind_index   = 0
        self.was_charging   = None
        self.reminder_timer = None
        self.vr_system = None
        
        self.vr_thread = threading.Thread(target=self.init_openvr, daemon=True)
        self.vr_thread.start()

        self.after(1000, self.check_charging)

    def _make_button(self, parent, text, command, width=None):
        kwargs = dict(
            text=text, command=command,
            bg=self._theme["button_bg"], fg=self._theme["button_fg"],
            activebackground=self._theme["button_active_bg"],
            activeforeground=self._theme["button_active_fg"],
            relief="flat", font=("Segoe UI", 10), cursor="hand2", bd=0,
            highlightthickness=1, highlightbackground=self._theme["border"],
            highlightcolor=self._theme["accent"],
        )
        if width: kwargs["width"] = width
        return Button(parent, **kwargs)

    def toggle_theme(self):
        self._mode = "light" if self._mode == "dark" else "dark"
        self._theme = THEMES[self._mode]
        self._apply_theme()

    def _apply_theme(self):
        t = self._theme
        self.configure(bg=t["bg"])
        self.btn_frame.configure(bg=t["bg"])
        self.label.update_bg(t["bg"])
        style = dict(
            bg=t["button_bg"], fg=t["button_fg"],
            activebackground=t["button_active_bg"],
            activeforeground=t["button_active_fg"],
            highlightbackground=t["border"], highlightcolor=t["accent"],
        )
        self.voice_button.configure(**style)
        self.theme_button.configure(**style)
        self.theme_button.configure(text="Light" if self._mode == "dark" else "Dark")

    def load_sound(self, filename):
        path = resource_path(os.path.join("assets", filename))
        return pygame.mixer.Sound(path) if os.path.exists(path) else None

    def load_group(self, prefix, count):
        sounds = []
        for i in range(1, count + 1):
            name = f"{prefix}{i}{'m' if self.male_voice else ''}.wav"
            sound = self.load_sound(name)
            if sound: sounds.append(sound)
        return sounds

    def load_all_sounds(self):
        self.dc_sounds = self.load_group("dc", 3)
        self.connect_sounds = self.load_group("connect", 3)
        self.remind_sounds = []
        for i in [1, 2]:
            name = f"remind{i}{'m' if self.male_voice else ''}.wav"
            sound = self.load_sound(name)
            if sound: self.remind_sounds.append(sound)

    def toggle_voice(self):
        self.male_voice = not self.male_voice
        self.voice_button.config(
            text="🎙 Switch to Female Voice" if self.male_voice else "🎙 Switch to Male Voice"
        )
        self.load_all_sounds()

    def play_with_notif(self, sound, is_connect=False):
        notif = self.notif2 if is_connect else self.notif1
        if not notif or not sound:
            if sound: sound.play()
            return
        channel = pygame.mixer.find_channel()
        if not channel:
            sound.play()
            return
        channel.play(notif)
        def play_after():
            if not channel.get_busy(): sound.play()
            else: self.after(50, play_after)
        self.after(50, play_after)

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

    def init_openvr(self):
        try:
            openvr.init(openvr.VRApplication_Background)
            self.vr_system = openvr.VRSystem()
        except:
            self.vr_system = None

    def check_charging(self):
        if self.vr_system:
            is_charging = False
            for i in range(openvr.k_unMaxTrackedDeviceCount):
                try:
                    if self.vr_system.getTrackedDeviceClass(i) == openvr.TrackedDeviceClass_HMD:
                        is_charging = self.vr_system.getBoolTrackedDeviceProperty(i, openvr.Prop_DeviceIsCharging_Bool)
                        break
                except: continue

            if self.was_charging is not None:
                if self.was_charging and not is_charging:
                    if self.dc_sounds: self.play_with_notif(random.choice(self.dc_sounds))
                    self.start_reminder_loop()
                elif not self.was_charging and is_charging:
                    if self.connect_sounds: self.play_with_notif(random.choice(self.connect_sounds), True)
                    self.cancel_reminder()

            if is_charging: self.cancel_reminder()

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
        if self.vr_system: openvr.shutdown()
        self.cancel_reminder()
        self.destroy()

if __name__ == "__main__":
    register_vr_manifest()
    app = ChargingApp()
    app.protocol("WM_DELETE_WINDOW", app.on_closing)
    app.mainloop()
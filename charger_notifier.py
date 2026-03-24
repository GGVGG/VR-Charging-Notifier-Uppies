import tkinter as tk
from tkinter import Label, Button
from PIL import Image, ImageTk, ImageSequence
import openvr
import os
import threading
import pygame
import sys
import random

def resource_path(relative_path):
    try:
        base_path = sys._MEIPASS
    except Exception:
        base_path = os.path.abspath(".")
    return os.path.join(base_path, relative_path)

class AnimatedGIF(Label):
    def __init__(self, master, path, *args, **kwargs):
        super().__init__(master, *args, **kwargs)
        self.path = path
        self.frames = []
        self.load_frames()
        self.index = 0
        self.cancel = None
        self.play()

    def load_frames(self):
        img = Image.open(self.path)
        self.frames = [ImageTk.PhotoImage(frame.copy().convert('RGBA')) for frame in ImageSequence.Iterator(img)]

    def play(self):
        self.config(image=self.frames[self.index])
        self.index = (self.index + 1) % len(self.frames)
        self.cancel = self.after(100, self.play)

    def stop(self):
        if self.cancel:
            self.after_cancel(self.cancel)
            self.cancel = None

class ChargingApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("VR Charging Status")
        self.geometry("400x450")
        self.resizable(False, False)

        icon_path = resource_path(os.path.join("assets", "pawicon.ico"))
        if os.path.exists(icon_path):
            self.iconbitmap(icon_path)

        self.cat_charging = resource_path(os.path.join("assets", "cat5.gif"))
        self.cat_not_charging = resource_path(os.path.join("assets", "cat1.gif"))

        self.label = AnimatedGIF(self, self.cat_not_charging)
        self.label.pack(expand=True)

        pygame.mixer.init()

        self.notif1 = self.load_sound("notif.wav")
        self.notif2 = self.load_sound("notif2.wav")

        self.male_voice = False

        self.dc_sounds = []
        self.connect_sounds = []
        self.remind_sounds = []
        self.load_all_sounds()

        self.remind_index = 0
        self.was_charging = None
        self.reminder_timer = None

        self.vr_system = None
        self.vr_thread = threading.Thread(target=self.init_openvr, daemon=True)
        self.vr_thread.start()

        self.voice_button = Button(self, text="Switch to Male Voice", command=self.toggle_voice)
        self.voice_button.pack(pady=10)

        self.after(1000, self.check_charging)

    def load_sound(self, filename):
        path = resource_path(os.path.join("assets", filename))
        return pygame.mixer.Sound(path) if os.path.exists(path) else None

    def load_group(self, prefix, count, male_suffix="m"):
        sounds = []
        for i in range(1, count + 1):
            name = f"{prefix}{i}{'m' if self.male_voice else ''}.wav"
            sound = self.load_sound(name)
            if sound:
                sounds.append(sound)
        return sounds

    def load_all_sounds(self):
        self.dc_sounds = self.load_group("dc", 3)
        self.connect_sounds = self.load_group("connect", 3)
        self.remind_sounds = []
        for i in [1, 2]:
            sound = self.load_sound(f"remind{i}{'m' if self.male_voice else ''}.wav")
            if sound:
                self.remind_sounds.append(sound)

    def toggle_voice(self):
        self.male_voice = not self.male_voice
        self.voice_button.config(text="Switch to Female Voice" if self.male_voice else "Switch to Male Voice")
        self.load_all_sounds()

    def play_with_notif(self, sound, is_connect=False):
        notif = self.notif2 if is_connect else self.notif1
        if not notif:
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
        except openvr.OpenVRError as e:
            print(f"VR Init failed: {e}")
            self.vr_system = None

    def check_charging(self):
        if self.vr_system is not None:
            is_charging = False
            for device_index in range(openvr.k_unMaxTrackedDeviceCount):
                try:
                    device_class = self.vr_system.getTrackedDeviceClass(device_index)
                    if device_class == openvr.TrackedDeviceClass_HMD:
                        charging = self.vr_system.getBoolTrackedDeviceProperty(device_index, openvr.Prop_DeviceIsCharging_Bool)
                        is_charging = charging
                        break
                except openvr.OpenVRError:
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
                self.label = AnimatedGIF(self, new_gif)
                self.label.pack(expand=True)

        self.after(3000, self.check_charging)

    def on_closing(self):
        if self.vr_system:
            openvr.shutdown()
        self.cancel_reminder()
        self.destroy()

if __name__ == "__main__":
    app = ChargingApp()
    app.protocol("WM_DELETE_WINDOW", app.on_closing)
    app.mainloop()

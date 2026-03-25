# VR Charging Notifier v1.1 - Edited by Uppy

A charging status notifier for your VR headset, with cute cat GIFs and sound alerts for charging status. Choose between Warframe-like male and female voice notifications! (Current version doesn't have an option for no human voice reminder)

(Highly requested by my friend (you know who you are <3) with a Pico headset that doesn't have any notifying sound for when you're charging or not. Same with Quest only having a sound when you start charging)

---

## Download

You can download the latest version of the VR Charging Notifier here:

[Download VR Charging Notifier](https://github.com/GGVGG/VR-Charging-Notifier-Uppies/releases/latest).
---

## 🐾 Features

- **Cute Cat GIFs** showing charging and not-charging status
- **Sound Notifications** for connect, disconnect, and reminders
- **Male/Female Voice Toggle** for all sounds
- **Reminder Loop** if the headset stops charging
- **Notification Sounds**
- **Dark Mode** finally!
---

## Installation

1. Download the `Charger Notifier` from the [Releases](https://github.com/GGVGG/VR-Charging-Notifier-Uppies/releases/latest) page.
2. Make a folder for the .exe in a safe place since it will dump it's .cfg and .vrmanifest there.
3. Run the executable to start the app once, after that it should auto start with steamvr.
---

## 📝 Notes

- The app is designed for Windows users.
- If you encounter any issues or have suggestions, feel free to reach out via Discord: **cngg**.

---

## Keep in mind, this is very much a work in progress but I hope it can make your life a little easier!  
I don't get paid for any of this so any tips are much appreciated!  
☕ [Ko-Fi/itsnep](https://ko-fi.com/itsnep)
☕ [Ko-Fi/uploader](https://ko-fi.com/uploader)

## Command for building - convenience
```pyinstaller --onefile --noconsole --add-binary "libopenvr_api_64.dll;openvr" --add-data "assets;assets" --add-data "manifest.vrmanifest;." --icon="assets/pawicon.ico" charger_notifier.py```
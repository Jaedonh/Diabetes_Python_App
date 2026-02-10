# Diabetes Site Rotation Tracker (Kivy MVP)

This MVP is a Kivy mobile-style app to help a person (or parent/caregiver) track body-site rotation for:

- Injections
- CGM placement
- Port placement
- Pump placement

## What this MVP does

- Provides a **body map** of common site locations.
- Lets you choose a **device type** (Injection / CGM / Port / Pump).
- Stores each tap as a timestamped entry for the selected device.
- Supports **notes** per site entry (pain, inaccurate readings, movement issues, etc.).
- Color-codes body spots based on usage intensity:
  - Green = not used yet
  - Yellow = lightly used
  - Red = frequently used
- Shows recent history and suggests the least-used area.
- Saves data to `tracker_data.json` locally.

## Run

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python main.py
```

## MVP notes

- This is an MVP focused on workflow and data capture.
- Future upgrades could include:
  - Distinct front/back body images
  - Child/adult profile management screens
  - Calendar and spacing reminders
  - Export for doctor visits
  - Site cooldown rules per device

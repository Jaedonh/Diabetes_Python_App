# Diabetes Site Rotation Tracker (Kivy MVP)

A simple mobile-focused Kivy app to track site rotation for:
- Injections
- CGM
- Port
- Pump

## MVP features
- **Clickable body map** (human silhouette with site markers).
- **Separate chart/history per device type**.
- **Tap-to-log workflow** with optional notes for pain, bad readings, or movement issues.
- **Usage coloring** for quick rotation guidance:
  - Green = unused
  - Yellow = used 1-2 times
  - Red = heavily used
- Local persistence in `tracker_data.json`.

## Run
```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python main.py
```

## Next practical upgrades
- Distinct front/back body views
- Multi-profile support (parent + child)
- Device-specific cooldown reminders
- CSV/PDF export for doctor visits

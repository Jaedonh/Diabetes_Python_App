from __future__ import annotations

from datetime import datetime
from typing import Dict, List

from kivy.app import App
from kivy.lang import Builder
from kivy.properties import DictProperty, ListProperty, StringProperty
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.button import Button
from kivy.uix.gridlayout import GridLayout
from kivy.uix.popup import Popup

from storage import DiabetesTrackerStore

KV = """
<TrackerRoot>:
    orientation: "vertical"
    spacing: "8dp"
    padding: "8dp"

    BoxLayout:
        size_hint_y: None
        height: "44dp"
        spacing: "8dp"

        Spinner:
            id: patient_spinner
            text: root.current_patient
            values: root.patients
            on_text: root.change_patient(self.text)

        Spinner:
            id: device_spinner
            text: root.current_device
            values: root.devices
            on_text: root.change_device(self.text)

    Label:
        size_hint_y: None
        height: "22dp"
        text: "Tap a body area to log usage + notes"
        color: (0.1, 0.1, 0.1, 1)

    BodyMap:
        id: body_map
        size_hint_y: 0.62

    Label:
        size_hint_y: None
        height: "28dp"
        text: root.summary_text
        bold: True
        color: (0.15, 0.25, 0.7, 1)

    ScrollView:
        do_scroll_x: False

        Label:
            id: history_label
            text_size: self.width, None
            size_hint_y: None
            height: self.texture_size[1] + dp(16)
            text: root.history_text
            halign: "left"
            valign: "top"

<BodyMap>:
    cols: 2
    spacing: "8dp"
    padding: "8dp"
"""


SPOTS = [
    "Left Arm",
    "Right Arm",
    "Upper Abdomen Left",
    "Upper Abdomen Right",
    "Lower Abdomen Left",
    "Lower Abdomen Right",
    "Left Thigh",
    "Right Thigh",
    "Left Hip",
    "Right Hip",
    "Left Lower Back",
    "Right Lower Back",
]

DEVICES = ["Injection", "CGM", "Port", "Pump"]


class BodyMap(GridLayout):
    pass


class NotePopup(Popup):
    pass


class TrackerRoot(BoxLayout):
    patients = ListProperty(["Default Patient"])
    devices = ListProperty(DEVICES)
    current_patient = StringProperty("Default Patient")
    current_device = StringProperty("Injection")
    history_text = StringProperty("No entries yet.")
    summary_text = StringProperty("No spots logged yet for this device.")
    spot_usage = DictProperty({})

    def __init__(self, store: DiabetesTrackerStore, **kwargs):
        super().__init__(**kwargs)
        self.store = store
        self.data = self.store.load()

        self.patients = sorted(self.data.keys()) or ["Default Patient"]
        if not self.data:
            self.data[self.current_patient] = {device: {} for device in DEVICES}
            self.store.save(self.data)

    def on_kv_post(self, *_):
        self._build_body_buttons()
        self._refresh_screen()

    def _build_body_buttons(self):
        body_map = self.ids.body_map
        body_map.clear_widgets()

        for spot in SPOTS:
            btn = Button(text=spot, on_release=lambda _, s=spot: self._open_note_popup(s))
            body_map.add_widget(btn)

    def _open_note_popup(self, spot: str):
        content = Builder.load_string(
            """
BoxLayout:
    orientation: "vertical"
    spacing: "8dp"
    padding: "8dp"

    Label:
        text: "Spot: " + root.spot_name
        size_hint_y: None
        height: "32dp"

    TextInput:
        id: note_input
        hint_text: "Note (pain, bad reading, movement issues, etc.)"
        multiline: True

    BoxLayout:
        size_hint_y: None
        height: "42dp"
        spacing: "8dp"

        Button:
            text: "Save"
            on_release: app.root.save_spot(root.spot_name, note_input.text); root.dismiss()

        Button:
            text: "Cancel"
            on_release: root.dismiss()
"""
        )
        popup = NotePopup(title=f"Log {self.current_device} spot", size_hint=(0.9, 0.6))
        popup.spot_name = spot
        popup.content = content
        popup.open()

    def save_spot(self, spot: str, note: str):
        entry = {
            "spot": spot,
            "note": note.strip(),
            "timestamp": datetime.now().isoformat(timespec="minutes"),
        }

        patient_data = self.data.setdefault(self.current_patient, {device: {} for device in DEVICES})
        device_data = patient_data.setdefault(self.current_device, {})
        history: List[Dict[str, str]] = device_data.setdefault("history", [])
        history.append(entry)

        self.store.save(self.data)
        self._refresh_screen()

    def change_patient(self, patient: str):
        self.current_patient = patient
        self._refresh_screen()

    def change_device(self, device: str):
        self.current_device = device
        self._refresh_screen()

    def _refresh_screen(self):
        patient_data = self.data.setdefault(self.current_patient, {device: {} for device in DEVICES})
        device_data = patient_data.setdefault(self.current_device, {})
        history: List[Dict[str, str]] = device_data.get("history", [])

        usage: Dict[str, int] = {}
        for item in history:
            usage[item["spot"]] = usage.get(item["spot"], 0) + 1

        self.spot_usage = usage
        self._refresh_body_button_styles()

        if not history:
            self.history_text = "No entries yet. Start by tapping a spot in the body map."
            self.summary_text = "No spots logged yet for this device."
            return

        recent = list(reversed(history[-12:]))
        lines = [f"• {r['timestamp']} | {r['spot']} | {r['note'] or 'No note'}" for r in recent]
        self.history_text = "\n".join(lines)

        if usage:
            least_used = min(usage, key=usage.get)
            self.summary_text = f"Least used area suggestion: {least_used} ({usage[least_used]} uses)"

    def _refresh_body_button_styles(self):
        for child in self.ids.body_map.children:
            count = self.spot_usage.get(child.text, 0)
            if count == 0:
                child.background_color = (0.3, 0.7, 0.3, 1)
            elif count < 3:
                child.background_color = (0.95, 0.75, 0.25, 1)
            else:
                child.background_color = (0.9, 0.35, 0.35, 1)


class DiabetesTrackerApp(App):
    def build(self):
        Builder.load_string(KV)
        store = DiabetesTrackerStore("tracker_data.json")
        return TrackerRoot(store=store)


if __name__ == "__main__":
    DiabetesTrackerApp().run()

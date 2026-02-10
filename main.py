from __future__ import annotations

from datetime import datetime
from math import hypot
from typing import Dict, List, Tuple

from kivy.app import App
from kivy.graphics import Color, Ellipse, Line, Rectangle
from kivy.lang import Builder
from kivy.properties import DictProperty, ListProperty, NumericProperty, StringProperty
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.popup import Popup
from kivy.uix.widget import Widget

from storage import DiabetesTrackerStore

KV = """
#:import dp kivy.metrics.dp

<TrackerRoot>:
    orientation: "vertical"
    padding: dp(10)
    spacing: dp(8)

    Label:
        text: "Diabetes Rotation Tracker"
        size_hint_y: None
        height: dp(34)
        bold: True
        color: (0.15, 0.2, 0.45, 1)

    BoxLayout:
        size_hint_y: None
        height: dp(44)
        spacing: dp(6)

        Label:
            text: "Device"
            size_hint_x: None
            width: dp(70)
            halign: "left"
            valign: "middle"
            text_size: self.size

        Spinner:
            text: root.current_device
            values: root.devices
            on_text: root.change_device(self.text)

    Label:
        size_hint_y: None
        height: dp(22)
        text: "Tap a highlighted site on the body map"
        color: (0.2, 0.2, 0.2, 1)

    BodyMap:
        id: body_map
        size_hint_y: 0.62
        on_spot_tapped: root.open_note_popup(args[1])

    Label:
        size_hint_y: None
        height: dp(28)
        text: root.summary_text
        color: (0.15, 0.25, 0.7, 1)

    ScrollView:
        do_scroll_x: False

        Label:
            text_size: self.width, None
            size_hint_y: None
            height: self.texture_size[1] + dp(12)
            text: root.history_text
            halign: "left"
            valign: "top"
"""

DEVICE_TYPES = ["Injection", "CGM", "Port", "Pump"]

# relative x, y in map coordinate space (0..1)
SPOT_COORDS: Dict[str, Tuple[float, float]] = {
    "Left Arm": (0.34, 0.66),
    "Right Arm": (0.66, 0.66),
    "Upper Abdomen Left": (0.44, 0.54),
    "Upper Abdomen Right": (0.56, 0.54),
    "Lower Abdomen Left": (0.45, 0.46),
    "Lower Abdomen Right": (0.55, 0.46),
    "Left Thigh": (0.46, 0.31),
    "Right Thigh": (0.54, 0.31),
    "Left Hip": (0.43, 0.41),
    "Right Hip": (0.57, 0.41),
    "Left Lower Back": (0.42, 0.50),
    "Right Lower Back": (0.58, 0.50),
}


class BodyMap(Widget):
    __events__ = ("on_spot_tapped",)

    spot_usage = DictProperty({})
    marker_radius = NumericProperty(16)

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.bind(pos=self._redraw, size=self._redraw, spot_usage=self._redraw)

    def on_spot_tapped(self, _spot_name: str):
        return None

    def on_touch_down(self, touch):
        if not self.collide_point(*touch.pos):
            return super().on_touch_down(touch)

        hit_spot = self._find_spot_at_point(touch.x, touch.y)
        if hit_spot:
            self.dispatch("on_spot_tapped", hit_spot)
            return True
        return super().on_touch_down(touch)

    def _find_spot_at_point(self, x: float, y: float) -> str | None:
        radius = self._spot_pixel_radius()
        for spot, (sx, sy) in SPOT_COORDS.items():
            px, py = self._to_widget_coords(sx, sy)
            if hypot(px - x, py - y) <= radius:
                return spot
        return None

    def _to_widget_coords(self, rx: float, ry: float) -> Tuple[float, float]:
        return self.x + (rx * self.width), self.y + (ry * self.height)

    def _spot_pixel_radius(self) -> float:
        return max(min(self.width, self.height) * 0.03, self.marker_radius)

    def _redraw(self, *_):
        self.canvas.clear()
        with self.canvas:
            Color(0.96, 0.97, 1, 1)
            Rectangle(pos=self.pos, size=self.size)

            # simple human silhouette
            body_width = self.width * 0.16
            body_height = self.height * 0.34
            body_x = self.center_x - body_width / 2
            body_y = self.y + self.height * 0.40

            Color(0.88, 0.88, 0.9, 1)
            Ellipse(pos=(self.center_x - self.width * 0.05, self.y + self.height * 0.76), size=(self.width * 0.10, self.height * 0.13))
            Rectangle(pos=(body_x, body_y), size=(body_width, body_height))

            arm_w = self.width * 0.06
            arm_h = self.height * 0.27
            Rectangle(pos=(body_x - arm_w, body_y + self.height * 0.05), size=(arm_w, arm_h))
            Rectangle(pos=(body_x + body_width, body_y + self.height * 0.05), size=(arm_w, arm_h))

            leg_w = self.width * 0.07
            leg_h = self.height * 0.30
            Rectangle(pos=(self.center_x - leg_w - self.width * 0.01, self.y + self.height * 0.10), size=(leg_w, leg_h))
            Rectangle(pos=(self.center_x + self.width * 0.01, self.y + self.height * 0.10), size=(leg_w, leg_h))

            Line(rectangle=(self.x, self.y, self.width, self.height), width=1)

            radius = self._spot_pixel_radius()
            for spot, (sx, sy) in SPOT_COORDS.items():
                px, py = self._to_widget_coords(sx, sy)
                usage_count = self.spot_usage.get(spot, 0)
                if usage_count == 0:
                    Color(0.2, 0.7, 0.3, 0.95)
                elif usage_count < 3:
                    Color(0.95, 0.75, 0.2, 0.95)
                else:
                    Color(0.9, 0.3, 0.3, 0.95)

                Ellipse(pos=(px - radius, py - radius), size=(radius * 2, radius * 2))


class TrackerRoot(BoxLayout):
    devices = ListProperty(DEVICE_TYPES)
    current_device = StringProperty("Injection")
    history_text = StringProperty("No entries yet.")
    summary_text = StringProperty("No spots logged yet for this device.")
    spot_usage = DictProperty({})

    def __init__(self, store: DiabetesTrackerStore, **kwargs):
        super().__init__(**kwargs)
        self.store = store
        self.data = self.store.load()
        if not self.data:
            self.data = {device: {"history": []} for device in DEVICE_TYPES}
            self.store.save(self.data)

    def on_kv_post(self, *_):
        self._refresh_screen()

    def change_device(self, device: str):
        self.current_device = device
        self._refresh_screen()

    def open_note_popup(self, spot: str):
        content = Builder.load_string(
            """
#:import dp kivy.metrics.dp
BoxLayout:
    orientation: "vertical"
    spacing: dp(8)
    padding: dp(8)

    Label:
        text: "Site: " + root.spot_name
        size_hint_y: None
        height: dp(30)

    TextInput:
        id: note_input
        hint_text: "Optional note (pain, bad reading, movement issue...)"
        multiline: True

    BoxLayout:
        size_hint_y: None
        height: dp(40)
        spacing: dp(8)

        Button:
            text: "Save"
            on_release: app.root.save_spot(root.spot_name, note_input.text); root.dismiss()

        Button:
            text: "Cancel"
            on_release: root.dismiss()
"""
        )
        popup = Popup(title=f"Log {self.current_device}", size_hint=(0.92, 0.56))
        popup.spot_name = spot
        popup.content = content
        popup.open()

    def save_spot(self, spot: str, note: str):
        entry = {
            "spot": spot,
            "note": note.strip(),
            "timestamp": datetime.now().isoformat(timespec="minutes"),
        }
        self.data.setdefault(self.current_device, {"history": []}).setdefault("history", []).append(entry)
        self.store.save(self.data)
        self._refresh_screen()

    def _refresh_screen(self):
        history: List[Dict[str, str]] = self.data.setdefault(self.current_device, {"history": []}).get("history", [])

        usage: Dict[str, int] = {}
        for entry in history:
            usage[entry["spot"]] = usage.get(entry["spot"], 0) + 1

        self.spot_usage = usage
        self.ids.body_map.spot_usage = usage

        if not history:
            self.summary_text = "No spots logged yet for this device."
            self.history_text = "Tap a body marker to save a site entry."
            return

        least_used_spot = min(usage, key=usage.get)
        self.summary_text = f"Rotation tip: use {least_used_spot} next ({usage[least_used_spot]} uses)."

        recent_entries = list(reversed(history[-10:]))
        self.history_text = "\n".join(
            f"• {item['timestamp']}  |  {item['spot']}  |  {item['note'] or 'No note'}" for item in recent_entries
        )


class DiabetesTrackerApp(App):
    def build(self):
        Builder.load_string(KV)
        store = DiabetesTrackerStore("tracker_data.json")
        return TrackerRoot(store=store)


if __name__ == "__main__":
    DiabetesTrackerApp().run()

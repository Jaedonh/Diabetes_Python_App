from __future__ import annotations

from datetime import datetime
from math import hypot
from typing import Dict, List, Tuple

from kivy.app import App
from kivy.graphics import Color, Ellipse, Line, Rectangle, RoundedRectangle
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

    canvas.before:
        Color:
            rgba: 0.96, 0.97, 1, 1
        Rectangle:
            pos: self.pos
            size: self.size

    Label:
        text: "Diabetes Body Site Rotation"
        size_hint_y: None
        height: dp(34)
        bold: True
        color: (0.15, 0.2, 0.45, 1)

    BoxLayout:
        size_hint_y: None
        height: dp(44)
        spacing: dp(8)

        Label:
            text: "Device"
            size_hint_x: None
            width: dp(64)
            text_size: self.size
            halign: "left"
            valign: "middle"

        Spinner:
            text: root.current_device
            values: root.devices
            on_text: root.change_device(self.text)

        Label:
            text: "View"
            size_hint_x: None
            width: dp(44)
            text_size: self.size
            halign: "left"
            valign: "middle"

        Spinner:
            text: root.current_view
            values: ["Front", "Back"]
            on_text: root.change_view(self.text)

    Label:
        size_hint_y: None
        height: dp(22)
        text: "Tap a body marker to log a site + note"
        color: (0.2, 0.2, 0.2, 1)

    BodyMap:
        id: body_map
        size_hint_y: 0.62
        view_mode: root.current_view
        on_spot_tapped: root.open_note_popup(args[1])

    Label:
        size_hint_y: None
        height: dp(24)
        text: "Legend: Green=unused  Yellow=1-2 uses  Red=3+ uses"
        color: (0.25, 0.25, 0.25, 1)

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

# relative x,y coordinates (0..1) for two chart views
FRONT_SPOTS: Dict[str, Tuple[float, float]] = {
    "Left Arm": (0.30, 0.67),
    "Right Arm": (0.70, 0.67),
    "Upper Abdomen Left": (0.44, 0.54),
    "Upper Abdomen Right": (0.56, 0.54),
    "Lower Abdomen Left": (0.46, 0.46),
    "Lower Abdomen Right": (0.54, 0.46),
    "Left Thigh": (0.46, 0.30),
    "Right Thigh": (0.54, 0.30),
    "Left Hip": (0.44, 0.40),
    "Right Hip": (0.56, 0.40),
}

BACK_SPOTS: Dict[str, Tuple[float, float]] = {
    "Left Arm": (0.30, 0.67),
    "Right Arm": (0.70, 0.67),
    "Left Lower Back": (0.44, 0.50),
    "Right Lower Back": (0.56, 0.50),
    "Left Hip": (0.44, 0.40),
    "Right Hip": (0.56, 0.40),
    "Left Thigh": (0.46, 0.30),
    "Right Thigh": (0.54, 0.30),
}


class BodyMap(Widget):
    __events__ = ("on_spot_tapped",)

    spot_usage = DictProperty({})
    marker_radius = NumericProperty(15)
    view_mode = StringProperty("Front")

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.bind(pos=self._redraw, size=self._redraw, spot_usage=self._redraw, view_mode=self._redraw)

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

    def _active_spots(self) -> Dict[str, Tuple[float, float]]:
        return FRONT_SPOTS if self.view_mode == "Front" else BACK_SPOTS

    def _find_spot_at_point(self, x: float, y: float) -> str | None:
        radius = self._spot_pixel_radius()
        for spot, (sx, sy) in self._active_spots().items():
            px, py = self._to_widget_coords(sx, sy)
            if hypot(px - x, py - y) <= radius:
                return spot
        return None

    def _to_widget_coords(self, rx: float, ry: float) -> Tuple[float, float]:
        return self.x + (rx * self.width), self.y + (ry * self.height)

    def _spot_pixel_radius(self) -> float:
        return max(min(self.width, self.height) * 0.028, self.marker_radius)

    def _draw_body_outline(self):
        # clean body-chart style similar to EMR charts (simple silhouette)
        x, y, w, h = self.x, self.y, self.width, self.height
        cx = self.center_x

        Color(1, 1, 1, 1)
        RoundedRectangle(pos=(x + w * 0.04, y + h * 0.04), size=(w * 0.92, h * 0.92), radius=[14])

        Color(0.75, 0.78, 0.84, 1)
        Line(rounded_rectangle=(x + w * 0.04, y + h * 0.04, w * 0.92, h * 0.92, 14), width=1.2)

        Color(0.86, 0.87, 0.90, 1)
        Ellipse(pos=(cx - w * 0.06, y + h * 0.77), size=(w * 0.12, h * 0.14))
        Rectangle(pos=(cx - w * 0.10, y + h * 0.43), size=(w * 0.20, h * 0.30))
        Rectangle(pos=(cx - w * 0.16, y + h * 0.47), size=(w * 0.06, h * 0.23))
        Rectangle(pos=(cx + w * 0.10, y + h * 0.47), size=(w * 0.06, h * 0.23))
        Rectangle(pos=(cx - w * 0.09, y + h * 0.14), size=(w * 0.07, h * 0.29))
        Rectangle(pos=(cx + w * 0.02, y + h * 0.14), size=(w * 0.07, h * 0.29))

        Color(0.68, 0.71, 0.77, 1)
        Line(rectangle=(cx - w * 0.10, y + h * 0.43, w * 0.20, h * 0.30), width=1)
        Line(ellipse=(cx - w * 0.06, y + h * 0.77, w * 0.12, h * 0.14), width=1)

    def _redraw(self, *_):
        self.canvas.clear()
        with self.canvas:
            Color(0.94, 0.96, 1, 1)
            Rectangle(pos=self.pos, size=self.size)

            self._draw_body_outline()

            radius = self._spot_pixel_radius()
            for spot, (sx, sy) in self._active_spots().items():
                px, py = self._to_widget_coords(sx, sy)
                use_count = self.spot_usage.get(spot, 0)
                if use_count == 0:
                    Color(0.2, 0.72, 0.32, 0.95)
                elif use_count < 3:
                    Color(0.96, 0.75, 0.18, 0.96)
                else:
                    Color(0.88, 0.25, 0.25, 0.96)

                Ellipse(pos=(px - radius, py - radius), size=(radius * 2, radius * 2))


class TrackerRoot(BoxLayout):
    devices = ListProperty(DEVICE_TYPES)
    current_device = StringProperty("Injection")
    current_view = StringProperty("Front")
    history_text = StringProperty("No entries yet.")
    summary_text = StringProperty("No spots logged yet for this device.")

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

    def change_view(self, view: str):
        self.current_view = view

    def open_note_popup(self, spot: str):
        popup = Popup(title=f"Log {self.current_device} site", size_hint=(0.92, 0.58))
        content = Builder.load_string(
            """
#:import dp kivy.metrics.dp
BoxLayout:
    orientation: "vertical"
    spacing: dp(8)
    padding: dp(8)

    Label:
        id: spot_lbl
        size_hint_y: None
        height: dp(32)

    TextInput:
        id: note_input
        hint_text: "Optional note: pain, inaccurate reading, movement issues"
        multiline: True

    BoxLayout:
        size_hint_y: None
        height: dp(42)
        spacing: dp(8)

        Button:
            id: save_btn
            text: "Save"
        Button:
            id: cancel_btn
            text: "Cancel"
"""
        )
        content.ids.spot_lbl.text = f"Site: {spot}"
        content.ids.cancel_btn.bind(on_release=lambda *_: popup.dismiss())
        content.ids.save_btn.bind(
            on_release=lambda *_: self._save_popup_entry_and_close(popup, spot, content.ids.note_input.text)
        )

        popup.content = content
        popup.open()

    def _save_popup_entry_and_close(self, popup: Popup, spot: str, note: str):
        self.save_spot(spot, note)
        popup.dismiss()

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

        self.ids.body_map.spot_usage = usage

        if not history:
            self.summary_text = "No spots logged yet for this device."
            self.history_text = "Tap a body marker to save an entry."
            return

        least_used_spot = min(usage, key=usage.get)
        self.summary_text = f"Rotation tip: use {least_used_spot} next ({usage[least_used_spot]} uses)."

        recent_entries = list(reversed(history[-12:]))
        self.history_text = "\n".join(
            f"• {item['timestamp']} | {item['spot']} | {item['note'] or 'No note'}" for item in recent_entries
        )


class DiabetesTrackerApp(App):
    def build(self):
        Builder.load_string(KV)
        store = DiabetesTrackerStore("tracker_data.json")
        return TrackerRoot(store=store)


if __name__ == "__main__":
    DiabetesTrackerApp().run()

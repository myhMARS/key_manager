"""Reusable UI widgets: SnackBar, Dot, TouchCard, KeyItem, EmptyKeyState."""

import time

from kivy.app import App
from kivy.clock import Clock
from kivy.core.clipboard import Clipboard
from kivy.metrics import dp
from kivy.properties import (
    BooleanProperty, ListProperty, NumericProperty, StringProperty,
)
from kivy.uix.button import Button
from kivy.uix.dropdown import DropDown
from kivy.uix.image import Image
from kivy.uix.label import Label
from kivy.uix.widget import Widget

from theme import PLATFORM_COLORS


# ================================================================
#  SNACK BAR
# ================================================================
class SnackBar(Widget):
    message = StringProperty("")
    bg_color = ListProperty([0.2, 0.8, 0.4, 1])
    snack_type = StringProperty("success")

    def show(self, root_widget, message, snack_type="success"):
        self.message = message
        self.snack_type = snack_type
        if snack_type == "success":
            self.bg_color = [0.2, 0.8, 0.4, 1]
        elif snack_type == "error":
            self.bg_color = [0.9, 0.2, 0.2, 1]
        else:
            self.bg_color = [0.95, 0.55, 0.1, 1]

        if self.parent:
            self.parent.remove_widget(self)

        root_widget.add_widget(self)
        self.y = dp(16)

        Clock.schedule_once(lambda dt: self._dismiss(), 2.5)

    def _dismiss(self):
        if self.parent:
            self.parent.remove_widget(self)


# ================================================================
#  DOT INDICATOR
# ================================================================
class Dot(Widget):
    dot_color = ListProperty([0.7, 0.7, 0.7, 1])


# ================================================================
#  TOUCH CARD (swipeable card on home screen)
# ================================================================
class TouchCard(Widget):
    platform_name = StringProperty("")
    key_count_text = StringProperty("0 keys")
    accent_color = ListProperty([0.42, 0.42, 0.42, 1])
    accent_bg_color = ListProperty([0.42, 0.42, 0.42, 0.09])
    icon_bg_color = ListProperty([0.42, 0.42, 0.42, 0.12])
    has_balance = BooleanProperty(False)
    feature_text = StringProperty("Key management")
    platform_id = StringProperty("")
    icon_source = StringProperty("")
    icon_text = StringProperty("")

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self._touch_start_x = 0
        self._touch_start_y = 0
        self._touch_start_pos = (0, 0)
        self._touch_start_time = 0
        self._swiping = False
        self.register_event_type('on_swipe_left')
        self.register_event_type('on_swipe_right')
        self.register_event_type('on_tap_card')
        self.register_event_type('on_snap_back')

    def on_icon_source(self, _, value):
        if value:
            img = Image(source=value, size_hint=(None, None), size=(dp(44), dp(44)))
            self.ids.icon_box.clear_widgets()
            self.ids.icon_box.add_widget(img)

    def on_icon_text(self, _, value):
        if value and not self.icon_source:
            self.ids.icon_box.clear_widgets()
            lbl = Label(text=value, font_size='22sp', bold=True,
                        size_hint=(None, None),
                        size=(dp(44), dp(44)), halign='center', valign='middle',
                        color=self.accent_color)
            lbl.text_size = (dp(44), dp(44))
            self.ids.icon_box.add_widget(lbl)

    def on_touch_down(self, touch):
        if self.collide_point(*touch.pos):
            self._touch_start_x = touch.x
            self._touch_start_y = touch.y
            self._touch_start_pos = (self.x, self.y)
            self._touch_start_time = touch.time_start
            self._swiping = False
            touch.grab(self)
            return True
        return super().on_touch_down(touch)

    def on_touch_move(self, touch):
        if touch.grab_current is self:
            dx = touch.x - self._touch_start_x
            if abs(dx) > dp(10):
                self._swiping = True
            if self._swiping:
                # Move card with finger
                self.x = self._touch_start_pos[0] + dx
                # Fade opacity based on drag distance
                progress = min(abs(dx) / dp(150), 1.0)
                self.opacity = 1.0 - progress * 0.5
            return True
        return super().on_touch_move(touch)

    def on_touch_up(self, touch):
        if touch.grab_current is self:
            dx = touch.x - self._touch_start_x
            dy = abs(touch.y - self._touch_start_y)

            # Calculate velocity (pixels per second)
            elapsed = time.time() - self._touch_start_time
            velocity = abs(dx) / max(elapsed, 0.01)

            # Trigger swipe if: distance > 30dp OR velocity > 400px/s (with min 15dp move)
            is_swipe = (abs(dx) > dp(30) and abs(dx) > dy) or \
                       (velocity > dp(400) and abs(dx) > dp(15) and abs(dx) > dy)

            if is_swipe:
                if dx < 0:
                    self.dispatch('on_swipe_left')
                else:
                    self.dispatch('on_swipe_right')
            elif self._swiping:
                # Didn't swipe far/fast enough, snap back
                self.dispatch('on_snap_back')
            else:
                relative_x = touch.x - self.x
                self.dispatch('on_tap_card', relative_x)

            touch.ungrab(self)
            return True
        return super().on_touch_up(touch)

    def on_swipe_left(self):
        pass

    def on_swipe_right(self):
        pass

    def on_snap_back(self):
        pass

    def on_tap_card(self, x):
        pass

    def on_view_keys(self):
        from events import bus
        bus.dispatch('on_navigate', 'platform', platform_id=self.platform_id)


# ================================================================
#  KEY ITEM
# ================================================================
class KeyItem(Widget):
    key_name = StringProperty("")
    masked_key = StringProperty("")
    created_at = StringProperty("")
    raw_key = StringProperty("")
    key_index = NumericProperty(0)
    platform_id = StringProperty("")
    has_balance = BooleanProperty(False)
    decrypt_ok = BooleanProperty(True)
    key_status = StringProperty("unknown")  # "unknown", "valid", "invalid", "checking"

    def open_menu(self, button):
        from ui.popups import RenameKeyPopup
        from events import bus

        app = App.get_running_app()
        dropdown = DropDown()
        dropdown.auto_width = False
        dropdown.width = dp(160)

        def make_btn(text, on_select):
            btn = Button(
                text=text,
                size_hint_y=None,
                height=dp(44),
                size_hint_x=1,
                background_normal='',
                background_down='',
                background_color=(0.98, 0.98, 0.98, 1),
                color=(0.15, 0.15, 0.15, 1),
                font_size='14sp',
            )
            btn.bind(on_release=lambda _: dropdown.select(on_select))
            return btn

        def do_verify():
            if not self.decrypt_ok:
                App.get_running_app().show_snackbar("Cannot verify: decryption failed", "error")
                return
            bus.dispatch('on_navigate', 'verify_key',
                         platform_id=self.platform_id, key=self.raw_key)

        def do_copy():
            if not self.decrypt_ok:
                App.get_running_app().show_snackbar("Cannot copy: decryption failed", "error")
                return
            Clipboard.copy(self.raw_key)
            App.get_running_app().show_snackbar("Copied to clipboard", "success")

        def do_rename():
            popup = RenameKeyPopup(
                self.platform_id, self.key_index, self.key_name,
                PLATFORM_COLORS.get(self.platform_id, (0.42, 0.42, 0.42, 1)))
            popup.open()

        def do_delete():
            bus.dispatch('on_key_deleted', self.platform_id,
                         key_index=self.key_index)
            App.get_running_app().show_snackbar("Key deleted", "warning")

        dropdown.add_widget(make_btn(
            "Balance" if self.has_balance else "Verify", do_verify))
        dropdown.add_widget(make_btn("Rename", do_rename))
        dropdown.add_widget(make_btn("Copy key", do_copy))
        dropdown.add_widget(make_btn("Delete", do_delete))

        dropdown.bind(on_select=lambda instance, x: x())
        dropdown.open(button)


# ================================================================
#  EMPTY KEY STATE
# ================================================================
class EmptyKeyState(Widget):
    pass

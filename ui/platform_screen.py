"""Platform detail screen with key list and API verification."""

import threading
import httpx

from kivy.app import App
from kivy.clock import Clock
from kivy.metrics import dp
from kivy.properties import ListProperty, StringProperty
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.image import Image
from kivy.uix.label import Label
from kivy.uix.screenmanager import Screen

import storage
from config import PLATFORM_COLORS
from platforms import get_platform
from ui.popups import AddKeyPopup
from ui.widgets import EmptyKeyState, KeyItem


class PlatformScreen(Screen):
    platform_id = StringProperty("")
    accent_color = ListProperty([0.42, 0.42, 0.42, 1])

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self._plat = None

    def load_platform(self, platform_id):
        self.platform_id = platform_id
        self._plat = get_platform(platform_id)
        if self._plat is None:
            self.go_back()
            return
        accent = PLATFORM_COLORS.get(platform_id, (0.42, 0.42, 0.42, 1))
        self.accent_color = accent
        self.ids.header_title.text = self._plat.name
        self.ids.header_subtitle.text = (
            "Balance check" if self._plat.balance_url
            else "Key verification" if self._plat.verify_url
            else "Key management"
        )

        icon_area = self.ids.header_icon_area
        icon_area.clear_widgets()
        if self._plat.icon_path:
            img = Image(source=self._plat.icon_path, size_hint=(None, None),
                        size=(dp(24), dp(24)))
            icon_area.add_widget(img)
        else:
            lbl = Label(text=self._plat.icon, font_size='18sp', bold=True,
                        size_hint=(None, None), size=(dp(24), dp(24)),
                        halign='center', valign='middle',
                        color=self.accent_color)
            lbl.text_size = (dp(24), dp(24))
            icon_area.add_widget(lbl)

        # Show edit/delete buttons only for custom platforms
        del_btn = self.ids.delete_platform_btn
        edit_btn = self.ids.edit_platform_btn
        if self._plat.is_custom:
            del_btn.opacity = 1
            del_btn.disabled = False
            edit_btn.opacity = 1
            edit_btn.disabled = False
        else:
            del_btn.opacity = 0
            del_btn.disabled = True
            edit_btn.opacity = 0
            edit_btn.disabled = True

        self._hide_result()
        self.ids.progress_bar.opacity = 0
        self.refresh_keys()

    def go_back(self):
        self.manager.current = 'home'

    def confirm_delete_platform(self):
        """Show confirmation if keys exist, otherwise delete directly."""
        from ui.popups import ConfirmDeletePlatformPopup

        key_count = storage.key_count(self.platform_id)
        if key_count > 0:
            popup = ConfirmDeletePlatformPopup(
                self.platform_id, self._plat.name, key_count)
            popup.open()
        else:
            self._do_delete_platform()

    def _do_delete_platform(self):
        """Actually delete the custom platform."""
        storage.delete_custom_platform(self.platform_id)
        app = App.get_running_app()
        app.show_snackbar(f"{self._plat.name} deleted", "warning")
        self.go_back()
        # Rebuild home deck
        home = app.sm.get_screen('home')
        home.rebuild_deck()

    def show_edit_platform(self):
        """Open edit popup for custom platform."""
        from ui.popups import EditPlatformPopup
        popup = EditPlatformPopup(
            platform_id=self.platform_id,
            name=self._plat.name,
            base_url=self._plat.base_url,
            verify_url=self._plat.verify_url,
            accent_color=self.accent_color,
        )
        popup.open()

    def refresh_keys(self):
        keys = storage.get_keys(self.platform_id)
        container = self.ids.key_list_container
        container.clear_widgets()

        for i, k in enumerate(keys):
            masked = (
                k["key"][:6] + "****" + k["key"][-4:]
                if len(k["key"]) > 10 else "****"
            )
            item = KeyItem(
                key_name=k["name"],
                masked_key=masked,
                created_at=k["created_at"],
                raw_key=k["key"],
                key_index=i,
                platform_id=self.platform_id,
                has_balance=bool(self._plat.balance_url if self._plat else False),
            )
            container.add_widget(item)

        if not keys:
            container.add_widget(EmptyKeyState())

    def show_add_dialog(self):
        popup = AddKeyPopup(self._plat, self.accent_color)
        popup.open()

    def trigger_check(self, api_key):
        self.ids.progress_bar.opacity = 1
        self.ids.progress_bar.value = 0
        self._hide_result()

        plat = self._plat

        def _run():
            try:
                headers = {"Authorization": plat.auth_header.format(api_key=api_key)}
                with httpx.Client(timeout=10) as client:
                    if plat.balance_url:
                        url = plat.base_url + plat.balance_url
                        resp = client.get(url, headers=headers)
                        if resp.status_code == 200:
                            data = resp.json()
                            Clock.schedule_once(lambda dt: self._show_balance_result(data))
                        elif resp.status_code == 401:
                            Clock.schedule_once(lambda dt: self._show_error("Invalid API key"))
                        else:
                            Clock.schedule_once(lambda dt: self._show_error(f"HTTP {resp.status_code}"))
                    elif plat.verify_url:
                        url = plat.base_url + plat.verify_url
                        resp = client.get(url, headers=headers)
                        valid = resp.status_code == 200
                        Clock.schedule_once(
                            lambda dt, v=valid, s=resp.status_code: self._show_verify_result(v, s))
            except httpx.ConnectError:
                Clock.schedule_once(lambda dt: self._show_error("Network error"))
            except httpx.TimeoutException:
                Clock.schedule_once(lambda dt: self._show_error("Request timed out"))
            except Exception as e:
                err_msg = f"Error: {e}"
                Clock.schedule_once(lambda dt: self._show_error(err_msg))
            finally:
                Clock.schedule_once(lambda dt: self._hide_progress())

        threading.Thread(target=_run, daemon=True).start()

    def _show_balance_result(self, data):
        container = self.ids.result_card
        container.clear_widgets()

        lbl_title = Label(
            text="Balance", font_size="15sp", bold=True,
            color=(0.1, 0.1, 0.1, 1),
            size_hint_y=None, height=dp(28),
            halign='center', valign='middle',
        )
        lbl_title.bind(size=lambda w, s: setattr(w, 'text_size', s))
        container.add_widget(lbl_title)

        rows = 1

        if not data.get("is_available"):
            lbl = Label(
                text="Balance info not available", font_size="13sp",
                color=(0.5, 0.5, 0.5, 1), size_hint_y=None, height=dp(24),
                halign='left', valign='middle',
            )
            lbl.bind(size=lambda w, s: setattr(w, 'text_size', s))
            container.add_widget(lbl)
            rows += 1
        else:
            for info in data.get("balance_infos", []):
                for label_text, value in [
                    ("Total Balance", str(info.get("total_balance", "-"))),
                    ("Topped Up", str(info.get("topped_up_balance", "-"))),
                    ("Granted", str(info.get("granted_balance", "-"))),
                    ("Currency", str(info.get("currency", "-"))),
                ]:
                    row = BoxLayout(size_hint_y=None, height=dp(28), spacing=dp(4))
                    lbl_left = Label(
                        text=label_text, font_size="13sp", color=(0.5, 0.5, 0.5, 1),
                        size_hint_x=0.5, halign='left', valign='middle',
                    )
                    lbl_left.bind(size=lambda w, s: setattr(w, 'text_size', s))
                    lbl_right = Label(
                        text=value, font_size="14sp", bold=True, color=(0.1, 0.1, 0.1, 1),
                        size_hint_x=0.5, halign='right', valign='middle',
                    )
                    lbl_right.bind(size=lambda w, s: setattr(w, 'text_size', s))
                    row.add_widget(lbl_left)
                    row.add_widget(lbl_right)
                    container.add_widget(row)
                    rows += 1

        content_height = rows * dp(28) + max(0, rows - 1) * dp(6)
        container.height = content_height + dp(32)
        container.opacity = 1

    def _show_verify_result(self, valid, status_code):
        container = self.ids.result_card
        container.clear_widgets()

        icon = "✓" if valid else "✗"
        color = (0.06, 0.64, 0.50, 1) if valid else (0.9, 0.2, 0.2, 1)
        msg = "Key is valid" if valid else f"Key rejected (HTTP {status_code})"

        row = BoxLayout(size_hint_y=None, height=dp(28), spacing=dp(8))
        lbl_icon = Label(
            text=icon, font_size="16sp", bold=True, color=color,
            size_hint_x=None, width=dp(24),
            halign='center', valign='middle',
        )
        lbl_icon.bind(size=lambda w, s: setattr(w, 'text_size', s))
        row.add_widget(lbl_icon)

        lbl_msg = Label(
            text=msg, font_size="14sp", bold=True, color=color,
            size_hint_x=1, halign='left', valign='middle',
        )
        lbl_msg.bind(size=lambda w, s: setattr(w, 'text_size', s))
        row.add_widget(lbl_msg)
        container.add_widget(row)
        container.height = dp(60)
        container.opacity = 1

    def _show_error(self, msg):
        container = self.ids.result_card
        container.clear_widgets()

        row = BoxLayout(size_hint_y=None, height=dp(28), spacing=dp(8))
        lbl_icon = Label(
            text="✗", font_size="16sp", bold=True,
            color=(0.9, 0.2, 0.2, 1),
            size_hint_x=None, width=dp(24),
            halign='center', valign='middle',
        )
        lbl_icon.bind(size=lambda w, s: setattr(w, 'text_size', s))
        row.add_widget(lbl_icon)

        lbl_msg = Label(
            text=msg, font_size="14sp", bold=True, color=(0.9, 0.2, 0.2, 1),
            size_hint_x=1, halign='left', valign='middle',
        )
        lbl_msg.bind(size=lambda w, s: setattr(w, 'text_size', s))
        row.add_widget(lbl_msg)
        container.add_widget(row)
        container.height = dp(60)
        container.opacity = 1

    def _hide_result(self):
        self.ids.result_card.clear_widgets()
        self.ids.result_card.height = 0
        self.ids.result_card.opacity = 0

    def _hide_progress(self):
        self.ids.progress_bar.opacity = 0
        self.ids.progress_bar.value = 0

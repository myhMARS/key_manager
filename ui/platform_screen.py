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
from theme import PLATFORM_COLORS
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
        self.ids.search_input.text = ""
        self.refresh_keys()
        # Start background validation of all keys
        Clock.schedule_once(lambda dt: self._validate_all_keys(), 0.3)

    def go_back(self):
        self._cancel_check()
        # Cancel background validation
        self._validation_generation = getattr(self, '_validation_generation', 0) + 1
        self.manager.current = 'home'

    def confirm_delete_platform(self):
        """Show confirmation if keys exist, otherwise dispatch delete directly."""
        from ui.popups import ConfirmDeletePlatformPopup

        key_count = storage.key_count(self.platform_id)
        if key_count > 0:
            popup = ConfirmDeletePlatformPopup(
                self.platform_id, self._plat.name, key_count)
            popup.open()
        else:
            from events import bus
            bus.dispatch('on_platform_deleted', self.platform_id)

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

    def refresh_keys(self, search_text=""):
        keys = storage.get_keys(self.platform_id)
        container = self.ids.key_list_container
        container.clear_widgets()

        # Filter by search text (match key name, case-insensitive)
        query = search_text.strip().lower()
        filtered = []
        for i, k in enumerate(keys):
            if query and query not in k["name"].lower():
                continue
            filtered.append((i, k))

        for i, k in filtered:
            if k.get("decrypt_ok", True):
                masked = (
                    k["key"][:6] + "****" + k["key"][-4:]
                    if len(k["key"]) > 10 else "****"
                )
            else:
                masked = "[decrypt error]"

            item = KeyItem(
                key_name=k["name"],
                masked_key=masked,
                created_at=k["created_at"],
                raw_key=k["key"],
                key_index=i,
                platform_id=self.platform_id,
                has_balance=bool(self._plat.balance_url if self._plat else False),
                decrypt_ok=k.get("decrypt_ok", True),
            )
            container.add_widget(item)

        if not filtered:
            container.add_widget(EmptyKeyState())

    def on_search_text(self, text):
        """Debounced search within platform keys."""
        if hasattr(self, '_search_event') and self._search_event:
            self._search_event.cancel()
        self._search_event = Clock.schedule_once(
            lambda dt: self.refresh_keys(search_text=text), 0.2)

    def _validate_all_keys(self):
        """Background-validate all keys for the current platform."""
        if not self._plat:
            return
        if not self._plat.verify_url and not self._plat.balance_url:
            return

        plat = self._plat
        platform_id = self.platform_id
        self._validation_generation = getattr(self, '_validation_generation', 0) + 1
        generation = self._validation_generation

        # Get all key items from the container
        container = self.ids.key_list_container
        items = [w for w in container.children[::-1] if isinstance(w, KeyItem)]

        # Mark all as checking
        for item in items:
            if item.decrypt_ok:
                item.key_status = "checking"

        def _validate_single(item):
            if not item.decrypt_ok or not item.raw_key:
                return
            try:
                headers = {"Authorization": plat.auth_header.format(api_key=item.raw_key)}
                with httpx.Client(timeout=8) as client:
                    if plat.balance_url:
                        url = plat.base_url + plat.balance_url
                        resp = client.get(url, headers=headers)
                        valid = resp.status_code == 200
                    elif plat.verify_url:
                        url = plat.base_url + plat.verify_url
                        resp = client.get(url, headers=headers)
                        valid = resp.status_code == 200
                    else:
                        return

                def _update(dt, v=valid, it=item):
                    if self._validation_generation != generation:
                        return
                    if self.platform_id != platform_id:
                        return
                    it.key_status = "valid" if v else "invalid"

                Clock.schedule_once(_update, 0)

            except Exception:
                def _mark_error(dt, it=item):
                    if self._validation_generation != generation:
                        return
                    it.key_status = "invalid"
                Clock.schedule_once(_mark_error, 0)

        def _run_all():
            for item in items:
                if self._validation_generation != generation:
                    break
                _validate_single(item)

        threading.Thread(target=_run_all, daemon=True).start()

    def show_add_dialog(self):
        popup = AddKeyPopup(self._plat, self.accent_color)
        popup.open()

    def trigger_check(self, api_key):
        """Verify a single key and update its KeyItem status indicator."""
        self._cancel_check()

        plat = self._plat
        if not plat:
            return
        if not plat.verify_url and not plat.balance_url:
            App.get_running_app().show_snackbar("No verify URL configured", "warning")
            return

        self._check_generation = getattr(self, '_check_generation', 0) + 1
        generation = self._check_generation

        # Find the KeyItem with this raw_key
        target_item = None
        container = self.ids.key_list_container
        for w in container.children:
            if isinstance(w, KeyItem) and w.raw_key == api_key:
                target_item = w
                break

        if target_item:
            target_item.key_status = "checking"

        client = httpx.Client(timeout=10)
        self._active_client = client

        def _run():
            valid = False
            try:
                headers = {"Authorization": plat.auth_header.format(api_key=api_key)}
                if plat.balance_url:
                    url = plat.base_url + plat.balance_url
                    resp = client.get(url, headers=headers)
                    valid = resp.status_code == 200
                elif plat.verify_url:
                    url = plat.base_url + plat.verify_url
                    resp = client.get(url, headers=headers)
                    valid = resp.status_code == 200

                def _update(dt, v=valid):
                    if self._check_generation != generation:
                        return
                    if target_item:
                        target_item.key_status = "valid" if v else "invalid"
                    app = App.get_running_app()
                    if v:
                        app.show_snackbar("Key is valid", "success")
                    else:
                        app.show_snackbar("Key is invalid", "error")

                Clock.schedule_once(_update, 0)

            except httpx.CloseError:
                pass
            except Exception:
                def _mark_error(dt):
                    if self._check_generation != generation:
                        return
                    if target_item:
                        target_item.key_status = "invalid"
                    App.get_running_app().show_snackbar("Verification failed", "error")
                Clock.schedule_once(_mark_error, 0)
            finally:
                client.close()
                if self._active_client is client:
                    self._active_client = None

        threading.Thread(target=_run, daemon=True).start()

    def _cancel_check(self):
        """Close the active HTTP client to abort any in-flight request."""
        client = getattr(self, '_active_client', None)
        if client:
            try:
                client.close()
            except Exception:
                pass
            self._active_client = None
        self._check_generation = getattr(self, '_check_generation', 0) + 1

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
        entries = self._parse_balance_response(data)

        if not entries:
            lbl = Label(
                text="Balance info not available", font_size="13sp",
                color=(0.5, 0.5, 0.5, 1), size_hint_y=None, height=dp(24),
                halign='center', valign='middle',
            )
            lbl.bind(size=lambda w, s: setattr(w, 'text_size', s))
            container.add_widget(lbl)
            rows += 1
        else:
            for label_text, value in entries:
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

    def _parse_balance_response(self, data: dict) -> list:
        """Parse balance API response into [(label, value), ...] pairs.
        Handles DeepSeek format and generic JSON responses."""

        # DeepSeek format: {"is_available": true, "balance_infos": [...]}
        if "balance_infos" in data:
            if not data.get("is_available"):
                return []
            entries = []
            for info in data["balance_infos"]:
                for k, v in info.items():
                    label = k.replace("_", " ").title()
                    entries.append((label, str(v)))
            return entries

        # Generic: try to extract numeric/string values from top-level or nested
        entries = []
        for k, v in data.items():
            if isinstance(v, (int, float, str)):
                label = k.replace("_", " ").title()
                entries.append((label, str(v)))
            elif isinstance(v, dict):
                # One level of nesting
                for sub_k, sub_v in v.items():
                    if isinstance(sub_v, (int, float, str)):
                        label = sub_k.replace("_", " ").title()
                        entries.append((label, str(sub_v)))
            elif isinstance(v, list) and v and isinstance(v[0], dict):
                # Array of objects (like DeepSeek)
                for item in v:
                    for sub_k, sub_v in item.items():
                        if isinstance(sub_v, (int, float, str)):
                            label = sub_k.replace("_", " ").title()
                            entries.append((label, str(sub_v)))

        return entries

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

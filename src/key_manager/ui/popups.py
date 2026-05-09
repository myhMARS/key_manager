"""Popup dialogs: AddKeyPopup, RenameKeyPopup, AddPlatform, EditPlatform, ConfirmDelete."""

from kivy.app import App
from kivy.clock import Clock
from kivy.properties import ListProperty, NumericProperty, StringProperty
from kivy.uix.popup import Popup

from ..core import storage
from ..core.events import bus


class RenameKeyPopup(Popup):
    platform_id = StringProperty("")
    key_index = NumericProperty(0)
    current_name = StringProperty("")
    accent_color = ListProperty([0.42, 0.42, 0.42, 1])

    def __init__(self, platform_id, key_index, current_name, accent_color, **kwargs):
        super().__init__(**kwargs)
        self.platform_id = platform_id
        self.key_index = key_index
        self.current_name = current_name
        self.accent_color = accent_color
        Clock.schedule_once(lambda dt: self._init_input(), 0)

    def _init_input(self):
        self.ids.rename_input.text = self.current_name

    def on_save(self):
        new_name = self.ids.rename_input.text.strip()
        if not new_name:
            self.ids.rename_error.text = "Name cannot be empty"
            return
        storage.rename_key(self.platform_id, self.key_index, new_name)
        self.dismiss()
        bus.dispatch('on_key_renamed', self.platform_id)
        App.get_running_app().show_snackbar("Key renamed", "success")


class AddKeyPopup(Popup):
    platform_name = StringProperty("")
    platform_id = StringProperty("")
    accent_color = ListProperty([0.42, 0.42, 0.42, 1])

    def __init__(self, platform, accent, **kwargs):
        super().__init__(**kwargs)
        self.platform_name = platform.name
        self.platform_id = platform.id
        self.accent_color = accent

    def on_save(self):
        if getattr(self, '_saving', False):
            return
        self._saving = True

        name = self.ids.name_input.text.strip()
        key = self.ids.key_input.text.strip()
        error_label = self.ids.error_label

        if not name:
            error_label.text = "Key name is required"
            self._saving = False
            return
        if not key:
            error_label.text = "API key is required"
            self._saving = False
            return

        storage.add_key(self.platform_id, name, key)
        self.dismiss()

        bus.dispatch('on_key_added', self.platform_id)
        App.get_running_app().show_snackbar("Key added", "success")


class AddPlatformPopup(Popup):
    accent_color = ListProperty([0.4, 0.4, 0.4, 1])

    def on_save(self):
        name = self.ids.platform_name_input.text.strip()
        base_url = self.ids.base_url_input.text.strip()
        verify_url = self.ids.verify_url_input.text.strip()
        balance_url = self.ids.balance_url_input.text.strip()
        error_label = self.ids.platform_error_label

        if not name:
            error_label.text = "Platform name is required"
            return

        pid = storage.add_custom_platform(
            name=name,
            base_url=base_url,
            verify_url=verify_url,
            balance_url=balance_url,
        )
        self.dismiss()

        bus.dispatch('on_platform_added', pid)
        App.get_running_app().show_snackbar(f"{name} added", "success")


class ConfirmDeletePlatformPopup(Popup):
    platform_id = StringProperty("")
    platform_name = StringProperty("")
    key_count_text = StringProperty("")

    def __init__(self, platform_id, platform_name, key_count, **kwargs):
        super().__init__(**kwargs)
        self.platform_id = platform_id
        self.platform_name = platform_name
        self.key_count_text = f"This platform has {key_count} key{'s' if key_count != 1 else ''}. They will be permanently deleted."

    def on_confirm(self):
        self.dismiss()
        bus.dispatch('on_platform_deleted', self.platform_id)


class EditPlatformPopup(Popup):
    platform_id = StringProperty("")
    platform_name = StringProperty("")
    base_url = StringProperty("")
    verify_url = StringProperty("")
    balance_url = StringProperty("")
    accent_color = ListProperty([0.4, 0.4, 0.4, 1])

    def __init__(self, platform_id, name, base_url, verify_url, balance_url, accent_color, **kwargs):
        super().__init__(**kwargs)
        self.platform_id = platform_id
        self.platform_name = name
        self.base_url = base_url
        self.verify_url = verify_url
        self.balance_url = balance_url
        self.accent_color = accent_color
        Clock.schedule_once(lambda dt: self._init_inputs(), 0)

    def _init_inputs(self):
        self.ids.edit_name_input.text = self.platform_name
        self.ids.edit_base_url_input.text = self.base_url
        self.ids.edit_verify_url_input.text = self.verify_url
        self.ids.edit_balance_url_input.text = self.balance_url

    def on_save(self):
        name = self.ids.edit_name_input.text.strip()
        base_url = self.ids.edit_base_url_input.text.strip()
        verify_url = self.ids.edit_verify_url_input.text.strip()
        balance_url = self.ids.edit_balance_url_input.text.strip()
        error_label = self.ids.edit_error_label

        if not name:
            error_label.text = "Platform name is required"
            return

        storage.update_custom_platform(
            self.platform_id,
            name=name,
            base_url=base_url,
            verify_url=verify_url,
            balance_url=balance_url,
        )
        self.dismiss()

        bus.dispatch('on_platform_updated', self.platform_id)
        App.get_running_app().show_snackbar("Platform updated", "success")

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
        new_index = storage.key_count(self.platform_id) - 1
        self.dismiss()

        bus.dispatch('on_key_added', self.platform_id, key_name=name, new_key_index=new_index)
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


# ----------------------------------------------------------
#  Import / Export popups
# ----------------------------------------------------------

def _is_android():
    try:
        from android import mActivity
        return True
    except Exception:
        return False


def _get_export_dir():
    import os
    if _is_android():
        try:
            from androidstorage4kivy import SharedStorage
            return SharedStorage().get_cache_dir() or os.path.expanduser('~')
        except Exception:
            return os.path.expanduser('~')
    return os.path.expanduser('~')


class ConfirmExportPopup(Popup):
    """Confirmation dialog before exporting keys."""

    def on_export(self):
        import os
        import threading
        from datetime import datetime

        export_dir = _get_export_dir()
        filename = f"key_manager_backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        filepath = os.path.join(export_dir, filename)

        # Show progress, hide content
        content = self.ids.confirm_content
        progress = self.ids.progress_section
        content.opacity = 0
        content.disabled = True
        content.size_hint_y = None
        content.height = 0
        progress.opacity = 1
        progress.size_hint_y = 1

        bar = self.ids.export_progress
        label = self.ids.progress_label

        def _on_progress(current, total):
            def _update(dt, c=current, t=total):
                bar.value = int(c / t * 100) if t else 100
                label.text = f'{c} / {t} keys'
            Clock.schedule_once(_update, 0)

        def _run():
            try:
                storage.export_config(filepath, on_progress=_on_progress)

                result_path = filepath
                if _is_android():
                    try:
                        from androidstorage4kivy import SharedStorage
                        from jnius import autoclass
                        Environment = autoclass('android.os.Environment')
                        ss = SharedStorage()
                        uri = ss.copy_to_shared(
                            filepath,
                            collection=Environment.DIRECTORY_DOWNLOADS,
                        )
                        if uri:
                            import os as _os
                            downloads_dir = Environment.getExternalStoragePublicDirectory(
                                Environment.DIRECTORY_DOWNLOADS).getAbsolutePath()
                            result_path = _os.path.join(
                                downloads_dir, ss.get_app_title(), filename)
                    except Exception:
                        pass

                def _done(dt, fp=result_path):
                    bar.value = 100
                    label.text = 'Done'
                    self.dismiss()
                    ExportResultPopup(filepath=fp).open()

                Clock.schedule_once(_done, 0)
            except Exception as e:
                def _fail(dt, err=str(e)):
                    self.dismiss()
                    App.get_running_app().show_snackbar(
                        f"Export failed: {err}", "error")

                Clock.schedule_once(_fail, 0)

        threading.Thread(target=_run, daemon=True).start()


class ExportResultPopup(Popup):
    """Dialog showing the exported file path."""
    filepath = StringProperty("")

    def __init__(self, filepath, **kwargs):
        super().__init__(**kwargs)
        self.filepath = filepath

    def on_copy(self):
        from kivy.core.clipboard import Clipboard
        Clipboard.copy(self.filepath)
        App.get_running_app().show_snackbar("Path copied", "success")


class ImportPopup(Popup):
    """Import dialog with merge/replace mode selection and file chooser."""
    error_text = StringProperty("")

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self._mode = 'merge'
        self._filepath = None
        Clock.schedule_once(lambda dt: self._set_mode_visual(), 0)

    def _set_mode_visual(self):
        """Update button colors to show active mode."""
        merge_btn = self.ids.merge_btn
        replace_btn = self.ids.replace_btn
        if self._mode == 'merge':
            merge_btn.canvas.before.clear()
            replace_btn.canvas.before.clear()
            self._draw_btn_bg(merge_btn, (0.2, 0.6, 0.9, 1))
            self._draw_btn_bg(replace_btn, (0.94, 0.94, 0.94, 1))
            merge_btn.color = (1, 1, 1, 1)
            replace_btn.color = (0.3, 0.3, 0.3, 1)
        else:
            merge_btn.canvas.before.clear()
            replace_btn.canvas.before.clear()
            self._draw_btn_bg(replace_btn, (0.9, 0.2, 0.2, 1))
            self._draw_btn_bg(merge_btn, (0.94, 0.94, 0.94, 1))
            replace_btn.color = (1, 1, 1, 1)
            merge_btn.color = (0.3, 0.3, 0.3, 1)

    @staticmethod
    def _draw_btn_bg(btn, color):
        """Draw a rounded rectangle background on a button."""
        from kivy.graphics import Color, RoundedRectangle
        from kivy.metrics import dp
        with btn.canvas.before:
            Color(*color)
            rr = RoundedRectangle(pos=btn.pos, size=btn.size, radius=[dp(8)])
        btn.bind(pos=lambda inst, val, r=rr: setattr(r, 'pos', val))
        btn.bind(size=lambda inst, val, r=rr: setattr(r, 'size', val))

    def on_merge(self):
        self._mode = 'merge'
        self._set_mode_visual()

    def on_replace(self):
        self._mode = 'replace'
        self._set_mode_visual()

    def on_choose_file(self):
        """Open system native file picker."""
        if self._try_android_chooser():
            return
        if self._try_tkinter_picker():
            return
        # Last resort: Kivy FileChooser
        popup = FileChooserPopup(
            on_select=lambda filepath: self._on_file_selected(filepath))
        popup.open()

    def _try_tkinter_picker(self):
        """Use tkinter native file dialog on desktop. Returns True on success."""
        try:
            import tkinter.filedialog as fd
            import tkinter

            root = tkinter.Tk()
            root.withdraw()
            root.attributes('-topmost', True)

            filepath = fd.askopenfilename(
                title='Select backup file',
                filetypes=[('JSON files', '*.json')],
            )
            root.destroy()

            if filepath:
                self._on_file_selected(filepath)
                return True
            return False
        except Exception:
            return False

    def _try_android_chooser(self):
        """Use androidstorage4kivy Chooser for native file picker. Returns True if launched."""
        try:
            from androidstorage4kivy import Chooser, SharedStorage

            def on_uris(uri_list):
                if not uri_list:
                    return
                uri = uri_list[0]
                # Validate .json extension from display name
                try:
                    from jnius import autoclass
                    from android import mActivity
                    cursor = mActivity.getContentResolver().query(uri, None, None, None, None)
                    if cursor:
                        cursor.moveToFirst()
                        name_col = cursor.getColumnIndex(
                            autoclass('android.provider.OpenableColumns').DISPLAY_NAME)
                        if name_col >= 0:
                            name = cursor.getString(name_col)
                            if name and not name.lower().endswith('.json'):
                                cursor.close()
                                Clock.schedule_once(
                                    lambda dt: App.get_running_app().show_snackbar(
                                        "Please select a .json file", "warning"), 0)
                                return
                        cursor.close()
                except Exception:
                    pass

                # Copy URI to local cache
                cache_path = SharedStorage().copy_from_shared(uri)
                if cache_path:
                    Clock.schedule_once(
                        lambda dt: self._on_file_selected(cache_path), 0)

            Chooser(callback=on_uris).choose_content("application/json")
            return True
        except Exception:
            return False

    def _on_file_selected(self, filepath):
        """Called after file is selected via file picker."""
        self._filepath = filepath
        self.ids.file_path_input.text = filepath or ""

    def on_import(self):
        """Execute import from the selected file in a background thread."""
        import os
        import threading
        from kivy.metrics import dp

        filepath = self._filepath or self.ids.file_path_input.text.strip()

        if not filepath:
            self.error_text = "Please select a file first"
            return

        if not filepath.endswith('.json'):
            self.error_text = "Please select a .json file"
            return

        if not os.path.exists(filepath):
            self.error_text = "File not found"
            return

        # Show progress, hide content
        self.ids.import_content.opacity = 0
        self.ids.import_content.height = 0
        self.ids.import_progress_section.opacity = 1
        self.ids.import_progress_section.height = dp(32)

        bar = self.ids.import_progress
        label = self.ids.import_progress_label
        mode = self._mode

        def _on_progress(current, total, status):
            def _update(dt, c=current, t=total, s=status):
                bar.value = int(c / t * 100) if t else 100
                label.text = f'{c} / {t} keys  ({s})'
            Clock.schedule_once(_update, 0)

        def _run():
            try:
                result = storage.import_config(
                    filepath, mode, on_progress=_on_progress)

                def _done(dt, r=result):
                    bar.value = 100
                    label.text = 'Done'
                    self.dismiss()
                    msg = f"Imported {r['keys_count']} keys across {r['platforms_count']} platforms"
                    if r.get('skipped_count'):
                        msg += f", skipped {r['skipped_count']} duplicates"
                    App.get_running_app().show_snackbar(msg, "success")
                    bus.dispatch('on_platform_added', '__import__')

                Clock.schedule_once(_done, 0)
            except ValueError as e:
                def _fail(dt, err=str(e)):
                    self.dismiss()
                    App.get_running_app().show_snackbar(str(err), "error")
                Clock.schedule_once(_fail, 0)
            except Exception as e:
                def _fail(dt, err=str(e)):
                    self.dismiss()
                    App.get_running_app().show_snackbar(
                        f"Import failed: {err}", "error")
                Clock.schedule_once(_fail, 0)

        threading.Thread(target=_run, daemon=True).start()


class FileChooserPopup(Popup):
    """Desktop file chooser using Kivy's built-in FileChooserListView."""
    file_selected = StringProperty("")

    def __init__(self, on_select, **kwargs):
        super().__init__(**kwargs)
        self._on_select_callback = on_select
        import os
        self._start_dir = os.path.expanduser("~")
        Clock.schedule_once(lambda dt: self._init_chooser(), 0)

    def _init_chooser(self):
        from kivy.uix.filechooser import FileChooserListView

        chooser = FileChooserListView(
            path=self._start_dir,
            filters=["*.json"],
            size_hint=(1, 1),
        )
        chooser.bind(
            on_submit=lambda instance, selection, *a:
                self._select(selection and selection[0] or ""))
        self.ids.chooser_box.add_widget(chooser)

    def on_choose(self):
        """Select the currently highlighted file."""
        chooser = self.ids.chooser_box.children[0] if self.ids.chooser_box.children else None
        if chooser and chooser.selection:
            self._select(chooser.selection[0])

    def _select(self, filepath):
        if filepath:
            self._on_select_callback(filepath)
        self.dismiss()

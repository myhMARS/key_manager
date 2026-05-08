"""Application event bus for decoupled communication between modules."""

from kivy.event import EventDispatcher


class AppEvents(EventDispatcher):
    """Central event bus. UI components dispatch events here,
    screens/controllers listen and react."""

    def __init__(self, **kwargs):
        self.register_event_type('on_key_added')
        self.register_event_type('on_key_deleted')
        self.register_event_type('on_key_renamed')
        self.register_event_type('on_platform_added')
        self.register_event_type('on_platform_deleted')
        self.register_event_type('on_platform_updated')
        self.register_event_type('on_navigate')
        super().__init__(**kwargs)

    def on_key_added(self, platform_id):
        pass

    def on_key_deleted(self, platform_id, **kwargs):
        pass

    def on_key_renamed(self, platform_id):
        pass

    def on_platform_added(self, platform_id):
        pass

    def on_platform_deleted(self, platform_id):
        pass

    def on_platform_updated(self, platform_id):
        pass

    def on_navigate(self, screen_name, **kwargs):
        pass


# Singleton instance
bus = AppEvents()

"""Home screen with stacked card deck and cut animation."""

from kivy.animation import Animation
from kivy.app import App
from kivy.clock import Clock
from kivy.metrics import dp
from kivy.properties import NumericProperty
from kivy.uix.screenmanager import Screen

import storage
import config
from config import PLATFORM_COLORS, DEFAULT_CUSTOM_COLOR, accent_bg, accent_icon_bg
from ui.widgets import Dot, TouchCard


class HomeScreen(Screen):
    current_index = NumericProperty(0)

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self._built = False
        self._animating = False
        self._cards = []
        self._key_count_cache = {}  # platform_id -> count

    def on_enter(self, *args):
        # Refresh key count cache on every entry
        self._refresh_key_counts()

        if not self._built:
            Clock.schedule_once(lambda dt: self._build(), 0)
            self._built = True
        else:
            old_total = config.TOTAL
            config.refresh_platforms()
            if config.TOTAL != old_total or config.TOTAL != len(self._cards):
                self.rebuild_deck()
            else:
                self._update_all_cards()
                self._update_dots()

    def _refresh_key_counts(self):
        """Cache key counts for all platforms to avoid repeated file reads."""
        self._key_count_cache = {}
        for plat in config.PLATFORM_LIST:
            self._key_count_cache[plat.id] = storage.key_count(plat.id)

    def _build(self):
        # Ensure custom platforms are loaded
        config.refresh_platforms()

        card_area = self.ids.card_area

        # Show all platforms as stacked cards (not limited to 3)
        self._cards = []
        for i in range(config.TOTAL):
            card = TouchCard(size_hint=(None, None), opacity=1)
            card.bind(on_swipe_left=lambda _: self._go_next())
            card.bind(on_swipe_right=lambda _: self._go_prev())
            card.bind(on_snap_back=lambda _: self._snap_back())

            def on_tap(_, relative_x, c=card):
                if c != self._cards[-1]:
                    return
                w = c.width
                if w <= 0:
                    return
                if relative_x < w * 0.25:
                    self._go_prev()
                elif relative_x > w * 0.75:
                    self._go_next()
                else:
                    plat = config.PLATFORM_LIST[self.current_index]
                    app = App.get_running_app()
                    app.sm.get_screen('platform').load_platform(plat.id)
                    app.sm.current = 'platform'

            card.bind(on_tap_card=on_tap)
            self._cards.append(card)
            card_area.add_widget(card)

        # Build dots
        self._rebuild_dots()

        Clock.schedule_once(lambda dt: self._layout_deck(), 0)
        card_area.bind(size=lambda *a: self._layout_deck())
        card_area.bind(pos=lambda *a: self._layout_deck())

    def rebuild_deck(self):
        """Rebuild the entire deck after platforms change."""
        config.refresh_platforms()
        self._refresh_key_counts()

        # Clamp current_index to new platform at the end
        if config.TOTAL > 0:
            self.current_index = config.TOTAL - 1
        else:
            self.current_index = 0

        # Remove old cards
        card_area = self.ids.card_area
        for card in self._cards:
            card_area.remove_widget(card)
        self._cards.clear()

        # Recreate all cards
        for i in range(config.TOTAL):
            card = TouchCard(size_hint=(None, None), opacity=1)
            card.bind(on_swipe_left=lambda _: self._go_next())
            card.bind(on_swipe_right=lambda _: self._go_prev())
            card.bind(on_snap_back=lambda _: self._snap_back())

            def on_tap(_, relative_x, c=card):
                if c != self._cards[-1]:
                    return
                w = c.width
                if w <= 0:
                    return
                if relative_x < w * 0.25:
                    self._go_prev()
                elif relative_x > w * 0.75:
                    self._go_next()
                else:
                    plat = config.PLATFORM_LIST[self.current_index]
                    app = App.get_running_app()
                    app.sm.get_screen('platform').load_platform(plat.id)
                    app.sm.current = 'platform'

            card.bind(on_tap_card=on_tap)
            self._cards.append(card)
            card_area.add_widget(card)

        self._rebuild_dots()
        self._layout_deck()

    def _rebuild_dots(self):
        dots = self.ids.dots_container
        dots.clear_widgets()
        for i in range(config.TOTAL):
            dot = Dot()
            dot.dot_color = (
                [0.27, 0.27, 0.27, 1] if i == self.current_index
                else [0.7, 0.7, 0.7, 1]
            )
            dot.size = (dp(20) if i == self.current_index else dp(8), dp(6))
            dots.add_widget(dot)

    # ----------------------------------------------------------
    #  Deck layout
    # ----------------------------------------------------------

    def _layout_deck(self):
        """Position cards in a stacked deck with right-edge peek."""
        if self._animating:
            return
        area = self.ids.card_area
        area_w = area.width
        area_h = area.height

        if area_w <= 0 or area_h <= 0:
            return

        num_cards = len(self._cards)
        for i, card in enumerate(self._cards):
            depth = num_cards - 1 - i
            x, y, w, h, opacity = self._get_deck_pos(depth, area_w, area_h)
            card.size = (w, h)
            card.pos = (x, y)
            card.opacity = opacity

        self._update_all_cards()

    def _get_deck_pos(self, depth, area_w, area_h):
        """Calculate position/size for a card at given depth.
        Peek offset shrinks as more cards are added to fit them all."""
        card_w = area_w * 0.88
        card_h = area_h * 0.90

        total = config.TOTAL
        # Dynamic peek: shrink as card count grows, min dp(4) per layer
        if total <= 3:
            peek_offset = dp(12)
        elif total <= 6:
            peek_offset = dp(8)
        else:
            peek_offset = dp(5)

        offset_x = depth * peek_offset
        offset_y = -depth * dp(4)

        x = (area_w - card_w) / 2 + offset_x
        y = (area_h - card_h) / 2 + offset_y

        # Fade out deeper cards more aggressively with many cards
        max_opacity_loss = 0.7
        if total > 1:
            opacity = 1.0 - (depth / (total - 1)) * max_opacity_loss
        else:
            opacity = 1.0
        opacity = max(opacity, 0.15)

        return x, y, card_w, card_h, opacity

    # ----------------------------------------------------------
    #  Card content
    # ----------------------------------------------------------

    def _update_all_cards(self):
        """Top card = current_index, below = next platforms."""
        total = config.TOTAL
        num_cards = len(self._cards)
        for i, card in enumerate(self._cards):
            depth = num_cards - 1 - i
            idx = (self.current_index + depth) % total
            self._set_card_content(card, idx)

    def _refresh_top_card(self):
        if self._cards:
            self._set_card_content(self._cards[-1], self.current_index)

    def _set_card_content(self, card, idx):
        plat = config.PLATFORM_LIST[idx]
        accent = PLATFORM_COLORS.get(plat.id, DEFAULT_CUSTOM_COLOR)
        count = self._key_count_cache.get(plat.id, 0)

        card.platform_name = plat.name
        card.key_count_text = f"{count} key{'s' if count != 1 else ''}"
        card.accent_color = accent
        card.accent_bg_color = accent_bg(accent)
        card.icon_bg_color = accent_icon_bg(accent)
        card.platform_id = plat.id
        card.has_balance = bool(plat.balance_url)
        card.feature_text = (
            "Balance check" if plat.balance_url
            else "Key verification" if plat.verify_url
            else "Key management"
        )
        if plat.icon_path:
            card.icon_source = plat.icon_path
            card.icon_text = ""
        else:
            card.icon_source = ""
            card.icon_text = plat.icon

    # ----------------------------------------------------------
    #  Dots
    # ----------------------------------------------------------

    def _update_dots(self):
        idx = self.current_index
        dots = self.ids.dots_container
        for i, dot in enumerate(dots.children[::-1]):
            if i == idx:
                dot.dot_color = [0.27, 0.27, 0.27, 1]
                dot.width = dp(20)
            else:
                dot.dot_color = [0.7, 0.7, 0.7, 1]
                dot.width = dp(8)

    # ----------------------------------------------------------
    #  Add platform
    # ----------------------------------------------------------

    def show_add_platform(self):
        from ui.popups import AddPlatformPopup
        popup = AddPlatformPopup()
        popup.open()

    # ----------------------------------------------------------
    #  Snap back (drag cancelled)
    # ----------------------------------------------------------

    def _snap_back(self):
        """Animate top card back to its deck position."""
        if not self._cards:
            return
        top_card = self._cards[-1]
        area = self.ids.card_area
        x, y, w, h, opacity = self._get_deck_pos(0, area.width, area.height)
        anim = Animation(x=x, y=y, opacity=opacity, duration=0.2, t='out_cubic')
        anim.start(top_card)

    # ----------------------------------------------------------
    #  Navigation
    # ----------------------------------------------------------

    def _go_to(self, idx):
        if idx == self.current_index:
            return
        if idx > self.current_index:
            self._animate_next(idx)
        else:
            self._animate_prev(idx)

    def _go_prev(self):
        new_idx = (self.current_index - 1) % config.TOTAL
        self._animate_prev(new_idx)

    def _go_next(self):
        new_idx = (self.current_index + 1) % config.TOTAL
        self._animate_next(new_idx)

    # ----------------------------------------------------------
    #  Cut animation: next (top card slides out left, goes to bottom)
    # ----------------------------------------------------------

    def _animate_next(self, new_idx):
        """Next card: top card slides out to the left and tucks under."""
        if self._animating:
            return
        self._animating = True

        top_card = self._cards[-1]
        area = self.ids.card_area
        area_w = area.width
        total = config.TOTAL

        # Pre-set bottom cards to show correct content during animation
        num_cards = len(self._cards)
        for i, card in enumerate(self._cards[:-1]):
            future_depth = num_cards - 2 - i
            idx = (new_idx + future_depth) % total
            self._set_card_content(card, idx)

        # Phase 1: Top card slides out to the left
        target_x = top_card.x - area_w * 0.8

        anim_out = Animation(
            x=target_x, opacity=0.3,
            duration=0.2, t='out_quad',
        )

        def on_slide_out(*args):
            card_area = self.ids.card_area
            card_area.remove_widget(top_card)
            card_area.add_widget(top_card, index=len(self._cards) - 1)

            self._cards.remove(top_card)
            self._cards.insert(0, top_card)

            self.current_index = new_idx
            self._update_all_cards()
            self._update_dots()

            # Phase 2: All cards settle into new positions
            cur_w = area.width
            cur_h = area.height
            n = len(self._cards)

            anims = []
            for i, card in enumerate(self._cards):
                depth = n - 1 - i
                x, y, w, h, opacity = self._get_deck_pos(depth, cur_w, cur_h)
                anim = Animation(
                    x=x, y=y, width=w, height=h, opacity=opacity,
                    duration=0.28, t='out_cubic',
                )
                anims.append((card, anim))

            for card, anim in anims:
                anim.start(card)

            if anims:
                anims[-1][1].bind(
                    on_complete=lambda *a: setattr(self, '_animating', False))
            else:
                self._animating = False

        anim_out.bind(on_complete=on_slide_out)
        anim_out.start(top_card)

    # ----------------------------------------------------------
    #  Cut animation: prev (bottom card slides in from left to top)
    # ----------------------------------------------------------

    def _animate_prev(self, new_idx):
        """Prev card: bottom card rises from the left side to become top."""
        if self._animating:
            return
        self._animating = True

        area = self.ids.card_area
        area_w = area.width
        area_h = area.height

        # Take the bottom card and prepare it as the new top
        bottom_card = self._cards[0]

        # Set its content to the new (previous) platform
        self._set_card_content(bottom_card, new_idx)

        # Move it to widget front (on top visually)
        card_area = self.ids.card_area
        card_area.remove_widget(bottom_card)
        card_area.add_widget(bottom_card)

        # Reorder internal list: bottom goes to top
        self._cards.remove(bottom_card)
        self._cards.append(bottom_card)

        # Position it off-screen to the left
        top_x, top_y, top_w, top_h, _ = self._get_deck_pos(0, area_w, area_h)
        bottom_card.size = (top_w, top_h)
        bottom_card.x = -top_w
        bottom_card.y = top_y
        bottom_card.opacity = 0.5

        # Update index and other cards
        self.current_index = new_idx
        self._update_all_cards()
        self._update_dots()

        # Animate all cards to their new positions
        n = len(self._cards)
        anims = []
        for i, card in enumerate(self._cards):
            depth = n - 1 - i
            x, y, w, h, opacity = self._get_deck_pos(depth, area_w, area_h)
            anim = Animation(
                x=x, y=y, width=w, height=h, opacity=opacity,
                duration=0.28, t='out_cubic',
            )
            anims.append((card, anim))

        for card, anim in anims:
            anim.start(card)

        if anims:
            anims[-1][1].bind(
                on_complete=lambda *a: setattr(self, '_animating', False))
        else:
            self._animating = False

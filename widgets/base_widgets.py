import os

from kivy.clock import Clock
from kivy.graphics import (Color, Ellipse, Line, Rectangle, RoundedRectangle,
                            StencilPush, StencilUse, StencilUnUse, StencilPop)
from kivy.metrics import dp, sp
from kivy.uix.behaviors import ButtonBehavior
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.button import Button
from kivy.uix.floatlayout import FloatLayout
from kivy.uix.image import Image
from kivy.uix.label import Label
from kivy.uix.widget import Widget

from config import (GREEN, IMAGE_DIR, LIKE_ICON_OFF, LIKE_ICON_ON,
                    HOME_TOOL_ICONS, COMMUNITY_FOCUS_ICONS)
from utils import text_style



class IconButton(ButtonBehavior, Label):
    pass


class UnderlineLabel(ButtonBehavior, Label):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.markup = True


class ClickableBox(ButtonBehavior, BoxLayout):
    pass


class RoundedButton(Button):
    def __init__(self, radius=18, fill_color=GREEN, **kwargs):
        self.radius = radius
        self.fill_color = fill_color
        super().__init__(
            background_normal="", background_down="",
            background_color=(0, 0, 0, 0), border=(0, 0, 0, 0),
            **kwargs,
        )
        self.bind(pos=self._update_canvas, size=self._update_canvas)
        Clock.schedule_once(lambda dt: self._update_canvas(), 0)

    def _update_canvas(self, *_args):
        self.canvas.before.clear()
        with self.canvas.before:
            Color(*self.fill_color)
            RoundedRectangle(pos=self.pos, size=self.size, radius=[self.radius] * 4)


class GrayPlaceholder(Widget):
    def __init__(self, radius=0, **kwargs):
        super().__init__(**kwargs)
        self.radius = radius
        self.bind(pos=self._update_canvas, size=self._update_canvas)

    def _update_canvas(self, *_args):
        self.canvas.before.clear()
        with self.canvas.before:
            Color(0.82, 0.82, 0.82, 1)
            if self.radius:
                Ellipse(pos=self.pos, size=self.size)
            else:
                Rectangle(pos=self.pos, size=self.size)


class CircleImage(Image):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.allow_stretch = True
        self.keep_ratio = False
        self.bind(pos=self._update_canvas, size=self._update_canvas)

    def _update_canvas(self, *_args):
        self.canvas.before.clear()
        self.canvas.after.clear()
        with self.canvas.before:
            StencilPush()
            Ellipse(pos=self.pos, size=self.size)
            StencilUse()
        with self.canvas.after:
            StencilUnUse()
            StencilPop()


class LikeImageButton(ButtonBehavior, Image):
    def __init__(self, source_off="", source_on="", liked=False, **kwargs):
        for k in ("text", "background_normal", "background_down", "background_color",
                  "color", "halign", "valign", "font_size", "border"):
            kwargs.pop(k, None)
        self.source_off = source_off or LIKE_ICON_OFF
        self.source_on = source_on or LIKE_ICON_ON
        super().__init__(**kwargs)
        self.allow_stretch = True
        self.keep_ratio = True
        if not self.size_hint and not kwargs.get("size"):
            self.size = (dp(24), dp(24))
        self.set_liked(liked)

    def set_liked(self, liked):
        if liked and self.source_on and os.path.exists(self.source_on):
            self.source = self.source_on
        else:
            self.source = self.source_off


class IconStat(ButtonBehavior, BoxLayout):
    def __init__(self, icon_text="", icon_source="", title="", value="", **kwargs):
        super().__init__(orientation="vertical", spacing=dp(4), **kwargs)
        self.size_hint = (1, 1)
        if icon_source and os.path.exists(icon_source):
            icon_widget = Image(source=icon_source, size_hint=(1, None), height=dp(34),
                                allow_stretch=True, keep_ratio=True)
        else:
            icon_widget = Label(text=icon_text, font_size=sp(24), color=GREEN,
                                size_hint=(1, None), height=dp(28),
                                halign="center", valign="middle", **text_style())
            icon_widget.bind(size=icon_widget.setter("text_size"))
        self.add_widget(icon_widget)
        title_label = Label(text=title, font_size=sp(13), color=(0.2, 0.2, 0.2, 1),
                            size_hint=(1, None), height=dp(22),
                            halign="center", valign="middle", **text_style())
        title_label.bind(size=title_label.setter("text_size"))
        self.add_widget(title_label)
        value_label = Label(text=value, font_size=sp(12), color=(0.45, 0.45, 0.45, 1),
                            size_hint=(1, None), height=dp(20),
                            halign="center", valign="middle", **text_style())
        value_label.bind(size=value_label.setter("text_size"))
        self.add_widget(value_label)


class ToolCard(ButtonBehavior, BoxLayout):
    def __init__(self, icon_text="", icon_source="", title="", **kwargs):
        super().__init__(orientation="vertical", spacing=dp(8), padding=dp(10), **kwargs)
        self.size_hint = (1, 1)
        self.bind(pos=self._update_bg, size=self._update_bg)
        icon_source = icon_source or HOME_TOOL_ICONS.get(title, "") or COMMUNITY_FOCUS_ICONS.get(title, "")
        if icon_source and os.path.exists(icon_source):
            icon_widget = Image(source=icon_source, size_hint=(1, None), height=dp(36),
                                allow_stretch=True, keep_ratio=True)
        else:
            icon_widget = Label(text=icon_text, font_size=sp(26), color=GREEN,
                                size_hint=(1, None), height=dp(30),
                                halign="center", valign="middle", **text_style())
            icon_widget.bind(size=icon_widget.setter("text_size"))
        self.add_widget(icon_widget)
        title_label = Label(text=title, font_size=sp(13), color=(0.12, 0.12, 0.12, 1),
                            size_hint=(1, None), height=dp(24),
                            halign="center", valign="middle", **text_style())
        title_label.bind(size=title_label.setter("text_size"))
        self.add_widget(title_label)

    def _update_bg(self, *_args):
        self.canvas.before.clear()
        with self.canvas.before:
            Color(1, 1, 1, 1)
            RoundedRectangle(pos=self.pos, size=self.size, radius=[dp(14)] * 4)


class HomeStoreItem(ButtonBehavior, BoxLayout):
    def __init__(self, product, on_open=None, **kwargs):
        super().__init__(orientation="vertical", spacing=dp(6), size_hint=(None, 1),
                         width=dp(128), padding=(0, dp(8), 0, dp(8)), **kwargs)
        self.product = product
        self.on_open = on_open
        self.add_widget(GrayPlaceholder(size_hint=(1, None), height=dp(82)))
        name_label = Label(text=product["name"], font_size=sp(13), color=(0.12, 0.12, 0.12, 1),
                           size_hint=(1, None), height=dp(34),
                           halign="left", valign="top", **text_style())
        name_label.bind(size=name_label.setter("text_size"))
        self.add_widget(name_label)
        price_label = Label(text=f"￥{product['price']:.2f}", font_size=sp(13),
                            color=(0.88, 0.34, 0.18, 1), size_hint=(1, None), height=dp(20),
                            halign="left", valign="middle", **text_style())
        price_label.bind(size=price_label.setter("text_size"))
        self.add_widget(price_label)

    def on_release(self):
        if self.on_open:
            self.on_open(self.product["id"])


class PestListRow(ButtonBehavior, BoxLayout):
    def __init__(self, pest_data, on_open=None, **kwargs):
        super().__init__(
            orientation="horizontal", spacing=dp(16),
            padding=(dp(16), dp(12), dp(16), dp(12)),
            size_hint_y=None, height=dp(100), **kwargs,
        )
        self.pest_data = pest_data
        self.on_open = on_open
        self.bind(pos=self._update_bg, size=self._update_bg)

        # 左侧图片（圆角）
        img_wrap = BoxLayout(size_hint=(None, 1), width=dp(76))
        from config import IMAGE_DIR
        img_path = ""
        for fmt in [
            os.path.join(IMAGE_DIR, f"pest_{pest_data['name']}.png"),
            os.path.join(IMAGE_DIR, f"pest_{pest_data['name']}.jpg"),
            os.path.join(IMAGE_DIR, f"{pest_data['name']}.png"),
            os.path.join(IMAGE_DIR, f"{pest_data['name']}.jpg"),
        ]:
            if os.path.exists(fmt):
                img_path = fmt
                break

        if img_path:
            img = Image(
                source=img_path,
                size_hint=(1, 1),
                allow_stretch=True, keep_ratio=False,
            )
            img_wrap.add_widget(img)
        else:
            ph = Widget(size_hint=(1, 1))
            with ph.canvas.before:
                Color(0.78, 0.94, 0.78, 1)
                ph_rect = RoundedRectangle(
                    pos=ph.pos, size=ph.size, radius=[dp(10)] * 4)
            ph.bind(
                pos=lambda i, r=ph_rect, *_: setattr(r, "pos", i.pos),
                size=lambda i, r=ph_rect, *_: setattr(r, "size", i.size),
            )
            first = Label(
                text=pest_data["name"][0],
                font_size=sp(26), bold=True, color=GREEN,
                size_hint=(1, 1),
                halign="center", valign="middle", **text_style(),
            )
            first.bind(size=first.setter("text_size"))
            ph.add_widget(first)
            img_wrap.add_widget(ph)
        self.add_widget(img_wrap)

        # 右侧：中文名 + 英文名
        info_box = BoxLayout(orientation="vertical", spacing=dp(4),
                             size_hint=(1, 1))
        info_box.add_widget(Widget(size_hint=(1, None), height=dp(8)))

        name_lbl = Label(
            text=pest_data["name"],
            font_size=sp(18), bold=True,
            color=(0.08, 0.08, 0.08, 1),
            size_hint=(1, None), height=dp(28),
            halign="left", valign="middle", **text_style(),
        )
        name_lbl.bind(size=name_lbl.setter("text_size"))
        info_box.add_widget(name_lbl)

        en_name = pest_data.get("en_name", "")
        if en_name:
            en_lbl = Label(
                text=en_name,
                font_size=sp(14),
                color=(0.55, 0.55, 0.55, 1),
                size_hint=(1, None), height=dp(22),
                halign="left", valign="middle", **text_style(),
            )
            en_lbl.bind(size=en_lbl.setter("text_size"))
            info_box.add_widget(en_lbl)

        info_box.add_widget(Widget(size_hint=(1, 1)))
        self.add_widget(info_box)

        # 右箭头
        arrow = Label(
            text=">", font_size=sp(18),
            color=(0.72, 0.72, 0.72, 1),
            size_hint=(None, 1), width=dp(20),
            halign="center", valign="middle",
        )
        self.add_widget(arrow)

    def _update_bg(self, *_args):
        self.canvas.before.clear()
        self.canvas.after.clear()
        with self.canvas.before:
            Color(1, 1, 1, 1)
            Rectangle(pos=self.pos, size=self.size)
        with self.canvas.after:
            Color(0.90, 0.90, 0.90, 1)
            Line(points=[self.x + dp(108), self.y,
                         self.right - dp(16), self.y], width=1)

    def on_release(self):
        if self.on_open:
            self.on_open(self.pest_data["id"])





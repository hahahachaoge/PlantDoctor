import os
from kivy.graphics import Color, Rectangle, RoundedRectangle
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.widget import Widget
from kivy.app import App
from kivy.clock import Clock
from kivy.graphics import Color, Rectangle
from kivy.metrics import dp, sp
from kivy.uix.boxlayout import BoxLayout

from kivy.uix.label import Label
from kivy.uix.screenmanager import Screen
from kivy.uix.scrollview import ScrollView
from kivy.uix.floatlayout import FloatLayout

from config import GREEN
from database.store_db import STORE_DB
from utils import text_style, bind_deferred_layout
from widgets.base_widgets import IconButton, RoundedButton, GrayPlaceholder, PestListRow



from config import IMAGE_DIR

PEST_IMAGES = {}

def get_pest_image(pest_name):
    path = os.path.join(IMAGE_DIR, f"{pest_name}.jpg")
    if os.path.exists(path):
        return path
    path_png = os.path.join(IMAGE_DIR, f"{pest_name}.png")
    if os.path.exists(path_png):
        return path_png
    return ""



class EncyclopediaScreen(Screen):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.name = "encyclopedia"
        self.build_ui()

    def build_ui(self):
        self.layout = FloatLayout()
        self.add_widget(self.layout)
        with self.layout.canvas.before:
            Color(0.97, 0.97, 0.97, 1)
            self.bg_rect = Rectangle(pos=self.layout.pos, size=self.layout.size)
        self.layout.bind(pos=self._update_bg, size=self._update_bg)

        self.top_bar = FloatLayout(size_hint=(1, None), height=dp(56), pos_hint={"x": 0, "top": 1})
        with self.top_bar.canvas.before:
            Color(*GREEN)
            self.top_bar_rect = Rectangle(pos=self.top_bar.pos, size=self.top_bar.size)
        self.top_bar.bind(pos=self._update_top_bar, size=self._update_top_bar)
        self.layout.add_widget(self.top_bar)

        self.back_btn = IconButton(
            text="<", font_size=sp(34), color=(0, 0, 0, 1),
            size_hint=(None, None), size=(dp(56), dp(56)),
            pos_hint={"x": 0.03, "center_y": 0.5}, **text_style(),
        )
        self.back_btn.bind(on_press=lambda *_: setattr(self.manager, "current", "home"))
        self.top_bar.add_widget(self.back_btn)

        self.title_label = Label(
            text="虫害百科", font_size=sp(22), color=(1, 1, 1, 1), size_hint=(0.6, None), height=dp(36),
            pos_hint={"center_x": 0.52, "center_y": 0.5},
            halign="center", valign="middle", **text_style(),
        )
        self.title_label.bind(size=self.title_label.setter("text_size"))
        self.top_bar.add_widget(self.title_label)

        self.scroll = ScrollView(size_hint=(1, None), do_scroll_x=False,
                                 pos_hint={"x": 0, "y": 0})
        self.layout.add_widget(self.scroll)
        self.content_box = BoxLayout(orientation="vertical", spacing=0, size_hint=(1, None))
        self.content_box.bind(minimum_height=self.content_box.setter("height"))
        self.scroll.add_widget(self.content_box)
        bind_deferred_layout(self.layout, self._update_layout)
        Clock.schedule_once(lambda dt: self._update_layout(), 0)

    def on_pre_enter(self, *args):
        self.refresh_data()
        return super().on_pre_enter(*args)

    def _update_bg(self, *_args):
        self.bg_rect.pos = self.layout.pos
        self.bg_rect.size = self.layout.size

    def _update_top_bar(self, *_args):
        self.top_bar_rect.pos = self.top_bar.pos
        self.top_bar_rect.size = self.top_bar.size

    def _update_layout(self, *_args):
        self.scroll.height = self.height - self.top_bar.height

    def refresh_data(self):
        self.content_box.clear_widgets()
        pests = STORE_DB.get_pest_entries()
        if not pests:
            empty = Label(
                text="暂无数据", font_size=sp(16),
                color=(0.45, 0.45, 0.45, 1),
                size_hint=(1, None), height=dp(60),
                halign="center", valign="middle", **text_style(),
            )
            empty.bind(size=empty.setter("text_size"))
            self.content_box.add_widget(empty)
            return

        # 按作物分组
        groups = {}
        for pest in pests:
            crop = pest.get("crop", "其他")
            groups.setdefault(crop, []).append(pest)

        for crop_name, items in groups.items():
            # 分组标题
            header = BoxLayout(
                size_hint=(1, None), height=dp(44),
                padding=(dp(16), dp(10), dp(16), dp(4)),
            )
            with header.canvas.before:
                Color(0.96, 0.98, 0.96, 1)
                h_bg = Rectangle(pos=header.pos, size=header.size)
            header.bind(
                pos=lambda i, _value, r=h_bg: setattr(r, "pos", i.pos),
                size=lambda i, _value, r=h_bg: setattr(r, "size", i.size),
            )
            # 绿色竖条
            bar = Widget(size_hint=(None, 1), width=dp(4))
            with bar.canvas.before:
                Color(*GREEN)
                bar_rect = RoundedRectangle(
                    pos=bar.pos, size=bar.size, radius=[dp(2)] * 4)
            bar.bind(
                pos=lambda i, _value, r=bar_rect: setattr(r, "pos", i.pos),
                size=lambda i, _value, r=bar_rect: setattr(r, "size", i.size),
            )
            header.add_widget(bar)
            header.add_widget(Widget(size_hint=(None, 1), width=dp(10)))
            crop_lbl = Label(
                text=crop_name, font_size=sp(18), bold=True,
                color=(0.08, 0.08, 0.08, 1),
                size_hint=(1, 1),
                halign="left", valign="middle", **text_style(),
            )
            crop_lbl.bind(size=crop_lbl.setter("text_size"))
            header.add_widget(crop_lbl)
            self.content_box.add_widget(header)

            for pest in items:
                self.content_box.add_widget(
                    PestListRow(pest, on_open=self.open_pest_detail))

    def open_pest_detail(self, pest_id):
        detail_screen = self.manager.get_screen("pest_detail")
        detail_screen.return_screen = "encyclopedia"
        detail_screen.set_pest(pest_id)
        self.manager.current = "pest_detail"


class PestDetailScreen(Screen):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.name = "pest_detail"
        self.current_pest_id = None
        self.return_screen = "encyclopedia"
        self.build_ui()

    def build_ui(self):
        self.layout = FloatLayout()
        self.add_widget(self.layout)
        with self.layout.canvas.before:
            Color(1, 1, 1, 1)
            self.bg_rect = Rectangle(pos=self.layout.pos, size=self.layout.size)
        self.layout.bind(pos=self._update_bg, size=self._update_bg)

        self.top_bar = FloatLayout(size_hint=(1, None), height=dp(56),
                                   pos_hint={"x": 0, "top": 1})
        with self.top_bar.canvas.before:
            Color(*GREEN)
            self.top_bar_rect = Rectangle(
                pos=self.top_bar.pos, size=self.top_bar.size)
        self.top_bar.bind(pos=self._update_top_bar, size=self._update_top_bar)
        self.layout.add_widget(self.top_bar)

        self.back_btn = IconButton(
            text="<", font_size=sp(34), color=(0, 0, 0, 1),
            size_hint=(None, None), size=(dp(56), dp(56)),
            pos_hint={"x": 0.03, "center_y": 0.5}, **text_style(),
        )
        self.back_btn.bind(on_press=self.go_back)
        self.top_bar.add_widget(self.back_btn)

        self.title_label = Label(
            text="病虫害详情", font_size=sp(22), color=(1, 1, 1, 1),
            size_hint=(0.6, None), height=dp(36),
            pos_hint={"center_x": 0.52, "center_y": 0.5},
            halign="center", valign="middle", **text_style(),
        )
        self.title_label.bind(size=self.title_label.setter("text_size"))
        self.top_bar.add_widget(self.title_label)

        self.scroll = ScrollView(size_hint=(1, None), do_scroll_x=False,
                                 pos_hint={"x": 0, "y": 0})
        self.layout.add_widget(self.scroll)
        self.content_box = BoxLayout(
            orientation="vertical", spacing=dp(14),
            padding=(dp(16), dp(12), dp(16), dp(20)), size_hint=(1, None),
        )
        self.content_box.bind(minimum_height=self.content_box.setter("height"))
        self.scroll.add_widget(self.content_box)

        # 图片占位
        self.photo = GrayPlaceholder(size_hint=(1, None), height=dp(220))
        self.content_box.add_widget(self.photo)

        self.name_label = Label(
            text="", font_size=sp(24), bold=True,
            color=(0.12, 0.12, 0.12, 1),
            size_hint=(1, None), height=dp(36),
            halign="left", valign="middle", **text_style(),
        )
        self.name_label.bind(size=self.name_label.setter("text_size"))
        self.content_box.add_widget(self.name_label)

        self.intro_label = Label(
            text="", font_size=sp(15), color=(0.18, 0.18, 0.18, 1),
            size_hint=(1, None), halign="left", valign="top", **text_style(),
        )
        self.intro_label.bind(
            texture_size=self._sync_label_height,
            width=self._sync_label_width,
        )
        self.content_box.add_widget(self.intro_label)

        self.treatment_label = Label(
            text="", font_size=sp(15), color=(0.18, 0.18, 0.18, 1),
            size_hint=(1, None), halign="left", valign="top", **text_style(),
        )
        self.treatment_label.bind(
            texture_size=self._sync_label_height,
            width=self._sync_label_width,
        )
        self.content_box.add_widget(self.treatment_label)

        action_box = BoxLayout(size_hint=(1, None), height=dp(48), spacing=dp(12))
        recognize_btn = RoundedButton(
            text="拍照识别", color=(1, 1, 1, 1), **text_style())
        recognize_btn.bind(
            on_press=lambda *_: App.get_running_app().show_capture_menu())
        action_box.add_widget(recognize_btn)
        self.content_box.add_widget(action_box)

        bind_deferred_layout(self.layout, self._update_layout)
        Clock.schedule_once(lambda dt: self._update_layout(), 0)

    def _update_bg(self, *_args):
        self.bg_rect.pos = self.layout.pos
        self.bg_rect.size = self.layout.size

    def _update_top_bar(self, *_args):
        self.top_bar_rect.pos = self.top_bar.pos
        self.top_bar_rect.size = self.top_bar.size

    def _update_layout(self, *_args):
        self.scroll.height = self.height - self.top_bar.height
        self.scroll.pos = (0, 0)

    def _sync_label_width(self, instance, _value):
        instance.text_size = (instance.width, None)

    def _sync_label_height(self, instance, _value):
        instance.height = max(dp(80), instance.texture_size[1] + dp(6))

    def set_pest(self, pest_id):
        self.current_pest_id = pest_id
        pest = STORE_DB.get_pest_entry(pest_id)
        if not pest:
            self.name_label.text = "暂无数据"
            self.intro_label.text = ""
            self.treatment_label.text = ""
            return
        self.name_label.text = pest["name"]
        self.title_label.text = pest["name"]
        self.intro_label.text = f"介绍：{pest['intro']}"
        self.treatment_label.text = f"防治方法：{pest['treatment']}"

        # 加载图片
        from config import IMAGE_DIR
        img_path = ""
        for fmt in [
            os.path.join(IMAGE_DIR, f"pest_{pest['name']}.png"),
            os.path.join(IMAGE_DIR, f"pest_{pest['name']}.jpg"),
            os.path.join(IMAGE_DIR, f"{pest['name']}.png"),
            os.path.join(IMAGE_DIR, f"{pest['name']}.jpg"),
        ]:
            if os.path.exists(fmt):
                img_path = fmt
                break

        if self.photo.parent:
            self.content_box.remove_widget(self.photo)

        if img_path:
            from kivy.uix.image import Image as KivyImg
            self.photo = KivyImg(
                source=img_path,
                size_hint=(1, None), height=dp(220),
                allow_stretch=True, keep_ratio=True,
            )
        else:
            self.photo = GrayPlaceholder(size_hint=(1, None), height=dp(220))

        self.content_box.add_widget(
            self.photo, index=len(self.content_box.children))

    def go_back(self, *_args):
        target = self.return_screen if self.manager.has_screen(self.return_screen) else "encyclopedia"
        self.manager.current = target






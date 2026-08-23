import os
import shutil

from kivy.app import App
from kivy.clock import Clock
from kivy.core.window import Window
from kivy.graphics import Color, Rectangle, RoundedRectangle
from kivy.metrics import dp, sp
from kivy.uix.behaviors import ButtonBehavior
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.button import Button
from kivy.uix.floatlayout import FloatLayout
from kivy.uix.image import Image
from kivy.uix.label import Label
from kivy.uix.popup import Popup
from kivy.uix.screenmanager import Screen
from kivy.uix.widget import Widget
from kivy.utils import platform as kivy_platform

try:
    from kivy.core.text import LabelBase
except Exception:
    LabelBase = None

try:
    from PIL import Image as PILImage
except Exception:
    PILImage = None

from config import AVATAR_DIR, GREEN

FONT_NAME = None


def register_chinese_font():
    global FONT_NAME
    if LabelBase is None:
        return
    for font_path in (
            "C:/Windows/Fonts/msyh.ttc",  # 只在 Windows 有
            "/system/fonts/NotoSansCJK-Regular.ttc",  # Android
            "/system/fonts/NotoSansSC-Regular.otf",  # Android
            "/system/fonts/DroidSansFallback.ttf",  # Android 旧版
            "/System/Library/Fonts/PingFang.ttc",  # macOS
            "/usr/share/fonts/truetype/wqy/wqy-zenhei.ttf",
    ):



        if os.path.exists(font_path):
            LabelBase.register(name="ChineseFont", fn_regular=font_path)
            FONT_NAME = "ChineseFont"
            return


def text_style():
    return {"font_name": FONT_NAME} if FONT_NAME else {}


def is_android():
    return kivy_platform == "android"


def normalize_comment_text(raw_text):
    text = (raw_text or "").replace("\r", "").replace("\n", " ").strip()
    if not text:
        return ""
    first_cjk = -1
    for idx, char in enumerate(text):
        if "\u4e00" <= char <= "\u9fff":
            first_cjk = idx
            break
    if first_cjk > 0:
        prefix = text[:first_cjk].strip()
        suffix = text[first_cjk:].strip()
        if prefix and all(ch.isalpha() or ch.isspace() for ch in prefix):
            return suffix
    return text


def is_android_permission_granted(permission_name):
    if not is_android():
        return True
    try:
        from importlib import import_module
        permissions_module = import_module("android.permissions")
        check_permission_func = getattr(permissions_module, "check_permission")
        return bool(check_permission_func(permission_name))
    except Exception:
        return False


def save_avatar_image(source_path, username):
    if not source_path or not os.path.exists(source_path):
        return ""
    os.makedirs(AVATAR_DIR, exist_ok=True)
    target_path = os.path.join(AVATAR_DIR, f"{username}.png")
    try:
        if PILImage is not None:
            image = PILImage.open(source_path).convert("RGBA")
            width, height = image.size
            side = min(width, height)
            left = (width - side) // 2
            top = (height - side) // 2
            image = image.crop((left, top, left + side, top + side))
            image.save(target_path)
        else:
            shutil.copyfile(source_path, target_path)
        return target_path
    except Exception:
        return source_path


def show_toast(message, duration=1.1):
    popup = SimpleToast(message)
    popup.open()
    Clock.schedule_once(lambda dt: popup.dismiss(), duration)


def open_text_popup(title, body):
    from widgets.base_widgets import RoundedButton
    popup = Popup(title="", separator_height=0, size_hint=(0.84, None), height=dp(260))
    content = BoxLayout(orientation="vertical", spacing=dp(14), padding=dp(16))
    with content.canvas.before:
        Color(0.16, 0.16, 0.16, 0.96)
        bg_rect = RoundedRectangle(pos=content.pos, size=content.size, radius=[dp(16)] * 4)
    content.bind(pos=lambda instance, *_: _update_popup_rect(instance, bg_rect),
                 size=lambda instance, *_: _update_popup_rect(instance, bg_rect))
    title_label = Label(
        text=title, font_size=sp(18), color=(1, 1, 1, 1),
        size_hint=(1, None), height=dp(30), halign="center", valign="middle",
        **text_style(),
    )
    title_label.bind(size=title_label.setter("text_size"))
    content.add_widget(title_label)
    body_label = Label(
        text=body, font_size=sp(15), color=(1, 1, 1, 1),
        size_hint=(1, 1), halign="center", valign="middle",
        **text_style(),
    )
    body_label.bind(size=body_label.setter("text_size"))
    content.add_widget(body_label)
    ok_btn = RoundedButton(
        text="知道了", color=(1, 1, 1, 1),
        size_hint=(1, None), height=dp(44), **text_style(),
    )
    ok_btn.bind(on_press=lambda *_: popup.dismiss())
    content.add_widget(ok_btn)
    popup.content = content
    popup.open()
    return popup


def _update_popup_rect(instance, rect):
    rect.pos = instance.pos
    rect.size = instance.size


def update_nav_rect(nav):
    if hasattr(nav, "bg_rect"):
        nav.bg_rect.pos = nav.pos
        nav.bg_rect.size = nav.size


class SimpleToast(Popup):
    def __init__(self, message, **kwargs):
        super().__init__(
            title="", separator_height=0,
            size_hint=(0.52, None), height=dp(112),
            auto_dismiss=True, background="",
            background_color=(0, 0, 0, 0), **kwargs,
        )
        content = BoxLayout(padding=dp(12))
        label = Label(
            text=message, color=(1, 1, 1, 1),
            halign="center", valign="middle", **text_style(),
        )
        label.bind(size=label.setter("text_size"))
        with content.canvas.before:
            Color(0.10, 0.10, 0.10, 0.86)
            self.bg_rect = Rectangle(pos=content.pos, size=content.size)
        content.bind(pos=self._update_bg, size=self._update_bg)
        content.add_widget(label)
        self.content = content

    def _update_bg(self, instance, *_args):
        self.bg_rect.pos = instance.pos
        self.bg_rect.size = instance.size


class BaseScreen(Screen):
    def setup_background(self, image_source):
        from kivy.uix.floatlayout import FloatLayout
        from kivy.uix.image import Image
        self.layout = FloatLayout()
        self.add_widget(self.layout)
        self.background = Image(
            source=image_source, allow_stretch=True,
            keep_ratio=False, size_hint=(1, 1),
            pos_hint={"x": 0, "y": 0},
        )
        self.layout.add_widget(self.background)

    def is_in_relative_area(self, x, y, rel_area):
        from kivy.core.window import Window
        rel_x1, rel_y1, rel_x2, rel_y2 = rel_area
        width = self.width or Window.width
        height = self.height or Window.height
        return rel_x1 * width <= x <= rel_x2 * width and rel_y1 * height <= y <= rel_y2 * height

    def get_relative_pos(self, x, y):
        from kivy.core.window import Window
        width = self.width or Window.width
        height = self.height or Window.height
        if width <= 0 or height <= 0:
            return 0, 0
        return x / width, y / height

    def open_camera(self):
        app = App.get_running_app()
        app.previous_before_camera = self.name
        app.camera_mode = "recognize"
        self.manager.current = "camera"

    def open_capture_menu(self, after_action=None):
        app = App.get_running_app()
        if not hasattr(app, "show_capture_menu"):
            return
        app.show_capture_menu(after_action=after_action)

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
from kivy.uix.modalview import ModalView
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
_WINDOWS_IME_STATE = {}


_MD_THEME = None
_MD_THEME_FAILED = False


def ensure_md_theme(style="Light", palette="Green"):
    """返回 KivyMD 的 ThemeManager 单例。

    KivyMD 的控件（如 MDDatePicker）都依赖 app.theme_cls，本项目主 App 仍继承
    kivy.app.App，所以这里独立维护一个主题对象；未安装 kivymd 时返回 None，
    调用方需自行降级处理，不能直接崩。
    """
    global _MD_THEME, _MD_THEME_FAILED
    if _MD_THEME is not None:
        return _MD_THEME
    if _MD_THEME_FAILED:
        return None
    try:
        from kivymd.theming import ThemeManager
    except Exception as exc:
        print("[kivymd] 未安装或无法导入 kivymd:", exc)
        _MD_THEME_FAILED = True
        return None
    try:
        theme = ThemeManager()
        theme.theme_style = style
        theme.primary_palette = palette
        theme.primary_hue = "500"
    except Exception as exc:
        print("[kivymd] 主题初始化失败:", exc)
        _MD_THEME_FAILED = True
        return None
    _MD_THEME = theme
    return _MD_THEME


def md_available():
    """KivyMD 是否可用。"""
    return ensure_md_theme() is not None


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


def ascii_input_filter(substring, from_undo=False):
    """Keep password input limited to ASCII characters."""
    return "".join(char for char in substring if char.isascii())


def set_ascii_input_mode(enabled=True):
    """Detach the Windows IME while a password field has focus.

    Merely clearing the Chinese conversion flag is temporary: the user can
    switch it back while typing.  Detaching the IME context from the SDL
    window locks the focused password box to direct keyboard (ASCII) input.
    The exact context is restored when that field loses focus.
    """
    if kivy_platform != "win":
        return
    try:
        import ctypes
        from ctypes import wintypes

        user32 = ctypes.windll.user32
        imm32 = ctypes.windll.imm32
        user32.GetForegroundWindow.restype = wintypes.HWND
        imm32.ImmAssociateContext.argtypes = [wintypes.HWND, wintypes.HANDLE]
        imm32.ImmAssociateContext.restype = wintypes.HANDLE
        if enabled:
            hwnd = user32.GetForegroundWindow()
            if not hwnd or _WINDOWS_IME_STATE.get("locked"):
                return
            previous_context = imm32.ImmAssociateContext(hwnd, None)
            _WINDOWS_IME_STATE.update(
                hwnd=hwnd, context=previous_context, locked=True)
        elif _WINDOWS_IME_STATE.get("locked"):
            hwnd = _WINDOWS_IME_STATE.get("hwnd")
            previous_context = _WINDOWS_IME_STATE.get("context")
            if hwnd and previous_context:
                imm32.ImmAssociateContext(hwnd, previous_context)
            _WINDOWS_IME_STATE.clear()
    except Exception:
        pass


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


def open_text_popup(title, body, height=260):
    from widgets.base_widgets import RoundedButton
    popup = ModalView(size_hint=(0.84, None), height=dp(height),
              background="", background_color=(0, 0, 0, 0),
              overlay_color=(0, 0, 0, 0.45))
    content = BoxLayout(orientation="vertical", spacing=dp(14), padding=dp(16))
    with content.canvas.before:
        Color(1, 1, 1, 1)
        bg_rect = RoundedRectangle(pos=content.pos, size=content.size, radius=[dp(16)] * 4)
    content.bind(pos=lambda instance, *_: _update_popup_rect(instance, bg_rect),
                 size=lambda instance, *_: _update_popup_rect(instance, bg_rect))
    title_label = Label(
        text=title, font_size=sp(18), color=(0.08, 0.08, 0.08, 1),
        size_hint=(1, None), height=dp(30), halign="center", valign="middle",
        **text_style(),
    )
    title_label.bind(size=title_label.setter("text_size"))
    content.add_widget(title_label)
    body_label = Label(
        text=body, font_size=sp(15), color=(0.22, 0.22, 0.22, 1),
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
    popup.add_widget(content)
    popup.open()
    return popup


def _update_popup_rect(instance, rect):
    rect.pos = instance.pos
    rect.size = instance.size


def update_nav_rect(nav):
    if hasattr(nav, "bg_rect"):
        nav.bg_rect.pos = nav.pos
        nav.bg_rect.size = nav.size


def bind_deferred_layout(widget, callback):
    """把尺寸变化的处理推迟到下一帧执行（带去重，避免重复排队）。

    原因：Kivy 在属性派发（size/pos）过程中若同步修改其它控件的尺寸，
    会形成「尺寸变化 → 回调 → 再改尺寸」的回环，最终抛出
    RecursionError 卡死主线程，表现为点右上角 X 关不掉窗口。
    延迟到下一帧执行可以彻底打断这个同步回环。
    """
    state = {"scheduled": False}

    def run(dt):
        state["scheduled"] = False
        try:
            callback()
        except Exception as exc:  # 布局异常绝不能影响主循环
            print("[layout] update failed:", exc)

    def schedule(*_args):
        if state["scheduled"]:
            return
        state["scheduled"] = True
        Clock.schedule_once(run, 0)

    widget.bind(size=schedule)
    return schedule


# ─────────────────── 摄像头兼容（OpenCV 5.x / Kivy 2.3.0） ───────────────────

def patch_opencv_camera():
    """修复 Kivy 2.3.0 与 OpenCV 5.x 不兼容导致的相机报错刷屏。

    现象：
        AttributeError: 'NoneType' object has no attribute 'read'
        [ERROR] [OpenCV] Couldn't get image from Camera   （每帧刷一次）

    根因：
        kivy/core/camera/camera_opencv.py 的 init_camera() 里只写了
        opencvMajorVersion in (1,2,3,4) 的分支。本机装的是 OpenCV 5.x，
        主版本号 = 5，两个分支都不匹配 → 根本没有创建 VideoCapture，
        self._device 一直是 None → _update() 每帧调用 None.read() 报错。

    处理：
        把主版本号 >= 5 归一到 4.x 分支，并重新初始化一次设备。
    """
    # 没安装 cv2 时不要触发 Kivy 的 provider 自动选择；自动选择会把
    # Windows 不需要的 picamera / gi 缺失也一起打印成 CRITICAL。
    try:
        import cv2  # noqa: F401
    except ImportError:
        print("[camera] 未安装 OpenCV；桌面相机功能已停用，请安装 opencv-python")
        return False

    try:
        from kivy.core.camera.camera_opencv import CameraOpenCV
    except Exception as exc:
        print("[camera] opencv provider 未加载:", exc)
        return False

    if getattr(CameraOpenCV, "_version_patched", False):
        return True

    original_init = CameraOpenCV.__init__

    def patched_init(self, **kwargs):
        # 1) Kivy 2.3.0 只在 1~4 版本分支里给 self.fps 赋值，OpenCV 5.x 走空分支
        #    会在 init_camera 末尾访问 self.fps 时抛 AttributeError，
        #    所以必须先把默认 fps 挂到类上（实例未赋值时也能读到）。
        if not hasattr(CameraOpenCV, "fps"):
            CameraOpenCV.fps = 30
        original_init(self, **kwargs)
        # 2) OpenCV 5.x 主版本号不在 Kivy 支持范围内，按 4.x 分支重建设备
        if getattr(self, "opencvMajorVersion", 4) not in (1, 2, 3, 4):
            self.opencvMajorVersion = 4
            self._device = None
            try:
                self.init_camera()
            except Exception as exc:
                print("[camera] init_camera 兼容重建失败:", exc)

    CameraOpenCV.__init__ = patched_init
    CameraOpenCV._version_patched = True
    return True


def probe_camera_index(max_index=4):
    """用 OpenCV 探测可用的摄像头索引，返回 index；没有可用设备返回 None。

    目的：在没有摄像头 / 被其它程序占用时，不要创建 Kivy 的 Camera 控件，
    否则它会每帧刷 "Couldn't get image from Camera" 把日志冲爆、界面卡死。
    """
    try:
        import cv2
    except Exception:
        return None

    for index in range(max_index):
        cap = None
        try:
            cap = cv2.VideoCapture(index)
            if not cap or not cap.isOpened():
                continue
            ret, _frame = cap.read()
            if ret:
                return index
        except Exception:
            continue
        finally:
            try:
                if cap is not None:
                    cap.release()
            except Exception:
                pass
    return None


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

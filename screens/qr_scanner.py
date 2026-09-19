import hashlib
import os
import threading
import webbrowser
from urllib.parse import parse_qs, urlparse

from kivy.app import App
from kivy.clock import Clock
from kivy.core.clipboard import Clipboard
from kivy.metrics import dp, sp
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.image import Image

from config import GREEN, IMAGE_DIR
from database.store_db import STORE_DB
from screens.account_pages import (
    AccountPage, INK, MUTED, ORANGE, SOFT_GREEN, _current_user, _text,
)
from utils import is_android, show_toast, text_style
from widgets.base_widgets import RoundedButton


class QRScannerScreen(AccountPage):
    title = "扫一扫"
    subtitle = ""

    def __init__(self, **kwargs):
        kwargs.setdefault("name", "qr_scanner")
        super().__init__(**kwargs)
        self.return_screen = "home"
        self.last_result = None
        self.scan_status = "将二维码完整放入画面，保持镜头稳定并避免反光。"
        self._scanning = False

    def on_pre_enter(self, *_args):
        self.refresh_page()

    def go_back(self, *_args):
        if self.manager and self.manager.has_screen(self.return_screen):
            self.manager.current = self.return_screen
        elif self.manager:
            self.manager.current = "home"

    def refresh_page(self):
        self.body.clear_widgets()
        hero = self.card(188, color=(0.84, 0.95, 0.87, 1))
        top = BoxLayout(spacing=dp(14), size_hint=(1, None), height=dp(82))
        icon_path = os.path.join(IMAGE_DIR, "扫一扫.png")
        top.add_widget(Image(
            source=icon_path if os.path.exists(icon_path) else "",
            size_hint=(None, None), size=(dp(76), dp(76)), fit_mode="contain"))
        intro = BoxLayout(orientation="vertical", spacing=dp(2))
        intro.add_widget(_text("扫描二维码", 19, INK, 34, True))
        intro.add_widget(_text(
            "支持农智云警个人码、网页链接和普通文本", 12, MUTED, 42))
        top.add_widget(intro)
        hero.add_widget(top)
        self.status_label = _text(
            self.scan_status, 12, (0.18, 0.43, 0.26, 1), 48,
            halign="center")
        hero.add_widget(self.status_label)
        self.body.add_widget(hero)

        actions = BoxLayout(spacing=dp(10), size_hint=(1, None), height=dp(50))
        camera = RoundedButton(
            text="打开相机扫描", color=(1, 1, 1, 1), **text_style())
        album = RoundedButton(
            text="从相册识别", color=GREEN, fill_color=SOFT_GREEN,
            **text_style())
        camera.bind(on_release=self.scan_from_camera)
        album.bind(on_release=self.scan_from_album)
        actions.add_widget(camera)
        actions.add_widget(album)
        self.body.add_widget(actions)

        if self.last_result:
            self.body.add_widget(self._result_card(self.last_result))
        self._append_history()

    def scan_from_camera(self, *_args):
        app = App.get_running_app()
        if not app or not self.manager:
            return
        app.camera_mode = "scan"
        app.previous_before_camera = self.name
        self.manager.current = "camera"

    def scan_from_album(self, *_args):
        app = App.get_running_app()
        if not app:
            return
        callback = lambda _mode, path: self.scan_image(path, source="相册")
        if is_android():
            app._open_photo_kivy_chooser(callback)
        else:
            app._open_photo_native_dialog(callback)

    def scan_image(self, image_path, source="相机"):
        if self._scanning:
            return
        self._scanning = True
        self.scan_status = "正在读取二维码，请稍候……"
        if hasattr(self, "status_label"):
            self.status_label.text = self.scan_status
        threading.Thread(
            target=self._decode_worker, args=(image_path, source), daemon=True
        ).start()

    def _decode_worker(self, image_path, source):
        try:
            content = self._decode_qr_image(image_path)
            if not content:
                raise ValueError("图片中没有检测到清晰、完整的二维码")
            result = self._classify_content(content)
            result["source"] = source
            username = _current_user().get("username", "游客")
            STORE_DB.add_qr_scan(
                username, content, result["type"], result["summary"], source)
            Clock.schedule_once(lambda _dt: self._scan_succeeded(result), 0)
        except Exception as exc:
            message = str(exc) or "二维码读取失败"
            Clock.schedule_once(lambda _dt, value=message: self._scan_failed(value), 0)

    @staticmethod
    def _decode_qr_image(image_path):
        if not image_path or not os.path.isfile(image_path):
            raise ValueError("所选图片不存在或已被移动")
        try:
            import cv2
            import numpy as np
        except ImportError as exc:
            raise RuntimeError("缺少二维码识别组件 OpenCV") from exc
        image_data = np.fromfile(image_path, dtype=np.uint8)
        frame = cv2.imdecode(image_data, cv2.IMREAD_COLOR)
        if frame is None:
            raise ValueError("无法读取该图片，请选择 PNG 或 JPG 图片")
        detector = cv2.QRCodeDetector()
        if hasattr(detector, "detectAndDecodeMulti"):
            try:
                detected, values, _points, _straight = detector.detectAndDecodeMulti(frame)
                if detected:
                    for value in values:
                        if value and value.strip():
                            return value.strip()
            except (cv2.error, ValueError):
                pass
        value, _points, _straight = detector.detectAndDecode(frame)
        return (value or "").strip()

    @staticmethod
    def _classify_content(content):
        parsed = urlparse(content)
        if parsed.scheme == "plantdoctor" and parsed.netloc == "profile":
            account_id = parsed.path.strip("/") or "未知"
            query = parse_qs(parsed.query)
            username = query.get("username", ["未知用户"])[0]
            supplied = query.get("token", [""])[0]
            expected = hashlib.sha256(
                f"PlantDoctor:v1:{account_id}:{username}".encode("utf-8")
            ).hexdigest()[:24]
            verified = bool(supplied) and supplied == expected
            return {
                "type": "农智云警名片",
                "summary": f"{username} · 账号 {account_id}",
                "detail": "账号二维码校验通过" if verified else "二维码格式有效，但校验信息不匹配",
                "content": content,
                "is_url": False,
                "verified": verified,
            }
        if parsed.scheme in ("http", "https") and parsed.netloc:
            return {
                "type": "网页链接", "summary": parsed.netloc,
                "detail": "打开前请确认域名可信，不要在陌生页面填写密码或验证码。",
                "content": content, "is_url": True, "verified": None,
            }
        if content.upper().startswith("WIFI:"):
            return {
                "type": "Wi-Fi 信息", "summary": "检测到无线网络配置",
                "detail": "出于安全考虑，本应用不会自动连接网络。",
                "content": content, "is_url": False, "verified": None,
            }
        return {
            "type": "文本内容", "summary": content[:48],
            "detail": "已按原始文本显示，可复制后在可信应用中使用。",
            "content": content, "is_url": False, "verified": None,
        }

    def _scan_succeeded(self, result):
        self._scanning = False
        self.last_result = result
        self.scan_status = "识别完成，可核对下方内容。"
        self.refresh_page()
        self.scroll.scroll_y = 0.82

    def _scan_failed(self, message):
        self._scanning = False
        self.scan_status = message
        if hasattr(self, "status_label"):
            self.status_label.text = message
        show_toast(message)

    def _result_card(self, result):
        card = self.card(color=(1, 1, 1, 1))
        heading = BoxLayout(size_hint=(1, None), height=dp(34))
        heading.add_widget(_text("扫码结果", 17, INK, 34, True))
        color = GREEN if result.get("verified") is not False else ORANGE
        heading.add_widget(_text(
            result["type"], 12, color, 34, True, "right",
            size_hint=(None, None), width=dp(112)))
        card.add_widget(heading)
        card.add_widget(_text(result["summary"], 15, INK, 34, True))
        card.add_widget(_text(result["detail"], 12, MUTED, 48))
        card.add_widget(_text(result["content"], 11, (0.27, 0.32, 0.29, 1), 74))
        actions = BoxLayout(spacing=dp(9), size_hint=(1, None), height=dp(42))
        copy_button = RoundedButton(
            text="复制内容", color=GREEN, fill_color=SOFT_GREEN, **text_style())
        copy_button.bind(on_release=lambda *_: self._copy(result["content"]))
        actions.add_widget(copy_button)
        if result.get("is_url"):
            open_button = RoundedButton(
                text="打开链接", color=(1, 1, 1, 1), **text_style())
            open_button.bind(on_release=lambda *_: self._open_url(result["content"]))
            actions.add_widget(open_button)
        card.add_widget(actions)
        return card

    def _append_history(self):
        username = _current_user().get("username", "游客")
        records = STORE_DB.get_qr_scans(username, limit=10)
        heading = BoxLayout(size_hint=(1, None), height=dp(40))
        heading.add_widget(_text("最近扫描", 17, INK, 40, True))
        if records:
            clear = RoundedButton(
                text="清空", color=(0.70, 0.24, 0.20, 1),
                fill_color=(1.0, 0.92, 0.90, 1), size_hint=(None, None),
                size=(dp(72), dp(34)), **text_style())
            clear.bind(on_release=self._clear_history)
            heading.add_widget(clear)
        self.body.add_widget(heading)
        if not records:
            self.body.add_widget(_text(
                "暂无扫码记录，识别结果只会保存在当前账号中。",
                12, MUTED, 58, halign="center"))
            return
        for record in records:
            card = self.card(102, padding=12, spacing=4)
            top = BoxLayout(size_hint=(1, None), height=dp(28))
            top.add_widget(_text(record["content_type"], 14, INK, 28, True))
            stamp = record["created_at"].replace("T", " ")[5:16]
            top.add_widget(_text(
                stamp, 10, MUTED, 28, halign="right",
                size_hint=(None, None), width=dp(92)))
            card.add_widget(top)
            card.add_widget(_text(record["summary"], 12, MUTED, 30))
            card.add_widget(_text(f"来源：{record['source']}", 10, MUTED, 20))
            self.body.add_widget(card)

    @staticmethod
    def _copy(content):
        Clipboard.copy(content)
        show_toast("扫码内容已复制")

    @staticmethod
    def _open_url(url):
        if urlparse(url).scheme not in ("http", "https"):
            show_toast("该内容不是可打开的网页链接")
            return
        webbrowser.open(url)

    def _clear_history(self, *_args):
        STORE_DB.clear_qr_scans(_current_user().get("username", "游客"))
        show_toast("扫码记录已清空")
        self.refresh_page()

import os
import threading
from importlib import import_module

#os.environ.setdefault("KIVY_NO_FILELOG", "1")
#os.environ.setdefault("KIVY_NO_CONSOLELOG", "1")

from kivy.app import App
from kivy.clock import Clock
from kivy.core.window import Window
from kivy.metrics import dp
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.button import Button
from kivy.uix.filechooser import FileChooserListView
from kivy.uix.label import Label
from kivy.uix.popup import Popup
from kivy.uix.screenmanager import ScreenManager

from config import GREEN
from database.user_db import USER_DB
from database.store_db import STORE_DB
from utils import (text_style, show_toast, is_android, is_android_permission_granted,
                   register_chinese_font, _update_popup_rect)
from widgets.base_widgets import RoundedButton
from screens.auth import LoginScreen, RegisterScreen
from screens.home import HomeScreen
from screens.community import CommunityScreen, CommunityDetailScreen
from screens.store import StoreScreen, StoreCategoryScreen, PesticideDetailScreen
from screens.mypage import MyPageScreen, FavoriteScreen, OrderScreen
from screens.encyclopedia import EncyclopediaScreen, PestDetailScreen
from screens.misc import MapScreen
from screens.camera import CameraScreen, ResultScreen


register_chinese_font()
Window.softinput_mode = "below_target"
if not is_android():
    Window.size = (360, 800)


class MyApp(App):
    previous_before_camera = "home"
    current_user = None
    camera_mode = "recognize"

    def build(self):
        import traceback
        try:
            sm = ScreenManager()
            sm.add_widget(LoginScreen())
            sm.add_widget(RegisterScreen())
            sm.add_widget(HomeScreen())
            sm.add_widget(CommunityScreen())
            sm.add_widget(CommunityDetailScreen())
            sm.add_widget(StoreScreen())
            sm.add_widget(StoreCategoryScreen())
            sm.add_widget(FavoriteScreen())
            sm.add_widget(OrderScreen())
            sm.add_widget(EncyclopediaScreen())
            sm.add_widget(PestDetailScreen())
            sm.add_widget(MyPageScreen())
            sm.add_widget(MapScreen())
            sm.add_widget(CameraScreen())
            sm.add_widget(ResultScreen())
            sm.add_widget(PesticideDetailScreen())
            sm.current = "login"
            return sm
        except Exception:
            with open("crash.log", "w", encoding="utf-8") as f:
                traceback.print_exc(file=f)
            raise

    def set_current_user(self, user):
        self.current_user = dict(user) if user else None

    def open_product_detail_screen(self, product_id, from_tab="精选好物", return_screen="store"):
        try:
            detail_screen = self.root.get_screen("product_detail")
            detail_screen.set_product(product_id, from_tab=from_tab, return_screen=return_screen)
            self.root.current = "product_detail"
        except Exception as exc:
            show_toast(f"打开商品失败: {exc}")

    def refresh_current_user(self):
        if not self.current_user:
            return None
        user = USER_DB.get_user(self.current_user["username"])
        if user:
            self.current_user = user
        return self.current_user

    def can_current_user_recognize(self):
        if not self.current_user:
            show_toast("请先登录")
            return False
        allowed, user = USER_DB.can_recognize_today(self.current_user["username"])
        if user:
            self.current_user = user
        return allowed

    def mark_current_user_recognized(self):
        if not self.current_user:
            return
        self.current_user = USER_DB.increase_recognize_count(self.current_user["username"])

    def handle_avatar_capture(self, image_path):
        self.camera_mode = "recognize"
        register_screen = self.root.get_screen("register")
        register_screen.selected_avatar_source = image_path
        register_screen._show_selected_avatar()
        self.root.current = "register"

    def show_capture_menu(self, after_action=None):
        popup = Popup(title="", separator_height=0, size_hint=(0.82, None), height=dp(228))
        content = BoxLayout(orientation="vertical", spacing=dp(12), padding=dp(14))
        with content.canvas.before:
            from kivy.graphics import Color, RoundedRectangle
            Color(0.16, 0.16, 0.16, 0.96)
            bg_rect = RoundedRectangle(pos=content.pos, size=content.size, radius=[dp(16)] * 4)
        content.bind(pos=lambda i, *_: _update_popup_rect(i, bg_rect),
                     size=lambda i, *_: _update_popup_rect(i, bg_rect))
        title_label = Label(
            text="选择识别方式", font_size=dp(18), color=(1, 1, 1, 1),
            size_hint=(1, None), height=dp(28),
            halign="center", valign="middle", **text_style(),
        )
        title_label.bind(size=title_label.setter("text_size"))
        content.add_widget(title_label)
        camera_btn = RoundedButton(text="使用相机", color=(1, 1, 1, 1),
                                   size_hint=(1, None), height=dp(44), **text_style())
        album_btn = RoundedButton(text="使用照片", color=(1, 1, 1, 1),
                                  size_hint=(1, None), height=dp(44), **text_style())
        cancel_btn = RoundedButton(text="取消", color=(1, 1, 1, 1),
                                   fill_color=(0.65, 0.65, 0.65, 1),
                                   size_hint=(1, None), height=dp(44), **text_style())
        camera_btn.bind(on_press=lambda *_: self._open_camera_from_menu(popup, after_action))
        album_btn.bind(on_press=lambda *_: self._open_photo_from_menu(popup, after_action))
        cancel_btn.bind(on_press=lambda *_: popup.dismiss())
        content.add_widget(camera_btn)
        content.add_widget(album_btn)
        content.add_widget(cancel_btn)
        popup.content = content
        popup.open()

    def _open_camera_from_menu(self, popup, after_action=None):
        popup.dismiss()
        if is_android() and not is_android_permission_granted("android.permission.CAMERA"):
            show_toast("相机使用失败")
            return
        self.camera_mode = "recognize"
        if callable(after_action):
            after_action("camera")
            return
        if self.root.current != "result":
            self.previous_before_camera = self.root.current
        self.root.current = "camera"

    def _open_photo_from_menu(self, popup, after_action=None):
        if popup is not None:
            popup.dismiss()

        if is_android():
            # Android：检查权限
            if not (
                    is_android_permission_granted("android.permission.READ_EXTERNAL_STORAGE")
                    or is_android_permission_granted("android.permission.READ_MEDIA_IMAGES")
            ):
                show_toast("文件使用失败")
                return
            self.camera_mode = "recognize"
            self._open_photo_kivy_chooser(after_action)
        else:
            # Windows/PC：调用系统原生文件对话框
            self.camera_mode = "recognize"
            self._open_photo_native_dialog(after_action)

    def _open_photo_native_dialog(self, after_action=None):
        """PC 端使用系统原生文件对话框"""
        import threading

        def open_dialog():
            try:
                import tkinter as tk
                from tkinter import filedialog
                # 必须隐藏 tkinter 主窗口，否则会闪出一个空窗口
                root = tk.Tk()
                root.withdraw()
                root.attributes("-topmost", True)
                file_path = filedialog.askopenfilename(
                    title="选择照片",
                    filetypes=[
                        ("图片文件", "*.png *.jpg *.jpeg *.bmp *.webp"),
                        ("所有文件", "*.*"),
                    ],
                    initialdir=self._get_default_photo_dir(),
                )
                root.destroy()
                if file_path:
                    Clock.schedule_once(lambda dt: self._on_native_file_selected(
                        file_path, after_action))
            except Exception as exc:
                Clock.schedule_once(lambda dt: show_toast(f"打开文件对话框失败: {exc}"))

        # 在子线程里打开，避免阻塞 Kivy 主线程
        threading.Thread(target=open_dialog, daemon=True).start()

    def _on_native_file_selected(self, image_path, after_action=None):
        if self.root.current != "result":
            self.previous_before_camera = self.root.current
        if callable(after_action):
            after_action("album", image_path)
            return
        self.recognize_image_from_file(image_path)

    def _get_default_photo_dir(self):
        """按优先级查找默认图片目录"""
        candidates = [
            os.path.join(os.path.expanduser("~"), "Pictures"),
            os.path.join(os.path.expanduser("~"), "图片"),
            os.path.join(os.path.expanduser("~"), "Desktop"),
            os.path.expanduser("~"),
        ]
        return next((p for p in candidates if os.path.isdir(p)), os.path.expanduser("~"))

    def _open_photo_kivy_chooser(self, after_action=None):
        """Android 端使用 Kivy 内置文件选择器"""
        default_paths = [
            os.path.join(os.path.expanduser("~"), "Pictures"),
            os.path.join(os.path.expanduser("~"), "图片"),
            os.path.expanduser("~"),
        ]
        start_path = next((p for p in default_paths if os.path.isdir(p)),
                          os.path.expanduser("~"))

        chooser_popup = Popup(title="", separator_height=0, size_hint=(0.92, 0.82))
        wrapper = BoxLayout(orientation="vertical", spacing=dp(10), padding=dp(10))
        with wrapper.canvas.before:
            from kivy.graphics import Color, RoundedRectangle
            Color(0.16, 0.16, 0.16, 0.96)
            bg_rect = RoundedRectangle(pos=wrapper.pos, size=wrapper.size, radius=[dp(16)] * 4)
        wrapper.bind(pos=lambda i, *_: _update_popup_rect(i, bg_rect),
                     size=lambda i, *_: _update_popup_rect(i, bg_rect))

        title_label = Label(
            text="选择照片", font_size=dp(18), color=(1, 1, 1, 1),
            size_hint=(1, None), height=dp(28),
            halign="center", valign="middle", **text_style(),
        )
        title_label.bind(size=title_label.setter("text_size"))

        chooser = FileChooserListView(
            path=start_path,
            filters=["*.png", "*.jpg", "*.jpeg", "*.bmp", "*.webp"],
        )

        wrapper.add_widget(title_label)
        wrapper.add_widget(chooser)

        btn_row = BoxLayout(size_hint=(1, None), height=dp(44), spacing=dp(10))
        ok_btn = RoundedButton(text="确定", color=(1, 1, 1, 1), **text_style())
        cancel_btn = RoundedButton(text="取消", color=(1, 1, 1, 1),
                                   fill_color=(0.65, 0.65, 0.65, 1), **text_style())

        def confirm_pick(_instance=None):
            if not chooser.selection:
                show_toast("请先选择一张照片")
                return
            image_path = chooser.selection[0]
            chooser_popup.dismiss()
            if callable(after_action):
                after_action("album", image_path)
                return
            if self.root.current != "result":
                self.previous_before_camera = self.root.current
            self.recognize_image_from_file(image_path)

        def on_submit(chooser_instance, selection, touch):
            if selection:
                confirm_pick()

        chooser.bind(on_submit=on_submit)
        ok_btn.bind(on_press=confirm_pick)
        cancel_btn.bind(on_press=lambda *_: chooser_popup.dismiss())
        btn_row.add_widget(ok_btn)
        btn_row.add_widget(cancel_btn)
        wrapper.add_widget(btn_row)
        chooser_popup.content = wrapper
        chooser_popup.open()

    def recognize_image_from_file(self, image_path):
        started = self.start_recognition_for_image(
            image_path,
            on_success=self.open_recognition_result,
            on_error=lambda msg: show_toast(msg),
        )
        if started:
            show_toast("正在识别，请稍候...")

    def start_recognition_for_image(self, image_path, on_success=None, on_error=None):
        if not self.can_current_user_recognize():
            show_toast("免费用户每天限识别3次，升级VIP解锁无限次")
            return False
        threading.Thread(
            target=self._do_recognize_image,
            args=(image_path, on_success, on_error),
            daemon=True,
        ).start()
        return True

    def _do_recognize_image(self, image_path, on_success=None, on_error=None):
        try:
            requests = import_module("requests")
            from config import get_api_base_url
            api_base_url = get_api_base_url()
            with open(image_path, "rb") as f:
                response = requests.post(
                    f"{api_base_url}/predict",
                    files={"file": (os.path.basename(image_path), f, "image/png")},
                    timeout=45,
                )
            if response.status_code != 200:
                err_msg = f"识别服务返回异常: {response.status_code}"
                Clock.schedule_once(
                    lambda dt: self._handle_recognition_error(err_msg, on_error)
                )
                return
            data = response.json()
            if not data.get("success"):
                err_msg = f"识别失败: {data.get('error', '未知错误')}"
                Clock.schedule_once(
                    lambda dt: self._handle_recognition_error(err_msg, on_error)
                )
                return
            from screens.camera import CameraScreen
            normalized_data = CameraScreen._normalize_api_result(data)
            Clock.schedule_once(
                lambda dt: self._handle_recognition_success(
                    image_path, normalized_data, on_success)
            )
        except Exception as exc:
            error_message = f"请求失败: {exc}"
            Clock.schedule_once(
                lambda dt: self._handle_recognition_error(error_message, on_error)
            )

    def _handle_recognition_success(self, image_path, data, on_success=None):
        self.mark_current_user_recognized()
        if callable(on_success):
            on_success(image_path, data)
            return
        self.open_recognition_result(image_path, data)

    def _handle_recognition_error(self, message, on_error=None):
        if callable(on_error):
            on_error(message)
            return
        show_toast(message)

    def open_recognition_result(self, image_path, data):
        try:
            if getattr(self, "camera_mode", "recognize") == "avatar":
                self.handle_avatar_capture(image_path)
                return
            if not self.root or not self.root.has_screen("result"):
                show_toast("识别结果页未准备好")
                return
            result_screen = self.root.get_screen("result")
            result_screen.set_result(image_path, data)
            self.root.current = "result"
        except Exception as exc:
            show_toast(f"跳转失败: {exc}")


if __name__ == "__main__":
    import traceback
    os.makedirs("photos", exist_ok=True)
    try:
        MyApp().run()
    except Exception:
        traceback.print_exc()
        input("按回车键退出")

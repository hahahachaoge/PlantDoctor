import os
from datetime import datetime
from importlib import import_module
from kivy.uix.scrollview import ScrollView

from kivy.app import App
from kivy.clock import Clock
from kivy.graphics import Color, Ellipse, Line, PopMatrix, PushMatrix, Rotate, Rectangle
from kivy.metrics import dp, sp
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.button import Button
from kivy.uix.floatlayout import FloatLayout
from kivy.uix.label import Label
from kivy.uix.screenmanager import Screen

from config import GREEN
from utils import text_style, show_toast, is_android, is_android_permission_granted
from widgets.base_widgets import IconButton, RoundedButton, CircleImage, GrayPlaceholder


class CameraScreen(Screen):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.name = "camera"
        self.camera = None
        self.camera_rotation = None
        self.capture_in_progress = False
        self._texture_check_count = 0
        self.build_ui()

    def build_ui(self):
        self.layout = FloatLayout()
        self.add_widget(self.layout)

        self.camera_container = FloatLayout(size_hint=(1, 1), pos_hint={"x": 0, "y": 0})
        self.layout.add_widget(self.camera_container)

        self.status_label = Label(
            text="", font_size=sp(14), color=(1, 1, 1, 1),
            size_hint=(0.84, None), height=dp(36),
            pos_hint={"center_x": 0.5, "top": 0.90},
            halign="center", valign="middle", **text_style(),
        )
        self.status_label.bind(size=self.status_label.setter("text_size"))
        self.layout.add_widget(self.status_label)

        self.back_btn = IconButton(
            text="<", font_size=sp(34), color=(0, 0, 0, 1),
            size_hint=(None, None), size=(dp(56), dp(56)),
            pos_hint={"x": 0.03, "center_y": 0.5},
            **text_style(),
        )
        self.back_btn.bind(on_press=self.go_back)
        self.layout.add_widget(self.back_btn)

        self.capture_btn = Button(
            text="", background_normal="", background_down="",
            background_color=(0, 0, 0, 0),
            size_hint=(None, None), size=(dp(86), dp(86)),
            pos_hint={"center_x": 0.5, "y": 0.08}, border=(0, 0, 0, 0),
        )
        self.capture_btn.bind(on_press=self.take_photo)
        self.capture_btn.bind(pos=self._update_capture_circle,
                              size=self._update_capture_circle)
        self.layout.add_widget(self.capture_btn)

        self.capture_label = Label(
            text="点击拍照", font_size=sp(12), color=(1, 1, 1, 1),
            size_hint=(0.40, None), height=dp(24),
            pos_hint={"center_x": 0.5, "y": 0.035},
            halign="center", valign="middle", **text_style(),
        )
        self.capture_label.bind(size=self.capture_label.setter("text_size"))
        self.layout.add_widget(self.capture_label)

        Clock.schedule_once(lambda dt: self._update_capture_circle(), 0)

    def _update_capture_circle(self, *_args):
        self.capture_btn.canvas.before.clear()
        with self.capture_btn.canvas.before:
            Color(0, 0, 0, 1)
            Ellipse(pos=(self.capture_btn.x - dp(4), self.capture_btn.y - dp(4)),
                    size=(self.capture_btn.width + dp(8), self.capture_btn.height + dp(8)))
            Color(1, 1, 1, 0.96)
            Ellipse(pos=self.capture_btn.pos, size=self.capture_btn.size)

    def on_pre_enter(self, *args):
        self._force_portrait_preview()
        self._request_camera_permission()
        return super().on_pre_enter(*args)

    def on_leave(self, *args):
        if self.camera:
            self.camera.play = False
        # 离开页面时停止轮询
        Clock.unschedule(self._wait_for_texture)
        return super().on_leave(*args)

    def _request_camera_permission(self):
        if not is_android():
            self._enable_camera()
            return
        try:
            permissions_module = import_module("android.permissions")
            permission_class = getattr(permissions_module, "Permission")
            check_permission_func = getattr(permissions_module, "check_permission")
            request_permissions_func = getattr(permissions_module, "request_permissions")
        except Exception as exc:
            self._show_status(f"相机权限模块加载失败: {exc}")
            return
        camera_permission = permission_class.CAMERA
        if check_permission_func(camera_permission):
            self._enable_camera()
            return

        def callback(_permissions, grants):
            if grants and grants[0]:
                Clock.schedule_once(lambda dt: self._enable_camera())
            else:
                Clock.schedule_once(lambda dt: self._show_status("未授予相机权限，无法拍照"))

        request_permissions_func([camera_permission], callback)

    def _force_portrait_preview(self):
        if not is_android():
            return
        try:
            autoclass = import_module("jnius").autoclass
            activity = autoclass("org.kivy.android.PythonActivity").mActivity
            activity_info = autoclass("android.content.pm.ActivityInfo")
            activity.setRequestedOrientation(activity_info.SCREEN_ORIENTATION_PORTRAIT)
        except Exception:
            pass

    def _layout_camera_preview(self, *_args):
        if not self.camera:
            return
        if not is_android():
            self.camera.size_hint = (1, 1)
            self.camera.pos_hint = {"x": 0, "y": 0}
            self.camera.canvas.before.clear()
            self.camera.canvas.after.clear()
            return
        from kivy.core.window import Window
        width = self.camera_container.width or Window.width
        height = self.camera_container.height or Window.height
        if width <= 0 or height <= 0:
            return
        self.camera.size_hint = (None, None)
        self.camera.size = (height, width)
        self.camera.pos = (
            self.camera_container.center_x - self.camera.width / 2,
            self.camera_container.center_y - self.camera.height / 2,
        )
        self.camera.canvas.before.clear()
        self.camera.canvas.after.clear()
        with self.camera.canvas.before:
            PushMatrix()
            self.camera_rotation = Rotate(angle=-90, origin=self.camera.center)
        with self.camera.canvas.after:
            PopMatrix()

    def _update_camera_transform(self, *_args):
        if self.camera_rotation and self.camera:
            self.camera_rotation.origin = self.camera.center

    def _ensure_camera_widget(self):
        if self.camera is not None:
            return True
        try:
            # 修复 Kivy 2.3.0 的 CameraOpenCV 缺少 fps 属性的 bug
            try:
                from kivy.core.camera.camera_opencv import CameraOpenCV
                if not hasattr(CameraOpenCV, 'fps'):
                    CameraOpenCV.fps = 30
            except Exception:
                pass

            from kivy.uix.camera import Camera
            self._force_portrait_preview()
            self.camera = Camera(
                resolution=(720, 1280), play=False, index=0,
                allow_stretch=True, keep_ratio=False,
                size_hint=(1, 1), pos_hint={"x": 0, "y": 0},
            )
            self.camera_container.clear_widgets()
            self.camera_container.add_widget(self.camera)
            self.camera.bind(pos=self._update_camera_transform,
                             size=self._update_camera_transform)
            self.camera_container.bind(pos=self._layout_camera_preview,
                                       size=self._layout_camera_preview)
            Clock.schedule_once(self._layout_camera_preview, 0)
            return True
        except Exception as exc:
            self._show_status(f"摄像头组件加载失败: {exc}")
            return False

    def _enable_camera(self):
        if not self._ensure_camera_widget():
            return
        try:
            self._force_portrait_preview()
            self._layout_camera_preview()
            self.camera.play = True
            self._show_status("摄像头启动中...")
            # 轮询等待 texture 就绪，每 0.1 秒检查一次，最多等 5 秒
            self._texture_check_count = 0
            Clock.unschedule(self._wait_for_texture)
            Clock.schedule_interval(self._wait_for_texture, 0.1)
        except Exception as exc:
            self._show_status(f"打开摄像头失败: {exc}")

    def _wait_for_texture(self, dt):
        self._texture_check_count += 1
        if self.camera and self.camera.texture:
            self._show_status("")   # texture 就绪，清空提示
            return False            # 返回 False 停止轮询
        if self._texture_check_count >= 50:  # 超过 5 秒
            self._show_status("摄像头启动超时，请检查设备是否被占用")
            return False            # 超时也停止轮询

    def take_photo(self, _instance):
        if self.capture_in_progress:
            return
        app = App.get_running_app()
        if getattr(app, "camera_mode", "recognize") == "recognize" \
                and not app.can_current_user_recognize():
            show_toast("免费用户每天限识别3次，升级VIP解锁无限次")
            return
        if not self.camera or not self.camera.play:
            self._show_status("摄像头未启动，请稍候")
            return
        if not self.camera.texture:
            self._show_status("摄像头预热中，请稍候再试")
            return
        self.capture_in_progress = True
        self.capture_btn.disabled = True
        self._show_status("正在识别...")
        Clock.schedule_once(lambda dt: self._capture_current_frame(), 0.05)

    def _build_photo_path(self):
        os.makedirs("photos", exist_ok=True)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        return os.path.abspath(os.path.join("photos", f"capture_{timestamp}.png"))

    def _capture_current_frame(self):
        image_path = self._build_photo_path()
        try:
            self.camera.export_to_png(image_path)
            app = App.get_running_app()
            if getattr(app, "camera_mode", "recognize") == "avatar":
                app.handle_avatar_capture(image_path)
                self._show_status("")
                self._finish_capture()
                return
            started = app.start_recognition_for_image(
                image_path,
                on_success=self._open_result,
                on_error=self._recognition_failed,
            )
            if not started:
                self._finish_capture()
        except Exception as exc:
            self._show_status(f"保存照片失败: {exc}")
            self._finish_capture()

    @staticmethod
    def _normalize_api_result(data):
        normalized = dict(data)
        confidence = normalized.get("confidence", 0)
        try:
            confidence = float(confidence)
        except Exception:
            confidence = 0
        if confidence > 1:
            confidence = round(confidence / 100, 4)
        normalized["confidence"] = confidence
        treatment = normalized.get("treatment")
        if isinstance(treatment, str):
            normalized["treatment"] = {"method": treatment}
        elif not isinstance(treatment, dict):
            normalized["treatment"] = {"method": normalized.get("treatment_text", "暂无防治建议")}
        normalized["pest_name"] = normalized.get("pest_name") or "未知病虫害"
        normalized["intro"] = normalized.get("intro") or "暂无简介"
        return normalized

    def _open_result(self, image_path, data):
        app = App.get_running_app()
        self._finish_capture()
        app.open_recognition_result(image_path, data)

    def _recognition_failed(self, message):
        self._show_status(message)
        self._finish_capture()

    def _finish_capture(self):
        self.capture_in_progress = False
        self.capture_btn.disabled = False

    def _show_status(self, text):
        self.status_label.text = text

    def go_back(self, _instance=None):
        app = App.get_running_app()
        self.manager.current = app.previous_before_camera or "home"


class ResultScreen(Screen):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.name = "result"
        self.photo_path = ""
        self.build_ui()

    def build_ui(self):
        self.layout = FloatLayout()
        self.add_widget(self.layout)
        with self.layout.canvas.before:
            Color(1, 1, 1, 1)
            self.bg_rect = Rectangle(pos=self.layout.pos, size=self.layout.size)
        self.layout.bind(pos=self._update_bg, size=self._update_bg)

        self.top_bar = FloatLayout(size_hint=(1, None), height=dp(88),
                                   pos_hint={"x": 0, "top": 1})
        with self.top_bar.canvas.before:
            Color(*GREEN)
            self.top_bar_rect = Rectangle(pos=self.top_bar.pos, size=self.top_bar.size)
        self.top_bar.bind(pos=self._update_top_bar, size=self._update_top_bar)
        self.layout.add_widget(self.top_bar)

        self.back_btn = IconButton(
            text="<", font_size=sp(34), color=(0, 0, 0, 1),
            size_hint=(None, None), size=(dp(56), dp(56)),
            pos_hint={"x": 0.03, "center_y": 0.5},
            **text_style(),
        )
        self.back_btn.bind(on_press=self.go_back)
        self.top_bar.add_widget(self.back_btn)

        self.name_label = Label(
            text="识别结果", font_size=sp(24), bold=True, color=(0.08, 0.08, 0.08, 1),
            size_hint=(0.88, None), height=dp(42),
            pos_hint={"center_x": 0.5, "top": 0.86},
            halign="center", valign="middle", **text_style(),
        )
        self.name_label.bind(size=self.name_label.setter("text_size"))
        self.layout.add_widget(self.name_label)

        self.photo = CircleImage(
            source="", size_hint=(None, None), size=(dp(168), dp(168)),
            pos_hint={"center_x": 0.5, "top": 0.72},
        )
        self.layout.add_widget(self.photo)

        self.placeholder = Label(
            text="", size_hint=(None, None), size=(dp(168), dp(168)),
            pos_hint={"center_x": 0.5, "top": 0.72},
        )
        with self.placeholder.canvas.before:
            Color(0, 0, 0, 1)
            self.placeholder_circle = Ellipse(pos=self.placeholder.pos,
                                              size=self.placeholder.size)
        self.placeholder.bind(pos=self._update_placeholder, size=self._update_placeholder)

        self.content_scroll = ScrollView(
            size_hint=(0.88, None), do_scroll_x=False,
            bar_width=dp(4), scroll_type=["bars", "content"],
            pos_hint={"center_x": 0.5, "y": 0.22},
        )
        self.layout.add_widget(self.content_scroll)

        self.content_box = BoxLayout(
            orientation="vertical", spacing=dp(14),
            padding=(0, dp(4), 0, dp(10)), size_hint=(1, None),
        )
        self.content_box.bind(minimum_height=self.content_box.setter("height"))
        self.content_scroll.add_widget(self.content_box)

        self.intro_label = Label(
            text="", font_size=sp(15), color=(0.12, 0.12, 0.12, 1),
            size_hint=(1, None), halign="left", valign="top", **text_style(),
        )
        self.intro_label.bind(texture_size=self._sync_intro_height,
                              width=self._sync_label_width)
        self.content_box.add_widget(self.intro_label)

        self.treatment_label = Label(
            text="", font_size=sp(15), color=(0.12, 0.12, 0.12, 1),
            size_hint=(1, None), halign="left", valign="top", **text_style(),
        )
        self.treatment_label.bind(texture_size=self._sync_treatment_height,
                                  width=self._sync_label_width)
        self.content_box.add_widget(self.treatment_label)

        self.retake_btn = Button(
            text="再拍一个", font_size=sp(18),
            background_normal="", background_down="",
            background_color=(0, 0, 0, 0), color=(1, 1, 1, 1),
            size_hint=(None, None), size=(dp(112), dp(112)),
            pos_hint={"center_x": 0.5, "y": 0.04},
            border=(0, 0, 0, 0), **text_style(),
        )
        self.retake_btn.bind(on_press=self.retake)
        self.retake_btn.bind(pos=self._update_retake_circle, size=self._update_retake_circle)
        self.layout.add_widget(self.retake_btn)

        self.layout.bind(size=self._update_content_area)
        Clock.schedule_once(lambda dt: self._update_retake_circle(), 0)
        Clock.schedule_once(lambda dt: self._update_content_area(), 0)

    def _update_bg(self, *_args):
        self.bg_rect.pos = self.layout.pos
        self.bg_rect.size = self.layout.size

    def _update_top_bar(self, *_args):
        self.top_bar_rect.pos = self.top_bar.pos
        self.top_bar_rect.size = self.top_bar.size

    def _update_placeholder(self, *_args):
        self.placeholder_circle.pos = self.placeholder.pos
        self.placeholder_circle.size = self.placeholder.size

    def _update_retake_circle(self, *_args):
        self.retake_btn.canvas.before.clear()
        with self.retake_btn.canvas.before:
            Color(*GREEN)
            Ellipse(pos=self.retake_btn.pos, size=self.retake_btn.size)

    def _update_content_area(self, *_args):
        top_limit = self.photo.y - dp(22)
        bottom_limit = self.retake_btn.top + dp(18)
        available_height = max(dp(120), top_limit - bottom_limit)
        self.content_scroll.height = available_height
        self.content_scroll.pos = (self.layout.width * 0.06, bottom_limit)

    def _sync_label_width(self, instance, _value):
        instance.text_size = (instance.width, None)

    def _sync_intro_height(self, instance, _value):
        instance.height = max(dp(70), instance.texture_size[1] + dp(8))

    def _sync_treatment_height(self, instance, _value):
        instance.height = max(dp(110), instance.texture_size[1] + dp(8))

    def set_result(self, image_path, data):
        self.photo_path = image_path
        pest_name = data.get("pest_name", "未知病虫害")
        intro = data.get("intro", "暂无简介")
        treatment = data.get("treatment", {})
        treatment_text = treatment.get("method") or data.get("treatment_text") or "暂无防治建议"
        confidence = data.get("confidence", 0)
        try:
            confidence_text = f"{float(confidence) * 100:.1f}%"
        except Exception:
            confidence_text = str(confidence)

        self.name_label.text = f"{pest_name}  置信度 {confidence_text}"
        self.intro_label.text = f"简介：{intro}"
        self.treatment_label.text = f"防治方法：{treatment_text}"
        self.content_scroll.scroll_y = 1
        Clock.schedule_once(lambda dt: self._update_content_area(), 0)

        if image_path and os.path.exists(image_path):
            if self.placeholder.parent:
                self.layout.remove_widget(self.placeholder)
            self.photo.source = image_path
            self.photo.reload()
            if self.photo.parent is None:
                self.layout.add_widget(self.photo)
        else:
            if self.photo.parent:
                self.layout.remove_widget(self.photo)
            if self.placeholder.parent is None:
                self.layout.add_widget(self.placeholder)

    def go_back(self, _instance=None):
        app = App.get_running_app()
        self.manager.current = app.previous_before_camera or "home"

    def retake(self, _instance=None):
        App.get_running_app().show_capture_menu()

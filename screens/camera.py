import json
import os
from datetime import datetime
from importlib import import_module
from kivy.uix.scrollview import ScrollView

from kivy.app import App
from kivy.clock import Clock
from kivy.core.image import Image as CoreImage
from kivy.graphics import (Color, Ellipse, Line, PopMatrix, PushMatrix,
                           Rotate, Rectangle, RoundedRectangle)
from kivy.metrics import dp, sp
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.button import Button
from kivy.uix.floatlayout import FloatLayout
from kivy.uix.label import Label
from kivy.uix.screenmanager import Screen
from kivy.uix.widget import Widget

from config import (DISEASE_INFO_PATH, DISEASE_METADATA_PATH, GREEN,
                    IMAGE_DIR)
from utils import (text_style, show_toast, open_text_popup, is_android,
                   is_android_permission_granted, bind_deferred_layout,
                   patch_opencv_camera, probe_camera_index)
from widgets.base_widgets import IconButton, RoundedButton, CircleImage, GrayPlaceholder


def _load_disease_details():
    """Load the bundled catalogue so older API deployments still show details."""
    details = {}
    try:
        with open(DISEASE_INFO_PATH, "r", encoding="utf-8") as file_obj:
            document = json.load(file_obj)
        if isinstance(document, dict):
            details = {
                key: dict(value) for key, value in document.items()
                if isinstance(value, dict)
            }
    except (OSError, ValueError, TypeError):
        pass

    try:
        with open(DISEASE_METADATA_PATH, "r", encoding="utf-8") as file_obj:
            metadata = json.load(file_obj).get("entries", {})
        for raw_class, values in metadata.items():
            if isinstance(values, dict):
                details.setdefault(raw_class, {}).update(values)
    except (OSError, ValueError, TypeError, AttributeError):
        pass
    return details


DISEASE_DETAILS = _load_disease_details()


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
        app = App.get_running_app()
        self.capture_label.text = (
            "点击扫描" if getattr(app, "camera_mode", "recognize") == "scan"
            else "点击拍照"
        )
        self._force_portrait_preview()
        self._request_camera_permission()
        return super().on_pre_enter(*args)

    def on_leave(self, *args):
        # 离开页面时停止轮询并彻底释放摄像头，避免设备被占用、
        # 也避免后台继续每帧刷新报错日志。
        Clock.unschedule(self._wait_for_texture)
        self._release_camera()
        return super().on_leave(*args)

    def _release_camera(self):
        """停止预览、释放 OpenCV 设备并销毁 Camera 控件。"""
        if not self.camera:
            return
        try:
            self.camera.play = False
        except Exception:
            pass
        try:
            core_camera = getattr(self.camera, "_camera", None)
            device = getattr(core_camera, "_device", None)
            if device is not None:
                device.release()
                core_camera._device = None
        except Exception:
            pass
        try:
            self.camera_container.remove_widget(self.camera)
        except Exception:
            pass
        self.camera = None
        self.camera_rotation = None

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
            # Windows 必须先确认 cv2 存在，再导入 Kivy Camera provider。
            # 否则 Kivy 会依次尝试 picamera / gi / opencv 并打印误导性 CRITICAL。
            if not is_android():
                try:
                    import_module("cv2")
                except ImportError:
                    self._show_status(
                        "缺少 OpenCV 相机组件，请运行：pip install opencv-python"
                    )
                    return False

            # OpenCV 5.x 与 Kivy 2.3.0 不兼容（_device 为 None，每帧报错刷屏）
            patch_opencv_camera()
            # 修复 Kivy 2.3.0 的 CameraOpenCV 缺少 fps 属性的 bug
            try:
                from kivy.core.camera.camera_opencv import CameraOpenCV
                if not hasattr(CameraOpenCV, 'fps'):
                    CameraOpenCV.fps = 30
            except Exception:
                pass

            # 桌面端先探测可用摄像头：没有设备就不再创建 Camera 控件，
            # 否则 Kivy 会每帧刷 "Couldn't get image from Camera" 把主线程拖垮
            if not is_android():
                index = probe_camera_index()
                if index is None:
                    self._show_status("未检测到可用摄像头，请改用「图片识别」上传照片")
                    return False
            else:
                index = 0

            from kivy.uix.camera import Camera
            self._force_portrait_preview()
            self.camera = Camera(
                resolution=(1280, 720), play=False, index=index,
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
            # 超时必须停掉预览：否则 Kivy 会一直按帧刷新 read() 报错
            try:
                self.camera.play = False
            except Exception:
                pass
            self._show_status("摄像头启动超时，请检查是否被其它软件占用")
            return False            # 超时也停止轮询

    def take_photo(self, _instance):
        if self.capture_in_progress:
            return
        app = App.get_running_app()
        if getattr(app, "camera_mode", "recognize") == "recognize" \
                and not app.can_current_user_recognize():
            open_text_popup(
                "今日免费次数已用完",
                "普通用户每天可免费识别 3 次。\n升级 VIP 后可不限次数使用拍照识别。",
                height=300,
            )
            return
        if not self.camera or not self.camera.play:
            self._show_status("摄像头未启动，请稍候")
            return
        if not self.camera.texture:
            self._show_status("摄像头预热中，请稍候再试")
            return
        self.capture_in_progress = True
        self.capture_btn.disabled = True
        self._show_status(
            "正在读取二维码..."
            if getattr(app, "camera_mode", "recognize") == "scan"
            else "正在识别..."
        )
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
            if getattr(app, "camera_mode", "recognize") == "scan":
                app.handle_qr_scan(image_path)
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




# ─────────────────── 识别结果页（参考 UI/7.jpg） ───────────────────

class CoverImage(Widget):
    """把图片按 cover 模式铺满控件（不变形、不裁空）。"""

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self._texture = None
        self._tex_size = (1, 1)
        self.bind(pos=self._redraw, size=self._redraw)

    def set_source(self, path):
        try:
            ci = CoreImage(path)
            self._texture = ci.texture
            self._tex_size = (ci.width or 1, ci.height or 1)
        except Exception:
            self._texture = None
        self._redraw()

    def _redraw(self, *_args):
        self.canvas.clear()
        if not self._texture:
            return
        tw, th = self._tex_size
        scale = max(self.width / tw, self.height / th)
        dw, dh = tw * scale, th * scale
        dx = self.center_x - dw / 2
        dy = self.center_y - dh / 2
        with self.canvas:
            Color(1, 1, 1, 1)
            Rectangle(texture=self._texture, pos=(dx, dy), size=(dw, dh))


class ResultScreen(Screen):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.name = "result"
        self.photo_path = ""
        self._result_data = {}
        self._top5 = []
        self.build_ui()

    # ---------------- 界面搭建 ----------------
    def build_ui(self):
        self.layout = FloatLayout()
        self.add_widget(self.layout)
        with self.layout.canvas.before:
            Color(0.96, 0.98, 0.96, 1)
            self.bg_rect = Rectangle(pos=self.layout.pos, size=self.layout.size)
        self.layout.bind(pos=self._update_bg, size=self._update_bg)

        # ① 顶部拍摄图（cover 铺满上半屏，尺寸由 _update_layout 手动控制）
        self.photo_area = CoverImage(size_hint=(None, None))
        self.layout.add_widget(self.photo_area)

        # 顶部白色圆环扫描装饰
        self.scan_ring = Widget(size_hint=(None, None))
        self.scan_ring.bind(pos=self._update_scan_ring,
                            size=self._update_scan_ring)
        self.layout.add_widget(self.scan_ring)

        # ② 图上顶栏：返回 + 标题 + 更多
        self.top_bar = FloatLayout(
            size_hint=(1, None), height=dp(72),
            pos_hint={"x": 0, "top": 1})
        with self.top_bar.canvas.before:
            Color(0, 0, 0, 0.28)
            self.top_bar_rect = Rectangle(
                pos=self.top_bar.pos, size=self.top_bar.size)
        self.top_bar.bind(pos=self._update_top_bar, size=self._update_top_bar)
        self.layout.add_widget(self.top_bar)

        self.back_btn = IconButton(
            text="<", font_size=sp(26), color=(1, 1, 1, 1),
            size_hint=(None, None), size=(dp(48), dp(48)),
            pos_hint={"x": 0.02, "center_y": 0.5}, **text_style(),
        )
        self.back_btn.bind(on_press=self.go_back)
        self.top_bar.add_widget(self.back_btn)

        self.title_label = Label(
            text="拍照智能识别", font_size=sp(19), bold=True,
            color=(1, 1, 1, 1),
            size_hint=(0.6, None), height=dp(36),
            pos_hint={"center_x": 0.5, "center_y": 0.5},
            halign="center", valign="middle", **text_style(),
        )
        self.title_label.bind(size=self.title_label.setter("text_size"))
        self.top_bar.add_widget(self.title_label)

        self.more_btn = IconButton(
            text="···", font_size=sp(22), color=(1, 1, 1, 1),
            size_hint=(None, None), size=(dp(48), dp(48)),
            pos_hint={"right": 0.98, "center_y": 0.5}, **text_style(),
        )
        self.more_btn.bind(on_press=self._on_more)
        self.top_bar.add_widget(self.more_btn)

        # ③ 白色大圆角卡片（顶部盖在图片上）
        self.card = BoxLayout(
            orientation="vertical",
            size_hint=(1, None),
            padding=(dp(16), dp(20), dp(16), dp(8)),
        )
        with self.card.canvas.before:
            Color(1, 1, 1, 1)
            self.card_bg = RoundedRectangle(
                pos=self.card.pos, size=self.card.size,
                radius=[dp(24), dp(24), 0, 0])
        self.card.bind(
            pos=lambda i, *_: setattr(self.card_bg, "pos", i.pos),
            size=lambda i, *_: setattr(self.card_bg, "size", i.size),
        )
        self.layout.add_widget(self.card)

        # 卡片内容滚动区
        self.scroll = ScrollView(do_scroll_x=False, bar_width=dp(3))
        self.card.add_widget(self.scroll)
        self.content_box = BoxLayout(
            orientation="vertical", spacing=dp(10), size_hint=(1, None))
        self.content_box.bind(minimum_height=self.content_box.setter("height"))
        self.scroll.add_widget(self.content_box)

        # ③-1 头部：左图 + 右名称/学名/置信度
        from screens.community import RoundedImage
        header = BoxLayout(size_hint=(1, None), height=dp(120), spacing=dp(14))
        self.thumb = RoundedImage(
            source="", radius=dp(14),
            size_hint=(None, None), size=(dp(120), dp(120)))
        thumb_wrap = FloatLayout(size_hint=(None, 1), width=dp(120))
        self.thumb.pos_hint = {"center_x": 0.5, "center_y": 0.5}
        thumb_wrap.add_widget(self.thumb)
        header.add_widget(thumb_wrap)

        info_col = BoxLayout(orientation="vertical", size_hint=(1, 1),
                             spacing=dp(4))
        self.name_label = Label(
            text="", font_size=sp(24), bold=True,
            color=(0.08, 0.08, 0.08, 1),
            size_hint=(1, None), height=dp(34),
            halign="left", valign="middle",
            shorten=True, shorten_from="right",
            **text_style(),
        )
        self.name_label.bind(size=self.name_label.setter("text_size"))
        info_col.add_widget(self.name_label)

        self.sci_label = Label(
            text="", font_size=sp(11), color=(0.55, 0.55, 0.55, 1),
            size_hint=(1, None), height=dp(20),
            halign="left", valign="middle",
            shorten=True, shorten_from="right",
            **text_style(),
        )
        self.sci_label.bind(size=self.sci_label.setter("text_size"))
        info_col.add_widget(self.sci_label)

        self.conf_chip = Label(
            text="", font_size=sp(13), bold=True, color=(1, 1, 1, 1),
            size_hint=(None, None), size=(dp(96), dp(26)),
            halign="center", valign="middle", **text_style(),
        )
        self.conf_chip.bind(
            texture_size=self._sync_conf_chip,
            pos=lambda i, *_: self._redraw_conf_chip())
        info_col.add_widget(self.conf_chip)
        header.add_widget(info_col)
        self.content_box.add_widget(header)

        self.content_box.add_widget(self._build_divider())

        # ③-2 信息区（界门纲目等图鉴字段暂缺，用现有接口字段呈现）
        self.section_labels = {}
        for key, title in [
            ("alias", "别名"),
            ("region", "分布地区"),
            ("feature", "形态特征"),
            ("treatment", "防治方法"),
        ]:
            self.content_box.add_widget(self._build_section_title(title))
            lbl = Label(
                text="", font_size=sp(14), color=(0.25, 0.25, 0.25, 1),
                size_hint=(1, None), halign="left", valign="top",
                **text_style(),
            )
            lbl.bind(width=self._sync_label_width,
                     texture_size=lambda inst, v, _l=lbl:
                     self._sync_dynamic_height(_l))
            self.section_labels[key] = lbl
            self.content_box.add_widget(lbl)

        # ④ 底部 Top-5 候选条
        self.chip_bar = BoxLayout(
            size_hint=(1, None), height=dp(74),
            padding=(dp(12), dp(12), dp(12), dp(12)),
        )
        with self.chip_bar.canvas.before:
            Color(1, 1, 1, 1)
            self.chip_bar_bg = Rectangle(
                pos=self.chip_bar.pos, size=self.chip_bar.size)
        self.chip_bar.bind(
            pos=lambda i, *_: setattr(self.chip_bar_bg, "pos", i.pos),
            size=lambda i, *_: setattr(self.chip_bar_bg, "size", i.size),
        )
        self.chip_scroll = ScrollView(
            do_scroll_x=True,
            do_scroll_y=False,
            scroll_type=["content", "bars"],
            bar_width=dp(4),
            bar_margin=dp(1),
            bar_color=(0.12, 0.58, 0.30, 0.85),
            bar_inactive_color=(0.72, 0.78, 0.73, 0.45),
        )
        self.chip_row = BoxLayout(
            orientation="horizontal", spacing=dp(10), size_hint=(None, 1),
            padding=(0, dp(2), 0, dp(9)),
        )
        self.chip_row.bind(minimum_width=self.chip_row.setter("width"))
        self.chip_scroll.add_widget(self.chip_row)
        self.chip_bar.add_widget(self.chip_scroll)
        self.layout.add_widget(self.chip_bar)

        bind_deferred_layout(self.layout, self._update_layout)
        Clock.schedule_once(lambda dt: self._update_layout(), 0)

    # ---------------- 小部件工厂 ----------------
    def _build_section_title(self, title):
        lbl = Label(
            text=title, font_size=sp(16), bold=True,
            color=(0.08, 0.08, 0.08, 1),
            size_hint=(1, None), height=dp(26),
            halign="left", valign="middle", **text_style(),
        )
        lbl.bind(size=lbl.setter("text_size"))
        return lbl

    def _build_divider(self):
        d = Widget(size_hint=(1, None), height=dp(1))
        with d.canvas:
            Color(0.92, 0.93, 0.92, 1)
            self._div_rect = Rectangle(pos=d.pos, size=d.size)
        d.bind(pos=lambda i, *_: setattr(self._div_rect, "pos", i.pos),
               size=lambda i, *_: setattr(self._div_rect, "size", i.size))
        return d

    def _build_chip(self, item, index):
        is_top = index == 0
        btn = Button(
            text=item.get("chinese_name", "?"),
            font_size=sp(14), bold=is_top,
            color=(1, 1, 1, 1) if is_top else (0.15, 0.45, 0.25, 1),
            background_normal="", background_down="",
            background_color=(0, 0, 0, 0),
            size_hint=(None, 1), width=max(
                dp(72), dp(28) + dp(14) * len(item.get("chinese_name", "?"))),
            **text_style(),
        )
        btn._chip_index = index
        btn.bind(pos=self._redraw_chip, size=self._redraw_chip)
        btn.bind(on_press=lambda *_: self._select_chip(index))
        return btn

    # ---------------- 绘制回调 ----------------
    def _update_bg(self, *_args):
        self.bg_rect.pos = self.layout.pos
        self.bg_rect.size = self.layout.size

    def _update_top_bar(self, *_args):
        self.top_bar_rect.pos = self.top_bar.pos
        self.top_bar_rect.size = self.top_bar.size

    def _update_scan_ring(self, *_args):
        self.scan_ring.canvas.after.clear()
        if not self.photo_area.size or self.photo_area.size == [1, 1]:
            return
        cx, cy = self.photo_area.center_x, self.photo_area.center_y + dp(30)
        with self.scan_ring.canvas.after:
            Color(1, 1, 1, 0.95)
            Line(circle=[cx, cy, dp(92)], width=dp(2.5))
            Color(1, 1, 1, 0.45)
            Line(circle=[cx, cy, dp(104)], width=dp(1.2))

    def _redraw_chip(self, inst, *_args):
        inst.canvas.before.clear()
        with inst.canvas.before:
            if inst._chip_index == self._active_chip:
                Color(*GREEN)
            else:
                Color(0.90, 0.97, 0.91, 1)
            RoundedRectangle(pos=inst.pos, size=inst.size,
                             radius=[dp(20)] * 4)

    def _sync_conf_chip(self, *_args):
        self.conf_chip.width = max(dp(96), self.conf_chip.texture_size[0] + dp(24))
        self._redraw_conf_chip()

    def _redraw_conf_chip(self, *_args):
        self.conf_chip.canvas.before.clear()
        with self.conf_chip.canvas.before:
            Color(GREEN[0], GREEN[1], GREEN[2], 0.9)
            RoundedRectangle(pos=self.conf_chip.pos, size=self.conf_chip.size,
                             radius=[dp(13)] * 4)

    def _sync_label_width(self, instance, _value):
        instance.text_size = (instance.width, None)

    def _sync_dynamic_height(self, lbl):
        lbl.height = max(dp(22), lbl.texture_size[1] + dp(6))

    # ---------------- 布局 ----------------
    def _update_layout(self, *_args):
        h = self.height
        w = self.width
        photo_h = h * 0.42
        self.photo_area.pos = (0, h - photo_h)
        self.photo_area.size = (w, photo_h)
        self.top_bar.pos = (0, h - self.top_bar.height)
        self.top_bar.size = (w, self.top_bar.height)
        self.chip_bar.pos = (0, 0)
        self.chip_bar.size = (w, self.chip_bar.height)
        card_h = h - photo_h + dp(28)
        self.card.pos = (0, self.chip_bar.height)
        self.card.size = (w, max(dp(120), card_h - self.chip_bar.height))
        self.scan_ring.pos = self.photo_area.pos
        self.scan_ring.size = self.photo_area.size
        self._update_scan_ring()

    # ---------------- 数据填充 ----------------
    def set_result(self, image_path, data):
        self.photo_path = image_path or ""
        self._result_data = data or {}
        top5 = self._result_data.get("top5") or []
        if not top5:
            top5 = [{
                "chinese_name": self._result_data.get("pest_name", "未知"),
                "raw_class": self._result_data.get("raw_class", ""),
                "confidence": self._result_data.get("confidence", 0),
            }]

        # Merge the bundled catalogue into every candidate.  This both supports
        # old servers and makes candidate chips show their own matching details.
        self._top5 = []
        for index, candidate in enumerate(top5):
            item = dict(candidate)
            raw_class = item.get("raw_class", "")
            bundled = DISEASE_DETAILS.get(raw_class, {})
            enriched = dict(bundled)
            enriched.update(item)
            if index == 0:
                treatment = self._result_data.get("treatment", {}) or {}
                if isinstance(treatment, dict):
                    result_method = treatment.get("method")
                else:
                    result_method = treatment
                first_values = {
                    "intro": self._result_data.get("intro"),
                    "method": result_method or self._result_data.get("treatment_text"),
                    "alias": self._result_data.get("alias"),
                    "region": self._result_data.get("region"),
                }
                for key, value in first_values.items():
                    if value:
                        enriched[key] = value
            self._top5.append(enriched)

        # 顶部大图始终用用户上传/相机拍摄的图片
        if self.photo_path and os.path.exists(self.photo_path):
            self.photo_area.set_source(self.photo_path)
        # 缩略图优先使用系统内置示例图，没有才回退到上传照片
        first_item = self._top5[0] if self._top5 else {}
        thumb_source = self._builtin_image_path(
            first_item.get("chinese_name") or self._result_data.get("pest_name", "")
        )
        if not thumb_source and self.photo_path and os.path.exists(self.photo_path):
            thumb_source = self.photo_path
        if thumb_source:
            self.thumb.set_source(thumb_source)
        # 重建候选 chips
        self.chip_row.clear_widgets()
        self._chips = []
        for i, item in enumerate(self._top5[:5]):
            chip = self._build_chip(item, i)
            self._chips.append(chip)
            self.chip_row.add_widget(chip)

        # 每次打开新结果都从第一项开始，用户可向左拖动内容查看右侧候选。
        self.chip_scroll.scroll_x = 0
        self._select_chip(0)
        self.scroll.scroll_y = 1

    def _builtin_image_path(self, chinese_name):
        """按中文名查找系统内置示例图（image/pest_<中文名>.png/jpg）。"""
        if not chinese_name or not IMAGE_DIR:
            return None
        base = os.path.join(IMAGE_DIR, f"pest_{chinese_name}")
        for ext in (".png", ".jpg", ".jpeg", ".webp"):
            path = base + ext
            if os.path.exists(path):
                return path
        # 兼容"芒果象甲危害"这类带"危害"后缀的命名
        if chinese_name.endswith("危害"):
            return self._builtin_image_path(chinese_name[:-2])
        return None

    def _select_chip(self, index):
        self._active_chip = index
        for i, chip in enumerate(getattr(self, "_chips", [])):
            chip.color = (1, 1, 1, 1) if i == index else (0.15, 0.45, 0.25, 1)
            chip.bold = i == index
            self._redraw_chip(chip)

        item = self._top5[index]
        name = item.get("chinese_name", "未知病虫害")
        raw = item.get("raw_class", "")
        conf = item.get("confidence", 0)
        try:
            conf_v = float(conf)
            if conf_v <= 1:
                conf_v *= 100
            conf_text = f"置信度 {conf_v:.1f}%"
        except Exception:
            conf_text = f"置信度 {conf}"

        self.name_label.text = name
        self.sci_label.text = f"学名 {raw}" if raw else ""
        self.conf_chip.text = conf_text
        # 切换候选时，缩略图也优先用系统示例图
        thumb_source = self._builtin_image_path(name)
        if not thumb_source and self.photo_path and os.path.exists(self.photo_path):
            thumb_source = self.photo_path
        if thumb_source:
            self.thumb.set_source(thumb_source)

        feature = item.get("intro") or "暂无形态描述资料"
        treatment = item.get("treatment", {}) or {}
        if isinstance(treatment, dict):
            treatment = treatment.get("method", "")
        treat = item.get("method") or treatment or "暂无防治建议"
        alias = item.get("alias") or "暂无经核实的常用别名"
        region = item.get("region") or "暂无经核实的分布资料"

        self.section_labels["feature"].text = feature
        self.section_labels["treatment"].text = treat
        self.section_labels["alias"].text = alias
        self.section_labels["region"].text = region

    def _on_more(self, *_args):
        App.get_running_app().show_capture_menu()

    def go_back(self, _instance=None):
        app = App.get_running_app()
        self.manager.current = app.previous_before_camera or "home"

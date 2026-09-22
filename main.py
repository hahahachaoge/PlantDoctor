import os
import threading
from importlib import import_module

# Let SDL show the system IME composition/candidate window on desktop.
os.environ.setdefault("SDL_IME_SHOW_UI", "1")

#os.environ.setdefault("KIVY_NO_FILELOG", "1")
#os.environ.setdefault("KIVY_NO_CONSOLELOG", "1")

from kivy.app import App
from kivy.clock import Clock
from kivy.core.window import Window
from kivy.metrics import dp
from kivy.properties import ObjectProperty
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.button import Button
from kivy.uix.label import Label
from kivy.uix.modalview import ModalView
from kivy.uix.screenmanager import ScreenManager

from config import GREEN
from database.user_db import USER_DB
from database.store_db import STORE_DB
from utils import (text_style, show_toast, open_text_popup, is_android, is_android_permission_granted,
                   register_chinese_font, _update_popup_rect, patch_opencv_camera,
                   ensure_md_theme)
from widgets.base_widgets import RoundedButton
from screens.auth import LoginScreen, RegisterScreen
from screens.home import HomeScreen
from screens.farming_plan import FarmingPlanScreen
from screens.community import CommunityScreen, CommunityDetailScreen
from screens.store import StoreScreen, StoreCategoryScreen, PesticideDetailScreen
from screens.mypage import MyPageScreen
from screens.account_pages import (
    CustomerServiceScreen, FavoriteScreen, FeedbackScreen,
    NotificationScreen, OrderScreen, ProfileScreen, SettingsScreen,
)
from screens.encyclopedia import EncyclopediaScreen, PestDetailScreen
from screens.misc import MapDataScreen, MapScreen
from screens.camera import CameraScreen, ResultScreen
from screens.qr_scanner import QRScannerScreen
from screens.search_results import SearchResultsScreen


register_chinese_font()
# This compatibility patch targets Kivy's desktop OpenCV provider.  Importing
# cv2 while Android is still creating the SDL surface eagerly loads the whole
# native OpenCV stack and can race the Android 16 window/splash transition.
# Android initializes its camera provider lazily when the camera page opens.
if not is_android():
    try:
        patch_opencv_camera()
    except Exception:
        pass
Window.softinput_mode = "below_target"
if not is_android():
    Window.size = (360, 800)


class MyApp(App):
    ANDROID_IMAGE_PICK_REQUEST = 0x5044
    previous_before_camera = "home"
    current_user = None
    camera_mode = "recognize"
    # KivyMD 控件（MDDatePicker 等）通过 app.theme_cls 取主题，这里单独挂一个，
    # 主 App 仍然继承 kivy.app.App 以保持原有结构不变。
    theme_cls = ObjectProperty()

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self._android_image_after_action = None
        self._android_image_result_handler = None
        self._android_image_result_bound = False
        self._android_image_picker_active = False
        self._pending_camera_after_action = None

    def on_pause(self):
        # The system photo picker temporarily backgrounds the SDL activity.
        # Returning True keeps Kivy alive until Android delivers its result.
        return True

    def build(self):
        import traceback
        if self.theme_cls is None:
            try:
                self.theme_cls = ensure_md_theme()
            except Exception:
                traceback.print_exc()
        try:
            sm = ScreenManager()
            sm.add_widget(LoginScreen())
            sm.add_widget(RegisterScreen())
            sm.add_widget(HomeScreen())
            sm.add_widget(FarmingPlanScreen())
            sm.add_widget(CommunityScreen())
            sm.add_widget(CommunityDetailScreen())
            sm.add_widget(StoreScreen())
            sm.add_widget(StoreCategoryScreen())
            sm.add_widget(FavoriteScreen())
            sm.add_widget(OrderScreen())
            sm.add_widget(EncyclopediaScreen())
            sm.add_widget(PestDetailScreen())
            sm.add_widget(MyPageScreen())
            sm.add_widget(SettingsScreen())
            sm.add_widget(NotificationScreen())
            sm.add_widget(ProfileScreen())
            sm.add_widget(FeedbackScreen())
            sm.add_widget(CustomerServiceScreen())
            sm.add_widget(MapScreen())
            sm.add_widget(MapDataScreen())
            sm.add_widget(CameraScreen())
            sm.add_widget(ResultScreen())
            sm.add_widget(QRScannerScreen())
            sm.add_widget(SearchResultsScreen())
            sm.add_widget(PesticideDetailScreen())
            sm.current = "login"
            # 启动后台自动发现服务器
            Clock.schedule_once(lambda dt: self._start_server_discovery(), 1)
            return sm
        except Exception:
            with open("crash.log", "w", encoding="utf-8") as f:
                traceback.print_exc(file=f)
            raise



    def _start_server_discovery(self):
        from config import get_api_base_url, set_api_base_url
        from discovery import discover_server
        # 已有缓存地址就先用缓存，同时后台刷新
        show_toast("正在搜索服务器...")
        discover_server(
            timeout=5,
            on_found=self._on_server_found,
            on_timeout=self._on_server_timeout,
        )
        # 广播找不到时，顺手校验/回退到本机服务，避免用着旧地址一直超时
        def verify():
            base = self._resolve_api_base()
            print("[server] 当前识别服务地址:", base)
        threading.Thread(target=verify, daemon=True).start()

    def _on_server_found(self, url):
        from config import set_api_base_url
        def update(dt):
            set_api_base_url(url)
            show_toast("已连接服务器")
        Clock.schedule_once(update, 0)

    def _on_server_timeout(self):
        def update(dt):
            from config import get_api_base_url
            if get_api_base_url() != "http://192.168.0.101:8000":
                # 有缓存地址，静默失败
                return
            show_toast("未找到服务器，请确认服务器已启动且在同一WiFi下")
        Clock.schedule_once(update, 0)



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

    def handle_camera_callback(self, image_path):
        callback = self._pending_camera_after_action
        self._pending_camera_after_action = None
        self.camera_mode = "recognize"
        return_screen = self.previous_before_camera or "home"
        if self.root and self.root.has_screen(return_screen):
            self.root.current = return_screen
        if callable(callback):
            try:
                callback("camera", image_path)
            except Exception as exc:
                import traceback
                traceback.print_exc()
                show_toast(f"处理照片失败: {exc}")

    def open_qr_scanner(self, return_screen=None):
        scanner = self.root.get_screen("qr_scanner")
        scanner.return_screen = return_screen or self.root.current or "home"
        self.root.current = "qr_scanner"

    def handle_qr_scan(self, image_path):
        scanner = self.root.get_screen("qr_scanner")
        self.root.current = "qr_scanner"
        scanner.scan_image(image_path, source="相机")

    def show_capture_menu(self, after_action=None):
        popup = ModalView(size_hint=(0.82, None), height=dp(228),
                  background="", background_color=(0, 0, 0, 0),
                  overlay_color=(0, 0, 0, 0.45))
        content = BoxLayout(orientation="vertical", spacing=dp(12), padding=dp(14))
        with content.canvas.before:
            from kivy.graphics import Color, RoundedRectangle
            Color(1, 1, 1, 1)
            bg_rect = RoundedRectangle(pos=content.pos, size=content.size, radius=[dp(16)] * 4)
        content.bind(pos=lambda i, *_: _update_popup_rect(i, bg_rect),
                     size=lambda i, *_: _update_popup_rect(i, bg_rect))
        title_label = Label(
            text="选择识别方式", font_size=dp(18), color=(0.08, 0.08, 0.08, 1),
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
        popup.add_widget(content)
        popup.open()

    def _open_camera_from_menu(self, popup, after_action=None):
        popup.dismiss()
        if is_android() and not is_android_permission_granted("android.permission.CAMERA"):
            show_toast("相机使用失败")
            return
        if self.root.current != "result":
            self.previous_before_camera = self.root.current
        if callable(after_action):
            self._pending_camera_after_action = after_action
            self.camera_mode = "callback"
        else:
            self._pending_camera_after_action = None
            self.camera_mode = "recognize"
        self.root.current = "camera"

    def _open_photo_from_menu(self, popup, after_action=None):
        if popup is not None:
            popup.dismiss()

        if is_android():
            self.camera_mode = "recognize"
            # Scoped-storage Android versions must use the system document
            # picker.  Scanning the private Python bundle with FileChooser can
            # terminate SDL on Android 16.
            Clock.schedule_once(
                lambda dt, callback=after_action:
                    self._open_android_image_picker(callback),
                0.08,
            )
        else:
            # Windows/PC：调用系统原生文件对话框
            self.camera_mode = "recognize"
            self._open_photo_native_dialog(after_action)

    def _ensure_android_image_result_handler(self):
        if self._android_image_result_bound:
            return
        activity_module = import_module("android.activity")
        # Keep one stable bound-method object for the whole app lifetime.
        self._android_image_result_handler = \
            self._on_android_image_activity_result
        activity_module.bind(
            on_activity_result=self._android_image_result_handler)
        self._android_image_result_bound = True

    def _open_android_image_picker(self, after_action=None):
        if self._android_image_picker_active:
            show_toast("请先完成当前图片选择")
            return
        try:
            autoclass = import_module("jnius").autoclass
            self._ensure_android_image_result_handler()
            Intent = autoclass("android.content.Intent")
            PythonActivity = autoclass("org.kivy.android.PythonActivity")

            intent = Intent()
            intent.setAction(Intent.ACTION_OPEN_DOCUMENT)
            intent.addCategory(Intent.CATEGORY_OPENABLE)
            intent.setType("image/*")
            intent.addFlags(Intent.FLAG_GRANT_READ_URI_PERMISSION)

            self._android_image_after_action = after_action
            self._android_image_picker_active = True
            PythonActivity.mActivity.startActivityForResult(
                intent, self.ANDROID_IMAGE_PICK_REQUEST)
        except Exception as exc:
            import traceback
            traceback.print_exc()
            self._android_image_picker_active = False
            self._android_image_after_action = None
            show_toast(f"打开系统相册失败: {exc}")

    def _on_android_image_activity_result(
            self, request_code, result_code, result_intent):
        if int(request_code) != self.ANDROID_IMAGE_PICK_REQUEST:
            return

        self._android_image_picker_active = False
        after_action = self._android_image_after_action
        self._android_image_after_action = None
        uri_text = None
        try:
            if int(result_code) == -1 and result_intent is not None:
                uri = result_intent.getData()
                if uri is not None:
                    uri_text = str(uri.toString())
        except Exception:
            import traceback
            traceback.print_exc()

        # Do not retain Java local references after this callback returns.
        Clock.schedule_once(
            lambda dt, value=uri_text, callback=after_action:
                self._consume_android_image_result(value, callback),
            0,
        )

    def _consume_android_image_result(self, uri_text, after_action=None):
        if not uri_text:  # The user cancelled the picker.
            return

        def copy_in_background():
            try:
                local_path = self._copy_android_uri_to_private(uri_text)
            except Exception as exc:
                import traceback
                traceback.print_exc()
                message = f"读取所选图片失败: {exc}"
                Clock.schedule_once(
                    lambda dt, text=message: show_toast(text), 0)
                return
            Clock.schedule_once(
                lambda dt, path=local_path, callback=after_action:
                    self._on_native_file_selected(path, callback),
                0,
            )

        threading.Thread(target=copy_in_background, daemon=True).start()

    def _copy_android_uri_to_private(self, uri_text):
        """Copy a granted content URI into app-private storage in Java."""
        import mimetypes
        import uuid

        autoclass = import_module("jnius").autoclass
        PythonActivity = autoclass("org.kivy.android.PythonActivity")
        Uri = autoclass("android.net.Uri")
        FileOutputStream = autoclass("java.io.FileOutputStream")
        Channels = autoclass("java.nio.channels.Channels")
        BuildVersion = autoclass("android.os.Build$VERSION")

        resolver = PythonActivity.mActivity.getContentResolver()
        uri = Uri.parse(uri_text)
        mime_type = str(resolver.getType(uri) or "").lower()
        suffix = {
            "image/jpeg": ".jpg",
            "image/jpg": ".jpg",
            "image/png": ".png",
            "image/webp": ".webp",
            "image/bmp": ".bmp",
        }.get(mime_type)
        if not suffix:
            guessed_suffix = mimetypes.guess_extension(mime_type) \
                if mime_type else None
            allowed_suffixes = {".jpg", ".jpeg", ".png", ".webp", ".bmp"}
            suffix = guessed_suffix \
                if guessed_suffix in allowed_suffixes else ".jpg"

        import_dir = os.path.join(self.user_data_dir, "imports")
        os.makedirs(import_dir, exist_ok=True)
        final_path = os.path.join(import_dir, uuid.uuid4().hex + suffix)
        partial_path = final_path + ".part"
        source = None
        output = None
        source_channel = None
        output_channel = None
        copied = 0

        try:
            try:
                source = resolver.openInputStream(uri)
                if source is None:
                    raise OSError("系统未返回可读取的图片流")
                output = FileOutputStream(partial_path)

                if int(BuildVersion.SDK_INT) >= 29:
                    FileUtils = autoclass("android.os.FileUtils")
                    copied = int(FileUtils.copy(source, output))
                else:
                    source_channel = Channels.newChannel(source)
                    output_channel = output.getChannel()
                    position = 0
                    block_size = 16 * 1024 * 1024
                    while True:
                        moved = int(output_channel.transferFrom(
                            source_channel, position, block_size))
                        if moved <= 0:
                            break
                        position += moved
                    copied = position
                output.flush()
            finally:
                for closeable in (
                        output_channel, source_channel, output, source):
                    if closeable is not None:
                        try:
                            closeable.close()
                        except Exception:
                            pass

            if copied <= 0:
                raise OSError("所选图片为空")
            os.replace(partial_path, final_path)
            return final_path
        except Exception:
            try:
                os.remove(partial_path)
            except OSError:
                pass
            raise

    @staticmethod
    def _ask_image_path():
        """弹出系统文件对话框并返回选中的图片路径（可能返回空字符串）。"""
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
            initialdir=MyApp._get_default_photo_dir_static(),
        )
        root.destroy()
        return file_path

    @staticmethod
    def _get_default_photo_dir_static():
        candidates = [
            os.path.join(os.path.expanduser("~"), "Pictures"),
            os.path.join(os.path.expanduser("~"), "图片"),
            os.path.join(os.path.expanduser("~"), "Desktop"),
            os.path.expanduser("~"),
        ]
        return next((p for p in candidates if os.path.isdir(p)),
                    os.path.expanduser("~"))

    def _open_photo_native_dialog(self, after_action=None):
        """PC 端使用系统原生文件对话框"""

        def on_picked(file_path):
            if file_path:
                Clock.schedule_once(
                    lambda dt: self._on_native_file_selected(file_path, after_action))

        def pick_in_thread():
            try:
                file_path = self._ask_image_path()
            except Exception as exc:
                # tkinter 在子线程里偶尔会失败（"main thread is not in main loop"），
                # 此时退回主线程再试一次，避免用户点了没反应
                print("[album] 子线程打开文件对话框失败:", exc)
                Clock.schedule_once(lambda dt: pick_in_main_thread())
                return
            on_picked(file_path)

        def pick_in_main_thread(*_args):
            try:
                file_path = self._ask_image_path()
            except Exception as exc:
                print("[album] 主线程打开文件对话框失败:", exc)
                show_toast(f"打开文件对话框失败: {exc}")
                return
            on_picked(file_path)

        # 先尝试在子线程打开，避免阻塞 Kivy 主线程
        threading.Thread(target=pick_in_thread, daemon=True).start()

    def _on_native_file_selected(self, image_path, after_action=None):
        if self.root.current != "result":
            self.previous_before_camera = self.root.current
        if callable(after_action):
            try:
                after_action("album", image_path)
            except Exception as exc:
                import traceback
                traceback.print_exc()
                show_toast(f"处理图片失败: {exc}")
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

    # ---------------- 识别中的加载提示 ----------------
    def _show_loading(self, text="识别中，请稍候..."):
        self._hide_loading()
        try:
            popup = ModalView(size_hint=(None, None), size=(dp(190), dp(96)),
                              background="", background_color=(0, 0, 0, 0),
                              overlay_color=(0, 0, 0, 0.25),
                              auto_dismiss=False)
            box = BoxLayout(orientation="vertical", padding=dp(14), spacing=dp(6))
            with box.canvas.before:
                from kivy.graphics import Color, RoundedRectangle
                Color(1, 1, 1, 1)
                bg = RoundedRectangle(pos=box.pos, size=box.size, radius=[dp(14)] * 4)
            box.bind(pos=lambda i, *_: _update_popup_rect(i, bg),
                     size=lambda i, *_: _update_popup_rect(i, bg))
            label = Label(text=text, font_size=dp(15), color=(0.15, 0.15, 0.15, 1),
                          halign="center", valign="middle", **text_style())
            label.bind(size=label.setter("text_size"))
            box.add_widget(label)
            popup.add_widget(box)
            popup.open()
            self._loading_popup = popup
        except Exception:
            self._loading_popup = None

    def _hide_loading(self):
        popup = getattr(self, "_loading_popup", None)
        if popup is not None:
            try:
                popup.dismiss()
            except Exception:
                pass
        self._loading_popup = None

    def recognize_image_from_file(self, image_path):
        started = self.start_recognition_for_image(
            image_path,
            on_success=self.open_recognition_result,
            on_error=lambda msg: show_toast(msg),
        )
        if started:
            self._show_loading("识别中，请稍候...")

    def start_recognition_for_image(self, image_path, on_success=None, on_error=None):
        if not self.can_current_user_recognize():
            open_text_popup(
                "今日免费次数已用完",
                "普通用户每天可免费识别 3 次。\n升级 VIP 后可不限次数使用拍照识别。",
                height=300,
            )
            return False
        threading.Thread(
            target=self._do_recognize_image,
            args=(image_path, on_success, on_error),
            daemon=True,
        ).start()
        return True

    @staticmethod
    def _probe_alive(base_url, timeout=2.5):
        """探测某个地址上的识别服务是否真的能连通（GET / 有响应即视为可用）。"""
        try:
            requests = import_module("requests")
            session = requests.Session()
            session.trust_env = False           # 不走系统代理
            response = session.get(
                base_url.rstrip("/") + "/",
                timeout=(timeout, timeout),
                proxies={"http": None, "https": None},
            )
            return response.status_code < 500
        except Exception:
            return False

    def _resolve_api_base(self):
        """挑一个真正能连上的识别服务地址。

        常见问题：api_url.txt 里缓存的是旧的局域网地址（例如 192.168.0.106:8000），
        但服务这次就跑在本机 127.0.0.1:8000 上，于是请求一直超时，
        界面上表现为「选完图片点识别，什么都没发生」。
        这里先验证缓存地址，不通就回退本机地址，并把可用地址写回缓存。
        """
        from config import get_api_base_url, set_api_base_url
        cached = (get_api_base_url() or "").rstrip("/")
        candidates = [cached]
        for item in ("http://127.0.0.1:8000", "http://localhost:8000"):
            if item not in candidates:
                candidates.append(item)
        for base in candidates:
            if not base:
                continue
            if self._probe_alive(base):
                if base != cached:
                    set_api_base_url(base)
                    print(f"[server] 缓存地址 {cached} 不可用，已切换到 {base}")
                return base
        return cached

    def _do_recognize_image(self, image_path, on_success=None, on_error=None):
        try:
            requests = import_module("requests")
            api_base_url = self._resolve_api_base()
            url = f"{api_base_url}/predict"
            print(f"[recognize] POST {url} <- {image_path}")
            # 局域网地址必须直连：requests 默认会读取系统代理（Clash/Charles/
            # 抓包软件都会设 HTTP_PROXY），把内网请求发给代理导致一直超时、
            # 界面上表现为"点了识别却什么都没发生"。这里显式禁用代理。
            session = requests.Session()
            session.trust_env = False
            with open(image_path, "rb") as f:
                response = session.post(
                    url,
                    files={"file": (os.path.basename(image_path), f, "image/png")},
                    timeout=(6, 30),          # 连接 6s / 读取 30s
                    proxies={"http": None, "https": None},
                )
            print(f"[recognize] response {response.status_code}")
            if response.status_code != 200:
                err_msg = f"识别服务返回异常: {response.status_code}（{api_base_url}）"
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
            import traceback
            traceback.print_exc()
            # 连接类异常给出可操作的提示，而不是干巴巴的英文堆栈
            name = type(exc).__name__
            if "Connect" in name or "Timeout" in name or "Proxy" in name:
                base = ""
                try:
                    from config import get_api_base_url
                    base = get_api_base_url()
                except Exception:
                    pass
                error_message = (f"连不上识别服务器 {base}\n"
                                 "请确认后端已启动、且和本机在同一网络")
            else:
                error_message = f"请求失败: {exc}"
            Clock.schedule_once(
                lambda dt: self._handle_recognition_error(error_message, on_error)
            )

    def _handle_recognition_success(self, image_path, data, on_success=None):
        self._hide_loading()
        self.mark_current_user_recognized()
        if callable(on_success):
            on_success(image_path, data)
            return
        self.open_recognition_result(image_path, data)

    def _handle_recognition_error(self, message, on_error=None):
        self._hide_loading()
        if callable(on_error):
            on_error(message)
            return
        show_toast(message)

    def open_recognition_result(self, image_path, data):
        try:
            self._hide_loading()
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
        if not is_android():
            input("按回车键退出")

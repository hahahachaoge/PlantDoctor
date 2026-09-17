import os
import random

from kivy.app import App
from kivy.clock import Clock
from kivy.graphics import Color, Rectangle, RoundedRectangle, Ellipse
from kivy.metrics import dp, sp
from kivy.uix.behaviors import ButtonBehavior
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.button import Button
from kivy.uix.floatlayout import FloatLayout
from kivy.uix.image import Image as KivyImage
from kivy.uix.label import Label
from kivy.uix.popup import Popup
from kivy.uix.screenmanager import Screen
from kivy.uix.textinput import TextInput
from kivy.uix.togglebutton import ToggleButton
from kivy.uix.widget import Widget

from config import GREEN, IMAGE_DIR
from database.user_db import USER_DB
from utils import text_style, show_toast, save_avatar_image, _update_popup_rect
from widgets.base_widgets import (
    IconButton, UnderlineLabel, RoundedButton, GrayPlaceholder, CircleImage,
)


class LoginScreen(Screen):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.name = "login"
        self.build_ui()

    def build_ui(self):
        self.layout = FloatLayout()
        self.add_widget(self.layout)

        # 渐变绿色背景
        with self.layout.canvas.before:
            Color(0.60, 0.88, 0.60, 1)
            self.bg_rect_top = Rectangle(pos=self.layout.pos, size=self.layout.size)
        with self.layout.canvas.before:
            Color(0.20, 0.65, 0.30, 1)
            self.bg_rect_bottom = Rectangle(
                pos=self.layout.pos,
                size=(self.layout.width, self.layout.height * 0.5),
            )
        self.layout.bind(pos=self._update_bg, size=self._update_bg)

        # 头像区域
        self.avatar_wrap = FloatLayout(
            size_hint=(None, None), size=(dp(120), dp(120)),
            pos_hint={"center_x": 0.5, "top": 0.88},
        )
        default_avatar = os.path.join(IMAGE_DIR, "nongming.png")
        self.avatar_image = CircleImage(
            source=default_avatar if os.path.exists(default_avatar) else "",
            size_hint=(None, None), size=(dp(120), dp(120)),
            allow_stretch=True, keep_ratio=False,
        )
        self.avatar_image.pos_hint = {"center_x": 0.5, "center_y": 0.5}
        self.avatar_placeholder = GrayPlaceholder(
            radius=1, size_hint=(None, None), size=(dp(120), dp(120)),
        )
        self.avatar_placeholder.pos_hint = {"center_x": 0.5, "center_y": 0.5}

        if os.path.exists(default_avatar):
            self.avatar_wrap.add_widget(self.avatar_image)
        else:
            self.avatar_wrap.add_widget(self.avatar_placeholder)
        self.layout.add_widget(self.avatar_wrap)

        # 昵称
        self.nick_label = Label(
            text="欢迎使用农智云警小程序",
            font_size=sp(18), bold=True,
            color=(1, 1, 1, 1),
            size_hint=(0.9, None), height=dp(30),
            pos_hint={"center_x": 0.5, "top": 0.67},
            halign="center", valign="middle", **text_style(),
        )
        self.nick_label.bind(size=self.nick_label.setter("text_size"))
        self.layout.add_widget(self.nick_label)

        # 白色圆角卡片
        card = FloatLayout(
            size_hint=(1, None), height=dp(420),
            pos_hint={"x": 0, "y": 0},
        )
        with card.canvas.before:
            Color(1, 1, 1, 1)
            self.card_rect = RoundedRectangle(
                pos=card.pos, size=card.size,
                radius=[dp(28), dp(28), 0, 0],
            )
        card.bind(
            pos=lambda i, *_: setattr(self.card_rect, "pos", i.pos),
            size=lambda i, *_: setattr(self.card_rect, "size", i.size),
        )
        self.layout.add_widget(card)

        # 登录/注册 Tab
        tab_box = BoxLayout(
            size_hint=(0.88, None), height=dp(48),
            pos_hint={"center_x": 0.5, "top": 0.98},
            spacing=dp(24),
        )
        self.login_tab = Button(
            text="登录", font_size=sp(22), bold=True,
            color=GREEN,
            background_normal="", background_down="",
            background_color=(0, 0, 0, 0),
            size_hint=(None, 1), width=dp(72),
            **text_style(),
        )
        self.login_tab.bind(pos=self._update_login_tab_underline,
                            size=self._update_login_tab_underline)
        tab_box.add_widget(self.login_tab)

        self.register_tab = Button(
            text="注册", font_size=sp(18),
            color=(0.55, 0.55, 0.55, 1),
            background_normal="", background_down="",
            background_color=(0, 0, 0, 0),
            size_hint=(None, 1), width=dp(72),
            **text_style(),
        )
        self.register_tab.bind(on_press=self.open_register)
        tab_box.add_widget(self.register_tab)
        tab_box.add_widget(Widget())
        card.add_widget(tab_box)

        # 账号输入框
        username_wrap = BoxLayout(
            size_hint=(0.88, None), height=dp(54),
            pos_hint={"center_x": 0.5, "top": 0.84},
        )
        with username_wrap.canvas.before:
            Color(0.94, 0.94, 0.94, 1)
            self.username_bg = RoundedRectangle(
                pos=username_wrap.pos, size=username_wrap.size,
                radius=[dp(27)] * 4,
            )
        username_wrap.bind(
            pos=lambda i, *_: setattr(self.username_bg, "pos", i.pos),
            size=lambda i, *_: setattr(self.username_bg, "size", i.size),
        )
        user_icon = Label(
            text="👤", font_size=sp(18),
            size_hint=(None, 1), width=dp(48),
            halign="center", valign="middle",
        )
        self.username_input = TextInput(
            hint_text="请输入账号/手机号码",
            multiline=False, input_type="text",
            background_normal="", background_active="",
            background_color=(0, 0, 0, 0),
            foreground_color=(0.12, 0.12, 0.12, 1),
            hint_text_color=(0.65, 0.65, 0.65, 1),
            cursor_color=(0.12, 0.12, 0.12, 1),
            padding=(0, dp(14), dp(14), dp(14)),
            font_size=sp(15), **text_style(),
        )
        username_wrap.add_widget(user_icon)
        username_wrap.add_widget(self.username_input)
        card.add_widget(username_wrap)

        # 密码输入框
        password_wrap = BoxLayout(
            size_hint=(0.88, None), height=dp(54),
            pos_hint={"center_x": 0.5, "top": 0.70},
        )
        with password_wrap.canvas.before:
            Color(0.94, 0.94, 0.94, 1)
            self.password_bg = RoundedRectangle(
                pos=password_wrap.pos, size=password_wrap.size,
                radius=[dp(27)] * 4,
            )
        password_wrap.bind(
            pos=lambda i, *_: setattr(self.password_bg, "pos", i.pos),
            size=lambda i, *_: setattr(self.password_bg, "size", i.size),
        )
        lock_icon = Label(
            text="🔒", font_size=sp(18),
            size_hint=(None, 1), width=dp(48),
            halign="center", valign="middle",
        )
        self.password_input = TextInput(
            hint_text="请输入密码",
            multiline=False, password=True,
            background_normal="", background_active="",
            background_color=(0, 0, 0, 0),
            foreground_color=(0.12, 0.12, 0.12, 1),
            hint_text_color=(0.65, 0.65, 0.65, 1),
            cursor_color=(0.12, 0.12, 0.12, 1),
            padding=(0, dp(14), dp(14), dp(14)),
            font_size=sp(15),
            keyboard_suggestions=False, **text_style(),
        )
        password_wrap.add_widget(lock_icon)
        password_wrap.add_widget(self.password_input)
        card.add_widget(password_wrap)

        # 短信快捷登录提示
        sms_hint = UnderlineLabel(
            text="[u]使用短信验证码快捷登录 >[/u]",
            font_size=sp(13), color=(0.55, 0.55, 0.55, 1),
            size_hint=(0.88, None), height=dp(28),
            pos_hint={"center_x": 0.5, "top": 0.57},
            halign="right", valign="middle", **text_style(),
        )
        sms_hint.bind(size=sms_hint.setter("text_size"))
        sms_hint.bind(on_press=self.open_sms_login)
        card.add_widget(sms_hint)

        # 登录按钮
        self.login_btn = RoundedButton(
            text="登  录",
            color=(1, 1, 1, 1),
            font_size=sp(20),
            bold=True,
            radius=dp(27),
            size_hint=(0.88, None),
            height=dp(54),
            pos_hint={"center_x": 0.5, "top": 0.47},
            **text_style(),
        )
        self.login_btn.bind(on_press=self.login)
        card.add_widget(self.login_btn)

        # 第三方登录分隔线
        divider_box = BoxLayout(
            size_hint=(0.88, None), height=dp(28),
            pos_hint={"center_x": 0.5, "top": 0.32},
            spacing=dp(8),
        )
        left_line = Widget(size_hint=(1, None), height=dp(1))
        divider_label = Label(
            text="第三方登录", font_size=sp(13),
            color=(0.55, 0.55, 0.55, 1),
            size_hint=(None, 1), width=dp(80),
            halign="center", valign="middle", **text_style(),
        )
        right_line = Widget(size_hint=(1, None), height=dp(1))

        def draw_line(instance, *_):
            instance.canvas.clear()
            with instance.canvas:
                Color(0.72, 0.72, 0.72, 1)
                Rectangle(
                    pos=(instance.x, instance.center_y),
                    size=(instance.width, dp(1)),
                )

        left_line.bind(pos=draw_line, size=draw_line)
        right_line.bind(pos=draw_line, size=draw_line)
        divider_box.add_widget(left_line)
        divider_box.add_widget(divider_label)
        divider_box.add_widget(right_line)
        card.add_widget(divider_box)

        # 第三方登录图标行
        third_party_box = BoxLayout(
            size_hint=(0.72, None), height=dp(80),
            pos_hint={"center_x": 0.5, "top": 0.22},
            spacing=dp(0),
        )
        for icon_path, name in [
            (os.path.join(IMAGE_DIR, "weixin.png"), "微信"),
            (os.path.join(IMAGE_DIR, "qq.png"), "QQ"),
            (os.path.join(IMAGE_DIR, "weibo.png"), "微博"),
        ]:
            item = BoxLayout(orientation="vertical", spacing=dp(6), size_hint=(1, 1))
            icon_wrap = FloatLayout(size_hint=(1, None), height=dp(52))
            if os.path.exists(icon_path):
                class _IconBtn(ButtonBehavior, KivyImage):
                    pass
                icon_btn = _IconBtn(
                    source=icon_path,
                    size_hint=(None, None), size=(dp(48), dp(48)),
                    allow_stretch=True, keep_ratio=True,
                )
                icon_btn.pos_hint = {"center_x": 0.5, "center_y": 0.5}
                icon_wrap.add_widget(icon_btn)
            else:
                icon_btn = Button(
                    text=name[0], font_size=sp(28),
                    background_normal="", background_down="",
                    background_color=(0.88, 0.88, 0.88, 1),
                    size_hint=(1, 1),
                )
                icon_wrap.add_widget(icon_btn)
            icon_btn.bind(on_press=lambda *_, n=name: show_toast(f"{n}登录暂未开放"))
            name_label = Label(
                text=name, font_size=sp(12),
                color=(0.35, 0.35, 0.35, 1),
                size_hint=(1, None), height=dp(20),
                halign="center", valign="middle", **text_style(),
            )
            name_label.bind(size=name_label.setter("text_size"))
            item.add_widget(icon_wrap)
            item.add_widget(name_label)
            third_party_box.add_widget(item)
        card.add_widget(third_party_box)

    def _update_bg(self, *_args):
        self.bg_rect_top.pos = self.layout.pos
        self.bg_rect_top.size = self.layout.size
        self.bg_rect_bottom.pos = self.layout.pos
        self.bg_rect_bottom.size = (self.layout.width, self.layout.height * 0.5)

    def _update_login_tab_underline(self, *_args):
        self.login_tab.canvas.after.clear()
        with self.login_tab.canvas.after:
            Color(*GREEN)
            Rectangle(
                pos=(self.login_tab.x, self.login_tab.y),
                size=(self.login_tab.width, dp(3)),
            )

    def on_pre_enter(self, *args):
        self._load_avatar()
        return super().on_pre_enter(*args)

    def _load_avatar(self):
        app = App.get_running_app()
        default_avatar = os.path.join(IMAGE_DIR, "nongming.png")
        avatar_path = ""
        if app.current_user and app.current_user.get("avatar_path"):
            avatar_path = app.current_user["avatar_path"]
        if not avatar_path or not os.path.exists(avatar_path):
            avatar_path = default_avatar if os.path.exists(default_avatar) else ""
        self.avatar_wrap.clear_widgets()
        if avatar_path:
            self.avatar_image.source = avatar_path
            self.avatar_image.reload()
            self.avatar_wrap.add_widget(self.avatar_image)
        else:
            self.avatar_wrap.add_widget(self.avatar_placeholder)

    def on_leave(self, *args):
        self.username_input.text = ""
        self.password_input.text = ""
        return super().on_leave(*args)

    def open_register(self, _instance=None):
        self.manager.current = "register"

    def login(self, _instance=None):
        username = self.username_input.text.strip()
        password = self.password_input.text
        if not username or not password:
            show_toast("请输入用户名和密码")
            return
        user = USER_DB.authenticate_user(username, password)
        if not user:
            show_toast("用户名或密码错误，请重试")
            return
        self.nick_label.text = user.get("nick_name") or user["username"]
        avatar_path = user.get("avatar_path", "")
        if avatar_path and os.path.exists(avatar_path):
            self.avatar_wrap.clear_widgets()
            self.avatar_image.source = avatar_path
            self.avatar_image.reload()
            self.avatar_wrap.add_widget(self.avatar_image)
        app = App.get_running_app()
        app.set_current_user(user)
        self.manager.current = "home"

    def open_sms_login(self, _instance=None):
        self._sms_code = str(random.randint(100000, 999999))
        self._sms_phone = ""
        self._send_countdown = 0

        popup = Popup(title="", separator_height=0, size_hint=(0.88, None), height=dp(360))
        content = BoxLayout(orientation="vertical", spacing=dp(14), padding=dp(20))
        with content.canvas.before:
            Color(1, 1, 1, 1)
            bg_rect = RoundedRectangle(
                pos=content.pos, size=content.size, radius=[dp(20)] * 4)
        content.bind(
            pos=lambda i, *_: _update_popup_rect(i, bg_rect),
            size=lambda i, *_: _update_popup_rect(i, bg_rect),
        )

        title_label = Label(
            text="手机号快捷登录", font_size=sp(20), bold=True,
            color=(0.08, 0.08, 0.08, 1), size_hint=(1, None), height=dp(32),
            halign="center", valign="middle", **text_style(),
        )
        title_label.bind(size=title_label.setter("text_size"))
        content.add_widget(title_label)

        # 手机号输入框
        phone_wrap = BoxLayout(size_hint=(1, None), height=dp(52))
        with phone_wrap.canvas.before:
            Color(0.94, 0.94, 0.94, 1)
            phone_bg = RoundedRectangle(
                pos=phone_wrap.pos, size=phone_wrap.size, radius=[dp(26)] * 4)
        phone_wrap.bind(
            pos=lambda i, *_: setattr(phone_bg, "pos", i.pos),
            size=lambda i, *_: setattr(phone_bg, "size", i.size),
        )
        phone_icon = Label(
            text="📱", font_size=sp(18),
            size_hint=(None, 1), width=dp(48),
            halign="center", valign="middle",
        )
        phone_input = TextInput(
            hint_text="请输入手机号码", multiline=False, input_type="number",
            background_normal="", background_active="",
            background_color=(0, 0, 0, 0),
            foreground_color=(0.12, 0.12, 0.12, 1),
            hint_text_color=(0.65, 0.65, 0.65, 1),
            cursor_color=(0.12, 0.12, 0.12, 1),
            padding=(0, dp(14), dp(14), dp(14)),
            font_size=sp(15), **text_style(),
        )
        phone_wrap.add_widget(phone_icon)
        phone_wrap.add_widget(phone_input)
        content.add_widget(phone_wrap)

        # 验证码输入框 + 发送按钮
        code_wrap = BoxLayout(size_hint=(1, None), height=dp(52), spacing=dp(10))
        input_wrap = BoxLayout(size_hint=(1, 1))
        with input_wrap.canvas.before:
            Color(0.94, 0.94, 0.94, 1)
            code_bg = RoundedRectangle(
                pos=input_wrap.pos, size=input_wrap.size, radius=[dp(26)] * 4)
        input_wrap.bind(
            pos=lambda i, *_: setattr(code_bg, "pos", i.pos),
            size=lambda i, *_: setattr(code_bg, "size", i.size),
        )
        code_icon = Label(
            text="🔑", font_size=sp(18),
            size_hint=(None, 1), width=dp(48),
            halign="center", valign="middle",
        )
        code_input = TextInput(
            hint_text="请输入验证码", multiline=False, input_type="number",
            background_normal="", background_active="",
            background_color=(0, 0, 0, 0),
            foreground_color=(0.12, 0.12, 0.12, 1),
            hint_text_color=(0.65, 0.65, 0.65, 1),
            cursor_color=(0.12, 0.12, 0.12, 1),
            padding=(0, dp(14), dp(14), dp(14)),
            font_size=sp(15), **text_style(),
        )
        input_wrap.add_widget(code_icon)
        input_wrap.add_widget(code_input)
        code_wrap.add_widget(input_wrap)

        send_btn = RoundedButton(
            text="发送验证码", color=(1, 1, 1, 1),
            size_hint=(None, 1), width=dp(108),
            font_size=sp(13), **text_style(),
        )
        code_wrap.add_widget(send_btn)
        content.add_widget(code_wrap)

        # 提示文字
        self._hint_label = Label(
            text="", font_size=sp(13), color=(0.88, 0.32, 0.18, 1),
            size_hint=(1, None), height=dp(22),
            halign="center", valign="middle", **text_style(),
        )
        self._hint_label.bind(size=self._hint_label.setter("text_size"))
        content.add_widget(self._hint_label)

        # 登录按钮
        confirm_btn = RoundedButton(
            text="登  录", color=(1, 1, 1, 1),
            font_size=sp(18), bold=True,
            size_hint=(1, None), height=dp(52), **text_style(),
        )
        content.add_widget(confirm_btn)

        # 取消按钮
        cancel_btn = Button(
            text="取消", font_size=sp(15),
            color=(0.55, 0.55, 0.55, 1),
            background_normal="", background_down="",
            background_color=(0, 0, 0, 0),
            size_hint=(1, None), height=dp(36), **text_style(),
        )
        cancel_btn.bind(on_press=lambda *_: popup.dismiss())
        content.add_widget(cancel_btn)
        popup.content = content

        def send_code(_instance=None):
            phone = phone_input.text.strip()
            if len(phone) != 11 or not phone.isdigit():
                self._hint_label.text = "请输入正确的11位手机号"
                return
            self._sms_phone = phone
            self._sms_code = str(random.randint(100000, 999999))
            show_toast(f"验证码已发送：{self._sms_code}")
            self._hint_label.text = f"验证码已发送到 {phone[:3]}****{phone[7:]}"
            send_btn.text = "60秒后重发"
            send_btn.disabled = True
            self._send_countdown = 60
            Clock.schedule_interval(self._tick_countdown(send_btn), 1)

        def confirm_login(_instance=None):
            phone = phone_input.text.strip()
            code = code_input.text.strip()
            if not phone or not code:
                self._hint_label.text = "请填写手机号和验证码"
                return
            if phone != self._sms_phone:
                self._hint_label.text = "手机号与发送验证码的号码不一致"
                return
            if code != self._sms_code:
                self._hint_label.text = "验证码错误，请重新输入"
                return
            user = USER_DB.get_user(phone)
            if not user:
                USER_DB.create_user(phone, "", "free")
                user = USER_DB.get_user(phone)
                show_toast("注册成功，已自动登录")
            else:
                show_toast("登录成功")
            popup.dismiss()
            app = App.get_running_app()
            app.set_current_user(user)
            self.manager.current = "home"

        send_btn.bind(on_press=send_code)
        confirm_btn.bind(on_press=confirm_login)
        popup.open()

    def _tick_countdown(self, send_btn):
        def tick(dt):
            self._send_countdown -= 1
            if self._send_countdown <= 0:
                send_btn.text = "重新发送"
                send_btn.disabled = False
                return False
            send_btn.text = f"{self._send_countdown}秒后重发"
        return tick


class RegisterScreen(Screen):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.name = "register"
        self.selected_avatar_source = ""
        self.selected_role = "free"
        self.build_ui()

    def build_ui(self):
        self.layout = FloatLayout()
        self.add_widget(self.layout)
        with self.layout.canvas.before:
            Color(1, 1, 1, 1)
            self.bg_rect = Rectangle(pos=self.layout.pos, size=self.layout.size)
        self.layout.bind(pos=self._update_bg, size=self._update_bg)

        self.top_bar = FloatLayout(
            size_hint=(1, None), height=dp(56),
            pos_hint={"x": 0, "top": 1},
        )
        with self.top_bar.canvas.before:
            Color(*GREEN)
            self.top_bar_rect = Rectangle(
                pos=self.top_bar.pos, size=self.top_bar.size)
        self.top_bar.bind(pos=self._update_top_bar, size=self._update_top_bar)
        self.layout.add_widget(self.top_bar)

        self.back_btn = IconButton(
            text="<", font_size=sp(34), color=(0, 0, 0, 1),
            size_hint=(None, None), size=(dp(56), dp(56)),
            pos_hint={"x": 0.03, "center_y": 0.5, **text_style(),}
        )
        self.back_btn.bind(on_press=lambda *_: setattr(self.manager, "current", "login"))
        self.top_bar.add_widget(self.back_btn)

        self.top_title = Label(
            text="注册新账号", color=(1, 1, 1, 1), font_size=sp(20),
            size_hint=(0.5, None), height=dp(34),
            pos_hint={"center_x": 0.52, "center_y": 0.5},
            halign="center", valign="middle", **text_style(),
        )
        self.top_title.bind(size=self.top_title.setter("text_size"))
        self.top_bar.add_widget(self.top_title)

        self.avatar_preview = GrayPlaceholder(
            radius=1, size_hint=(None, None), size=(dp(112), dp(112)),
            pos_hint={"center_x": 0.5, "top": 0.82},
        )
        self.layout.add_widget(self.avatar_preview)

        self.avatar_image = CircleImage(
            source="", size_hint=(None, None), size=(dp(112), dp(112)),
            pos_hint={"center_x": 0.5, "top": 0.82},
        )

        self.avatar_link = UnderlineLabel(
            text="[u]点击选头像框[/u]", color=GREEN, font_size=sp(14),
            size_hint=(None, None), size=(dp(140), dp(28)),
            pos_hint={"center_x": 0.5, "top": 0.66},
            halign="center", valign="middle", **text_style(),
        )
        self.avatar_link.bind(size=self.avatar_link.setter("text_size"))
        self.avatar_link.bind(on_press=self.show_avatar_menu)
        self.layout.add_widget(self.avatar_link)

        self.username_input = TextInput(
            hint_text="请输入用户名", multiline=False,
            size_hint=(0.84, None), height=dp(52),
            pos_hint={"center_x": 0.5, "top": 0.58},
            background_normal="", background_active="",
            background_color=(0.94, 0.94, 0.94, 1),
            padding=(dp(14), dp(14), dp(14), dp(14)),
            font_size=sp(15), input_type="text", **text_style(),
        )
        self.layout.add_widget(self.username_input)

        self.password_input = TextInput(
            hint_text="请输入密码", multiline=False, password=True,
            size_hint=(0.84, None), height=dp(52),
            pos_hint={"center_x": 0.5, "top": 0.49},
            background_normal="", background_active="",
            background_color=(0.94, 0.94, 0.94, 1),
            padding=(dp(14), dp(14), dp(14), dp(14)),
            font_size=sp(15), input_type="text",
            keyboard_suggestions=False, **text_style(),
        )
        self.layout.add_widget(self.password_input)

        self.role_box = BoxLayout(
            orientation="horizontal", spacing=dp(18),
            size_hint=(0.84, None), height=dp(44),
            pos_hint={"center_x": 0.5, "top": 0.40},
        )
        self.layout.add_widget(self.role_box)

        self.free_toggle = ToggleButton(
            text="免费", group="role_group", state="down",
            background_normal="", background_down="",
            background_color=(0.92, 0.92, 0.92, 1),
            color=(0.1, 0.1, 0.1, 1), **text_style(),
        )
        self.free_toggle.bind(on_press=lambda *_: self._set_role("free"))
        self.role_box.add_widget(self.free_toggle)

        self.vip_toggle = ToggleButton(
            text="VIP（399元/年）", group="role_group",
            background_normal="", background_down="",
            background_color=(0.92, 0.92, 0.92, 1),
            color=(0.1, 0.1, 0.1, 1), **text_style(),
        )
        self.vip_toggle.bind(on_press=lambda *_: self._set_role("vip"))
        self.role_box.add_widget(self.vip_toggle)

        self.confirm_btn = RoundedButton(
            text="确定", color=(1, 1, 1, 1), font_size=sp(18),
            size_hint=(0.84, None), height=dp(52),
            pos_hint={"center_x": 0.5, "top": 0.30}, **text_style(),
        )
        self.confirm_btn.bind(on_press=self.submit_register)
        self.layout.add_widget(self.confirm_btn)

    def _update_bg(self, *_args):
        self.bg_rect.pos = self.layout.pos
        self.bg_rect.size = self.layout.size

    def _update_top_bar(self, *_args):
        self.top_bar_rect.pos = self.top_bar.pos
        self.top_bar_rect.size = self.top_bar.size

    def _set_role(self, role_name):
        self.selected_role = role_name
        if role_name == "free":
            self.free_toggle.state = "down"
            self.vip_toggle.state = "normal"
            self.free_toggle.background_color = (0.68, 0.88, 0.68, 1)
            self.vip_toggle.background_color = (0.92, 0.92, 0.92, 1)
        else:
            self.free_toggle.state = "normal"
            self.vip_toggle.state = "down"
            self.free_toggle.background_color = (0.92, 0.92, 0.92, 1)
            self.vip_toggle.background_color = (0.68, 0.88, 0.68, 1)

    def _show_selected_avatar(self):
        if self.selected_avatar_source and os.path.exists(self.selected_avatar_source):
            if self.avatar_preview.parent:
                self.layout.remove_widget(self.avatar_preview)
            self.avatar_image.source = self.selected_avatar_source
            self.avatar_image.reload()
            if self.avatar_image.parent is None:
                self.layout.add_widget(self.avatar_image)
        else:
            if self.avatar_image.parent:
                self.layout.remove_widget(self.avatar_image)
            if self.avatar_preview.parent is None:
                self.layout.add_widget(self.avatar_preview)

    def show_avatar_menu(self, _instance=None):
        popup = Popup(title="", separator_height=0, size_hint=(0.82, None), height=dp(220))
        content = BoxLayout(orientation="vertical", spacing=dp(12), padding=dp(14))
        with content.canvas.before:
            Color(0.16, 0.16, 0.16, 0.96)
            bg_rect = RoundedRectangle(
                pos=content.pos, size=content.size, radius=[dp(16)] * 4)
        content.bind(
            pos=lambda i, *_: _update_popup_rect(i, bg_rect),
            size=lambda i, *_: _update_popup_rect(i, bg_rect),
        )
        title_label = Label(
            text="选择头像", color=(1, 1, 1, 1), font_size=sp(18),
            size_hint=(1, None), height=dp(28),
            halign="center", valign="middle", **text_style(),
        )
        title_label.bind(size=title_label.setter("text_size"))
        content.add_widget(title_label)
        use_camera_btn = RoundedButton(
            text="使用相机", color=(1, 1, 1, 1),
            size_hint=(1, None), height=dp(44), **text_style(),
        )
        use_album_btn = RoundedButton(
            text="使用照片", color=(1, 1, 1, 1),
            size_hint=(1, None), height=dp(44), **text_style(),
        )
        cancel_btn = RoundedButton(
            text="取消", color=(1, 1, 1, 1),
            fill_color=(0.65, 0.65, 0.65, 1),
            size_hint=(1, None), height=dp(44), **text_style(),
        )
        use_camera_btn.bind(on_press=lambda *_: self._use_camera_for_avatar(popup))
        use_album_btn.bind(on_press=lambda *_: self._open_file_picker(popup))
        cancel_btn.bind(on_press=lambda *_: popup.dismiss())
        content.add_widget(use_camera_btn)
        content.add_widget(use_album_btn)
        content.add_widget(cancel_btn)
        popup.content = content
        popup.open()

    def _use_camera_for_avatar(self, popup):
        popup.dismiss()
        app = App.get_running_app()
        app.previous_before_camera = "register"
        app.camera_mode = "avatar"
        self.manager.current = "camera"

    def _open_file_picker(self, popup):
        popup.dismiss()
        App.get_running_app()._open_photo_from_menu(
            popup=None,
            after_action=lambda _mode, image_path: self._set_avatar_from_file(image_path),
        )

    def _set_avatar_from_file(self, image_path):
        self.selected_avatar_source = image_path
        self._show_selected_avatar()

    def _validate_register_form(self):
        username = self.username_input.text.strip()
        password = self.password_input.text
        if not username or not password:
            show_toast("请输入用户名和密码")
            return None, None
        if USER_DB.username_exists(username):
            show_toast("用户名已存在，请更换用户名")
            return None, None
        return username, password

    def submit_register(self, _instance=None):
        username, password = self._validate_register_form()
        if not username:
            return
        self.selected_role = "vip" if self.vip_toggle.state == "down" else "free"
        if self.selected_role == "vip":
            self._confirm_vip_register(username, password)
            return
        self._create_account(username, password, "free")

    def _confirm_vip_register(self, username, password):
        popup = Popup(title="", separator_height=0, size_hint=(0.82, None), height=dp(220))
        content = BoxLayout(orientation="vertical", spacing=dp(16), padding=dp(16))
        with content.canvas.before:
            Color(0.16, 0.16, 0.16, 0.96)
            bg_rect = RoundedRectangle(
                pos=content.pos, size=content.size, radius=[dp(16)] * 4)
        content.bind(
            pos=lambda i, *_: _update_popup_rect(i, bg_rect),
            size=lambda i, *_: _update_popup_rect(i, bg_rect),
        )
        title_label = Label(
            text="确认注册VIP", color=(1, 1, 1, 1), font_size=sp(18),
            size_hint=(1, None), height=dp(28),
            halign="center", valign="middle", **text_style(),
        )
        title_label.bind(size=title_label.setter("text_size"))
        label = Label(
            text="您已选择VIP服务，需付费399元/年",
            color=(1, 1, 1, 1), halign="center", valign="middle", **text_style(),
        )
        label.bind(size=label.setter("text_size"))
        content.add_widget(title_label)
        content.add_widget(label)
        button_bar = BoxLayout(size_hint=(1, None), height=dp(46), spacing=dp(12))
        ok_btn = RoundedButton(text="确定", color=(1, 1, 1, 1), **text_style())
        cancel_btn = RoundedButton(
            text="取消", color=(1, 1, 1, 1),
            fill_color=(0.65, 0.65, 0.65, 1), **text_style(),
        )
        ok_btn.bind(on_press=lambda *_: self._confirm_register_and_close(
            popup, username, password))
        cancel_btn.bind(on_press=lambda *_: popup.dismiss())
        button_bar.add_widget(ok_btn)
        button_bar.add_widget(cancel_btn)
        content.add_widget(button_bar)
        popup.content = content
        popup.open()

    def _confirm_register_and_close(self, popup, username, password):
        popup.dismiss()
        self._create_account(username, password, "vip")

    def _create_account(self, username, password, role):
        avatar_path = save_avatar_image(self.selected_avatar_source, username) \
            if self.selected_avatar_source else ""
        USER_DB.create_user(username, password, role, avatar_path)
        show_toast("注册成功")
        self.clear_form()
        self.manager.current = "login"

    def clear_form(self):
        self.username_input.text = ""
        self.password_input.text = ""
        self.selected_avatar_source = ""
        self.selected_role = None
        self.free_toggle.state = "normal"
        self.vip_toggle.state = "normal"
        self.free_toggle.background_color = (0.92, 0.92, 0.92, 1)
        self.vip_toggle.background_color = (0.92, 0.92, 0.92, 1)
        self._show_selected_avatar()

    def on_leave(self, *args):
        self.clear_form()
        return super().on_leave(*args)


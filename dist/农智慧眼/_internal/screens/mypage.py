import os

from kivy.app import App
from kivy.clock import Clock
from kivy.graphics import Color, Rectangle, RoundedRectangle, Ellipse, Line
from kivy.metrics import dp, sp
from kivy.uix.behaviors import ButtonBehavior
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.button import Button
from kivy.uix.floatlayout import FloatLayout
from kivy.uix.label import Label
from kivy.uix.popup import Popup
from kivy.uix.screenmanager import Screen
from kivy.uix.scrollview import ScrollView
from kivy.uix.textinput import TextInput
from kivy.uix.widget import Widget

from config import GREEN, IMAGE_DIR
from database.user_db import USER_DB
from database.store_db import STORE_DB
from utils import (text_style, show_toast, save_avatar_image,
                   open_text_popup, _update_popup_rect)
from widgets.base_widgets import (IconButton, UnderlineLabel, RoundedButton,
                                   GrayPlaceholder, CircleImage)
from screens.home import HomeScreen, _update_camera_btn


class MyPageScreen(Screen):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.name = "mypage"
        self.nick_name = "开心菜园阿伯"
        self.signature = "欢迎光临我的开心菜园！"
        self.build_ui()

    def build_ui(self):
        self.layout = FloatLayout()
        self.add_widget(self.layout)

        # 整体背景
        with self.layout.canvas.before:
            Color(0.96, 0.98, 0.96, 1)
            self.bg_rect = Rectangle(pos=self.layout.pos, size=self.layout.size)
        self.layout.bind(pos=self._update_bg, size=self._update_bg)

        # 顶部绿色区域（顶部栏 + 用户卡片背景）
        self.top_green = FloatLayout(
            size_hint=(1, None), height=dp(300),
            pos_hint={"x": 0, "top": 1},
        )
        with self.top_green.canvas.before:
            Color(0.42, 0.82, 0.52, 1)
            self.top_green_rect = Rectangle(
                pos=self.top_green.pos, size=self.top_green.size)
        self.top_green.bind(
            pos=lambda i, *_: setattr(self.top_green_rect, "pos", i.pos),
            size=lambda i, *_: setattr(self.top_green_rect, "size", i.size),
        )
        self.layout.add_widget(self.top_green)

        # 顶部导航栏
        nav_bar = BoxLayout(
            size_hint=(1, None), height=dp(56),
            pos_hint={"x": 0, "top": 1},
            padding=(dp(16), dp(8), dp(16), dp(8)),
            spacing=dp(8),
        )
        back_btn = Button(
            text="<", font_size=sp(26), bold=True,
            color=(1, 1, 1, 1),
            background_normal="", background_down="",
            background_color=(0, 0, 0, 0),
            size_hint=(None, 1), width=dp(36),
        )
        back_btn.bind(on_press=lambda *_: setattr(self.manager, "current", "home"))
        nav_bar.add_widget(back_btn)

        nav_title = Label(
            text="我的", font_size=sp(20), bold=True,
            color=(1, 1, 1, 1),
            size_hint=(1, 1),
            halign="left", valign="middle", **text_style(),
        )
        nav_title.bind(size=nav_title.setter("text_size"))
        nav_bar.add_widget(nav_title)

        settings_btn = Button(
            text="@", font_size=sp(22),
            color=(1, 1, 1, 1),
            background_normal="", background_down="",
            background_color=(0, 0, 0, 0),
            size_hint=(None, 1), width=dp(40),
        )
        settings_btn.bind(on_press=lambda *_: show_toast("设置功能即将推出"))
        nav_bar.add_widget(settings_btn)
        self.top_green.add_widget(nav_bar)

        # 用户信息卡片（浅绿色圆角卡片）
        self.user_card = BoxLayout(
            orientation="vertical", spacing=dp(12),
            size_hint=(0.90, None), height=dp(200),
            pos_hint={"center_x": 0.5, "y": 0.02},
            padding=(dp(16), dp(16), dp(16), dp(16)),
        )
        with self.user_card.canvas.before:
            Color(0.82, 0.96, 0.82, 1)
            self.card_rect = RoundedRectangle(
                pos=self.user_card.pos, size=self.user_card.size,
                radius=[dp(20)] * 4)
        self.user_card.bind(
            pos=lambda i, *_: setattr(self.card_rect, "pos", i.pos),
            size=lambda i, *_: setattr(self.card_rect, "size", i.size),
        )
        self.top_green.add_widget(self.user_card)

        # 头像 + 名字 + 签名 行
        profile_row = BoxLayout(
            size_hint=(1, None), height=dp(84),
            spacing=dp(14),
        )
        avatar_container = FloatLayout(
            size_hint=(None, None), size=(dp(84), dp(84)))
        default_avatar = os.path.join(IMAGE_DIR, "nongming.png")
        self.avatar_image = CircleImage(
            source=default_avatar if os.path.exists(default_avatar) else "",
            size_hint=(None, None), size=(dp(84), dp(84)),
            allow_stretch=True, keep_ratio=False,
        )
        self.avatar_image.pos_hint = {"center_x": 0.5, "center_y": 0.5}
        self.avatar_placeholder = GrayPlaceholder(
            radius=1,
            size_hint=(None, None), size=(dp(84), dp(84)),
        )
        self.avatar_placeholder.pos_hint = {"center_x": 0.5, "center_y": 0.5}
        if os.path.exists(default_avatar):
            avatar_container.add_widget(self.avatar_image)
        else:
            avatar_container.add_widget(self.avatar_placeholder)
        self.avatar_container = avatar_container

        avatar_btn = Button(
            size_hint=(1, 1),
            background_normal="", background_down="",
            background_color=(0, 0, 0, 0),
        )
        avatar_btn.bind(on_press=lambda *_: App.get_running_app().show_capture_menu(
            after_action=self._on_avatar_captured))
        avatar_container.add_widget(avatar_btn)
        profile_row.add_widget(avatar_container)

        name_box = BoxLayout(orientation="vertical", spacing=dp(6),
                             size_hint=(1, 1))
        name_box.add_widget(Widget(size_hint=(1, None), height=dp(12)))
        self.nick_label = Label(
            text=self.nick_name,
            font_size=sp(20), bold=True,
            color=(0.12, 0.35, 0.12, 1),
            size_hint=(1, None), height=dp(30),
            halign="left", valign="middle", **text_style(),
        )
        self.nick_label.bind(size=self.nick_label.setter("text_size"))
        self.nick_label.bind(on_touch_down=self._on_nick_touch)
        name_box.add_widget(self.nick_label)

        self.signature_label = Label(
            text=self.signature,
            font_size=sp(14), color=(0.28, 0.48, 0.28, 1),
            size_hint=(1, None), height=dp(24),
            halign="left", valign="middle", **text_style(),
        )
        self.signature_label.bind(size=self.signature_label.setter("text_size"))
        name_box.add_widget(self.signature_label)
        profile_row.add_widget(name_box)
        self.user_card.add_widget(profile_row)

        # 分隔线
        divider = Widget(size_hint=(1, None), height=dp(1))
        with divider.canvas:
            Color(0.68, 0.88, 0.68, 1)
            div_rect = Rectangle(pos=divider.pos, size=divider.size)
        divider.bind(
            pos=lambda i, r=div_rect, *_: setattr(r, "pos", i.pos),
            size=lambda i, r=div_rect, *_: setattr(r, "size", i.size),
        )
        self.user_card.add_widget(divider)

        # 关注/粉丝/分享 统计行
        self.stats_row = BoxLayout(
            size_hint=(1, None), height=dp(72),
            spacing=dp(0),
        )
        self.user_card.add_widget(self.stats_row)

        # 滚动内容区（白色背景）
        self.scroll = ScrollView(
            size_hint=(1, None), do_scroll_x=False,
            pos_hint={"x": 0, "y": 0},
        )
        self.layout.add_widget(self.scroll)
        self.content_box = BoxLayout(
            orientation="vertical", spacing=dp(10),
            padding=(dp(12), dp(12), dp(12), dp(18)),
            size_hint=(1, None),
        )
        self.content_box.bind(minimum_height=self.content_box.setter("height"))
        self.scroll.add_widget(self.content_box)

        # 快捷功能区（通知/二维码/扫一扫/通讯录）
        self.content_box.add_widget(self._build_quick_actions())

        # 菜单列表
        menu_items = [
            ("我的档案", self.open_profile_editor),
            ("我的订单", self.open_orders),
            ("我的反馈", lambda *_: open_text_popup("我的反馈", "即将推出")),
            ("客服服务", lambda *_: open_text_popup("客服服务", "即将推出")),
        ]
        for title, callback in menu_items:
            self.content_box.add_widget(
                self._build_menu_item(title, callback))

        # 退出登录
        logout_btn = Button(
            text="退出登录",
            font_size=sp(16), color=(0.75, 0.25, 0.25, 1),
            background_normal="", background_down="",
            background_color=(0, 0, 0, 0),
            size_hint=(1, None), height=dp(52),
            **text_style(),
        )
        logout_btn.bind(on_press=self.logout)
        self.content_box.add_widget(logout_btn)

        # 底部导航
        self.bottom_nav = HomeScreen._build_bottom_nav(self)
        self.layout.add_widget(self.bottom_nav)

        self.layout.bind(size=self._update_layout)
        Clock.schedule_once(lambda dt: self._update_layout(), 0)

    def _build_quick_actions(self):
        card = BoxLayout(
            orientation="vertical", spacing=dp(8),
            padding=(dp(12), dp(12), dp(12), dp(12)),
            size_hint=(1, None), height=dp(110),
        )
        with card.canvas.before:
            Color(1, 1, 1, 1)
            card_bg = RoundedRectangle(
                pos=card.pos, size=card.size, radius=[dp(16)] * 4)
        card.bind(
            pos=lambda i, *_: setattr(card_bg, "pos", i.pos),
            size=lambda i, *_: setattr(card_bg, "size", i.size),
        )
        actions_row = BoxLayout(size_hint=(1, None), height=dp(86))
        items = [
            ("通知", (0.95, 0.62, 0.15, 1), lambda *_: show_toast("暂无通知")),
            ("二维码名片", (0.20, 0.55, 0.90, 1), lambda *_: show_toast("即将推出")),
            ("扫一扫", (0.58, 0.38, 0.88, 1), lambda *_: show_toast("即将推出")),
            ("通讯录", (0.20, 0.55, 0.90, 1), lambda *_: show_toast("即将推出")),
        ]
        for title, color, callback in items:
            item_box = BoxLayout(orientation="vertical", spacing=dp(6),
                                 size_hint=(1, 1))
            icon_wrap = FloatLayout(size_hint=(1, None), height=dp(52))
            circle = Widget(size_hint=(None, None), size=(dp(48), dp(48)))
            with circle.canvas:
                Color(*color)
                circle_bg = Ellipse(pos=circle.pos, size=circle.size)
            circle.bind(
                pos=lambda i, e=circle_bg, *_: setattr(e, "pos", i.pos),
                size=lambda i, e=circle_bg, *_: setattr(e, "size", i.size),
            )
            circle.pos_hint = {"center_x": 0.5, "center_y": 0.5}

            icon_label = Label(
                text=title[0], font_size=sp(20), bold=True,
                color=(1, 1, 1, 1),
                size_hint=(None, None), size=(dp(48), dp(48)),
                halign="center", valign="middle", **text_style(),
            )
            icon_label.bind(size=icon_label.setter("text_size"))
            icon_label.pos_hint = {"center_x": 0.5, "center_y": 0.5}

            btn = Button(
                size_hint=(1, 1),
                background_normal="", background_down="",
                background_color=(0, 0, 0, 0),
            )
            btn.bind(on_press=callback)
            icon_wrap.add_widget(circle)
            icon_wrap.add_widget(icon_label)
            icon_wrap.add_widget(btn)
            item_box.add_widget(icon_wrap)

            name_lbl = Label(
                text=title, font_size=sp(12),
                color=(0.22, 0.22, 0.22, 1),
                size_hint=(1, None), height=dp(20),
                halign="center", valign="middle", **text_style(),
            )
            name_lbl.bind(size=name_lbl.setter("text_size"))
            item_box.add_widget(name_lbl)
            actions_row.add_widget(item_box)
        card.add_widget(actions_row)
        return card

    def _build_menu_item(self, title, callback):
        card = BoxLayout(
            orientation="horizontal", spacing=dp(12),
            padding=(dp(16), dp(0), dp(16), dp(0)),
            size_hint=(1, None), height=dp(64),
        )
        with card.canvas.before:
            Color(1, 1, 1, 1)
            card_bg = RoundedRectangle(
                pos=card.pos, size=card.size, radius=[dp(16)] * 4)
        card.bind(
            pos=lambda i, *_: setattr(card_bg, "pos", i.pos),
            size=lambda i, *_: setattr(card_bg, "size", i.size),
        )

        # 绿色图标圆圈
        icon_wrap = FloatLayout(size_hint=(None, 1), width=dp(44))
        icon_circle = Widget(size_hint=(None, None), size=(dp(38), dp(38)))
        with icon_circle.canvas:
            Color(0.78, 0.96, 0.78, 1)
            ic_bg = RoundedRectangle(
                pos=icon_circle.pos, size=icon_circle.size,
                radius=[dp(10)] * 4)
        icon_circle.bind(
            pos=lambda i, r=ic_bg, *_: setattr(r, "pos", i.pos),
            size=lambda i, r=ic_bg, *_: setattr(r, "size", i.size),
        )
        icon_circle.pos_hint = {"center_x": 0.5, "center_y": 0.5}
        icon_lbl = Label(
            text=title[2] if len(title) > 2 else title[0],
            font_size=sp(18), color=GREEN,
            size_hint=(None, None), size=(dp(38), dp(38)),
            halign="center", valign="middle", **text_style(),
        )
        icon_lbl.bind(size=icon_lbl.setter("text_size"))
        icon_lbl.pos_hint = {"center_x": 0.5, "center_y": 0.5}
        icon_wrap.add_widget(icon_circle)
        icon_wrap.add_widget(icon_lbl)
        card.add_widget(icon_wrap)

        # 标题
        title_label = Label(
            text=title, font_size=sp(17),
            color=(0.12, 0.12, 0.12, 1),
            size_hint=(1, 1),
            halign="left", valign="middle", **text_style(),
        )
        title_label.bind(size=title_label.setter("text_size"))
        card.add_widget(title_label)

        # 右箭头
        arrow = Label(
            text=">", font_size=sp(18),
            color=(0.72, 0.72, 0.72, 1),
            size_hint=(None, 1), width=dp(24),
            halign="center", valign="middle",
        )
        card.add_widget(arrow)

        btn = Button(
            size_hint=(1, 1), pos_hint={"x": 0, "y": 0},
            background_normal="", background_down="",
            background_color=(0, 0, 0, 0),
        )
        btn.bind(on_press=callback)

        outer = FloatLayout(size_hint=(1, None), height=dp(64))
        card.pos_hint = {"x": 0, "y": 0}
        outer.add_widget(card)
        outer.add_widget(btn)
        return outer

    def on_pre_enter(self, *args):
        self.refresh_profile()
        return super().on_pre_enter(*args)

    def _update_bg(self, *_args):
        self.bg_rect.pos = self.layout.pos
        self.bg_rect.size = self.layout.size

    def _update_layout(self, *_args):
        nav_h = self.bottom_nav.height
        top_h = self.top_green.height
        available = max(dp(200), self.height - nav_h - top_h + dp(20))
        self.scroll.height = available
        self.scroll.pos = (0, nav_h)
        self.top_green.pos = (0, self.height - top_h)
        self.top_green.size = (self.width, top_h)

    def refresh_profile(self):
        app = App.get_running_app()
        user = app.refresh_current_user()
        self.nick_name = user["nick_name"] if user else "开心菜园阿伯"
        self.signature = user["signature"] if user else "欢迎光临我的开心菜园！"
        self.nick_label.text = self.nick_name
        self.signature_label.text = self.signature

        # 统计数据
        self.stats_row.clear_widgets()
        following = user["following_count"] if user else 0
        followers = user["followers_count"] if user else 0
        share = user["share_count"] if user else 0
        for num, label in [
            (following, "我的关注"),
            (followers, "我的粉丝"),
            (share, "我的分享"),
        ]:
            stat_box = BoxLayout(orientation="vertical", spacing=dp(2),
                                 size_hint=(1, 1))
            num_label = Label(
                text=str(num), font_size=sp(22), bold=True,
                color=(0.12, 0.35, 0.12, 1),
                size_hint=(1, None), height=dp(32),
                halign="center", valign="middle", **text_style(),
            )
            num_label.bind(size=num_label.setter("text_size"))
            stat_box.add_widget(num_label)
            name_label = Label(
                text=label, font_size=sp(13),
                color=(0.28, 0.48, 0.28, 1),
                size_hint=(1, None), height=dp(22),
                halign="center", valign="middle", **text_style(),
            )
            name_label.bind(size=name_label.setter("text_size"))
            stat_box.add_widget(name_label)
            self.stats_row.add_widget(stat_box)

        # 头像
        avatar_path = user["avatar_path"] if user else ""
        if not avatar_path or not os.path.exists(avatar_path):
            avatar_path = os.path.join(IMAGE_DIR, "nongming.png")
        self.avatar_container.clear_widgets()
        if avatar_path and os.path.exists(avatar_path):
            self.avatar_image.source = avatar_path
            self.avatar_image.reload()
            self.avatar_container.add_widget(self.avatar_image)
        else:
            self.avatar_container.add_widget(self.avatar_placeholder)
        avatar_btn = Button(
            size_hint=(1, 1),
            background_normal="", background_down="",
            background_color=(0, 0, 0, 0),
        )
        avatar_btn.bind(on_press=lambda *_: App.get_running_app().show_capture_menu(
            after_action=self._on_avatar_captured))
        self.avatar_container.add_widget(avatar_btn)

    def _on_nick_touch(self, instance, touch):
        if instance.collide_point(*touch.pos):
            self.edit_profile_field("nick_name", "编辑昵称", self.nick_name)

    def _on_avatar_captured(self, mode, image_path=None):
        if image_path and os.path.exists(image_path):
            self._save_new_avatar(image_path)

    def _save_new_avatar(self, image_path):
        app = App.get_running_app()
        if not app.current_user:
            return
        username = app.current_user["username"]
        new_avatar_path = save_avatar_image(image_path, username)
        USER_DB.update_avatar(username, new_avatar_path)
        app.refresh_current_user()
        self.refresh_profile()
        show_toast("头像更新成功")

    def edit_profile_field(self, field_name, title, current_value):
        popup = Popup(title="", separator_height=0,
                      size_hint=(0.84, None), height=dp(240))
        box = BoxLayout(orientation="vertical", spacing=dp(12), padding=dp(16))
        with box.canvas.before:
            Color(1, 1, 1, 1)
            bg_rect = RoundedRectangle(
                pos=box.pos, size=box.size, radius=[dp(16)] * 4)
        box.bind(
            pos=lambda i, *_: _update_popup_rect(i, bg_rect),
            size=lambda i, *_: _update_popup_rect(i, bg_rect),
        )
        title_label = Label(
            text=title, font_size=sp(18), color=(0.08, 0.08, 0.08, 1),
            size_hint=(1, None), height=dp(28),
            halign="center", valign="middle", **text_style(),
        )
        title_label.bind(size=title_label.setter("text_size"))
        box.add_widget(title_label)
        input_box = TextInput(
            text=current_value, multiline=False, input_type="text",
            keyboard_suggestions=True,
            background_normal="", background_active="",
            background_color=(0.94, 0.94, 0.94, 1), **text_style(),
        )
        box.add_widget(input_box)
        save_btn = RoundedButton(
            text="保存", color=(1, 1, 1, 1),
            size_hint=(1, None), height=dp(44), **text_style(),
        )

        def save_value(_instance=None):
            app = App.get_running_app()
            if not app.current_user:
                popup.dismiss()
                return
            value = input_box.text.strip()
            if field_name == "nick_name":
                USER_DB.update_profile(
                    app.current_user["username"],
                    nick_name=value or "开心菜园阿伯",
                )
            else:
                USER_DB.update_profile(
                    app.current_user["username"],
                    signature=value or "欢迎光临我的开心菜园！",
                )
            app.refresh_current_user()
            self.refresh_profile()
            popup.dismiss()

        save_btn.bind(on_press=save_value)
        box.add_widget(save_btn)
        popup.content = box
        popup.open()

    def open_profile_editor(self, _instance=None):
        self.edit_profile_field("nick_name", "编辑我的档案", self.nick_name)

    def open_orders(self, _instance=None):
        self.manager.current = "order"

    def logout(self, _instance=None):
        app = App.get_running_app()
        app.current_user = None
        self.manager.current = "login"


class FavoriteScreen(Screen):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.name = "favorite"
        self.build_ui()

    def build_ui(self):
        self.layout = FloatLayout()
        self.add_widget(self.layout)
        with self.layout.canvas.before:
            Color(0.97, 0.97, 0.97, 1)
            self.bg_rect = Rectangle(pos=self.layout.pos, size=self.layout.size)
        self.layout.bind(pos=self._update_bg, size=self._update_bg)

        self.top_bar = FloatLayout(size_hint=(1, None), height=dp(92),
                                   pos_hint={"x": 0, "top": 1})
        with self.top_bar.canvas.before:
            Color(*GREEN)
            self.top_bar_rect = Rectangle(
                pos=self.top_bar.pos, size=self.top_bar.size)
        self.top_bar.bind(
            pos=self._update_top_bar, size=self._update_top_bar)
        self.layout.add_widget(self.top_bar)

        back_btn = IconButton(
            text="<", font_size=sp(34), color=(0, 0, 0, 1),
            size_hint=(None, None), size=(dp(56), dp(56)),
            pos_hint={"x": 0.03, "center_y": 0.42}, **text_style(),
        )
        back_btn.bind(on_press=self.go_back)
        self.top_bar.add_widget(back_btn)

        title = Label(
            text="我的收藏", font_size=sp(22), bold=True, color=(1, 1, 1, 1),
            size_hint=(0.7, None), height=dp(36),
            pos_hint={"center_x": 0.52, "center_y": 0.42},
            halign="center", valign="middle", **text_style(),
        )
        title.bind(size=title.setter("text_size"))
        self.top_bar.add_widget(title)

        self.scroll = ScrollView(size_hint=(1, None), do_scroll_x=False,
                                 pos_hint={"x": 0, "y": 0})
        self.layout.add_widget(self.scroll)
        self.content_box = BoxLayout(
            orientation="vertical", spacing=0, size_hint=(1, None))
        self.content_box.bind(minimum_height=self.content_box.setter("height"))
        self.scroll.add_widget(self.content_box)

        self.layout.bind(size=self._update_layout)
        Clock.schedule_once(lambda dt: self._update_layout(), 0)

    def on_pre_enter(self, *args):
        self.refresh_products()
        return super().on_pre_enter(*args)

    def _update_bg(self, *_args):
        self.bg_rect.pos = self.layout.pos
        self.bg_rect.size = self.layout.size

    def _update_top_bar(self, *_args):
        self.top_bar_rect.pos = self.top_bar.pos
        self.top_bar_rect.size = self.top_bar.size

    def _update_layout(self, *_args):
        self.scroll.height = self.height - self.top_bar.height
        self.scroll.pos = (0, 0)

    def refresh_products(self):
        self.content_box.clear_widgets()
        empty = Label(
            text="收藏功能暂未开放", font_size=sp(16),
            color=(0.45, 0.45, 0.45, 1),
            size_hint=(1, None), height=dp(60),
            halign="center", valign="middle", **text_style(),
        )
        empty.bind(size=empty.setter("text_size"))
        self.content_box.add_widget(empty)

    def sync_product_views(self, tab_name=None):
        pass

    def go_back(self, _instance=None):
        self.manager.current = "home"

class OrderScreen(Screen):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.name = "order"
        self.return_screen = "mypage"
        self.build_ui()

    def build_ui(self):
        self.layout = FloatLayout()
        self.add_widget(self.layout)
        with self.layout.canvas.before:
            Color(0.97, 0.97, 0.97, 1)
            self.bg_rect = Rectangle(pos=self.layout.pos, size=self.layout.size)
        self.layout.bind(pos=self._update_bg, size=self._update_bg)

        self.top_bar = FloatLayout(size_hint=(1, None), height=dp(92),
                                   pos_hint={"x": 0, "top": 1})
        with self.top_bar.canvas.before:
            Color(*GREEN)
            self.top_bar_rect = Rectangle(
                pos=self.top_bar.pos, size=self.top_bar.size)
        self.top_bar.bind(
            pos=self._update_top_bar, size=self._update_top_bar)
        self.layout.add_widget(self.top_bar)

        back_btn = IconButton(
            text="<", font_size=sp(34), color=(0, 0, 0, 1),
            size_hint=(None, None), size=(dp(56), dp(56)),
            pos_hint={"x": 0.03, "center_y": 0.42}, **text_style(),
        )
        back_btn.bind(on_press=self.go_back)
        self.top_bar.add_widget(back_btn)

        title = Label(
            text="我的订单", font_size=sp(22), bold=True, color=(1, 1, 1, 1),
            size_hint=(0.7, None), height=dp(36),
            pos_hint={"center_x": 0.52, "center_y": 0.42},
            halign="center", valign="middle", **text_style(),
        )
        title.bind(size=title.setter("text_size"))
        self.top_bar.add_widget(title)

        self.scroll = ScrollView(size_hint=(1, None), do_scroll_x=False,
                                 pos_hint={"x": 0, "y": 0})
        self.layout.add_widget(self.scroll)
        self.content_box = BoxLayout(
            orientation="vertical", spacing=0, size_hint=(1, None))
        self.content_box.bind(minimum_height=self.content_box.setter("height"))
        self.scroll.add_widget(self.content_box)

        self.layout.bind(size=self._update_layout)
        Clock.schedule_once(lambda dt: self._update_layout(), 0)

    def on_pre_enter(self, *args):
        self.refresh_orders()
        return super().on_pre_enter(*args)

    def _update_bg(self, *_args):
        self.bg_rect.pos = self.layout.pos
        self.bg_rect.size = self.layout.size

    def _update_top_bar(self, *_args):
        self.top_bar_rect.pos = self.top_bar.pos
        self.top_bar_rect.size = self.top_bar.size

    def _update_layout(self, *_args):
        self.scroll.height = self.height - self.top_bar.height
        self.scroll.pos = (0, 0)

    def refresh_orders(self):
        self.content_box.clear_widgets()
        app = App.get_running_app()
        username = app.current_user["username"] if app and app.current_user else ""
        orders = STORE_DB.get_orders(username)
        if not orders:
            empty = Label(
                text="暂无订单", font_size=sp(16),
                color=(0.45, 0.45, 0.45, 1),
                size_hint=(1, None), height=dp(60),
                halign="center", valign="middle", **text_style(),
            )
            empty.bind(size=empty.setter("text_size"))
            self.content_box.add_widget(empty)
            return
        for order in orders:
            self.content_box.add_widget(OrderRow(order))

    def sync_product_views(self, tab_name=None):
        self.refresh_orders()

    def go_back(self, _instance=None):
        if self.manager and self.manager.has_screen(self.return_screen):
            self.manager.current = self.return_screen


class OrderRow(ButtonBehavior, BoxLayout):
    def __init__(self, order_data, **kwargs):
        super().__init__(
            orientation="horizontal", spacing=dp(12),
            padding=(dp(14), dp(10)), size_hint_y=None, height=dp(118),
            **kwargs,
        )
        self.order_data = order_data
        self.bind(pos=self._update_canvas, size=self._update_canvas)

        thumb_wrap = FloatLayout(size_hint=(None, None), size=(dp(80), dp(80)))
        placeholder = Widget(size_hint=(1, 1))
        with placeholder.canvas.before:
            Color(0.88, 0.88, 0.88, 1)
            ph_rect = RoundedRectangle(
                pos=placeholder.pos, size=placeholder.size,
                radius=[dp(8)] * 4)
        placeholder.bind(
            pos=lambda i, r=ph_rect, *_: setattr(r, "pos", i.pos),
            size=lambda i, r=ph_rect, *_: setattr(r, "size", i.size),
        )
        thumb_wrap.add_widget(placeholder)
        self.add_widget(thumb_wrap)

        info_box = BoxLayout(orientation="vertical", spacing=dp(4))
        for text, size, color in [
            (order_data["name"], sp(16), (0.1, 0.1, 0.1, 1)),
            (f"规格：{order_data['specification']}", sp(13),
             (0.42, 0.42, 0.42, 1)),
            (f"下单时间：{order_data['order_date']}", sp(13),
             (0.42, 0.42, 0.42, 1)),
            (f"预计送达：{order_data['delivery_date']}", sp(13),
             (0.42, 0.42, 0.42, 1)),
        ]:
            label = Label(
                text=text, font_size=size, color=color,
                size_hint=(1, None), height=dp(22),
                halign="left", valign="middle", **text_style(),
            )
            label.bind(size=label.setter("text_size"))
            info_box.add_widget(label)
        self.add_widget(info_box)

        price_label = Label(
            text=f"￥{order_data['price']:.2f}",
            font_size=sp(16), color=(0.88, 0.32, 0.18, 1),
            size_hint=(None, 1), width=dp(88),
            halign="right", valign="middle", **text_style(),
        )
        price_label.bind(size=price_label.setter("text_size"))
        self.add_widget(price_label)

    def _update_canvas(self, *_args):
        self.canvas.before.clear()
        self.canvas.after.clear()
        with self.canvas.before:
            Color(1, 1, 1, 1)
            Rectangle(pos=self.pos, size=self.size)
        with self.canvas.after:
            Color(0.90, 0.90, 0.90, 1)
            Line(points=[self.x, self.y, self.right, self.y], width=1)


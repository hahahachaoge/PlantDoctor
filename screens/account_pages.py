import calendar
import os
from datetime import date, datetime

from kivy.app import App
from kivy.clock import Clock
from kivy.graphics import Color, Rectangle, RoundedRectangle
from kivy.metrics import dp, sp
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.button import Button
from kivy.uix.dropdown import DropDown
from kivy.uix.floatlayout import FloatLayout
from kivy.uix.image import Image
from kivy.uix.label import Label
from kivy.uix.screenmanager import Screen
from kivy.uix.scrollview import ScrollView
from kivy.uix.spinner import Spinner, SpinnerOption
from kivy.uix.textinput import TextInput
from kivy.uix.widget import Widget

from config import GREEN, IMAGE_DIR
from database.store_db import STORE_DB
from database.user_db import USER_DB
from utils import save_avatar_image, show_toast, text_style
from widgets.base_widgets import CircleImage, RoundedButton


INK = (0.08, 0.13, 0.10, 1)
MUTED = (0.42, 0.48, 0.44, 1)
SURFACE = (1, 1, 1, 1)
PAGE_BG = (0.955, 0.975, 0.96, 1)
SOFT_GREEN = (0.90, 0.97, 0.92, 1)
ORANGE = (0.92, 0.48, 0.16, 1)


class ChineseSpinnerOption(SpinnerOption):
    def __init__(self, **kwargs):
        kwargs.update(text_style())
        kwargs.setdefault("font_size", sp(14))
        kwargs.setdefault("background_normal", "")
        kwargs.setdefault("background_color", (0.95, 0.98, 0.96, 1))
        kwargs.setdefault("color", INK)
        kwargs.setdefault("height", dp(44))
        super().__init__(**kwargs)


class CompactDropDown(DropDown):
    def __init__(self, **kwargs):
        kwargs.setdefault("max_height", dp(286))
        super().__init__(**kwargs)


def _paint(widget, color=SURFACE, radius=16):
    with widget.canvas.before:
        Color(*color)
        shape = RoundedRectangle(pos=widget.pos, size=widget.size,
                                 radius=[dp(radius)] * 4)
    widget.bind(pos=lambda item, *_: setattr(shape, "pos", item.pos))
    widget.bind(size=lambda item, *_: setattr(shape, "size", item.size))
    return shape


def _text(text, size=14, color=INK, height=28, bold=False,
          halign="left", **kwargs):
    options = dict(
        text=text, font_size=sp(size), color=color, bold=bold,
        size_hint=(1, None), height=dp(height), halign=halign,
        valign="middle",
    )
    options.update(text_style())
    options.update(kwargs)
    label = Label(**options)
    label.bind(size=label.setter("text_size"))
    return label


def _input(hint, multiline=False, height=46, input_filter=None):
    return TextInput(
        hint_text=hint, multiline=multiline, input_filter=input_filter,
        size_hint=(1, None), height=dp(height), font_size=sp(14),
        padding=(dp(12), dp(12)), foreground_color=INK,
        hint_text_color=(0.58, 0.62, 0.59, 1), cursor_color=GREEN,
        background_normal="", background_active="",
        background_color=(0.94, 0.97, 0.95, 1), **text_style(),
    )


def _product_image(product):
    raw = product.get("image", "")
    candidates = []
    if raw and raw != "gray_placeholder":
        candidates.extend((raw, os.path.join(IMAGE_DIR, raw)))
    name = product.get("name", "")
    candidates.extend(
        os.path.join(IMAGE_DIR, f"{name}.{ext}")
        for ext in ("jpg", "png", "jpeg")
    )
    return next((path for path in candidates if os.path.exists(path)), "")


def _current_user():
    app = App.get_running_app()
    return (app.current_user if app and app.current_user else {})


class AccountPage(Screen):
    title = ""
    subtitle = ""

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.root_layout = FloatLayout()
        self.add_widget(self.root_layout)
        with self.root_layout.canvas.before:
            Color(*PAGE_BG)
            self.page_bg = Rectangle(pos=self.root_layout.pos,
                                     size=self.root_layout.size)
        self.root_layout.bind(
            pos=lambda item, *_: setattr(self.page_bg, "pos", item.pos),
            size=lambda item, *_: setattr(self.page_bg, "size", item.size),
        )
        self._build_header()
        self.scroll = ScrollView(
            size_hint=(1, None), pos_hint={"x": 0, "y": 0},
            do_scroll_x=False, bar_width=dp(4), bar_color=GREEN,
        )
        self.body = BoxLayout(
            orientation="vertical", spacing=dp(12),
            padding=(dp(14), dp(16), dp(14), dp(28)), size_hint=(1, None),
        )
        self.body.bind(minimum_height=self.body.setter("height"))
        self.scroll.add_widget(self.body)
        self.root_layout.add_widget(self.scroll)
        self.bind(size=self._layout, pos=self._layout)
        Clock.schedule_once(self._layout, 0)

    def _build_header(self):
        has_subtitle = bool((self.subtitle or "").strip())
        self.header = FloatLayout(
            size_hint=(1, None), height=dp(92 if has_subtitle else 70),
            pos_hint={"x": 0, "top": 1})
        with self.header.canvas.before:
            Color(0.10, 0.49, 0.25, 1)
            self.header_bg = Rectangle(pos=self.header.pos, size=self.header.size)
        self.header.bind(
            pos=lambda item, *_: setattr(self.header_bg, "pos", item.pos),
            size=lambda item, *_: setattr(self.header_bg, "size", item.size),
        )
        back = Button(
            text="<", size_hint=(None, None), size=(dp(54), dp(54)),
            pos_hint={"x": 0.015, "top": 0.96}, font_size=sp(28),
            color=(1, 1, 1, 1), background_normal="", background_down="",
            background_color=(0, 0, 0, 0), **text_style(),
        )
        back.bind(on_release=self.go_back)
        self.header.add_widget(back)
        self.title_label = _text(
            self.title, 21, (1, 1, 1, 1), 34, True, "center",
            size_hint=(None, None), width=dp(250),
            pos_hint=({"center_x": 0.5, "top": 0.90} if has_subtitle
                      else {"center_x": 0.5, "center_y": 0.5}),
        )
        self.header.add_widget(self.title_label)
        if has_subtitle:
            self.subtitle_label = _text(
                self.subtitle, 11, (0.84, 0.94, 0.87, 1), 24,
                size_hint=(None, None), width=dp(270),
                pos_hint={"x": 0.17, "y": 0.08},
            )
            self.header.add_widget(self.subtitle_label)
        self.root_layout.add_widget(self.header)

    def _layout(self, *_args):
        self.header.top = self.top
        self.header.width = self.width
        self.scroll.height = max(0, self.height - self.header.height)

    def go_back(self, *_args):
        if self.manager:
            self.manager.current = "mypage"

    def card(self, height=None, padding=14, spacing=8, color=SURFACE):
        card = BoxLayout(
            orientation="vertical", spacing=dp(spacing),
            padding=(dp(padding), dp(padding)), size_hint=(1, None),
        )
        if height is not None:
            card.height = dp(height)
        else:
            card.bind(minimum_height=card.setter("height"))
        _paint(card, color)
        return card


class FavoriteScreen(AccountPage):
    title = "我的收藏"
    subtitle = ""

    def __init__(self, **kwargs):
        kwargs.setdefault("name", "favorite")
        super().__init__(**kwargs)

    def on_pre_enter(self, *_args):
        self.refresh_products()

    def go_back(self, *_args):
        if self.manager and self.manager.has_screen("home"):
            self.manager.current = "home"

    def refresh_products(self):
        self.body.clear_widgets()
        user = _current_user()
        products = STORE_DB.get_favorite_products(user.get("username", ""))
        summary = self.card(92, color=(0.84, 0.95, 0.87, 1))
        summary.add_widget(_text(f"已收藏 {len(products)} 件商品", 20,
                                 (0.08, 0.36, 0.18, 1), 30, True))
        summary.add_widget(_text(
            "价格和库存以商城详情页为准，可随时取消收藏。", 12, MUTED, 24))
        self.body.add_widget(summary)
        if not products:
            empty = self.card(220)
            empty.add_widget(_text("还没有收藏商品", 19, INK, 44, True, "center"))
            empty.add_widget(_text(
                "在商城商品详情中点击收藏，这里会自动同步。", 13, MUTED, 58,
                halign="center"))
            visit = RoundedButton(
                text="去商城看看", size_hint=(1, None), height=dp(44),
                color=(1, 1, 1, 1), **text_style())
            visit.bind(on_release=lambda *_: setattr(self.manager, "current", "store"))
            empty.add_widget(visit)
            self.body.add_widget(empty)
            return
        for product in products:
            self.body.add_widget(self._product_card(product))

    def _product_card(self, product):
        card = self.card(172)
        top = BoxLayout(spacing=dp(12), size_hint=(1, None), height=dp(102))
        source = _product_image(product)
        image = Image(
            source=source, size_hint=(None, None), size=(dp(96), dp(96)),
            fit_mode="cover" if source else "contain",
        )
        top.add_widget(image)
        info = BoxLayout(orientation="vertical", spacing=dp(2))
        info.add_widget(_text(product["name"], 16, INK, 30, True))
        info.add_widget(_text(
            f"{product.get('category', '农资')} · {product.get('specification', '')}",
            12, MUTED, 23))
        info.add_widget(_text(
            f"库存 {product.get('stock', 0)}  |  已售 {product.get('sold_count', 0)}",
            11, MUTED, 22))
        info.add_widget(_text(f"¥ {float(product['price']):.2f}", 18, ORANGE, 28, True))
        top.add_widget(info)
        card.add_widget(top)
        actions = BoxLayout(spacing=dp(9), size_hint=(1, None), height=dp(40))
        remove = RoundedButton(
            text="取消收藏", color=(0.70, 0.24, 0.20, 1),
            fill_color=(1.0, 0.92, 0.90, 1), **text_style())
        detail = RoundedButton(text="查看详情", color=(1, 1, 1, 1), **text_style())
        remove.bind(on_release=lambda *_args, item=product: self._remove(item))
        detail.bind(on_release=lambda *_args, item=product: self._open(item))
        actions.add_widget(remove)
        actions.add_widget(detail)
        card.add_widget(actions)
        return card

    def _remove(self, product):
        username = _current_user().get("username", "")
        STORE_DB.remove_favorite(username, product["id"])
        show_toast("已取消收藏")
        self.refresh_products()

    def _open(self, product):
        app = App.get_running_app()
        if hasattr(app, "open_product_detail_screen"):
            app.open_product_detail_screen(
                product["id"], return_screen="favorite")


class NotificationScreen(AccountPage):
    title = "通知中心"
    subtitle = ""

    def __init__(self, **kwargs):
        kwargs.setdefault("name", "notifications")
        super().__init__(**kwargs)

    def on_pre_enter(self, *_args):
        self.refresh_notifications()

    def refresh_notifications(self):
        self.body.clear_widgets()
        user = _current_user()
        username = user.get("username", "")
        orders = STORE_DB.get_orders(username) if username else []
        count = int(user.get("recognize_count", 0))
        role = user.get("role", "free")
        remaining = "不限次数" if role == "vip" else f"剩余 {max(0, 3 - count)} 次"
        banner = self.card(112, color=(0.84, 0.95, 0.87, 1))
        banner.add_widget(_text("今天也要留意作物变化", 19,
                                (0.08, 0.36, 0.18, 1), 34, True))
        banner.add_widget(_text(
            f"拍照识别：{remaining}  ·  当前订单：{len(orders)} 单",
            13, (0.18, 0.43, 0.26, 1), 28))
        self.body.add_widget(banner)
        items = [
            ("识别额度", f"普通用户每日可识别 3 次；你今天已使用 {count} 次。"
             if role != "vip" else "VIP 账户已启用不限次数识别。", "今天", GREEN),
            ("账户安全", "密码内容仅在本机校验，请勿向他人透露账号或验证码。",
             "长期有效", (0.24, 0.48, 0.82, 1)),
            ("病虫害地图", "用户上报内容未经植保部门审核，防治前请结合现场诊断。",
             "使用提示", ORANGE),
        ]
        if orders:
            newest = orders[0]
            items.insert(1, (
                "订单进度",
                f"订单 PD{newest['id']:06d}：{newest['name']}，预计 {newest['delivery_date']} 送达。",
                newest["order_date"], GREEN,
            ))
        else:
            items.insert(1, ("订单动态", "目前没有待跟踪订单。", "暂无", MUTED))
        for title, content, stamp, color in items:
            card = self.card(118)
            heading = BoxLayout(size_hint=(1, None), height=dp(30))
            dot_wrap = FloatLayout(size_hint=(None, 1), width=dp(14))
            dot = Widget(
                size_hint=(None, None), size=(dp(9), dp(9)),
                pos_hint={"center_x": 0.5, "center_y": 0.5})
            _paint(dot, color, 5)
            dot_wrap.add_widget(dot)
            heading.add_widget(dot_wrap)
            heading.add_widget(_text(title, 16, INK, 30, True))
            heading.add_widget(_text(stamp, 11, MUTED, 30, halign="right",
                                     size_hint=(None, None), width=dp(84)))
            card.add_widget(heading)
            card.add_widget(_text(content, 13, (0.28, 0.32, 0.29, 1), 56))
            self.body.add_widget(card)


class ProfileScreen(AccountPage):
    title = "我的档案"
    subtitle = ""

    def __init__(self, **kwargs):
        kwargs.setdefault("name", "profile")
        super().__init__(**kwargs)
        self.fields = {}
        self.gender = "未设置"
        self.birth_date = ""

    def on_pre_enter(self, *_args):
        self.build_profile()

    def build_profile(self):
        self.body.clear_widgets()
        user = _current_user()
        profile = self.card(132, padding=12, color=(0.84, 0.95, 0.87, 1))
        row = BoxLayout(spacing=dp(14))
        avatar_path = user.get("avatar_path") or os.path.join(IMAGE_DIR, "nongming.png")
        avatar = CircleImage(
            source=avatar_path if os.path.exists(avatar_path) else "",
            size_hint=(None, None), size=(dp(82), dp(82)),
            pos_hint={"center_x": 0.5, "center_y": 0.5})
        avatar_wrap = FloatLayout(size_hint=(None, 1), width=dp(82))
        avatar_wrap.add_widget(avatar)
        row.add_widget(avatar_wrap)
        info_wrap = FloatLayout()
        info = BoxLayout(
            orientation="vertical", spacing=dp(7), size_hint=(1, None),
            height=dp(81), pos_hint={"x": 0, "center_y": 0.5})
        info.add_widget(_text(user.get("nick_name") or user.get("username", "用户"),
                              19, INK, 38, True))
        change = RoundedButton(
            text="更换头像", size_hint=(None, None), size=(dp(92), dp(36)),
            color=GREEN, fill_color=(1, 1, 1, 0.88), **text_style())
        change.bind(on_release=self._choose_avatar)
        info.add_widget(change)
        info_wrap.add_widget(info)
        row.add_widget(info_wrap)
        role_text = "VIP 用户" if user.get("role") == "vip" else "普通用户"
        badge_wrap = FloatLayout(size_hint=(None, 1), width=dp(82))
        role_badge = Label(
            text=role_text, font_size=sp(12), bold=True,
            color=((0.72, 0.39, 0.08, 1) if user.get("role") == "vip" else GREEN),
            size_hint=(None, None), size=(dp(78), dp(30)),
            pos_hint={"center_x": 0.5, "center_y": 0.5},
            halign="center", valign="middle", **text_style())
        role_badge.bind(size=role_badge.setter("text_size"))
        _paint(
            role_badge,
            ((1.0, 0.93, 0.74, 1) if user.get("role") == "vip" else (1, 1, 1, 0.88)),
            13)
        badge_wrap.add_widget(role_badge)
        row.add_widget(badge_wrap)
        profile.add_widget(row)
        self.body.add_widget(profile)

        form = self.card()
        form.add_widget(_text("基本信息", 17, INK, 32, True))

        def add_field(key, caption, hint, multiline=False, height=46):
            form.add_widget(_text(caption, 12, MUTED, 22))
            field = _input(hint, multiline, height)
            field.text = str(user.get(key, "") or "")
            self.fields[key] = field
            form.add_widget(field)

        add_field("nick_name", "昵称", "例如：开心菜园阿伯")
        add_field("phone", "联系电话", "用于客服联系，不公开展示")

        form.add_widget(_text("性别", 12, MUTED, 22))
        self.gender = user.get("gender", "未设置")
        self.gender_spinner = Spinner(
            text=self.gender, values=("男", "女", "未设置"),
            option_cls=ChineseSpinnerOption,
            size_hint=(1, None), height=dp(46), font_size=sp(14),
            background_normal="", background_color=SOFT_GREEN,
            color=(0.12, 0.30, 0.18, 1), **text_style())
        form.add_widget(self.gender_spinner)

        form.add_widget(_text("生日", 12, MUTED, 22))
        self.birth_date = str(user.get("birth_date", "") or "")
        try:
            selected_birth = datetime.strptime(self.birth_date, "%Y-%m-%d").date()
        except (TypeError, ValueError):
            selected_birth = None
        birth_row = BoxLayout(spacing=dp(8), size_hint=(1, None), height=dp(46))
        self.birth_year = self._birth_spinner(
            f"{selected_birth.year}年" if selected_birth else "请选择年",
            tuple(f"{year}年" for year in range(date.today().year, 1899, -1)))
        self.birth_month = self._birth_spinner(
            f"{selected_birth.month}月" if selected_birth else "请选择月",
            tuple(f"{month}月" for month in range(1, 13)))
        self.birth_day = self._birth_spinner(
            f"{selected_birth.day}日" if selected_birth else "请选择日", ())
        self.birth_year.bind(text=self._refresh_birth_days)
        self.birth_month.bind(text=self._refresh_birth_days)
        birth_row.add_widget(self.birth_year)
        birth_row.add_widget(self.birth_month)
        birth_row.add_widget(self.birth_day)
        form.add_widget(birth_row)
        self._refresh_birth_days()

        add_field("region", "所在地区", "例如：广东省广州市天河区")
        add_field("main_crop", "主要种植作物", "例如：水稻、番茄")
        add_field("signature", "个人简介", "介绍你的种植经验", True, 82)

        save = RoundedButton(
            text="保存档案", size_hint=(1, None), height=dp(48),
            color=(1, 1, 1, 1), **text_style())
        save.bind(on_release=self.save_profile)
        form.add_widget(save)
        self.body.add_widget(form)

    @staticmethod
    def _birth_spinner(text, values):
        return Spinner(
            text=text, values=values, option_cls=ChineseSpinnerOption,
            dropdown_cls=CompactDropDown,
            size_hint=(1, 1), font_size=sp(13), background_normal="",
            background_color=SOFT_GREEN, color=(0.12, 0.30, 0.18, 1),
            **text_style())

    def _refresh_birth_days(self, *_args):
        try:
            year = int(self.birth_year.text.rstrip("年"))
            month = int(self.birth_month.text.rstrip("月"))
        except (TypeError, ValueError):
            self.birth_day.values = tuple(f"{day}日" for day in range(1, 32))
            return
        day_count = calendar.monthrange(year, month)[1]
        current_text = self.birth_day.text
        self.birth_day.values = tuple(f"{day}日" for day in range(1, day_count + 1))
        try:
            current_day = int(current_text.rstrip("日"))
        except (TypeError, ValueError):
            return
        if current_day > day_count:
            self.birth_day.text = f"{day_count}日"

    def _selected_birth_date(self):
        try:
            year = int(self.birth_year.text.rstrip("年"))
            month = int(self.birth_month.text.rstrip("月"))
            day = int(self.birth_day.text.rstrip("日"))
            return date(year, month, day).strftime("%Y-%m-%d")
        except (TypeError, ValueError):
            return ""

    def save_profile(self, *_args):
        user = _current_user()
        if not user:
            return
        nick = self.fields["nick_name"].text.strip()
        if not nick:
            show_toast("昵称不能为空")
            return
        values = {key: field.text.strip() for key, field in self.fields.items()}
        values["gender"] = self.gender_spinner.text
        values["birth_date"] = self._selected_birth_date()
        updated = USER_DB.update_profile_details(user["username"], **values)
        app = App.get_running_app()
        app.current_user = updated
        show_toast("档案已保存")

    def _choose_avatar(self, *_args):
        app = App.get_running_app()
        if hasattr(app, "show_capture_menu"):
            app.show_capture_menu(after_action=self._save_avatar)

    def _save_avatar(self, _mode, image_path=None):
        user = _current_user()
        if not user or not image_path or not os.path.exists(image_path):
            return
        saved = save_avatar_image(image_path, user["username"])
        USER_DB.update_avatar(user["username"], saved)
        App.get_running_app().current_user = USER_DB.get_user(user["username"])
        self.build_profile()
        show_toast("头像已更新")


class OrderScreen(AccountPage):
    title = "我的订单"
    subtitle = ""

    def __init__(self, **kwargs):
        kwargs.setdefault("name", "order")
        super().__init__(**kwargs)
        self.return_screen = "mypage"

    def go_back(self, *_args):
        if self.manager and self.manager.has_screen(self.return_screen):
            self.manager.current = self.return_screen

    def on_pre_enter(self, *_args):
        self.refresh_orders()

    @staticmethod
    def _status(order):
        try:
            delivery = datetime.strptime(order["delivery_date"], "%Y-%m-%d").date()
            return "运输中" if delivery >= date.today() else "已完成"
        except (TypeError, ValueError):
            return "处理中"

    def refresh_orders(self):
        self.body.clear_widgets()
        username = _current_user().get("username", "")
        orders = STORE_DB.get_orders(username) if username else []
        summary = BoxLayout(spacing=dp(8), size_hint=(1, None), height=dp(86))
        for caption, value in (
                ("全部订单", len(orders)),
                ("运输中", sum(self._status(item) == "运输中" for item in orders)),
                ("已完成", sum(self._status(item) == "已完成" for item in orders))):
            card = BoxLayout(orientation="vertical", padding=dp(9))
            _paint(card, SURFACE)
            card.add_widget(_text(str(value), 20, GREEN, 32, True, "center"))
            card.add_widget(_text(caption, 11, MUTED, 24, halign="center"))
            summary.add_widget(card)
        self.body.add_widget(summary)
        if not orders:
            empty = self.card(220)
            empty.add_widget(_text("暂无订单", 19, INK, 42, True, "center"))
            empty.add_widget(_text("购买农资后，配送进度会显示在这里。", 13, MUTED,
                                   60, halign="center"))
            visit = RoundedButton(text="进入商城", color=(1, 1, 1, 1),
                                  size_hint=(1, None), height=dp(44), **text_style())
            visit.bind(on_release=lambda *_: setattr(self.manager, "current", "store"))
            empty.add_widget(visit)
            self.body.add_widget(empty)
            return
        for order in orders:
            self.body.add_widget(self._order_card(order))

    def _order_card(self, order):
        card = self.card(205)
        heading = BoxLayout(size_hint=(1, None), height=dp(30))
        heading.add_widget(_text(f"订单号  PD{order['id']:06d}", 12, MUTED, 30))
        status = self._status(order)
        heading.add_widget(_text(status, 13, GREEN if status == "运输中" else MUTED,
                                 30, True, "right", size_hint=(None, None),
                                 width=dp(76)))
        card.add_widget(heading)
        product = STORE_DB.get_product(order["product_id"]) or order
        row = BoxLayout(spacing=dp(12), size_hint=(1, None), height=dp(92))
        source = _product_image(product)
        row.add_widget(Image(source=source, size_hint=(None, None),
                             size=(dp(86), dp(86)), fit_mode="cover"))
        info = BoxLayout(orientation="vertical")
        info.add_widget(_text(order["name"], 15, INK, 28, True))
        info.add_widget(_text(f"规格：{order['specification']}", 12, MUTED, 23))
        info.add_widget(_text(f"下单：{order['order_date']}", 12, MUTED, 23))
        info.add_widget(_text(f"预计送达：{order['delivery_date']}", 12, MUTED, 23))
        row.add_widget(info)
        card.add_widget(row)
        footer = BoxLayout(size_hint=(1, None), height=dp(42))
        footer.add_widget(_text(f"实付  ¥ {float(order['price']):.2f}", 15,
                                ORANGE, 42, True))
        service = RoundedButton(
            text="售后咨询", size_hint=(None, 1), width=dp(96),
            color=GREEN, fill_color=SOFT_GREEN, **text_style())
        service.bind(on_release=lambda *_: setattr(self.manager, "current", "customer_service"))
        footer.add_widget(service)
        card.add_widget(footer)
        return card


class FeedbackScreen(AccountPage):
    title = "我的反馈"
    subtitle = ""

    def __init__(self, **kwargs):
        kwargs.setdefault("name", "feedback")
        super().__init__(**kwargs)
        self.category = "功能建议"

    def on_pre_enter(self, *_args):
        self.build_feedback()

    def build_feedback(self):
        self.body.clear_widgets()
        form = self.card()
        form.add_widget(_text("提交新反馈", 17, INK, 32, True))
        form.add_widget(_text("反馈类型", 12, MUTED, 22))
        options = BoxLayout(spacing=dp(6), size_hint=(1, None), height=dp(42))
        self.category_buttons = {}
        for item in ("功能建议", "识别问题", "订单售后"):
            selected = item == self.category
            button = RoundedButton(
                text=item, font_size=sp(12),
                color=(1, 1, 1, 1) if selected else GREEN,
                fill_color=GREEN if selected else SOFT_GREEN, **text_style())
            button.bind(on_release=lambda _button, value=item: self._set_category(value))
            self.category_buttons[item] = button
            options.add_widget(button)
        form.add_widget(options)
        form.add_widget(_text("问题标题", 12, MUTED, 22))
        self.feedback_title = _input("请简要概括问题")
        form.add_widget(self.feedback_title)
        form.add_widget(_text("详细描述", 12, MUTED, 22))
        self.feedback_content = _input(
            "请描述操作步骤、期望结果和实际结果", True, 130)
        form.add_widget(self.feedback_content)
        form.add_widget(_text("联系方式（选填）", 12, MUTED, 22))
        self.feedback_contact = _input("手机号或邮箱，仅用于回复")
        form.add_widget(self.feedback_contact)
        submit = RoundedButton(
            text="提交反馈", color=(1, 1, 1, 1),
            size_hint=(1, None), height=dp(48), **text_style())
        submit.bind(on_release=self.submit_feedback)
        form.add_widget(submit)
        self.body.add_widget(form)
        self.body.add_widget(_text("历史反馈", 17, INK, 34, True))
        records = STORE_DB.get_feedback(_current_user().get("username", ""))
        if not records:
            self.body.add_widget(_text("还没有提交过反馈", 13, MUTED, 58,
                                       halign="center"))
        for record in records:
            card = self.card(122)
            top = BoxLayout(size_hint=(1, None), height=dp(30))
            top.add_widget(_text(record["title"], 15, INK, 30, True))
            top.add_widget(_text(record["status"], 12, GREEN, 30, True, "right",
                                 size_hint=(None, None), width=dp(70)))
            card.add_widget(top)
            card.add_widget(_text(
                f"{record['category']} · {record['created_at'].replace('T', ' ')}",
                11, MUTED, 22))
            card.add_widget(_text(record["content"], 12, (0.28, 0.32, 0.29, 1), 46))
            self.body.add_widget(card)

    def _set_category(self, category):
        self.category = category
        for item, button in self.category_buttons.items():
            selected = item == category
            button.fill_color = GREEN if selected else SOFT_GREEN
            button.color = (1, 1, 1, 1) if selected else GREEN
            button._update_canvas()

    def submit_feedback(self, *_args):
        title = self.feedback_title.text.strip()
        content = self.feedback_content.text.strip()
        if not title or not content:
            show_toast("请填写问题标题和详细描述")
            return
        STORE_DB.add_feedback(
            _current_user().get("username", "游客"), self.category,
            title, content, self.feedback_contact.text.strip())
        show_toast("反馈已提交，我们会认真处理")
        self.build_feedback()


class CustomerServiceScreen(AccountPage):
    title = "客服服务"
    subtitle = ""

    def __init__(self, **kwargs):
        kwargs.setdefault("name", "customer_service")
        super().__init__(**kwargs)
        self.build_service()

    def build_service(self):
        banner = self.card(96, color=(0.84, 0.95, 0.87, 1))
        banner.add_widget(_text("人工客服在线", 20, (0.08, 0.36, 0.18, 1), 34, True))
        banner.add_widget(_text("服务时间：每天 08:30—20:30", 13, MUTED, 26))
        self.body.add_widget(banner)
        actions = BoxLayout(spacing=dp(8), size_hint=(1, None), height=dp(52))
        for caption, message in (
                ("在线咨询", "已为你排队，请稍候，客服将在服务时间内回复"),
                ("客服电话", "客服热线：400-800-2026（演示号码，请勿实际拨打）")):
            button = RoundedButton(
                text=caption, color=(1, 1, 1, 1), **text_style())
            button.bind(on_release=lambda _button, value=message: show_toast(value))
            actions.add_widget(button)
        self.body.add_widget(actions)
        self.body.add_widget(_text("常见问题", 18, INK, 38, True))
        faqs = (
            ("为什么识别结果会有多个候选？",
             "Top-5 展示模型最可能的五个类别。请结合叶片正反面、茎秆和田间症状综合判断。"),
            ("普通用户每天可以识别几次？",
             "普通用户每天免费识别 3 次，次日自动重置；VIP 用户不限次数。"),
            ("地图上的点都是官方监测结果吗？",
             "不是。地图中的真实统计来自用户上报，未经植保部门审核，不能替代官方预警。"),
            ("订单配送时间如何计算？",
             "当前系统按下单日期预计 3 天送达，实际时间以物流和商城通知为准。"),
            ("怎样提交可复现的问题？",
             "请在“我的反馈”中写明操作步骤、期望结果、实际结果，并附上可联系信息。"),
        )
        for question, answer in faqs:
            card = self.card()
            card.add_widget(_text(question, 15, INK, 30, True))
            answer_label = _text(answer, 12, MUTED, 52)
            card.add_widget(answer_label)
            self.body.add_widget(card)

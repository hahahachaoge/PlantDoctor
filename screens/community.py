import os

from config import (GREEN, COMMUNITY_POSTS, COMMUNITY_ARTICLES,
                    LIKE_ICON_OFF, LIKE_ICON_ON, IMAGE_DIR,
                    KANDIAN_IMAGES, KANDIAN_TITLES)

from kivy.app import App
from kivy.clock import Clock
from kivy.graphics import Color, Rectangle, RoundedRectangle, Line
from kivy.metrics import dp, sp
from kivy.uix.behaviors import ButtonBehavior
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.button import Button
from kivy.uix.floatlayout import FloatLayout
from kivy.uix.image import Image as KImage
from kivy.uix.label import Label
from kivy.uix.screenmanager import Screen
from kivy.uix.scrollview import ScrollView
from kivy.uix.textinput import TextInput
from kivy.uix.widget import Widget

from database.store_db import STORE_DB
from utils import (text_style, update_nav_rect, show_toast,
                   bind_deferred_layout)
from widgets.base_widgets import (
    UnderlineLabel, IconButton, CircleImage, GrayPlaceholder, LikeImageButton,
    RoundedButton,
)
from screens.home import HomeScreen, _update_camera_btn

HOT_USER_AVATARS = [
    os.path.join(IMAGE_DIR, "user1.jpg"),
    os.path.join(IMAGE_DIR, "user2.jpg"),
    os.path.join(IMAGE_DIR, "user3.jpg"),
    os.path.join(IMAGE_DIR, "user4.jpg"),
    os.path.join(IMAGE_DIR, "user5.jpg"),
]
HOT_USER_NAMES = ["张大叔", "葡萄园主", "青年农人", "采茶阿姨", "老王头"]

DROPDOWN_ICON = os.path.join(IMAGE_DIR, "下拉.png")
BELL_ICON = os.path.join(IMAGE_DIR, "通知.png")
COMMENT_ICON = os.path.join(IMAGE_DIR, "评论.png")
# 用户新版 UI 图标：转发.png（分享箭头）
SHARE_ICON = os.path.join(IMAGE_DIR, "转发.png")


class _BarButton(ButtonBehavior, BoxLayout):
    """可点击的水平布局。"""
    pass


class _TapImage(ButtonBehavior, KImage):
    """可点击的图片。"""
    pass


def _draw_magnifier(instance, *_args):
    """canvas 画放大镜，避免字体缺字。"""
    instance.canvas.clear()
    cx = instance.center_x - dp(2)
    cy = instance.center_y + dp(2)
    r = dp(6)
    with instance.canvas:
        Color(0.45, 0.55, 0.45, 1)
        Line(circle=(cx, cy, r), width=dp(1.4))
        Line(
            points=[
                cx + r * 0.72, cy - r * 0.72,
                cx + r * 0.72 + dp(5), cy - r * 0.72 - dp(5),
            ],
            width=dp(1.6), cap="round",
        )


def _draw_comment_icon(instance, *_args):
    """canvas 画对话气泡（评论图标）。"""
    instance.canvas.clear()
    cx, cy = instance.center
    r = min(instance.width, instance.height) * 0.5
    with instance.canvas:
        Color(0.18, 0.18, 0.18, 1)
        Line(
            rounded_rectangle=(
                cx - r, cy - r * 0.65, r * 2, r * 1.3, r * 0.55),
            width=dp(1.4),
        )
        Line(
            points=[
                cx - r * 0.45, cy - r * 0.6,
                cx - r * 0.62, cy - r * 1.05,
                cx - r * 0.05, cy - r * 0.65,
            ],
            width=dp(1.4), cap="round",
        )


def _draw_share_icon(instance, *_args):
    """canvas 画分享图标（箭头向上飞出方框）。"""
    instance.canvas.clear()
    cx, cy = instance.center
    r = min(instance.width, instance.height) * 0.5
    with instance.canvas:
        Color(0.18, 0.18, 0.18, 1)
        # 底部方框（顶部留开口）
        Line(
            points=[
                cx - r * 0.55, cy - r * 0.05,
                cx - r * 0.55, cy - r * 0.8,
                cx + r * 0.55, cy - r * 0.8,
                cx + r * 0.55, cy - r * 0.05,
            ],
            width=dp(1.4),
        )
        # 向上的箭头
        Line(points=[cx, cy + r * 0.8, cx, cy - r * 0.45],
             width=dp(1.4), cap="round")
        Line(
            points=[
                cx - r * 0.35, cy + r * 0.45,
                cx, cy + r * 0.8,
                cx + r * 0.35, cy + r * 0.45,
            ],
            width=dp(1.4), cap="round",
        )


def _rounded_png(source, radius=12):
    """用 PIL 把图片四角烤成透明圆角并缓存，返回缓存路径。

    不再使用 StencilView 蒙版：ScrollView 本身就是 StencilView，
    嵌套 stencil 在滚动时会错乱（白块盖住导航栏）。
    """
    if not source or not os.path.exists(source):
        return ""
    cache_dir = os.path.join(IMAGE_DIR, "_rounded")
    try:
        os.makedirs(cache_dir, exist_ok=True)
    except OSError:
        return source
    base = os.path.splitext(os.path.basename(source))[0]
    out = os.path.join(cache_dir, f"{base}_r{int(radius)}.png")
    if not os.path.exists(out):
        try:
            from PIL import Image as PILImage, ImageDraw
            im = PILImage.open(source).convert("RGBA")
            mask = PILImage.new("L", im.size, 0)
            ImageDraw.Draw(mask).rounded_rectangle(
                [0, 0, im.size[0] - 1, im.size[1] - 1],
                radius=max(2, int(radius * 3)), fill=255)
            im.putalpha(mask)
            im.save(out)
        except Exception:
            return source
    return out


def _circular_png(source):
    """Create a circular transparent PNG without nested stencil operations."""
    if not source or not os.path.exists(source):
        return ""
    cache_dir = os.path.join(IMAGE_DIR, "_rounded")
    try:
        os.makedirs(cache_dir, exist_ok=True)
    except OSError:
        return source
    base = os.path.splitext(os.path.basename(source))[0]
    out = os.path.join(cache_dir, f"{base}_circle.png")
    if not os.path.exists(out):
        try:
            from PIL import Image as PILImage, ImageDraw
            im = PILImage.open(source).convert("RGBA")
            mask = PILImage.new("L", im.size, 0)
            ImageDraw.Draw(mask).ellipse(
                (0, 0, im.size[0] - 1, im.size[1] - 1),
                fill=255,
            )
            im.putalpha(mask)
            im.save(out)
        except Exception:
            return source
    return out


class RoundedImage(ButtonBehavior, KImage):
    """圆角图片：四角透明（PIL 预处理 + 本地缓存），点击可打开详情。"""

    def __init__(self, source="", radius=dp(12), on_press=None, **kwargs):
        super().__init__(**kwargs)
        self._radius = float(radius)
        self.allow_stretch = True
        self.keep_ratio = False
        if source:
            self.set_source(source)
        if on_press:
            self.bind(on_press=on_press)

    def set_source(self, source):
        self.source = _rounded_png(source, self._radius)

    def reload(self):
        if self.source:
            super().reload()


class CommunityScreen(Screen):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.name = "community"
        self.build_ui()

    def build_ui(self):
        self.layout = FloatLayout()
        self.add_widget(self.layout)
        with self.layout.canvas.before:
            Color(0.96, 0.98, 0.96, 1)
            self.bg_rect = Rectangle(pos=self.layout.pos, size=self.layout.size)
        self.layout.bind(pos=self._update_bg, size=self._update_bg)


        # 注意：ScrollView 不能设置 pos_hint，否则 FloatLayout 布局时
        # 会覆盖 _update_layout 中手动设置的 pos=(0, nav_h)，
        # 导致内容区下移、顶部出现大段空白。
        self.scroll = ScrollView(size_hint=(1, None), do_scroll_x=False)
        self.layout.add_widget(self.scroll)
        self.content_box = BoxLayout(
            orientation="vertical", spacing=dp(10),
            # 底部 padding 必须大于凸起拍照按钮高出导航条的部分（凹槽顶到
            # 106dp，滚动内容底沿在 90dp），否则滚到底时最后的内容
            # （看点图片）会顶进凸起按钮区域，看起来"挡住导航栏"。
            padding=(dp(12), dp(6), dp(12), dp(34)),
            size_hint=(1, None),
        )
        self.content_box.bind(minimum_height=self.content_box.setter("height"))
        self.scroll.add_widget(self.content_box)

        self.refresh_default_content()

        # Draw the fixed top bar above the scrollable content.
        self.top_bar = self._build_top_bar()
        self.add_widget(self.top_bar)

        self.bottom_nav = HomeScreen._build_bottom_nav(self)
        self.layout.add_widget(self.bottom_nav)

        bind_deferred_layout(self.layout, self._update_layout)
        Clock.schedule_once(lambda dt: self._update_layout(), 0)

    def _build_top_bar(self):
        bar = BoxLayout(
            size_hint=(1, None), height=dp(56),
            pos_hint={"x": 0, "top": 1},
            spacing=dp(8),
            padding=(dp(12), dp(8), dp(12), dp(8)),
        )
        with bar.canvas.before:
            Color(1, 1, 1, 1)
            self.top_bar_bg = Rectangle(pos=bar.pos, size=bar.size)
        bar.bind(
            pos=lambda i, *_: setattr(self.top_bar_bg, "pos", i.pos),
            size=lambda i, *_: setattr(self.top_bar_bg, "size", i.size),
        )

        # 「社区」标题 + 下拉图标（图片紧贴文字，整体可点击）
        title_box = _BarButton(
            size_hint=(None, 1), width=dp(72), spacing=dp(2),
        )
        title_label = Label(
            text="社区", font_size=sp(20), bold=True,
            color=(0.08, 0.08, 0.08, 1),
            size_hint=(None, 1), width=dp(48),
            halign="left", valign="middle", **text_style(),
        )
        title_label.bind(size=title_label.setter("text_size"))
        title_box.add_widget(title_label)
        if os.path.exists(DROPDOWN_ICON):
            arrow = KImage(
                source=DROPDOWN_ICON,
                size_hint=(None, 1), width=dp(18),
                allow_stretch=True, keep_ratio=True,
            )
        else:
            arrow = Widget(size_hint=(None, 1), width=dp(18))
        title_box.add_widget(arrow)
        title_box.bind(
            on_press=lambda *_: show_toast("频道切换开发中"))
        bar.add_widget(title_box)

        # 搜索框（绿色圆角边框 + 白底，与首页风格一致）
        search_wrap = BoxLayout(size_hint=(1, 1))
        with search_wrap.canvas.before:
            Color(*GREEN)
            self.search_border = RoundedRectangle(
                pos=search_wrap.pos, size=search_wrap.size,
                radius=[dp(20)] * 4,
            )
        with search_wrap.canvas.before:
            Color(1, 1, 1, 1)
            self.search_bg = RoundedRectangle(
                pos=(search_wrap.x + dp(1), search_wrap.y + dp(1)),
                size=(search_wrap.width - dp(2), search_wrap.height - dp(2)),
                radius=[dp(20)] * 4,
            )

        def _update_search_bg(*_):
            self.search_border.pos = search_wrap.pos
            self.search_border.size = search_wrap.size
            self.search_bg.pos = (
                search_wrap.x + dp(1), search_wrap.y + dp(1))
            self.search_bg.size = (
                search_wrap.width - dp(2), search_wrap.height - dp(2))

        search_wrap.bind(pos=_update_search_bg, size=_update_search_bg)

        search_icon = Widget(size_hint=(None, 1), width=dp(30))
        search_icon.bind(pos=_draw_magnifier, size=_draw_magnifier)
        search_wrap.add_widget(search_icon)
        self.community_search_input = TextInput(
            hint_text="点击搜索关键词",
            multiline=False, input_type="text",
            keyboard_suggestions=True,
            background_normal="", background_active="",
            background_color=(0, 0, 0, 0),
            foreground_color=(0.18, 0.18, 0.18, 1),
            hint_text_color=(0.65, 0.65, 0.65, 1),
            cursor_color=GREEN,
            padding=(dp(4), dp(10), dp(14), dp(10)),
            font_size=sp(13), **text_style(),
        )
        self.community_search_input.bind(
            on_text_validate=self.search_posts,
            text=self._on_search_text,
        )
        search_wrap.add_widget(self.community_search_input)
        bar.add_widget(search_wrap)

        # 通知铃铛（图标）
        if os.path.exists(BELL_ICON):
            bell_btn = _TapImage(
                source=BELL_ICON,
                size_hint=(None, 1), width=dp(26),
                allow_stretch=True, keep_ratio=True,
            )
        else:
            bell_btn = Widget(size_hint=(None, 1), width=dp(26))
        if isinstance(bell_btn, _TapImage):
            bell_btn.bind(on_press=lambda *_: show_toast("暂无新消息"))
        bar.add_widget(bell_btn)

        # 右侧头像：进入社区时按当前登录用户刷新
        self.community_avatar_wrap = FloatLayout(
            size_hint=(None, 1), width=dp(38),
        )
        bar.add_widget(self.community_avatar_wrap)
        self._refresh_user_avatar()
        return bar

    def on_pre_enter(self, *args):
        self._refresh_user_avatar()
        return super().on_pre_enter(*args)

    def _refresh_user_avatar(self):
        avatar_path = ""
        app = App.get_running_app()
        if app and app.current_user:
            app.refresh_current_user()
            avatar_path = app.current_user.get("avatar_path") or ""
        if not avatar_path or not os.path.exists(avatar_path):
            avatar_path = os.path.join(IMAGE_DIR, "nongming.png")

        self.community_avatar_wrap.clear_widgets()
        if avatar_path and os.path.exists(avatar_path):
            avatar = CircleImage(
                source=avatar_path,
                size_hint=(None, None), size=(dp(34), dp(34)),
                allow_stretch=True, keep_ratio=False,
            )
            avatar.pos_hint = {"center_x": 0.5, "center_y": 0.5}
            self.community_avatar_wrap.add_widget(avatar)
        else:
            placeholder = GrayPlaceholder(
                radius=1,
                size_hint=(None, None), size=(dp(34), dp(34)),
            )
            placeholder.pos_hint = {"center_x": 0.5, "center_y": 0.5}
            self.community_avatar_wrap.add_widget(placeholder)

    def refresh_default_content(self):
        self.content_box.clear_widgets()
        self.content_box.add_widget(self._build_section_header("热门用户"))
        self.content_box.add_widget(self._build_hot_users())
        self.content_box.add_widget(self._build_section_header("推 荐"))
        for post in COMMUNITY_POSTS:
            self.content_box.add_widget(self._build_post_card(post))
        self.content_box.add_widget(self._build_section_header("看 点"))
        self.content_box.add_widget(self._build_kandian())

    def _build_section_header(self, text):
        row = BoxLayout(size_hint=(1, None), height=dp(30), spacing=dp(6),
                        padding=(dp(4), 0, 0, 0))
        arrow = Label(
            text=">>", font_size=sp(14), bold=True, color=GREEN,
            size_hint=(None, 1), width=dp(26),
            halign="left", valign="middle", **text_style(),
        )
        arrow.bind(size=arrow.setter("text_size"))
        row.add_widget(arrow)
        title = Label(
            text=text, font_size=sp(16), bold=True,
            color=(0.08, 0.08, 0.08, 1),
            size_hint=(1, 1),
            halign="left", valign="middle", **text_style(),
        )
        title.bind(size=title.setter("text_size"))
        row.add_widget(title)
        return row

    def _build_hot_users(self):
        card = BoxLayout(
            orientation="vertical", spacing=dp(8),
            padding=(dp(10), dp(8), dp(10), dp(10)),
            size_hint=(1, None), height=dp(100),
        )
        with card.canvas.before:
            Color(1, 1, 1, 1)
            hot_bg = RoundedRectangle(
                pos=card.pos, size=card.size, radius=[dp(16)] * 4)
        card.bind(
            pos=lambda i, *_: setattr(hot_bg, "pos", i.pos),
            size=lambda i, *_: setattr(hot_bg, "size", i.size),
        )
        users_row = BoxLayout(spacing=dp(6), size_hint=(1, None), height=dp(82))
        for idx, name in enumerate(HOT_USER_NAMES):
            item = BoxLayout(orientation="vertical", spacing=dp(4),
                             size_hint=(1, 1))
            avatar_wrap = BoxLayout(size_hint=(1, None), height=dp(58))
            avatar_path = (
                HOT_USER_AVATARS[idx] if idx < len(HOT_USER_AVATARS) else "")
            if avatar_path and os.path.exists(avatar_path):
                avatar = KImage(
                    source=_circular_png(avatar_path),
                    size_hint=(None, None), size=(dp(54), dp(54)),
                    fit_mode="fill",
                )
                wrap = FloatLayout(size_hint=(1, 1))
                avatar.pos_hint = {"center_x": 0.5, "center_y": 0.5}
                wrap.add_widget(avatar)
                avatar_wrap.add_widget(wrap)
            else:
                ph = GrayPlaceholder(
                    radius=1,
                    size_hint=(None, None), size=(dp(54), dp(54)),
                )
                wrap = FloatLayout(size_hint=(1, 1))
                ph.pos_hint = {"center_x": 0.5, "center_y": 0.5}
                wrap.add_widget(ph)
                avatar_wrap.add_widget(wrap)
            item.add_widget(avatar_wrap)
            name_label = Label(
                text=name, font_size=sp(11),
                color=(0.22, 0.22, 0.22, 1),
                size_hint=(1, None), height=dp(16),
                halign="center", valign="middle", **text_style(),
            )
            name_label.bind(size=name_label.setter("text_size"))
            item.add_widget(name_label)
            users_row.add_widget(item)
        card.add_widget(users_row)
        return card

    def _build_post_card(self, post):
        """推荐帖子卡片：头像+标题 / 摘要 / 查看全部 / 点赞·评论·分享。"""
        card = BoxLayout(
            orientation="vertical", spacing=dp(3),
            padding=((dp(10), dp(8), dp(10), dp(6))),
            size_hint=(1, None),
        )
        card.bind(minimum_height=card.setter("height"))
        with card.canvas.before:
            Color(0.90, 0.97, 0.90, 1)
            post_bg = RoundedRectangle(
                pos=card.pos, size=card.size, radius=[dp(16)] * 4)
        card.bind(
            pos=lambda i, *_: setattr(post_bg, "pos", i.pos),
            size=lambda i, *_: setattr(post_bg, "size", i.size),
        )

        # 顶部：头像 + 标题
        top_row = BoxLayout(size_hint=(1, None), height=dp(48), spacing=dp(10))
        post_idx = COMMUNITY_POSTS.index(post) if post in COMMUNITY_POSTS else 0
        avatar_path = os.path.join(IMAGE_DIR, f"post{post_idx + 1}.jpg")
        if not os.path.exists(avatar_path):
            avatar_path = os.path.join(IMAGE_DIR, "nongming.png")
        if avatar_path and os.path.exists(avatar_path):
            avatar = KImage(
                source=_circular_png(avatar_path),
                size_hint=(None, None), size=(dp(44), dp(44)),
                fit_mode="fill",
            )
        else:
            avatar = GrayPlaceholder(
                radius=1, size_hint=(None, None), size=(dp(44), dp(44)))
        avatar_wrap = FloatLayout(size_hint=(None, 1), width=dp(48))
        avatar.pos_hint = {"center_x": 0.5, "center_y": 0.5}
        avatar_wrap.add_widget(avatar)
        top_row.add_widget(avatar_wrap)

        title_label = Label(
            text=post["title"], font_size=sp(16), bold=True,
            color=(0.08, 0.08, 0.08, 1),
            size_hint=(1, 1),
            halign="left", valign="middle", **text_style(),
        )
        title_label.bind(size=title_label.setter("text_size"))
        top_row.add_widget(title_label)
        card.add_widget(top_row)

        # 摘要（最多两行，紧凑）
        summary = Label(
            text=post["summary"], font_size=sp(13),
            color=(0.28, 0.28, 0.28, 1),
            size_hint=(1, None), height=dp(38),
            halign="left", valign="top", **text_style(),
        )
        summary.bind(size=summary.setter("text_size"))
        card.add_widget(summary)

        # 点击查看全部内容（右对齐）
        full_link_row = BoxLayout(size_hint=(1, None), height=dp(20))
        full_link_row.add_widget(Widget(size_hint=(1, 1)))
        full_link = UnderlineLabel(
            text="[u]点击查看全部内容 >[/u]",
            color=(0.45, 0.45, 0.45, 1), font_size=sp(12),
            size_hint=(None, 1), width=dp(150),
            halign="right", valign="middle", **text_style(),
        )
        full_link.bind(size=full_link.setter("text_size"))
        full_link.bind(on_press=lambda *_: self.open_community_detail(post))
        full_link_row.add_widget(full_link)
        card.add_widget(full_link_row)

        # 底部：点赞 / 评论 / 分享（固定尺寸 + pos_hint 居中，保证水平对齐）
        footer = BoxLayout(
            size_hint=(1, None), height=dp(28),
            spacing=dp(4),
        )

        liked = self._is_post_liked(post["id"])
        count_val = STORE_DB.get_post_like_count(post["id"])
        like_key = self._post_key(post)
        comment_count = len(STORE_DB.get_post_comments(like_key))

        like_off = LIKE_ICON_OFF
        like_on = LIKE_ICON_ON

        # —— 点赞 ——
        heart_img = KImage(
            source=like_on if liked else like_off,
            size_hint=(None, None), size=(dp(22), dp(22)),
            allow_stretch=True, keep_ratio=True,
            pos_hint={"center_y": 0.5, "x": 0},
        )
        like_count_lbl = Label(
            text=f"{count_val}",
            font_size=sp(13), color=(0.18, 0.18, 0.18, 1),
            size_hint=(None, None), size=(dp(42), dp(22)),
            pos_hint={"center_y": 0.5, "right": 1},
            halign="left", valign="middle", **text_style(),
        )
        like_count_lbl.bind(size=like_count_lbl.setter("text_size"))

        def make_like_handler(p, img, count_lbl, off_src, on_src):
            def handler(*_):
                app = App.get_running_app()
                username = app.current_user["username"] if app.current_user else ""
                if not username:
                    show_toast("请先登录")
                    return
                liked_now = STORE_DB.toggle_post_like(username, p["id"])
                img.source = on_src if liked_now else off_src
                img.reload()
                count = STORE_DB.get_post_like_count(p["id"])
                count_lbl.text = str(count)

            return handler

        like_wrap = FloatLayout(size_hint=(None, 1), width=dp(70))
        like_wrap.add_widget(heart_img)
        like_wrap.add_widget(like_count_lbl)
        like_btn = Button(
            background_normal="", background_down="",
            background_color=(0, 0, 0, 0),
            size_hint=(1, 1),
        )
        like_btn.bind(on_press=make_like_handler(
            post, heart_img, like_count_lbl, like_off, like_on))
        like_wrap.add_widget(like_btn)
        footer.add_widget(like_wrap)

        # —— 评论数 ——
        if os.path.exists(COMMENT_ICON):
            comment_icon = KImage(
                source=COMMENT_ICON,
                size_hint=(None, None), size=(dp(20), dp(20)),
                allow_stretch=True, keep_ratio=True,
                pos_hint={"center_y": 0.5, "x": 0},
            )
        else:
            comment_icon = Widget(
                size_hint=(None, None), size=(dp(20), dp(20)),
                pos_hint={"center_y": 0.5, "x": 0},
            )
            comment_icon.bind(pos=_draw_comment_icon,
                              size=_draw_comment_icon)
        comment_lbl = Label(
            text=f"{comment_count}",
            font_size=sp(13), color=(0.18, 0.18, 0.18, 1),
            size_hint=(None, None), size=(dp(34), dp(22)),
            pos_hint={"center_y": 0.5, "right": 1},
            halign="left", valign="middle", **text_style(),
        )
        comment_lbl.bind(size=comment_lbl.setter("text_size"))
        comment_wrap = FloatLayout(size_hint=(None, 1), width=dp(58))
        comment_wrap.add_widget(comment_icon)
        comment_wrap.add_widget(comment_lbl)
        comment_btn = Button(
            background_normal="", background_down="",
            background_color=(0, 0, 0, 0),
            size_hint=(1, 1),
        )
        comment_btn.bind(
            on_press=lambda *_: self.open_community_detail(post))
        comment_wrap.add_widget(comment_btn)
        footer.add_widget(comment_wrap)

        footer.add_widget(Widget(size_hint=(1, 1)))

        # —— 分享 ——
        if os.path.exists(SHARE_ICON):
            share_icon = KImage(
                source=SHARE_ICON,
                size_hint=(None, None), size=(dp(22), dp(22)),
                allow_stretch=True, keep_ratio=True,
                pos_hint={"center_x": 0.5, "center_y": 0.5},
            )
        else:
            share_icon = Widget(
                size_hint=(None, None), size=(dp(22), dp(22)),
                pos_hint={"center_x": 0.5, "center_y": 0.5},
            )
            share_icon.bind(pos=_draw_share_icon, size=_draw_share_icon)
        share_wrap = FloatLayout(size_hint=(None, 1), width=dp(36))
        share_wrap.add_widget(share_icon)
        share_btn = Button(
            size_hint=(1, 1),
            background_normal="", background_down="",
            background_color=(0, 0, 0, 0),
        )
        share_btn.bind(on_press=lambda *_: show_toast("分享功能即将推出"))
        share_wrap.add_widget(share_btn)
        footer.add_widget(share_wrap)

        card.add_widget(footer)
        return card

    def _build_kandian(self):
        """看点：两张固定统一尺寸的圆角图片 + 标题。"""
        outer = BoxLayout(
            spacing=dp(12), size_hint=(1, None), height=dp(172),
        )
        for idx, (img_path, title) in enumerate(
                zip(KANDIAN_IMAGES, KANDIAN_TITLES)):
            item = BoxLayout(
                orientation="vertical", spacing=dp(6),
                size_hint=(1, 1),
            )
            from config import COMMUNITY_ARTICLES as _articles
            article_key = (
                "article:planting" if idx == 0 else "article:control")
            article = _articles.get(article_key, {})

            img = RoundedImage(
                source=img_path if img_path and os.path.exists(img_path) else "",
                radius=dp(12),
                size_hint=(1, None), height=dp(140),
                on_press=lambda *_, a=article: self.open_community_detail(a),
            )
            item.add_widget(img)

            title_lbl = Label(
                text=title, font_size=sp(14), bold=True,
                color=(0.12, 0.12, 0.12, 1),
                size_hint=(1, None), height=dp(24),
                halign="center", valign="middle", **text_style(),
            )
            title_lbl.bind(size=title_lbl.setter("text_size"))
            item.add_widget(title_lbl)
            outer.add_widget(item)
        return outer

    def _on_search_text(self, _instance, value):
        if not value.strip():
            self.refresh_default_content()

    def search_posts(self, _instance=None):
        keyword = self.community_search_input.text.strip()
        if not keyword:
            self.refresh_default_content()
            return
        keyword_lower = keyword.lower()
        results = [
            post for post in COMMUNITY_POSTS
            if keyword_lower in post["title"].lower()
            or keyword_lower in post["full_text"].lower()
            or keyword_lower in post["summary"].lower()
        ]
        self.content_box.clear_widgets()
        header = Label(
            text=f'找到{len(results)}条关于"{keyword}"的帖子' if results else "未找到相关帖子",
            font_size=sp(15), color=(0.25, 0.25, 0.25, 1),
            size_hint=(1, None), height=dp(34),
            halign="left", valign="middle", **text_style(),
        )
        header.bind(size=header.setter("text_size"))
        self.content_box.add_widget(header)
        for post in results:
            self.content_box.add_widget(self._build_search_result_card(post))

    def _build_search_result_card(self, post):
        card = BoxLayout(
            orientation="vertical", spacing=dp(6),
            padding=((dp(14), dp(12), dp(14), dp(10))),
            size_hint=(1, None),
        )
        card.bind(minimum_height=card.setter("height"))
        with card.canvas.before:
            Color(0.90, 0.97, 0.90, 1)
            card_bg = RoundedRectangle(
                pos=card.pos, size=card.size, radius=[dp(16)] * 4)
        card.bind(
            pos=lambda i, *_: setattr(card_bg, "pos", i.pos),
            size=lambda i, *_: setattr(card_bg, "size", i.size),
        )
        title_label = Label(
            text=post["title"], font_size=sp(16), bold=True,
            color=(0.08, 0.08, 0.08, 1),
            size_hint=(1, None), height=dp(26),
            halign="left", valign="middle", **text_style(),
        )
        title_label.bind(size=title_label.setter("text_size"))
        card.add_widget(title_label)

        summary = Label(
            text=post["summary"], font_size=sp(13),
            color=(0.28, 0.28, 0.28, 1),
            size_hint=(1, None), height=dp(38),
            halign="left", valign="top", **text_style(),
        )
        summary.bind(size=summary.setter("text_size"))
        card.add_widget(summary)

        link_row = BoxLayout(size_hint=(1, None), height=dp(20))
        link_row.add_widget(Widget(size_hint=(1, 1)))
        link = UnderlineLabel(
            text="[u]点击查看全部内容 >[/u]",
            color=(0.45, 0.45, 0.45, 1), font_size=sp(12),
            size_hint=(None, 1), width=dp(150),
            halign="right", valign="middle", **text_style(),
        )
        link.bind(size=link.setter("text_size"))
        link.bind(on_press=lambda *_: self.open_community_detail(post))
        link_row.add_widget(link)
        card.add_widget(link_row)
        return card

    def cancel_search(self, _instance=None):
        self.community_search_input.text = ""
        self.community_search_input.focus = False
        self.refresh_default_content()

    @staticmethod
    def _post_key(post):
        return post.get("key") or f"post:{post['id']}"

    def _is_post_liked(self, post_id):
        app = App.get_running_app()
        username = app.current_user["username"] if app.current_user else ""
        return STORE_DB.has_liked_post(username, post_id)

    def _toggle_like(self, post, button, count_label):
        app = App.get_running_app()
        username = app.current_user["username"] if app.current_user else ""
        liked = STORE_DB.toggle_post_like(username, post["id"])
        button.color = GREEN if liked else (0.45, 0.45, 0.45, 1)
        count = STORE_DB.get_post_like_count(post["id"])
        count_label.text = f"{count}+" if count >= 999 else str(count)

    def open_community_detail(self, post):
        if not post:
            return
        detail_data = dict(post)
        detail_data["key"] = self._post_key(detail_data)
        detail_screen = self.manager.get_screen("community_detail")
        detail_screen.set_item(detail_data, return_screen="community")
        self.manager.current = "community_detail"

    def sync_product_views(self, tab_name=None):
        self.refresh_default_content()

    def _update_bg(self, *_args):
        self.bg_rect.pos = self.layout.pos
        self.bg_rect.size = self.layout.size

    def _update_layout(self, *_args):
        nav_h = self.bottom_nav.height
        top_h = self.top_bar.height
        available = max(dp(200), self.height - nav_h - top_h)
        self.scroll.height = available
        self.scroll.pos = (0, nav_h)
        self.top_bar.pos = (0, self.height - top_h)
        self.top_bar.size = (self.width, top_h)


class CommunityDetailScreen(Screen):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.name = "community_detail"
        self.item_data = None
        self.return_screen = "community"
        self.build_ui()

    def build_ui(self):
        self.layout = FloatLayout()
        self.add_widget(self.layout)
        with self.layout.canvas.before:
            Color(0.96, 0.98, 0.96, 1)
            self.bg_rect = Rectangle(pos=self.layout.pos, size=self.layout.size)
        self.layout.bind(pos=self._update_bg, size=self._update_bg)

        # 顶部栏：白底 + 深色返回箭头 + 标题（与社区页风格一致）
        self.top_bar = FloatLayout(size_hint=(1, None), height=dp(56),
                                   pos_hint={"x": 0, "top": 1})
        with self.top_bar.canvas.before:
            Color(1, 1, 1, 1)
            self.top_bar_rect = Rectangle(
                pos=self.top_bar.pos, size=self.top_bar.size)
        self.top_bar.bind(
            pos=self._update_top_bar, size=self._update_top_bar)
        self.layout.add_widget(self.top_bar)

        self.back_btn = IconButton(
            text="<", font_size=sp(30), color=(0.1, 0.1, 0.1, 1),
            size_hint=(None, None), size=(dp(56), dp(56)),
            pos_hint={"x": 0.03, "center_y": 0.5},
            **text_style(),
        )
        self.back_btn.bind(on_press=self.go_back)
        self.top_bar.add_widget(self.back_btn)

        self.title_label = Label(
            text="详情", font_size=sp(20), bold=True, color=(0.08, 0.08, 0.08, 1),
            size_hint=(0.6, None), height=dp(36),
            pos_hint={"center_x": 0.52, "center_y": 0.5},
            halign="center", valign="middle", **text_style(),
        )
        self.title_label.bind(size=self.title_label.setter("text_size"))
        self.top_bar.add_widget(self.title_label)

        # 注意：不能设置 pos_hint，否则会覆盖手动设置的 pos
        self.scroll_view = ScrollView(
            size_hint=(1, None), do_scroll_x=False, bar_width=dp(4),
        )
        self.layout.add_widget(self.scroll_view)

        self.content_box = BoxLayout(
            orientation="vertical", spacing=dp(10),
            padding=(dp(14), dp(10), dp(14), dp(110)),
            size_hint=(1, None),
        )
        self.content_box.bind(
            minimum_height=self.content_box.setter("height"))
        self.scroll_view.add_widget(self.content_box)

        # 作者行（无作者时高度置 0，不占空白）
        self.author_label = Label(
            text="", font_size=sp(13), color=GREEN,
            size_hint=(1, None), height=dp(0),
            halign="left", valign="middle", **text_style(),
        )
        self.author_label.bind(size=self.author_label.setter("text_size"))
        self.content_box.add_widget(self.author_label)

        # 正文白色圆角卡片：标题 + 正文
        body_card = BoxLayout(
            orientation="vertical", spacing=dp(8),
            padding=(dp(14), dp(12), dp(14), dp(14)),
            size_hint=(1, None),
        )
        body_card.bind(minimum_height=body_card.setter("height"))
        with body_card.canvas.before:
            Color(1, 1, 1, 1)
            self.body_card_bg = RoundedRectangle(
                pos=body_card.pos, size=body_card.size, radius=[dp(14)] * 4)
        body_card.bind(
            pos=lambda i, *_: setattr(self.body_card_bg, "pos", i.pos),
            size=lambda i, *_: setattr(self.body_card_bg, "size", i.size),
        )

        self.post_title_label = Label(
            text="", font_size=sp(19), bold=True,
            color=(0.08, 0.08, 0.08, 1), size_hint=(1, None),
            halign="left", valign="top", **text_style(),
        )
        self.post_title_label.bind(
            width=self._sync_label_width,
            texture_size=self._sync_dynamic_label,
        )
        body_card.add_widget(self.post_title_label)

        self.body_label = Label(
            text="", font_size=sp(15), color=(0.15, 0.15, 0.15, 1),
            size_hint=(1, None), halign="left", valign="top", **text_style(),
        )
        self.body_label.bind(
            width=self._sync_label_width,
            texture_size=self._sync_dynamic_label,
        )
        body_card.add_widget(self.body_label)
        self.content_box.add_widget(body_card)

        # 若帖子带配图（full_image 字段），展示统一尺寸的圆角图片
        self.post_image = RoundedImage(radius=dp(14), size_hint=(1, None),
                                       height=dp(170))
        self.content_box.add_widget(self.post_image)

        # 互动统计行：点赞 + 点赞数 + 浏览量（位于历史评论上方）
        stats_row = BoxLayout(
            size_hint=(1, None), height=dp(32), spacing=dp(6),
        )
        self.like_btn = LikeImageButton(
            source_off=LIKE_ICON_OFF, source_on=LIKE_ICON_ON,
            size_hint=(None, 1), width=dp(24),
        )
        self.like_btn.bind(on_press=self.toggle_like)
        stats_row.add_widget(self.like_btn)

        self.like_count_label = Label(
            text="0", size_hint=(None, 1), width=dp(32),
            color=(0.2, 0.2, 0.2, 1),
            halign="left", valign="middle", **text_style(),
        )
        self.like_count_label.bind(
            size=self.like_count_label.setter("text_size"))
        stats_row.add_widget(self.like_count_label)

        stats_row.add_widget(Widget(size_hint=(1, 1)))

        self.view_label = Label(
            text="浏览量 0", size_hint=(None, 1), width=dp(110),
            color=(0.35, 0.35, 0.35, 1),
            halign="right", valign="middle", **text_style(),
        )
        self.view_label.bind(size=self.view_label.setter("text_size"))
        stats_row.add_widget(self.view_label)
        self.content_box.add_widget(stats_row)

        self.comment_title = Label(
            text="历史评论", font_size=sp(16), bold=True,
            color=(0.08, 0.08, 0.08, 1),
            size_hint=(1, None), height=dp(28),
            halign="left", valign="middle", **text_style(),
        )
        self.comment_title.bind(size=self.comment_title.setter("text_size"))
        self.content_box.add_widget(self.comment_title)

        self.comment_list = BoxLayout(
            orientation="vertical", spacing=dp(8), size_hint=(1, None))
        self.comment_list.bind(
            minimum_height=self.comment_list.setter("height"))
        self.content_box.add_widget(self.comment_list)

        # 底部操作栏：白底 + 输入框占满剩余宽度 + 绿色圆角发表按钮
        self.action_bar = BoxLayout(
            orientation="horizontal", size_hint=(1, None), height=dp(56),
            spacing=dp(10), padding=(dp(12), dp(10), dp(12), dp(10)),
            pos_hint={"x": 0, "y": 0},
        )
        with self.action_bar.canvas.before:
            Color(1, 1, 1, 1)
            self.action_bar_rect = Rectangle(
                pos=self.action_bar.pos, size=self.action_bar.size)
        self.action_bar.bind(
            pos=self._update_action_bar,
            size=self._update_action_bar,
        )
        self.layout.add_widget(self.action_bar)

        self.comment_input = TextInput(
            hint_text="写下你的评论", multiline=False, size_hint=(1, 1),
            padding=(dp(12), dp(12), dp(12), dp(12)), font_size=sp(14),
            input_type="text", keyboard_suggestions=True,
            write_tab=False,
            background_normal="", background_active="",
            background_color=(0.93, 0.96, 0.93, 1),
            foreground_color=(0.12, 0.12, 0.12, 1),
            hint_text_color=(0.6, 0.6, 0.6, 1),
            cursor_color=GREEN,
            **text_style(),
        )
        self.action_bar.add_widget(self.comment_input)

        self.publish_btn = RoundedButton(
            text="发表", size_hint=(None, 1), width=dp(84), font_size=sp(14),
            color=(1, 1, 1, 1), fill_color=GREEN,
            **text_style(),
        )
        self.publish_btn.bind(on_press=self.publish_comment)
        self.action_bar.add_widget(self.publish_btn)

        bind_deferred_layout(self.layout, self._update_scroll_height)
        Clock.schedule_once(lambda dt: self._update_scroll_height(), 0)

    def _update_bg(self, *_args):
        self.bg_rect.pos = self.layout.pos
        self.bg_rect.size = self.layout.size

    def _update_top_bar(self, *_args):
        self.top_bar_rect.pos = self.top_bar.pos
        self.top_bar_rect.size = self.top_bar.size

    def _update_action_bar(self, *_args):
        self.action_bar_rect.pos = self.action_bar.pos
        self.action_bar_rect.size = self.action_bar.size

    def _update_scroll_height(self, *_args):
        self.scroll_view.height = max(
            dp(200), self.height - self.top_bar.height - self.action_bar.height)
        self.scroll_view.pos = (0, self.action_bar.height)

    def _sync_label_width(self, instance, _value):
        instance.text_size = (instance.width, None)

    def _sync_dynamic_label(self, instance, _value):
        instance.height = max(dp(28), instance.texture_size[1] + dp(6))

    def _build_comment_widget(self, comment):
        wrapper = BoxLayout(
            orientation="vertical", spacing=dp(4),
            padding=(dp(12), dp(10), dp(12), dp(10)),
            size_hint=(1, None),
        )
        wrapper.bind(minimum_height=wrapper.setter("height"))
        with wrapper.canvas.before:
            Color(0.93, 0.97, 0.93, 1)
            bg_rect = RoundedRectangle(
                pos=wrapper.pos, size=wrapper.size, radius=[dp(12)] * 4)
        wrapper.bind(
            pos=lambda i, r=bg_rect, *_: setattr(r, "pos", i.pos),
            size=lambda i, r=bg_rect, *_: setattr(r, "size", i.size),
        )
        header = Label(
            text=f"{comment['username']}  {comment['comment_date']}",
            font_size=sp(12), color=GREEN,
            size_hint=(1, None), height=dp(20),
            halign="left", valign="middle", **text_style(),
        )
        header.bind(size=header.setter("text_size"))
        wrapper.add_widget(header)
        body = Label(
            text=comment["comment"], font_size=sp(14),
            color=(0.1, 0.1, 0.1, 1),
            size_hint=(1, None), halign="left", valign="top",
            **text_style(),
        )
        body.bind(
            width=self._sync_label_width,
            texture_size=self._sync_dynamic_label,
        )
        wrapper.add_widget(body)
        return wrapper

    def set_item(self, item_data, return_screen="community"):
        self.item_data = dict(item_data)
        self.return_screen = return_screen
        self.title_label.text = "详情"
        username = self.item_data.get("username", "")
        if username:
            self.author_label.text = f"@{username}"
            self.author_label.height = dp(22)
        else:
            self.author_label.text = ""
            self.author_label.height = dp(0)  # 无作者时不留空白
        self.post_title_label.text = self.item_data.get("title", "")
        self.body_label.text = self.item_data.get("full_text", "")
        # 帖子带配图则展示，否则隐藏（不留空白占位）
        img_path = self.item_data.get("image", "")
        if img_path and img_path != "gray_placeholder" and os.path.exists(img_path):
            self.post_image.set_source(img_path)
            self.post_image.reload()
            self.post_image.height = dp(170)
            self.post_image.opacity = 1
        else:
            self.post_image.height = dp(0)
            self.post_image.opacity = 0
        STORE_DB.increment_post_view(self.item_data["key"])
        self.refresh_stats()
        self.refresh_comments()
        self.scroll_view.scroll_y = 1

    def refresh_stats(self):
        if not self.item_data:
            return
        app = App.get_running_app()
        username = app.current_user["username"] if app and app.current_user else ""
        liked = STORE_DB.has_liked_post(username, self.item_data["id"])
        if hasattr(self.like_btn, "set_liked"):
            self.like_btn.set_liked(liked)
        self.like_count_label.text = str(
            STORE_DB.get_post_like_count(self.item_data["id"]))
        self.view_label.text = (
            f"浏览量 {STORE_DB.get_post_view_count(self.item_data['key'])}")

    def refresh_comments(self):
        self.comment_list.clear_widgets()
        if not self.item_data:
            return
        comments = STORE_DB.get_post_comments(self.item_data["key"])
        if not comments:
            empty_label = Label(
                text="暂无评论，快来抢沙发",
                font_size=sp(14), color=(0.45, 0.45, 0.45, 1),
                size_hint=(1, None), height=dp(30),
                halign="left", valign="middle", **text_style(),
            )
            empty_label.bind(size=empty_label.setter("text_size"))
            self.comment_list.add_widget(empty_label)
            return
        for comment in comments:
            self.comment_list.add_widget(
                self._build_comment_widget(comment))

    def publish_comment(self, _instance=None):
        from utils import normalize_comment_text
        from config import DEFAULT_COMMENT_USER
        comment_text = normalize_comment_text(self.comment_input.text)
        if not comment_text or not self.item_data:
            show_toast("请输入评论内容")
            return
        app = App.get_running_app()
        username = (app.current_user["username"]
                    if app and app.current_user else DEFAULT_COMMENT_USER)
        STORE_DB.add_post_comment(
            self.item_data["key"], comment_text, username)
        self.comment_input.text = ""
        self.refresh_comments()
        self.scroll_view.scroll_y = 0
        show_toast("评论已发表")

    def toggle_like(self, _instance=None):
        if not self.item_data:
            return
        app = App.get_running_app()
        username = (app.current_user["username"]
                    if app and app.current_user else "")
        if not username:
            show_toast("请先登录")
            return
        STORE_DB.toggle_post_like(username, self.item_data["id"])
        self.refresh_stats()
        if self.manager and self.manager.has_screen("community"):
            community_screen = self.manager.get_screen("community")
            if community_screen.community_search_input.text.strip():
                community_screen.search_posts()
            else:
                community_screen.refresh_default_content()

    def go_back(self, _instance=None):
        if self.manager and self.manager.has_screen(self.return_screen):
            self.manager.current = self.return_screen

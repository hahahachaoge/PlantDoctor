import os


from config import (GREEN, COMMUNITY_POSTS, COMMUNITY_ARTICLES,
                    LIKE_ICON_OFF, LIKE_ICON_ON, IMAGE_DIR,
                    KANDIAN_IMAGES, KANDIAN_TITLES)



from kivy.app import App
from kivy.clock import Clock
from kivy.graphics import Color, Rectangle, RoundedRectangle, Ellipse, Line
from kivy.metrics import dp, sp
from kivy.uix.behaviors import ButtonBehavior
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.button import Button
from kivy.uix.floatlayout import FloatLayout
from kivy.uix.image import Image
from kivy.uix.label import Label
from kivy.uix.screenmanager import Screen
from kivy.uix.scrollview import ScrollView
from kivy.uix.textinput import TextInput
from kivy.uix.widget import Widget

from config import (GREEN, COMMUNITY_POSTS, COMMUNITY_ARTICLES,
                    LIKE_ICON_OFF, LIKE_ICON_ON, IMAGE_DIR)
from database.store_db import STORE_DB
from utils import text_style, update_nav_rect, show_toast
from widgets.base_widgets import (
    UnderlineLabel, IconButton, CircleImage, GrayPlaceholder, LikeImageButton,
)
from screens.home import HomeScreen, _update_camera_btn

# 热门用户头像图片（放在 image/ 目录下）
HOT_USER_AVATARS = [
    os.path.join(IMAGE_DIR, "user1.jpg"),
    os.path.join(IMAGE_DIR, "user2.jpg"),
    os.path.join(IMAGE_DIR, "user3.jpg"),
    os.path.join(IMAGE_DIR, "user4.jpg"),
    os.path.join(IMAGE_DIR, "user5.jpg"),
]
HOT_USER_NAMES = ["张大叔", "葡萄园主", "青年农人", "采茶阿姨", "老王头"]


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

        # 顶部栏
        self.top_bar = self._build_top_bar()
        self.layout.add_widget(self.top_bar)

        # 滚动内容
        self.scroll = ScrollView(
            size_hint=(1, None), do_scroll_x=False,
            pos_hint={"x": 0, "y": 0},
        )
        self.layout.add_widget(self.scroll)
        self.content_box = BoxLayout(
            orientation="vertical", spacing=dp(12),
            padding=(dp(12), dp(8), dp(12), dp(18)),
            size_hint=(1, None),
        )
        self.content_box.bind(minimum_height=self.content_box.setter("height"))
        self.scroll.add_widget(self.content_box)

        self.refresh_default_content()

        # 底部导航
        self.bottom_nav = HomeScreen._build_bottom_nav(self)
        self.layout.add_widget(self.bottom_nav)

        self.layout.bind(size=self._update_layout)
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

        # 社区标题 + 下拉箭头
        title_box = BoxLayout(size_hint=(None, 1), width=dp(72), spacing=dp(4))
        title_label = Label(
            text="社区", font_size=sp(20), bold=True,
            color=(0.08, 0.08, 0.08, 1),
            size_hint=(None, 1), width=dp(48),
            halign="left", valign="middle", **text_style(),
        )
        title_label.bind(size=title_label.setter("text_size"))
        arrow = Label(
            text="v", font_size=sp(12), color=(0.4, 0.4, 0.4, 1),
            size_hint=(None, 1), width=dp(16),
            halign="center", valign="middle",
        )
        title_box.add_widget(title_label)
        title_box.add_widget(arrow)
        bar.add_widget(title_box)

        # 搜索框
        search_wrap = BoxLayout(size_hint=(1, 1))
        with search_wrap.canvas.before:
            Color(0.94, 0.94, 0.94, 1)
            self.search_bg = RoundedRectangle(
                pos=search_wrap.pos, size=search_wrap.size, radius=[dp(18)] * 4)
        search_wrap.bind(
            pos=lambda i, *_: setattr(self.search_bg, "pos", i.pos),
            size=lambda i, *_: setattr(self.search_bg, "size", i.size),
        )
        search_icon = Label(
            text="Q", font_size=sp(14), color=(0.55, 0.55, 0.55, 1),
            size_hint=(None, 1), width=dp(28),
            halign="center", valign="middle",
        )
        search_wrap.add_widget(search_icon)
        self.community_search_input = TextInput(
            hint_text="点击搜索关键词",
            multiline=False, input_type="text",
            keyboard_suggestions=True,
            background_normal="", background_active="",
            background_color=(0, 0, 0, 0),
            foreground_color=(0.12, 0.12, 0.12, 1),
            hint_text_color=(0.65, 0.65, 0.65, 1),
            cursor_color=(0.12, 0.12, 0.12, 1),
            padding=(0, dp(10), dp(10), dp(10)),
            font_size=sp(14), **text_style(),
        )
        self.community_search_input.bind(
            on_text_validate=self.search_posts,
            text=self._on_search_text,
        )
        search_wrap.add_widget(self.community_search_input)
        bar.add_widget(search_wrap)

        # 铃铛按钮
        bell_btn = Button(
            text="bell", font_size=sp(13),
            color=(0.3, 0.3, 0.3, 1),
            background_normal="", background_down="",
            background_color=(0, 0, 0, 0),
            size_hint=(None, 1), width=dp(36),
            **text_style(),
        )
        bell_btn.bind(on_press=lambda *_: show_toast("暂无新消息"))
        bar.add_widget(bell_btn)

        # 头像
        app = App.get_running_app()
        default_avatar = os.path.join(IMAGE_DIR, "OIP-C.png")
        if os.path.exists(default_avatar):
            avatar = CircleImage(
                source=default_avatar,
                size_hint=(None, None), size=(dp(34), dp(34)),
                allow_stretch=True, keep_ratio=False,
            )
            avatar_wrap = FloatLayout(size_hint=(None, 1), width=dp(38))
            avatar.pos_hint = {"center_x": 0.5, "center_y": 0.5}
            avatar_wrap.add_widget(avatar)
            bar.add_widget(avatar_wrap)
        return bar

    def refresh_default_content(self):
        self.content_box.clear_widgets()

        # 热门用户区块
        self.content_box.add_widget(self._build_section_header("热门用户"))
        self.content_box.add_widget(self._build_hot_users())

        # 推荐区块标题
        self.content_box.add_widget(self._build_section_header("推 荐"))

        # 帖子列表
        for post in COMMUNITY_POSTS:
            self.content_box.add_widget(self._build_post_card(post))

        # 看点区块
        self.content_box.add_widget(self._build_section_header("看 点"))
        self.content_box.add_widget(self._build_kandian())

    def _build_section_header(self, text):
        row = BoxLayout(size_hint=(1, None), height=dp(36), spacing=dp(8),
                        padding=(dp(4), 0, 0, 0))
        # 绿色双箭头
        arrow = Label(
            text=">>", font_size=sp(14), bold=True, color=GREEN,
            size_hint=(None, 1), width=dp(28),
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
            orientation="vertical", spacing=dp(10),
            padding=(dp(12), dp(10), dp(12), dp(12)),
            size_hint=(1, None), height=dp(110),
        )
        with card.canvas.before:
            Color(1, 1, 1, 1)
            hot_bg = RoundedRectangle(
                pos=card.pos, size=card.size, radius=[dp(16)] * 4)
        card.bind(
            pos=lambda i, *_: setattr(hot_bg, "pos", i.pos),
            size=lambda i, *_: setattr(hot_bg, "size", i.size),
        )
        users_row = BoxLayout(spacing=dp(8), size_hint=(1, None), height=dp(96))
        for idx, name in enumerate(HOT_USER_NAMES):
            item = BoxLayout(orientation="vertical", spacing=dp(6), size_hint=(1, 1))
            avatar_wrap = BoxLayout(size_hint=(1, None), height=dp(62))
            avatar_path = HOT_USER_AVATARS[idx] if idx < len(HOT_USER_AVATARS) else ""
            if avatar_path and os.path.exists(avatar_path):
                avatar = CircleImage(
                    source=avatar_path,
                    size_hint=(None, None), size=(dp(56), dp(56)),
                    allow_stretch=True, keep_ratio=False,
                )
                wrap = FloatLayout(size_hint=(1, 1))
                avatar.pos_hint = {"center_x": 0.5, "center_y": 0.5}
                wrap.add_widget(avatar)
                avatar_wrap.add_widget(wrap)
            else:
                ph = GrayPlaceholder(
                    radius=1,
                    size_hint=(None, None), size=(dp(56), dp(56)),
                )
                wrap = FloatLayout(size_hint=(1, 1))
                ph.pos_hint = {"center_x": 0.5, "center_y": 0.5}
                wrap.add_widget(ph)
                avatar_wrap.add_widget(wrap)
            item.add_widget(avatar_wrap)
            name_label = Label(
                text=name, font_size=sp(11),
                color=(0.22, 0.22, 0.22, 1),
                size_hint=(1, None), height=dp(18),
                halign="center", valign="middle", **text_style(),
            )
            name_label.bind(size=name_label.setter("text_size"))
            item.add_widget(name_label)
            users_row.add_widget(item)
        card.add_widget(users_row)
        return card

    def _build_post_card(self, post):
        card = BoxLayout(
            orientation="vertical", spacing=dp(8),
            padding=(dp(14), dp(14), dp(14), dp(12)),
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
        top_row = BoxLayout(size_hint=(1, None), height=dp(56), spacing=dp(10))

        post_idx = COMMUNITY_POSTS.index(post) if post in COMMUNITY_POSTS else 0
        avatar_path = os.path.join(IMAGE_DIR, f"post{post_idx + 1}.jpg")
        if not os.path.exists(avatar_path):
            avatar_path = os.path.join(IMAGE_DIR, "nongming.png")

        if avatar_path and os.path.exists(avatar_path):
            avatar = CircleImage(
                source=avatar_path,
                size_hint=(None, None), size=(dp(48), dp(48)),
                allow_stretch=True, keep_ratio=False,
            )
        else:
            avatar = GrayPlaceholder(
                radius=1,
                size_hint=(None, None), size=(dp(48), dp(48)),
            )
        avatar_wrap = FloatLayout(size_hint=(None, 1), width=dp(52))
        avatar.pos_hint = {"center_x": 0.5, "center_y": 0.5}
        avatar_wrap.add_widget(avatar)
        top_row.add_widget(avatar_wrap)

        title_label = Label(
            text=post["title"], font_size=sp(17), bold=True,
            color=(0.08, 0.08, 0.08, 1),
            size_hint=(1, 1),
            halign="left", valign="middle", **text_style(),
        )
        title_label.bind(size=title_label.setter("text_size"))
        top_row.add_widget(title_label)
        card.add_widget(top_row)

        # 摘要
        summary = Label(
            text=post["summary"], font_size=sp(14),
            color=(0.28, 0.28, 0.28, 1),
            size_hint=(1, None), height=dp(44),
            halign="left", valign="top", **text_style(),
        )
        summary.bind(size=summary.setter("text_size"))
        card.add_widget(summary)

        # 查看全部
        full_link_row = BoxLayout(size_hint=(1, None), height=dp(24))
        full_link_row.add_widget(Widget(size_hint=(1, 1)))
        full_link = UnderlineLabel(
            text="[u]点击查看全部内容 >[/u]",
            color=(0.45, 0.45, 0.45, 1), font_size=sp(13),
            size_hint=(None, 1), width=dp(160),
            halign="right", valign="middle", **text_style(),
        )
        full_link.bind(size=full_link.setter("text_size"))
        full_link.bind(on_press=lambda *_: self.open_community_detail(post))
        full_link_row.add_widget(full_link)
        card.add_widget(full_link_row)

        # 底部：点赞 + 评论 + 分享
        footer = BoxLayout(size_hint=(1, None), height=dp(40), spacing=dp(16))

        liked = self._is_post_liked(post["id"])
        like_row = BoxLayout(size_hint=(None, 1), width=dp(100), spacing=dp(4))

        # 点赞图标
        like_icon = Label(
            text="like", font_size=sp(18),
            color=GREEN if liked else (0.45, 0.45, 0.45, 1),
            size_hint=(None, 1), width=dp(24),
            halign="center", valign="middle",
        )
        like_count = Label(
            text=f"{STORE_DB.get_post_like_count(post['id'])}+",
            font_size=sp(14), color=(0.35, 0.35, 0.35, 1),
            size_hint=(None, 1), width=dp(56),
            halign="left", valign="middle", **text_style(),
        )
        like_count.bind(size=like_count.setter("text_size"))

        like_btn = Button(
            size_hint=(1, 1),
            background_normal="", background_down="",
            background_color=(0, 0, 0, 0),
        )

        def make_like_handler(p, icon, count_lbl):
            def handler(*_):
                self._toggle_like_icon(p, icon, count_lbl)

            return handler

        like_btn.bind(on_press=make_like_handler(post, like_icon, like_count))
        like_wrap = FloatLayout(size_hint=(None, 1), width=dp(100))
        inner_row = BoxLayout(size_hint=(1, 1), spacing=dp(4))
        inner_row.add_widget(like_icon)
        inner_row.add_widget(like_count)
        like_wrap.add_widget(inner_row)
        like_wrap.add_widget(like_btn)
        footer.add_widget(like_wrap)

        # 评论图标
        comment_row = BoxLayout(size_hint=(None, 1), width=dp(100), spacing=dp(4))
        comment_icon = Label(
            text="msg", font_size=sp(17),
            color=(0.45, 0.45, 0.45, 1),
            size_hint=(None, 1), width=dp(24),
            halign="center", valign="middle",
        )
        comment_count = Label(
            text=f"{post.get('comments', '0')}",
            font_size=sp(14), color=(0.35, 0.35, 0.35, 1),
            size_hint=(None, 1), width=dp(56),
            halign="left", valign="middle", **text_style(),
        )
        comment_count.bind(size=comment_count.setter("text_size"))
        comment_row.add_widget(comment_icon)
        comment_row.add_widget(comment_count)
        footer.add_widget(comment_row)

        # 分享图标
        share_btn = Button(
            text="share", font_size=sp(17),
            color=(0.45, 0.45, 0.45, 1),
            background_normal="", background_down="",
            background_color=(0, 0, 0, 0),
            size_hint=(None, 1), width=dp(36),
        )
        share_btn.bind(on_press=lambda *_: show_toast("分享功能即将推出"))
        footer.add_widget(share_btn)
        footer.add_widget(Widget(size_hint=(1, 1)))
        card.add_widget(footer)
        return card

    def _toggle_like_icon(self, post, icon, count_label):
        app = App.get_running_app()
        username = app.current_user["username"] if app.current_user else ""
        liked = STORE_DB.toggle_post_like(username, post["id"])
        icon.color = GREEN if liked else (0.45, 0.45, 0.45, 1)
        count = STORE_DB.get_post_like_count(post["id"])
        count_label.text = f"{count}+" if count >= 999 else str(count)

        def make_like_handler(p, btn, count_lbl):
            def handler(*_):
                self._toggle_like(p, btn, count_lbl)
            return handler

        like_btn.bind(on_press=make_like_handler(post, like_btn, like_count))
        like_row.add_widget(like_btn)
        like_row.add_widget(like_count)
        footer.add_widget(like_row)

        # 评论数
        comment_row = BoxLayout(size_hint=(None, 1), width=dp(90), spacing=dp(4))
        comment_icon = Label(
            text="msg", font_size=sp(17),
            color=(0.45, 0.45, 0.45, 1),
            size_hint=(None, 1), width=dp(28),
            halign="center", valign="middle",
        )
        comment_count = Label(
            text=f"{post.get('comments', '0')}",
            font_size=sp(14), color=(0.35, 0.35, 0.35, 1),
            size_hint=(None, 1), width=dp(56),
            halign="left", valign="middle", **text_style(),
        )
        comment_count.bind(size=comment_count.setter("text_size"))
        comment_row.add_widget(comment_icon)
        comment_row.add_widget(comment_count)
        footer.add_widget(comment_row)

        # 分享
        share_btn = Button(
            text="share", font_size=sp(17),
            color=(0.45, 0.45, 0.45, 1),
            background_normal="", background_down="",
            background_color=(0, 0, 0, 0),
            size_hint=(None, 1), width=dp(36),
        )
        share_btn.bind(on_press=lambda *_: show_toast("分享功能即将推出"))
        footer.add_widget(share_btn)
        footer.add_widget(Widget(size_hint=(1, 1)))
        card.add_widget(footer)
        return card

    def _build_kandian(self):
        outer = BoxLayout(
            spacing=dp(10), size_hint=(1, None), height=dp(230),
            padding=(0, 0, 0, 0),
        )
        for idx, (img_path, title) in enumerate(
                zip(KANDIAN_IMAGES, KANDIAN_TITLES)):

            item = BoxLayout(
                orientation="vertical", spacing=dp(6),
                size_hint=(1, 1),
            )

            # 图片容器，固定宽高比
            img_box = FloatLayout(size_hint=(1, None), height=dp(195))

            if img_path and os.path.exists(img_path):
                from kivy.uix.image import Image as KImg
                img = KImg(
                    source=img_path,
                    size_hint=(1, 1),
                    pos_hint={"x": 0, "y": 0},
                    allow_stretch=True,
                    keep_ratio=False,
                )
                img_box.add_widget(img)
            # 没有图片时不加任何占位，保持空白干净

            # 点击跳转按钮覆盖在图片上
            from config import COMMUNITY_ARTICLES as _articles
            article_key = "article:planting" if idx == 0 else "article:control"
            article = _articles.get(article_key, {})
            btn = Button(
                size_hint=(1, 1),
                pos_hint={"x": 0, "y": 0},
                background_normal="", background_down="",
                background_color=(0, 0, 0, 0),
            )
            btn.bind(on_press=lambda *_, a=article: self.open_community_detail(a))
            img_box.add_widget(btn)
            item.add_widget(img_box)

            # 标题
            title_lbl = Label(
                text=title, font_size=sp(14), bold=True,
                color=(0.12, 0.12, 0.12, 1),
                size_hint=(1, None), height=dp(28),
                halign="center", valign="middle", **text_style(),
            )
            title_lbl.bind(size=title_lbl.setter("text_size"))
            item.add_widget(title_lbl)
            outer.add_widget(item)
        return outer

    def _build_search_result_card(self, post):
        card = BoxLayout(
            orientation="vertical", spacing=dp(6),
            padding=(dp(14), dp(10), dp(14), dp(10)),
            size_hint=(1, None), height=dp(110),
        )
        with card.canvas.before:
            Color(1, 1, 1, 1)
            post_bg = RoundedRectangle(
                pos=card.pos, size=card.size, radius=[dp(14)] * 4)
        card.bind(
            pos=lambda i, *_: setattr(post_bg, "pos", i.pos),
            size=lambda i, *_: setattr(post_bg, "size", i.size),
        )
        title = Label(
            text=post["title"], font_size=sp(16), bold=True,
            color=(0.08, 0.08, 0.08, 1),
            size_hint=(1, None), height=dp(26),
            halign="left", valign="middle", **text_style(),
        )
        title.bind(size=title.setter("text_size"))
        card.add_widget(title)
        summary = Label(
            text=post["summary"], font_size=sp(13),
            color=(0.35, 0.35, 0.35, 1),
            size_hint=(1, None), height=dp(38),
            halign="left", valign="top", **text_style(),
        )
        summary.bind(size=summary.setter("text_size"))
        card.add_widget(summary)
        opener = Button(
            text="点击查看全部内容 >",
            font_size=sp(13), color=GREEN,
            background_normal="", background_down="",
            background_color=(0, 0, 0, 0),
            size_hint=(1, None), height=dp(26),
            halign="right", **text_style(),
        )
        opener.bind(on_press=lambda *_: self.open_community_detail(post))
        card.add_widget(opener)
        return card

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

    def cancel_search(self, _instance=None):
        self.community_search_input.text = ""
        self.community_search_input.focus = False
        self.refresh_default_content()

    def _display_like_text(self, post):
        count = STORE_DB.get_post_like_count(post["id"])
        return f"{count}+" if count >= 999 else str(count)

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
            Color(1, 1, 1, 1)
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

        self.back_btn = IconButton(
            text="<", font_size=sp(34), color=(0, 0, 0, 1),
            size_hint=(None, None), size=(dp(56), dp(56)),
            pos_hint={"x": 0.03, "center_y": 0.42}, **text_style(),
        )
        self.back_btn.bind(on_press=self.go_back)
        self.top_bar.add_widget(self.back_btn)

        self.title_label = Label(
            text="社区详情", font_size=sp(22), bold=True, color=(1, 1, 1, 1),
            size_hint=(0.7, None), height=dp(36),
            pos_hint={"center_x": 0.52, "center_y": 0.42},
            halign="center", valign="middle", **text_style(),
        )
        self.title_label.bind(size=self.title_label.setter("text_size"))
        self.top_bar.add_widget(self.title_label)

        self.scroll_view = ScrollView(
            size_hint=(1, None), pos_hint={"x": 0, "y": 0},
            do_scroll_x=False, bar_width=dp(4),
            scroll_type=["bars", "content"],
        )
        self.layout.add_widget(self.scroll_view)

        self.content_box = BoxLayout(
            orientation="vertical", spacing=dp(14),
            padding=(dp(16), dp(12), dp(16), dp(110)),
            size_hint=(1, None),
        )
        self.content_box.bind(
            minimum_height=self._sync_detail_content_height)
        self.scroll_view.add_widget(self.content_box)
        self.scroll_view.bind(height=self._sync_detail_content_height)

        self.author_label = Label(
            text="", font_size=sp(14), color=GREEN,
            size_hint=(1, None), height=dp(24),
            halign="left", valign="middle", **text_style(),
        )
        self.author_label.bind(size=self.author_label.setter("text_size"))
        self.content_box.add_widget(self.author_label)

        self.post_title_label = Label(
            text="", font_size=sp(22), bold=True,
            color=(0.08, 0.08, 0.08, 1), size_hint=(1, None),
            halign="left", valign="top", **text_style(),
        )
        self.post_title_label.bind(
            width=self._sync_label_width,
            texture_size=self._sync_dynamic_label,
        )
        self.content_box.add_widget(self.post_title_label)

        self.body_label = Label(
            text="", font_size=sp(15), color=(0.12, 0.12, 0.12, 1),
            size_hint=(1, None), halign="left", valign="top", **text_style(),
        )
        self.body_label.bind(
            width=self._sync_label_width,
            texture_size=self._sync_dynamic_label,
        )
        self.content_box.add_widget(self.body_label)

        self.comment_title = Label(
            text="历史评论", font_size=sp(18), bold=True,
            color=(0.08, 0.08, 0.08, 1),
            size_hint=(1, None), height=dp(30),
            halign="left", valign="middle", **text_style(),
        )
        self.comment_title.bind(size=self.comment_title.setter("text_size"))
        self.content_box.add_widget(self.comment_title)

        self.comment_list = BoxLayout(
            orientation="vertical", spacing=dp(10), size_hint=(1, None))
        self.comment_list.bind(
            minimum_height=self.comment_list.setter("height"))
        self.content_box.add_widget(self.comment_list)

        # 底部操作栏
        self.action_bar = BoxLayout(
            orientation="horizontal", size_hint=(1, None), height=dp(68),
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
            hint_text="写下你的评论", multiline=False, size_hint=(0.56, 1),
            padding=(dp(12), dp(10), dp(12), dp(10)), font_size=sp(15),
            input_type="text", keyboard_suggestions=True,
            write_tab=False, **text_style(),
        )
        self.action_bar.add_widget(self.comment_input)

        self.publish_btn = Button(
            text="发表", size_hint=(0.18, 1), font_size=sp(15),
            background_normal="", background_down="",
            background_color=GREEN, color=(1, 1, 1, 1),
            border=(0, 0, 0, 0), **text_style(),
        )
        self.publish_btn.bind(on_press=self.publish_comment)
        self.action_bar.add_widget(self.publish_btn)

        self.like_btn = LikeImageButton(
            source_off=LIKE_ICON_OFF, source_on=LIKE_ICON_ON,
            size_hint=(None, 1), width=dp(18),
        )
        self.like_btn.bind(on_press=self.toggle_like)
        self.action_bar.add_widget(self.like_btn)

        self.like_count_label = Label(
            text="0", size_hint=(None, 1), width=dp(34),
            color=(0.2, 0.2, 0.2, 1),
            halign="center", valign="middle", **text_style(),
        )
        self.like_count_label.bind(
            size=self.like_count_label.setter("text_size"))
        self.action_bar.add_widget(self.like_count_label)

        self.view_label = Label(
            text="浏览量 0", size_hint=(None, 1), width=dp(96),
            color=(0.35, 0.35, 0.35, 1),
            halign="left", valign="middle", **text_style(),
        )
        self.view_label.bind(size=self.view_label.setter("text_size"))
        self.action_bar.add_widget(self.view_label)

        self.layout.bind(size=self._update_scroll_height)
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
        self._sync_detail_content_height()

    def _sync_label_width(self, instance, _value):
        instance.text_size = (instance.width, None)

    def _sync_dynamic_label(self, instance, _value):
        instance.height = max(dp(28), instance.texture_size[1] + dp(6))

    def _sync_detail_content_height(self, *_args):
        minimum_height = getattr(self.content_box, "minimum_height", 0)
        viewport_height = self.scroll_view.height if hasattr(
            self, "scroll_view") else 0
        self.content_box.height = max(minimum_height, viewport_height)

    def _build_comment_widget(self, comment):
        wrapper = BoxLayout(
            orientation="vertical", spacing=dp(4),
            padding=(dp(12), dp(10), dp(12), dp(10)),
            size_hint=(1, None),
        )
        wrapper.bind(minimum_height=wrapper.setter("height"))
        with wrapper.canvas.before:
            Color(0.96, 0.96, 0.96, 1)
            bg_rect = Rectangle(pos=wrapper.pos, size=wrapper.size)
        wrapper.bind(
            pos=lambda i, *_: self._update_comment_rect(i, bg_rect),
            size=lambda i, *_: self._update_comment_rect(i, bg_rect),
        )
        header = Label(
            text=f"{comment['username']}  {comment['comment_date']}",
            font_size=sp(13), color=(0.32, 0.32, 0.32, 1),
            size_hint=(1, None), height=dp(22),
            halign="left", valign="middle", **text_style(),
        )
        header.bind(size=header.setter("text_size"))
        wrapper.add_widget(header)
        body = Label(
            text=comment["comment"], font_size=sp(15),
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

    @staticmethod
    def _update_comment_rect(instance, rect):
        rect.pos = instance.pos
        rect.size = instance.size

    def set_item(self, item_data, return_screen="community"):
        self.item_data = dict(item_data)
        self.return_screen = return_screen
        self.title_label.text = self.item_data.get("title", "社区详情")
        self.author_label.text = self.item_data.get("username", "")
        self.post_title_label.text = self.item_data.get("title", "")
        self.body_label.text = self.item_data.get("full_text", "")
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
                font_size=sp(15), color=(0.45, 0.45, 0.45, 1),
                size_hint=(1, None), height=dp(34),
                halign="left", valign="middle", **text_style(),
            )
            empty_label.bind(size=empty_label.setter("text_size"))
            self.comment_list.add_widget(empty_label)
            return
        for comment in comments:
            self.comment_list.add_widget(
                self._build_comment_widget(comment))

    def publish_comment(self, _instance=None):
        from utils import normalize_comment_text, show_toast
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
        from utils import show_toast
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


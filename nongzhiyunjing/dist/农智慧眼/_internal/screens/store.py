import os

from kivy.app import App
from kivy.clock import Clock
from kivy.graphics import Color, Rectangle, RoundedRectangle, Line, Ellipse
from kivy.metrics import dp, sp
from kivy.uix.behaviors import ButtonBehavior
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.button import Button
from kivy.uix.floatlayout import FloatLayout
from kivy.uix.label import Label
from kivy.uix.screenmanager import Screen
from kivy.uix.scrollview import ScrollView
from kivy.uix.textinput import TextInput
from kivy.uix.widget import Widget

from config import GREEN, IMAGE_DIR
from database.store_db import STORE_DB
from utils import text_style, show_toast, update_nav_rect
from widgets.base_widgets import IconButton, RoundedButton
from screens.home import HomeScreen, _update_camera_btn
from kivy.uix.image import Image

TYPE_COLORS = {
    "杀虫剂": (0.12, 0.58, 0.30, 1),
    "杀菌剂": (0.18, 0.42, 0.78, 1),
    "除草剂": (0.78, 0.42, 0.12, 1),
}

PESTICIDE_IMAGES = {
    "吡虫啉": os.path.join(IMAGE_DIR, "吡虫啉.jpg"),
    "阿维菌素": os.path.join(IMAGE_DIR, "阿维菌素.jpg"),
    "氯虫苯甲酰胺": os.path.join(IMAGE_DIR, "氯虫苯甲酰胺.jpg"),
    "甲维盐": os.path.join(IMAGE_DIR, "甲维盐.jpg"),
    "噻虫嗪": os.path.join(IMAGE_DIR, "噻虫嗪.jpg"),
    "高效氯氟氰菊酯": os.path.join(IMAGE_DIR, "高效氯氟氰菊酯.jpg"),
    "代森锰锌": os.path.join(IMAGE_DIR, "代森锰锌.jpg"),
    "苯醚甲环唑": os.path.join(IMAGE_DIR, "苯醚甲环唑.jpg"),
    "三环唑": os.path.join(IMAGE_DIR, "三环唑.jpg"),
    "霜霉威盐酸盐": os.path.join(IMAGE_DIR, "霜霉威盐酸盐.jpg"),
    "草铵膦": os.path.join(IMAGE_DIR, "草铵膦.jpg"),
    "莠去津": os.path.join(IMAGE_DIR, "莠去津.jpg"),
    "二甲戊灵": os.path.join(IMAGE_DIR, "二甲戊灵.jpg"),
    "烟嘧磺隆": os.path.join(IMAGE_DIR, "烟嘧磺隆.jpg"),
    "敌敌畏": os.path.join(IMAGE_DIR, "敌敌畏.png"),
    "硫酸钾复合肥": os.path.join(IMAGE_DIR, "硫酸钾复合肥.png"),
    "磷酸二氢钾": os.path.join(IMAGE_DIR, "磷酸二氢钾.png"),
    "生物有机肥": os.path.join(IMAGE_DIR, "生物有机肥.png"),
    "乙酰甲胺磷": os.path.join(IMAGE_DIR, "乙酰甲胺磷.png"),
    "乙蒜素": os.path.join(IMAGE_DIR, "乙蒜素.png"),
    "百草枯": os.path.join(IMAGE_DIR, "百草枯.png"),
    "乐果": os.path.join(IMAGE_DIR, "氧乐果.png"),
    "嘧菌酯": os.path.join(IMAGE_DIR, "嘧菌酯.png"),
}






class PesticideCard(ButtonBehavior, BoxLayout):
    def __init__(self, pesticide_data, on_open=None, **kwargs):
        super().__init__(
            orientation="horizontal", spacing=dp(12),
            padding=(dp(14), dp(12), dp(14), dp(12)),
            size_hint=(1, None), height=dp(80), **kwargs,
        )
        self.pesticide_data = pesticide_data
        self.on_open = on_open
        self.bind(pos=self._update_bg, size=self._update_bg)

        type_color = TYPE_COLORS.get(pesticide_data.get("type", ""), GREEN)

        # 左侧图片
        img_wrap = BoxLayout(size_hint=(None, 1), width=dp(56))
        img_path = PESTICIDE_IMAGES.get(pesticide_data["name"], "")
        print(f"图片路径: {img_path}, 存在: {os.path.exists(img_path)}")  # 调试用
        if img_path and os.path.exists(img_path):
            img = Image(
                source=img_path,
                size_hint=(1, 1),
                allow_stretch=True, keep_ratio=True,
            )
            img_wrap.add_widget(img)
        else:
            ph = Widget(size_hint=(1, 1))
            with ph.canvas.before:
                Color(*type_color, 0.12)
                ph_rect = RoundedRectangle(
                    pos=ph.pos, size=ph.size, radius=[dp(10)] * 4)
            ph.bind(
                pos=lambda i, r=ph_rect, *_: setattr(r, "pos", i.pos),
                size=lambda i, r=ph_rect, *_: setattr(r, "size", i.size),
            )
            first = Label(
                text=pesticide_data["name"][0],
                font_size=sp(22), bold=True, color=type_color,
                size_hint=(1, 1),
                halign="center", valign="middle", **text_style(),
            )
            first.bind(size=first.setter("text_size"))
            ph.add_widget(first)
            img_wrap.add_widget(ph)
        self.add_widget(img_wrap)

        # 中间内容
        info = BoxLayout(orientation="vertical", spacing=dp(4),
                         size_hint=(1, 1))

        # 第一行：名称 + 类型标签
        name_row = BoxLayout(size_hint=(1, None), height=dp(26), spacing=dp(6))
        name_lbl = Label(
            text=pesticide_data["name"], font_size=sp(16), bold=True,
            color=(0.08, 0.08, 0.08, 1),
            size_hint=(None, 1), width=dp(130),
            halign="left", valign="middle", **text_style(),
        )
        name_lbl.bind(size=name_lbl.setter("text_size"))
        name_row.add_widget(name_lbl)

        type_wrap = BoxLayout(size_hint=(None, 1), width=dp(52))
        with type_wrap.canvas.before:
            Color(*type_color, 0.15)
            tw_bg = RoundedRectangle(
                pos=type_wrap.pos, size=type_wrap.size, radius=[dp(6)] * 4)
        type_wrap.bind(
            pos=lambda i, r=tw_bg, *_: setattr(r, "pos", i.pos),
            size=lambda i, r=tw_bg, *_: setattr(r, "size", i.size),
        )
        type_lbl = Label(
            text=pesticide_data.get("type", ""),
            font_size=sp(12), color=type_color,
            size_hint=(1, 1),
            halign="center", valign="middle", **text_style(),
        )
        type_lbl.bind(size=type_lbl.setter("text_size"))
        type_wrap.add_widget(type_lbl)
        name_row.add_widget(type_wrap)
        name_row.add_widget(Widget(size_hint=(1, 1)))
        info.add_widget(name_row)

        # 第二行：适用作物
        crops_lbl = Label(
            text=f"适用：{pesticide_data.get('crops', '')}",
            font_size=sp(13), color=(0.45, 0.45, 0.45, 1),
            size_hint=(1, None), height=dp(22),
            halign="left", valign="middle", **text_style(),
        )
        crops_lbl.bind(size=crops_lbl.setter("text_size"))
        info.add_widget(crops_lbl)
        self.add_widget(info)

        # 右侧箭头
        arrow = Label(
            text=">", font_size=sp(18),
            color=(0.72, 0.72, 0.72, 1),
            size_hint=(None, 1), width=dp(20),
            halign="center", valign="middle",
        )
        self.add_widget(arrow)

    def _update_bg(self, *_args):
        self.canvas.before.clear()
        self.canvas.after.clear()
        with self.canvas.before:
            Color(1, 1, 1, 1)
            Rectangle(pos=self.pos, size=self.size)
        with self.canvas.after:
            Color(0.92, 0.92, 0.92, 1)
            Line(points=[self.x + dp(14), self.y,
                         self.right - dp(14), self.y], width=1)

    def on_release(self):
        if self.on_open:
            self.on_open(self.pesticide_data["id"])



class StoreScreen(Screen):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.name = "store"
        self._current_type = "全部"
        self.build_ui()

    def sync_product_views(self, tab_name=None):
        return None

    def build_ui(self):
        self.layout = FloatLayout()
        self.add_widget(self.layout)
        with self.layout.canvas.before:
            Color(0.96, 0.98, 0.96, 1)
            self.bg_rect = Rectangle(pos=self.layout.pos, size=self.layout.size)
        self.layout.bind(pos=self._update_bg, size=self._update_bg)

        self.top_bar = self._build_top_bar()
        self.layout.add_widget(self.top_bar)

        self.scroll = ScrollView(
            size_hint=(1, None), do_scroll_x=False,
            pos_hint={"x": 0, "y": 0},
        )
        self.layout.add_widget(self.scroll)
        self.content_box = BoxLayout(
            orientation="vertical", spacing=0,
            padding=(0, 0, 0, dp(18)),
            size_hint=(1, None),
        )
        self.content_box.bind(minimum_height=self.content_box.setter("height"))
        self.scroll.add_widget(self.content_box)

        self.bottom_nav = HomeScreen._build_bottom_nav(self)
        self.layout.add_widget(self.bottom_nav)

        self.layout.bind(size=self._update_layout)
        Clock.schedule_once(lambda dt: self._update_layout(), 0)
        Clock.schedule_once(lambda dt: self.refresh_default_view(), 0)

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

        title_label = Label(
            text="农药百科", font_size=sp(20), bold=True,
            color=(0.08, 0.08, 0.08, 1),
            size_hint=(None, 1), width=dp(88),
            halign="left", valign="middle", **text_style(),
        )
        title_label.bind(size=title_label.setter("text_size"))
        bar.add_widget(title_label)

        search_wrap = BoxLayout(size_hint=(1, 1))
        with search_wrap.canvas.before:
            Color(0.88, 0.96, 0.88, 1)
            self.search_bg = RoundedRectangle(
                pos=search_wrap.pos, size=search_wrap.size,
                radius=[dp(20)] * 4)
        search_wrap.bind(
            pos=lambda i, *_: setattr(self.search_bg, "pos", i.pos),
            size=lambda i, *_: setattr(self.search_bg, "size", i.size),
        )
        self.search_input = TextInput(
            hint_text="搜索农药名称、用途、作物",
            multiline=False, input_type="text",
            keyboard_suggestions=True,
            background_normal="", background_active="",
            background_color=(0, 0, 0, 0),
            foreground_color=(0.12, 0.12, 0.12, 1),
            hint_text_color=(0.45, 0.65, 0.45, 1),
            cursor_color=(0.12, 0.12, 0.12, 1),
            padding=(dp(14), dp(10), dp(14), dp(10)),
            font_size=sp(14), **text_style(),
        )
        self.search_input.bind(
            on_text_validate=self.search_pesticide,
            text=self._on_search_text,
        )
        search_wrap.add_widget(self.search_input)
        bar.add_widget(search_wrap)

        cancel_btn = Button(
            text="取消", font_size=sp(14), color=GREEN,
            background_normal="", background_down="",
            background_color=(0, 0, 0, 0),
            size_hint=(None, 1), width=dp(44),
            **text_style(),
        )
        cancel_btn.bind(on_press=self.cancel_search)
        bar.add_widget(cancel_btn)
        return bar

    def _build_type_tabs(self):
        tab_bar = BoxLayout(
            size_hint=(1, None), height=dp(52),
            padding=(dp(16), dp(8), dp(16), dp(8)),
            spacing=dp(0),
        )
        with tab_bar.canvas.before:
            Color(1, 1, 1, 1)
            tb_bg = Rectangle(pos=tab_bar.pos, size=tab_bar.size)
        tab_bar.bind(
            pos=lambda i, *_: setattr(tb_bg, "pos", i.pos),
            size=lambda i, *_: setattr(tb_bg, "size", i.size),
        )

        self._type_btns = {}
        types = [
            ("杀虫剂", TYPE_COLORS["杀虫剂"]),
            ("杀菌剂", TYPE_COLORS["杀菌剂"]),
            ("除草剂", TYPE_COLORS["除草剂"]),
        ]
        for type_name, color in types:
            is_active = type_name == self._current_type
            btn = Button(
                text=type_name, font_size=sp(16),
                color=color if is_active else (0.45, 0.45, 0.45, 1),
                bold=is_active,
                background_normal="", background_down="",
                background_color=(0, 0, 0, 0),
                size_hint=(1, 1),
                **text_style(),
            )
            btn.bind(on_press=lambda *_, t=type_name: self._filter_by_type(t))
            self._type_btns[type_name] = btn
            tab_bar.add_widget(btn)
        return tab_bar

    def _build_section_header(self, title, count):
        row = BoxLayout(
            size_hint=(1, None), height=dp(44),
            padding=(dp(14), dp(10), dp(14), dp(10)),
            spacing=dp(0),
        )
        with row.canvas.before:
            Color(0.96, 0.98, 0.96, 1)
            row_bg = Rectangle(pos=row.pos, size=row.size)
        row.bind(
            pos=lambda i, *_: setattr(row_bg, "pos", i.pos),
            size=lambda i, *_: setattr(row_bg, "size", i.size),
        )
        title_lbl = Label(
            text=title, font_size=sp(15), bold=True,
            color=(0.12, 0.12, 0.12, 1),
            size_hint=(1, 1),
            halign="left", valign="middle", **text_style(),
        )
        title_lbl.bind(size=title_lbl.setter("text_size"))
        row.add_widget(title_lbl)
        count_lbl = Label(
            text=f"共{count}种", font_size=sp(13),
            color=(0.55, 0.55, 0.55, 1),
            size_hint=(None, 1), width=dp(56),
            halign="right", valign="middle", **text_style(),
        )
        count_lbl.bind(size=count_lbl.setter("text_size"))
        row.add_widget(count_lbl)
        return row

    def refresh_default_view(self):
        self.content_box.clear_widgets()
        self.content_box.add_widget(self._build_type_tabs())
        self._show_list(STORE_DB.get_pesticide_entries())

    def refresh_list(self):
        self.content_box.clear_widgets()
        self.content_box.add_widget(self._build_type_tabs())
        pesticides = STORE_DB.get_pesticide_entries()
        if self._current_type != "全部":
            pesticides = [p for p in pesticides
                          if p["type"] == self._current_type]
        self._show_list(pesticides)

    def _show_list(self, pesticides):
        if not pesticides:
            empty = Label(
                text="暂无数据", font_size=sp(16),
                color=(0.45, 0.45, 0.45, 1),
                size_hint=(1, None), height=dp(60),
                halign="center", valign="middle", **text_style(),
            )
            empty.bind(size=empty.setter("text_size"))
            self.content_box.add_widget(empty)
            return

        if self._current_type == "全部":
            groups = {}
            for p in pesticides:
                groups.setdefault(p["type"], []).append(p)
            for group_name, items in groups.items():
                self.content_box.add_widget(
                    self._build_section_header(group_name, len(items)))
                for item in items:
                    self.content_box.add_widget(
                        PesticideCard(item, on_open=self.open_pesticide_detail))
        else:
            self.content_box.add_widget(
                self._build_section_header(self._current_type, len(pesticides)))
            for item in pesticides:
                self.content_box.add_widget(
                    PesticideCard(item, on_open=self.open_pesticide_detail))

    def _filter_by_type(self, type_name):
        self._current_type = type_name
        self.refresh_list()

    def _on_search_text(self, _instance, value):
        if not value.strip():
            self._current_type = "全部"
            self.refresh_default_view()

    def search_pesticide(self, _instance=None):
        keyword = self.search_input.text.strip()
        if not keyword:
            self._current_type = "全部"
            self.refresh_default_view()
            return
        results = STORE_DB.search_pesticides(keyword)
        self.content_box.clear_widgets()
        header_box = BoxLayout(
            size_hint=(1, None), height=dp(44),
            padding=(dp(14), dp(10), dp(14), dp(10)),
        )
        with header_box.canvas.before:
            Color(0.96, 0.98, 0.96, 1)
            h_bg = Rectangle(pos=header_box.pos, size=header_box.size)
        header_box.bind(
            pos=lambda i, *_: setattr(h_bg, "pos", i.pos),
            size=lambda i, *_: setattr(h_bg, "size", i.size),
        )
        result_text = (f'找到 {len(results)} 个结果'
                       if results else f'未找到"{keyword}"相关农药')
        result_lbl = Label(
            text=result_text, font_size=sp(14),
            color=(0.35, 0.35, 0.35, 1),
            size_hint=(1, 1),
            halign="left", valign="middle", **text_style(),
        )
        result_lbl.bind(size=result_lbl.setter("text_size"))
        header_box.add_widget(result_lbl)
        self.content_box.add_widget(header_box)
        for item in results:
            self.content_box.add_widget(
                PesticideCard(item, on_open=self.open_pesticide_detail))

    def cancel_search(self, _instance=None):
        self.search_input.text = ""
        self.search_input.focus = False
        self._current_type = "全部"
        self.refresh_default_view()

    def open_pesticide_detail(self, pesticide_id):
        try:
            detail_screen = self.manager.get_screen("pesticide_detail")
            detail_screen.set_pesticide(pesticide_id)
            self.manager.current = "pesticide_detail"
        except Exception as exc:
            show_toast(f"打开详情失败: {exc}")

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


class StoreCategoryScreen(Screen):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.name = "store_category"

    def set_category(self, category_name):
        pass

    def sync_product_views(self, tab_name=None):
        pass

    def refresh_products(self):
        pass

    def go_back(self, _instance=None):
        self.manager.current = "store"


class ProductDetailScreen(Screen):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.name = "product_detail"

    def set_product(self, product_id, from_tab="", return_screen="store"):
        self.manager.current = "store"

    def sync_product_views(self, tab_name=None):
        pass

    def go_back(self, _instance=None):
        self.manager.current = "store"


class PesticideDetailScreen(Screen):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.name = "pesticide_detail"
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
            text="农药详情", font_size=sp(22), bold=True, color=(1, 1, 1, 1),
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
            orientation="vertical", spacing=0,
            padding=(dp(16), dp(16), dp(16), dp(24)), size_hint=(1, None),
        )
        self.content_box.bind(minimum_height=self.content_box.setter("height"))
        self.scroll_view.add_widget(self.content_box)

        self.name_label = Label(
            text="", font_size=sp(26), bold=True,
            color=(0.08, 0.08, 0.08, 1),
            size_hint=(1, None), height=dp(42),
            halign="left", valign="middle", **text_style(),
        )
        self.name_label.bind(size=self.name_label.setter("text_size"))
        self.content_box.add_widget(self.name_label)

        tag_row = BoxLayout(size_hint=(1, None), height=dp(36))
        self.type_tag = Label(
            text="", font_size=sp(14), color=(1, 1, 1, 1),
            size_hint=(None, None), height=dp(28),
            halign="center", valign="middle", **text_style(),
        )
        self.type_tag.bind(texture_size=self._sync_tag_size)
        tag_row.add_widget(self.type_tag)
        tag_row.add_widget(Widget())
        self.content_box.add_widget(tag_row)

        self.content_box.add_widget(self._build_divider())
        self.crops_section = self._build_section(
            "适用作物", "", (0.12, 0.58, 0.30, 1))
        self.content_box.add_widget(self.crops_section["wrapper"])
        self.content_box.add_widget(self._build_divider())
        self.target_section = self._build_section(
            "防治对象", "", (0.18, 0.42, 0.78, 1))
        self.content_box.add_widget(self.target_section["wrapper"])
        self.content_box.add_widget(self._build_divider())
        self.method_section = self._build_section(
            "使用方法", "", (0.55, 0.35, 0.75, 1))
        self.content_box.add_widget(self.method_section["wrapper"])
        self.content_box.add_widget(self._build_divider())
        self.caution_section = self._build_section(
            "注意事项", "", (0.88, 0.45, 0.18, 1))
        self.content_box.add_widget(self.caution_section["wrapper"])

        self.layout.bind(size=self._update_scroll_height)
        Clock.schedule_once(lambda dt: self._update_scroll_height(), 0)

    def _build_section(self, title, content, accent_color):
        wrapper = BoxLayout(
            orientation="vertical", spacing=dp(8),
            padding=(0, dp(14), 0, dp(14)),
            size_hint=(1, None),
        )
        wrapper.bind(minimum_height=wrapper.setter("height"))

        title_row = BoxLayout(
            size_hint=(1, None), height=dp(26), spacing=dp(8))
        dot = Widget(size_hint=(None, None), size=(dp(8), dp(8)))
        dot.pos_hint = {"center_y": 0.5}
        with dot.canvas:
            Color(*accent_color)
            dot_circle = Ellipse(pos=dot.pos, size=dot.size)
        dot.bind(
            pos=lambda i, e=dot_circle, *_: setattr(e, "pos", i.pos),
            size=lambda i, e=dot_circle, *_: setattr(e, "size", i.size),
        )
        title_row.add_widget(dot)
        title_lbl = Label(
            text=title, font_size=sp(15), bold=True,
            color=(0.12, 0.12, 0.12, 1),
            size_hint=(1, None), height=dp(26),
            halign="left", valign="middle", **text_style(),
        )
        title_lbl.bind(size=title_lbl.setter("text_size"))
        title_row.add_widget(title_lbl)
        wrapper.add_widget(title_row)

        content_lbl = Label(
            text=content, font_size=sp(15),
            color=(0.22, 0.22, 0.22, 1),
            size_hint=(1, None), halign="left", valign="top",
            **text_style(),
        )
        content_lbl.bind(
            width=self._sync_label_width,
            texture_size=self._sync_dynamic_label,
        )
        wrapper.add_widget(content_lbl)
        return {"wrapper": wrapper, "content_label": content_lbl}

    def _build_divider(self):
        divider = Widget(size_hint=(1, None), height=dp(1))
        with divider.canvas:
            Color(0.92, 0.92, 0.92, 1)
            div_rect = Rectangle(pos=divider.pos, size=divider.size)
        divider.bind(
            pos=lambda i, r=div_rect, *_: setattr(r, "pos", i.pos),
            size=lambda i, r=div_rect, *_: setattr(r, "size", i.size),
        )
        return divider

    def _sync_tag_size(self, instance, value):
        instance.width = value[0] + dp(20)
        instance.canvas.before.clear()
        with instance.canvas.before:
            type_color = TYPE_COLORS.get(instance.text, GREEN)
            Color(*type_color)
            RoundedRectangle(
                pos=instance.pos, size=instance.size, radius=[dp(6)] * 4)

    def _sync_label_width(self, instance, _value):
        instance.text_size = (instance.width, None)

    def _sync_dynamic_label(self, instance, _value):
        instance.height = max(dp(24), instance.texture_size[1] + dp(8))

    def _update_bg(self, *_args):
        self.bg_rect.pos = self.layout.pos
        self.bg_rect.size = self.layout.size

    def _update_top_bar(self, *_args):
        self.top_bar_rect.pos = self.top_bar.pos
        self.top_bar_rect.size = self.top_bar.size

    def _update_scroll_height(self, *_args):
        self.scroll_view.height = max(
            dp(200), self.height - self.top_bar.height)
        self.scroll_view.pos = (0, 0)

    def set_pesticide(self, pesticide_id):
        pesticide = STORE_DB.get_pesticide_entry(pesticide_id)
        if not pesticide:
            show_toast("暂无数据")
            return
        self.title_label.text = pesticide["name"]
        self.name_label.text = pesticide["name"]
        self.type_tag.text = pesticide["type"]
        self.crops_section["content_label"].text = pesticide["crops"]
        self.target_section["content_label"].text = pesticide["target"]
        self.method_section["content_label"].text = pesticide["method"]
        self.caution_section["content_label"].text = pesticide["caution"]

        self.scroll_view.scroll_y = 1

    def go_back(self, _instance=None):
        self.manager.current = "store"

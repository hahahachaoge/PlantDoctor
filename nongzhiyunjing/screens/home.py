import json
import os
import threading

from kivy.app import App
from kivy.clock import Clock
from kivy.graphics import Color, Ellipse, Rectangle, RoundedRectangle
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
from config import GREEN, HOME_TOOL_ICONS, HOME_REMINDERS, IMAGE_DIR



from config import GREEN, HOME_TOOL_ICONS, HOME_REMINDERS, IMAGE_DIR
from database.store_db import STORE_DB
from utils import text_style, show_toast, open_text_popup, update_nav_rect
from widgets.base_widgets import UnderlineLabel, RoundedButton

import json

_CITY_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                          "..", "weather_city.json")

def _load_city():
    try:
        if os.path.exists(_CITY_FILE):
            with open(_CITY_FILE, "r", encoding="utf-8") as f:
                return json.load(f).get("city", "guangzhou")
    except Exception:
        pass
    return "guangzhou"

def _save_city(city):
    try:
        with open(_CITY_FILE, "w", encoding="utf-8") as f:
            json.dump({"city": city}, f, ensure_ascii=False)
    except Exception:
        pass

WEATHER_CITY = _load_city()



def fetch_weather(city, on_success, on_error):
    def run():
        try:
            import urllib.request
            # 加 lang=zh 获取中文天气描述
            url = f"https://wttr.in/{city}?format=j1&lang=zh"
            req = urllib.request.Request(
                url,
                headers={
                    "User-Agent": "Mozilla/5.0",
                    "Accept": "application/json",
                }
            )
            with urllib.request.urlopen(req, timeout=10) as resp:
                raw = resp.read().decode("utf-8")
            data = json.loads(raw)
            current = data["current_condition"][0]
            lang_zh_list = current.get("lang_zh", [])
            if lang_zh_list and isinstance(lang_zh_list, list):
                weather_desc = lang_zh_list[0].get("value", "")
            else:
                weather_desc = ""
            if not weather_desc:
                desc_list = current.get("weatherDesc", [])
                weather_desc = desc_list[0].get("value", "晴") if desc_list else "晴"
            temp_c = current.get("temp_C", "24")
            today = data["weather"][0]
            max_temp = today.get("maxtempC", "26")
            min_temp = today.get("mintempC", "21")
            result = {
                "temp": temp_c,
                "desc": weather_desc,
                "max": max_temp,
                "min": min_temp,
                "city": city,
            }
            Clock.schedule_once(lambda dt: on_success(result))
        except Exception as exc:
            err_msg = str(exc)
            Clock.schedule_once(lambda dt: on_error(err_msg))

    threading.Thread(target=run, daemon=True).start()



def _update_camera_btn(instance, *_args):
    instance.canvas.before.clear()
    with instance.canvas.before:
        Color(*GREEN)
        Ellipse(pos=instance.pos, size=instance.size)


class HomeToolCard(ButtonBehavior, BoxLayout):
    def __init__(self, icon_source="", icon_text="", title="", **kwargs):
        super().__init__(orientation="vertical", spacing=dp(4),
                         padding=(dp(8), dp(10), dp(8), dp(8)), **kwargs)
        self.size_hint = (1, None)
        self.height = dp(90)
        self.bind(pos=self._update_bg, size=self._update_bg)

        icon_wrap = FloatLayout(size_hint=(1, None), height=dp(48))
        if icon_source and os.path.exists(icon_source):
            icon = Image(
                source=icon_source,
                size_hint=(None, None), size=(dp(40), dp(40)),
                allow_stretch=True, keep_ratio=True,
            )
            icon.pos_hint = {"center_x": 0.5, "center_y": 0.5}
            icon_wrap.add_widget(icon)
        else:
            icon = Label(
                text=icon_text, font_size=sp(24), color=GREEN,
                size_hint=(1, 1),
                halign="center", valign="middle", **text_style(),
            )
            icon.bind(size=icon.setter("text_size"))
            icon_wrap.add_widget(icon)
        self.add_widget(icon_wrap)

        title_label = Label(
            text=title, font_size=sp(12), color=(0.22, 0.22, 0.22, 1),
            size_hint=(1, None), height=dp(20),
            halign="center", valign="middle", **text_style(),
        )
        title_label.bind(size=title_label.setter("text_size"))
        self.add_widget(title_label)

    def _update_bg(self, *_args):
        self.canvas.before.clear()
        with self.canvas.before:
            Color(1, 1, 1, 1)
            RoundedRectangle(pos=self.pos, size=self.size, radius=[dp(14)] * 4)


class HomeScreen(Screen):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.name = "home"
        self.build_ui()

    def build_ui(self):
        self.layout = FloatLayout()
        self.add_widget(self.layout)

        with self.layout.canvas.before:
            Color(0.94, 0.96, 0.94, 1)
            self.bg_rect = Rectangle(pos=self.layout.pos, size=self.layout.size)
        self.layout.bind(pos=self._update_bg, size=self._update_bg)

        self.top_bar = self._build_top_bar()
        self.layout.add_widget(self.top_bar)

        self.content_scroll = ScrollView(
            size_hint=(1, None), do_scroll_x=False,
            pos_hint={"x": 0, "y": 0},
        )
        self.layout.add_widget(self.content_scroll)
        self.content_box = BoxLayout(
            orientation="vertical", spacing=dp(12),
            padding=(dp(12), dp(8), dp(12), dp(18)),
            size_hint=(1, None),
        )
        self.content_box.bind(minimum_height=self.content_box.setter("height"))
        self.content_scroll.add_widget(self.content_box)

        self.content_box.add_widget(self._build_weather_card())
        self.content_box.add_widget(self._build_tool_section())
        self.content_box.add_widget(self._build_reminder_card())

        self.bottom_nav = self._build_bottom_nav()
        self.layout.add_widget(self.bottom_nav)

        self.layout.bind(size=self._update_layout)
        Clock.schedule_once(lambda dt: self._update_layout(), 0)
        Clock.schedule_once(lambda dt: self._load_weather(), 1)

    def _update_bg(self, *_args):
        self.bg_rect.pos = self.layout.pos
        self.bg_rect.size = self.layout.size

    def _update_layout(self, *_args):
        nav_h = self.bottom_nav.height
        top_h = self.top_bar.height
        available = max(dp(200), self.height - nav_h - top_h)
        self.content_scroll.height = available
        self.content_scroll.pos = (0, nav_h)
        self.top_bar.pos = (0, self.height - top_h)
        self.top_bar.size = (self.width, top_h)

    def _build_top_bar(self):
        bar = BoxLayout(
            size_hint=(1, None), height=dp(56),
            pos_hint={"x": 0, "top": 1},
            spacing=dp(8),
            padding=(dp(12), dp(8), dp(12), dp(8)),
        )
        with bar.canvas.before:
            Color(0.20, 0.65, 0.30, 1)
            self.top_bar_bg = Rectangle(pos=bar.pos, size=bar.size)
        bar.bind(
            pos=lambda i, *_: setattr(self.top_bar_bg, "pos", i.pos),
            size=lambda i, *_: setattr(self.top_bar_bg, "size", i.size),
        )

        location = Label(
            text="广州",
            font_size=sp(15), bold=True, color=(1, 1, 1, 1),
            size_hint=(None, 1), width=dp(56),
            halign="center", valign="middle", **text_style(),
        )
        location.bind(size=location.setter("text_size"))
        bar.add_widget(location)

        search_wrap = BoxLayout(size_hint=(1, 1))
        with search_wrap.canvas.before:
            Color(1, 1, 1, 0.22)
            self.search_bg = RoundedRectangle(
                pos=search_wrap.pos, size=search_wrap.size, radius=[dp(18)] * 4)
        search_wrap.bind(
            pos=lambda i, *_: setattr(self.search_bg, "pos", i.pos),
            size=lambda i, *_: setattr(self.search_bg, "size", i.size),
        )
        self.home_search_input = TextInput(
            hint_text="搜索病虫害、农药...",
            multiline=False, input_type="text",
            keyboard_suggestions=True,
            background_normal="", background_active="",
            background_color=(0, 0, 0, 0),
            foreground_color=(1, 1, 1, 1),
            hint_text_color=(0.88, 0.96, 0.88, 1),
            cursor_color=(1, 1, 1, 1),
            padding=(dp(14), dp(10), dp(14), dp(10)),
            font_size=sp(14), **text_style(),
        )
        self.home_search_input.bind(on_text_validate=self.search_pests)
        search_wrap.add_widget(self.home_search_input)
        bar.add_widget(search_wrap)

        msg_btn = Button(
            text="消息",
            font_size=sp(13), color=(1, 1, 1, 1),
            background_normal="", background_down="",
            background_color=(0, 0, 0, 0),
            size_hint=(None, 1), width=dp(44),
            **text_style(),
        )
        msg_btn.bind(on_press=lambda *_: show_toast("暂无新消息"))
        bar.add_widget(msg_btn)
        return bar

    def _build_weather_card(self):
        card = FloatLayout(size_hint=(1, None), height=dp(180))
        with card.canvas.before:
            Color(0.20, 0.65, 0.30, 1)
            self.weather_bg = RoundedRectangle(
                pos=card.pos, size=card.size, radius=[dp(18)] * 4)
        card.bind(
            pos=lambda i, *_: setattr(self.weather_bg, "pos", i.pos),
            size=lambda i, *_: setattr(self.weather_bg, "size", i.size),
        )

        # 主内容区（上半部分）
        main_box = BoxLayout(
            orientation="vertical", spacing=dp(6),
            size_hint=(1, None), height=dp(136),
            padding=(dp(18), dp(16), dp(18), dp(8)),
            pos_hint={"x": 0, "top": 1},
        )

        # 右上角城市切换按钮
        self.city_btn = Button(
            text="广州 v",
            font_size=sp(14), color=(1, 1, 1, 0.88),
            background_normal="", background_down="",
            background_color=(0, 0, 0, 0),
            size_hint=(None, None), size=(dp(80), dp(32)),
            pos_hint={"right": 0.98, "top": 0.98},
            **text_style(),
        )
        self.city_btn.bind(on_press=self._show_city_picker)
        card.add_widget(self.city_btn)


        # 第一行：温度 + 天气图标
        top_row = BoxLayout(size_hint=(1, None), height=dp(58), spacing=dp(0))
        self.temp_label = Label(
            text="--°", font_size=sp(48), bold=True,
            color=(1, 1, 1, 1), size_hint=(1, None), height=dp(58),
            halign="left", valign="middle", **text_style(),
        )
        self.temp_label.bind(size=self.temp_label.setter("text_size"))
        top_row.add_widget(self.temp_label)

        self._weather_icon_label = Label(
            text="晴",
            font_size=sp(16), bold=True,
            color=(1, 0.96, 0.60, 1),
            size_hint=(None, None), size=(dp(48), dp(58)),
            halign="center", valign="middle", **text_style(),
        )
        self._weather_icon_label.bind(
            size=self._weather_icon_label.setter("text_size"))
        top_row.add_widget(self._weather_icon_label)
        main_box.add_widget(top_row)

        # 第二行：最高最低温 + 天气描述
        self.desc_label = Label(
            text="天气加载中...",
            font_size=sp(13), color=(0.88, 1, 0.88, 1),
            size_hint=(1, None), height=dp(24),
            halign="left", valign="middle", **text_style(),
        )
        self.desc_label.bind(size=self.desc_label.setter("text_size"))
        main_box.add_widget(self.desc_label)

        # 第三行：气象预警按钮
        warning_btn = Button(
            text="气象预警",
            font_size=sp(13), color=(1, 0.92, 0.60, 1),
            background_normal="", background_down="",
            background_color=(0, 0, 0, 0),
            size_hint=(None, None), size=(dp(80), dp(30)),
            halign="left",
            **text_style(),
        )
        warning_btn.bind(on_press=lambda *_: open_text_popup(
            "气象预警", "气象台发布暴雨蓝色预警"))
        main_box.add_widget(warning_btn)
        card.add_widget(main_box)

        # 底部今日适宜标签行
        suitable_box = BoxLayout(
            size_hint=(1, None), height=dp(44),
            pos_hint={"x": 0, "y": 0},
            padding=(dp(12), dp(6), dp(12), dp(6)),
            spacing=dp(8),
        )
        with suitable_box.canvas.before:
            Color(0.16, 0.55, 0.26, 1)
            suitable_bg = RoundedRectangle(
                pos=suitable_box.pos, size=suitable_box.size,
                radius=[0, 0, dp(18), dp(18)],
            )
        suitable_box.bind(
            pos=lambda i, *_: setattr(suitable_bg, "pos", i.pos),
            size=lambda i, *_: setattr(suitable_bg, "size", i.size),
        )
        suitable_title = Label(
            text="今日适宜", font_size=sp(13),
            color=(0.88, 1, 0.88, 1),
            size_hint=(None, 1), width=dp(56),
            halign="left", valign="middle", **text_style(),
        )
        suitable_box.add_widget(suitable_title)

        for item in ["浇灌", "种植", "除虫", "巡田"]:
            tag_wrap = BoxLayout(size_hint=(None, 1), width=dp(48))
            with tag_wrap.canvas.before:
                Color(0.28, 0.72, 0.40, 1)
                tag_bg = RoundedRectangle(
                    pos=tag_wrap.pos, size=tag_wrap.size, radius=[dp(8)] * 4)
            tag_wrap.bind(
                pos=lambda i, b=tag_bg, *_: setattr(b, "pos", i.pos),
                size=lambda i, b=tag_bg, *_: setattr(b, "size", i.size),
            )
            tag = Label(
                text=item, font_size=sp(13),
                color=(1, 1, 1, 1),
                size_hint=(1, 1),
                halign="center", valign="middle", **text_style(),
            )
            tag.bind(size=tag.setter("text_size"))
            tag_wrap.add_widget(tag)
            suitable_box.add_widget(tag_wrap)

        card.add_widget(suitable_box)
        return card

    def _show_city_picker(self, _instance=None):
        from kivy.uix.popup import Popup
        from kivy.uix.textinput import TextInput
        from utils import _update_popup_rect
        from kivy.graphics import Color, RoundedRectangle

        popup = Popup(title="", separator_height=0,
                      size_hint=(0.84, None), height=dp(320))  # 高度从260改成320
        box = BoxLayout(orientation="vertical", spacing=dp(12), padding=dp(18))
        with box.canvas.before:
            Color(1, 1, 1, 1)
            bg = RoundedRectangle(pos=box.pos, size=box.size, radius=[dp(16)] * 4)
        box.bind(
            pos=lambda i, *_: _update_popup_rect(i, bg),
            size=lambda i, *_: _update_popup_rect(i, bg),
        )

        title_lbl = Label(
            text="切换城市", font_size=sp(18), bold=True,
            color=(0.08, 0.08, 0.08, 1),
            size_hint=(1, None), height=dp(28),
            halign="center", valign="middle", **text_style(),
        )
        title_lbl.bind(size=title_lbl.setter("text_size"))
        box.add_widget(title_lbl)

        hint_lbl = Label(
            text="输入城市拼音，如：beijing、shanghai",
            font_size=sp(13), color=(0.55, 0.55, 0.55, 1),
            size_hint=(1, None), height=dp(22),
            halign="left", valign="middle", **text_style(),
        )
        hint_lbl.bind(size=hint_lbl.setter("text_size"))
        box.add_widget(hint_lbl)

        # 输入框
        city_input = TextInput(
            hint_text="输入城市拼音",
            text=WEATHER_CITY,
            multiline=False, input_type="text",
            background_normal="", background_active="",
            background_color=(0.94, 0.94, 0.94, 1),
            padding=(dp(12), dp(10)),
            font_size=sp(16),
            size_hint=(1, None), height=dp(48),  # 固定高度
            **text_style(),
        )
        box.add_widget(city_input)

        # 常用城市快捷按钮
        quick_row = BoxLayout(
            size_hint=(1, None), height=dp(40), spacing=dp(8))
        for city_name, city_en in [
            ("广州", "guangzhou"), ("北京", "beijing"),
            ("上海", "shanghai"), ("深圳", "shenzhen"),
        ]:
            qbtn = Button(
                text=city_name, font_size=sp(14),
                color=GREEN,
                background_normal="", background_down="",
                background_color=(0.88, 0.97, 0.88, 1),
                size_hint=(1, 1),
                **text_style(),
            )
            qbtn.bind(on_press=lambda *_, c=city_en: setattr(city_input, "text", c))
            quick_row.add_widget(qbtn)
        box.add_widget(quick_row)

        btn_row = BoxLayout(size_hint=(1, None), height=dp(48), spacing=dp(12))
        from widgets.base_widgets import RoundedButton
        confirm_btn = RoundedButton(
            text="确定", color=(1, 1, 1, 1),
            size_hint=(1, 1), **text_style(),
        )
        cancel_btn = RoundedButton(
            text="取消", color=(1, 1, 1, 1),
            fill_color=(0.65, 0.65, 0.65, 1),
            size_hint=(1, 1), **text_style(),
        )

        def confirm(*_):
            global WEATHER_CITY
            new_city = city_input.text.strip()
            if not new_city:
                return
            WEATHER_CITY = new_city
            _save_city(new_city)
            self.city_btn.text = f"{new_city} v"
            self.temp_label.text = "--°"
            self.desc_label.text = "天气加载中..."
            popup.dismiss()
            self._load_weather()

        confirm_btn.bind(on_press=confirm)
        cancel_btn.bind(on_press=lambda *_: popup.dismiss())
        btn_row.add_widget(confirm_btn)
        btn_row.add_widget(cancel_btn)
        box.add_widget(btn_row)
        popup.content = box
        popup.open()

    def _load_weather(self):
        def on_success(data):
            self.temp_label.text = f"{data['temp']}°"
            self.desc_label.text = (
                f"最高{data['max']}° 最低{data['min']}°  {data['desc']}"
            )
            city = data.get("city", WEATHER_CITY)
            self.city_btn.text = f"{city} v"
            desc = data["desc"]
            if "雨" in desc:
                self._weather_icon_label.text = "雨"
            elif "云" in desc or "阴" in desc:
                self._weather_icon_label.text = "阴"
            elif "雪" in desc:
                self._weather_icon_label.text = "雪"
            else:
                self._weather_icon_label.text = "晴"

        def on_error(msg):
            self.temp_label.text = "--°"
            self.desc_label.text = "网络异常，无法获取天气"

        fetch_weather(WEATHER_CITY, on_success, on_error)


    def _load_weather(self):
        def on_success(data):
            self.temp_label.text = f"{data['temp']}°"
            self.desc_label.text = (
                f"最高{data['max']}° 最低{data['min']}°  {data['desc']}"
            )
            desc = data["desc"]
            if "雨" in desc:
                self._weather_icon_label.text = "雨"
            elif "云" in desc or "阴" in desc:
                self._weather_icon_label.text = "阴"
            elif "雪" in desc:
                self._weather_icon_label.text = "雪"
            else:
                self._weather_icon_label.text = "晴"

        def on_error(msg):
            self.temp_label.text = "--°"
            self.desc_label.text = "网络异常，无法获取天气"

        fetch_weather(WEATHER_CITY, on_success, on_error)

    def _build_tool_section(self):
        wrapper = BoxLayout(orientation="vertical", spacing=dp(8),
                            size_hint=(1, None))
        wrapper.bind(minimum_height=wrapper.setter("height"))

        header = BoxLayout(size_hint=(1, None), height=dp(36),
                           padding=(dp(4), 0, 0, 0))
        title = Label(
            text="我的工具", font_size=sp(16), bold=True,
            color=(0.08, 0.08, 0.08, 1),
            halign="left", valign="middle", **text_style(),
        )
        title.bind(size=title.setter("text_size"))
        header.add_widget(title)
        wrapper.add_widget(header)

        tools = [
            (os.path.join(IMAGE_DIR, "icon_plan.png"), "计划", "农事计划",
             lambda *_: open_text_popup("农事计划", "即将推出")),
            (os.path.join(IMAGE_DIR, "icon_encyclopedia.png"), "百科", "虫害百科",
             lambda *_: setattr(self.manager, "current", "encyclopedia")),
            (os.path.join(IMAGE_DIR, "icon_favorite.png"), "收藏", "我的收藏",
             lambda *_: setattr(self.manager, "current", "favorite")),
            (os.path.join(IMAGE_DIR, "icon_map.png"), "地图", "病虫害分布图",
             lambda *_: setattr(self.manager, "current", "map")),
            (os.path.join(IMAGE_DIR, "icon_camera.png"), "拍照", "拍照识别",
             lambda *_: App.get_running_app().show_capture_menu()),
            (os.path.join(IMAGE_DIR, "icon_more.png"), "更多", "更多工具",
             lambda *_: open_text_popup("更多工具", "土壤分析\n农资识别\n作物生长监测")),
        ]

        row1 = BoxLayout(spacing=dp(8), size_hint=(1, None), height=dp(90))
        row2 = BoxLayout(spacing=dp(8), size_hint=(1, None), height=dp(90))
        for idx, (icon_src, icon_txt, title_txt, callback) in enumerate(tools):
            card = HomeToolCard(
                icon_source=icon_src,
                icon_text=icon_txt,
                title=title_txt,
            )
            card.bind(on_press=callback)
            if idx < 3:
                row1.add_widget(card)
            else:
                row2.add_widget(card)
        wrapper.add_widget(row1)
        wrapper.add_widget(row2)
        return wrapper

    def _build_reminder_card(self):
        wrapper = BoxLayout(orientation="vertical", spacing=dp(8),
                            size_hint=(1, None))
        wrapper.bind(minimum_height=wrapper.setter("height"))

        header = BoxLayout(size_hint=(1, None), height=dp(36),
                           padding=(dp(4), 0, 0, 0))
        title = Label(
            text="今日提醒", font_size=sp(16), bold=True,
            color=(0.08, 0.08, 0.08, 1),
            halign="left", valign="middle", **text_style(),
        )
        title.bind(size=title.setter("text_size"))
        header.add_widget(title)
        view_all = UnderlineLabel(
            text="[u]查看全部[/u]", color=GREEN, font_size=sp(13),
            size_hint=(None, 1), width=dp(72),
            halign="right", valign="middle", **text_style(),
        )
        view_all.bind(size=view_all.setter("text_size"))
        view_all.bind(on_press=lambda *_: open_text_popup(
            "更多提醒", "\n".join(HOME_REMINDERS)))
        header.add_widget(view_all)
        wrapper.add_widget(header)

        card = BoxLayout(
            orientation="vertical", spacing=0,
            padding=(dp(14), dp(6), dp(14), dp(6)),
            size_hint=(1, None),
        )
        card.bind(minimum_height=card.setter("height"))
        with card.canvas.before:
            Color(1, 1, 1, 1)
            reminder_bg = RoundedRectangle(
                pos=card.pos, size=card.size, radius=[dp(14)] * 4)
        card.bind(
            pos=lambda i, *_: setattr(reminder_bg, "pos", i.pos),
            size=lambda i, *_: setattr(reminder_bg, "size", i.size),
        )
        for idx, reminder in enumerate(HOME_REMINDERS):
            row = BoxLayout(size_hint=(1, None), height=dp(48), spacing=dp(8))

            bar_wrap = BoxLayout(size_hint=(None, 1), width=dp(4))
            with bar_wrap.canvas.before:
                Color(*GREEN)
                bar_rect = RoundedRectangle(
                    pos=bar_wrap.pos, size=bar_wrap.size, radius=[dp(2)] * 4)
            bar_wrap.bind(
                pos=lambda i, r=bar_rect, *_: setattr(r, "pos", i.pos),
                size=lambda i, r=bar_rect, *_: setattr(r, "size", i.size),
            )
            row.add_widget(bar_wrap)

            label = Label(
                text=reminder, font_size=sp(14),
                color=(0.16, 0.16, 0.16, 1),
                size_hint=(1, 1),
                halign="left", valign="middle", **text_style(),
            )
            label.bind(size=label.setter("text_size"))
            row.add_widget(label)

            detail_btn = UnderlineLabel(
                text="[u]详情[/u]",
                color=GREEN, font_size=sp(13),
                size_hint=(None, 1), width=dp(40),
                halign="right", valign="middle", **text_style(),
            )
            detail_btn.bind(size=detail_btn.setter("text_size"))
            detail_btn.bind(
                on_press=lambda *_, r=reminder: open_text_popup("提醒详情", r))
            row.add_widget(detail_btn)
            card.add_widget(row)

            if idx < len(HOME_REMINDERS) - 1:
                divider = Widget(size_hint=(1, None), height=dp(1))
                with divider.canvas:
                    Color(0.92, 0.92, 0.92, 1)
                    div_rect = Rectangle(pos=divider.pos, size=divider.size)
                divider.bind(
                    pos=lambda i, r=div_rect, *_: setattr(r, "pos", i.pos),
                    size=lambda i, r=div_rect, *_: setattr(r, "size", i.size),
                )
                card.add_widget(divider)
        wrapper.add_widget(card)
        return wrapper

    def _build_bottom_nav(self):
        from kivy.uix.image import Image as KImg
        nav = BoxLayout(
            orientation="horizontal", size_hint=(1, None), height=dp(64),
            pos_hint={"x": 0, "y": 0},
            padding=(0, dp(2), 0, dp(2)),
        )
        with nav.canvas.before:
            Color(1, 1, 1, 1)
            nav.bg_rect = Rectangle(pos=nav.pos, size=nav.size)
        nav.bind(
            pos=lambda inst, *_: update_nav_rect(inst),
            size=lambda inst, *_: update_nav_rect(inst),
        )

        items = [
            ("首页", "icon_home.png",
             lambda *_: setattr(self.manager, "current", "home"), True),
            ("社区", "icon_community.png",
             lambda *_: setattr(self.manager, "current", "community"), False),
            ("拍照", "",
             lambda *_: App.get_running_app().show_capture_menu(), False),
            ("百科", "icon_encyclopedia.png",
             lambda *_: setattr(self.manager, "current", "store"), False),
            ("我的", "icon_my.png",
             lambda *_: setattr(self.manager, "current", "mypage"), False),
        ]

        for title, icon_file, callback, is_active in items:
            text_color = GREEN if is_active else (0.55, 0.55, 0.55, 1)

            if title == "拍照":
                btn_wrap = FloatLayout(size_hint=(1, 1))
                circle_btn = Button(
                    text="+",
                    font_size=sp(28), bold=True,
                    color=(1, 1, 1, 1),
                    background_normal="", background_down="",
                    background_color=(0, 0, 0, 0),
                    size_hint=(None, None), size=(dp(48), dp(48)),
                    pos_hint={"center_x": 0.5, "center_y": 0.5},
                )
                circle_btn.bind(on_press=callback)
                circle_btn.bind(
                    pos=_update_camera_btn,
                    size=_update_camera_btn,
                )
                btn_wrap.add_widget(circle_btn)
                nav.add_widget(btn_wrap)
                continue

            # 外层用 ButtonBehavior + BoxLayout 实现可点击的竖排布局
            from kivy.uix.behaviors import ButtonBehavior

            class NavItem(ButtonBehavior, BoxLayout):
                pass

            item = NavItem(
                orientation="vertical",
                spacing=dp(2),
                size_hint=(1, 1),
                padding=(0, dp(4), 0, dp(4)),
            )
            item.bind(on_press=callback)

            # 图标
            icon_path = os.path.join(IMAGE_DIR, icon_file)
            if icon_file and os.path.exists(icon_path):
                icon_widget = KImg(
                    source=icon_path,
                    size_hint=(1, None), height=dp(26),
                    allow_stretch=True, keep_ratio=True,
                )
            else:
                icon_widget = Label(
                    text="●", font_size=sp(8),
                    color=text_color,
                    size_hint=(1, None), height=dp(26),
                    halign="center", valign="middle",
                )
                icon_widget.bind(size=icon_widget.setter("text_size"))
            item.add_widget(icon_widget)

            # 文字
            lbl = Label(
                text=title, font_size=sp(12),
                color=text_color,
                size_hint=(1, None), height=dp(16),
                halign="center", valign="middle",
                **text_style(),
            )
            lbl.bind(size=lbl.setter("text_size"))
            item.add_widget(lbl)

            nav.add_widget(item)
        return nav

    def search_pests(self, _instance=None):
        keyword = self.home_search_input.text.strip().lower()
        if not keyword:
            show_toast("请输入病虫害名称")
            return
        pests = STORE_DB.get_pest_entries()
        for pest in pests:
            if keyword in pest["name"].lower():
                detail_screen = self.manager.get_screen("pest_detail")
                detail_screen.set_pest(pest["id"])
                self.manager.current = "pest_detail"
                return
        show_toast("未找到相关病虫害")

    def cancel_home_search(self, _instance=None):
        self.home_search_input.text = ""
        self.home_search_input.focus = False

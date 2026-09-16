# -*- coding: utf-8 -*-
"""农事计划页面（新版 QQ 风格，简洁卡片式）。

日历部分使用现成的 KivyMD ``MDDatePicker``（成熟的三方月历组件），
页面内的周视图改为 7 等分 GridLayout，不使用横向 ScrollView，
避免 ScrollView 自动居中导致「周一被挤出可视区」的老问题。
"""
import os
from datetime import datetime, timedelta

from kivy.app import App
from kivy.clock import Clock
from kivy.graphics import Color, Ellipse, Line, Rectangle, RoundedRectangle
from kivy.metrics import dp, sp
from kivy.uix.behaviors import ButtonBehavior
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.button import Button
from kivy.uix.floatlayout import FloatLayout
from kivy.uix.gridlayout import GridLayout
from kivy.uix.image import Image
from kivy.uix.label import Label
from kivy.uix.screenmanager import Screen
from kivy.uix.scrollview import ScrollView
from kivy.uix.widget import Widget

from config import GREEN, IMAGE_DIR
from utils import (text_style, show_toast, open_text_popup, bind_deferred_layout,
                   ensure_md_theme)
from widgets.base_widgets import RoundedButton

WEEK_CN = ["一", "二", "三", "四", "五", "六", "日"]


# 分类配色（柔和低饱和）
CATEGORY_COLORS = {
    "施肥": (0.98, 0.58, 0.18, 1),
    "浇灌": (0.24, 0.68, 0.92, 1),
    "除虫": (0.94, 0.36, 0.36, 1),
    "巡田": (0.48, 0.76, 0.38, 1),
    "除草": (0.58, 0.72, 0.30, 1),
    "收获": (0.94, 0.70, 0.20, 1),
}

# 作物 → 对应图标（用户提供的独立插画，透明底）
CROP_ICONS = {
    "番茄": "番茄.png",
    "黄瓜": "黄瓜.png",
    "水稻": "水稻.png",
    "果园": "果园.png",
    "玉米": "玉米.png",
}

# 模拟农事计划数据
FARMING_PLANS = [
    {
        "id": 1,
        "title": "番茄地块追肥",
        "category": "施肥",
        "crop": "番茄",
        "date": "今天",
        "time": "08:00",
        "plot": "地块1",
        "status": "pending",
    },
    {
        "id": 2,
        "title": "大棚黄瓜浇水",
        "category": "浇灌",
        "crop": "黄瓜",
        "date": "今天",
        "time": "10:30",
        "plot": "地块2",
        "status": "done",
    },
    {
        "id": 3,
        "title": "水稻稻飞虱巡查",
        "category": "除虫",
        "crop": "水稻",
        "date": "今天",
        "time": "14:00",
        "plot": "地块3",
        "status": "pending",
    },
    {
        "id": 4,
        "title": "果园巡田除草",
        "category": "巡田",
        "crop": "果园",
        "date": "明天",
        "time": "07:00",
        "plot": "果园A",
        "status": "pending",
    },
    {
        "id": 5,
        "title": "玉米追肥施药",
        "category": "施肥",
        "crop": "玉米",
        "date": "明天",
        "time": "09:00",
        "plot": "地块4",
        "status": "pending",
    },
]


def _category_color(category):
    return CATEGORY_COLORS.get(category, GREEN)


class DateCell(ButtonBehavior, BoxLayout):
    """周视图中的一个日期格子。

    用 GridLayout 的 7 等分来摆放，格子宽度由父容器均分，
    不存在横向滚动，因此周一永远不会被挤出可视区。
    """

    def __init__(self, day, is_selected=False, is_today=False, on_select=None, **kwargs):
        super().__init__(
            orientation="vertical", spacing=dp(1),
            size_hint=(1, 1), padding=(0, dp(2), 0, dp(2)),
            **kwargs,
        )
        self.day = day
        self.on_select = on_select

        self.bg_color = GREEN
        if is_selected:
            self.bg_color = GREEN
            text_color = (1, 1, 1, 1)
        elif is_today:
            self.bg_color = (0.86, 0.94, 0.86, 1)
            text_color = GREEN
        else:
            self.bg_color = (0.94, 0.96, 0.94, 1)
            text_color = (0.40, 0.40, 0.40, 1)

        self.bind(pos=self._update_bg, size=self._update_bg)

        week_label = Label(
            text=f"周{WEEK_CN[day.weekday()]}", font_size=sp(9),
            color=text_color,
            size_hint=(1, None), height=dp(14),
            halign="center", valign="middle", **text_style(),
        )
        week_label.bind(size=week_label.setter("text_size"))
        day_label = Label(
            text=str(day.day), font_size=sp(14), bold=True,
            color=text_color,
            size_hint=(1, 1),
            halign="center", valign="middle", **text_style(),
        )
        day_label.bind(size=day_label.setter("text_size"))
        self.add_widget(week_label)
        self.add_widget(day_label)

        self.bind(on_press=self._pressed)

    def _update_bg(self, *_args):
        self.canvas.before.clear()
        with self.canvas.before:
            Color(*self.bg_color)
            RoundedRectangle(pos=self.pos, size=self.size, radius=[dp(10)] * 4)

    def _pressed(self, *_args):
        if self.on_select:
            self.on_select(self.day)


class PlanItemCard(ButtonBehavior, BoxLayout):
    """单个农事计划项卡片。"""

    def __init__(self, plan, on_toggle=None, **kwargs):
        super().__init__(
            orientation="horizontal",
            spacing=dp(12),
            padding=(dp(12), dp(10), dp(12), dp(10)),
            size_hint=(1, None), height=dp(64),
            **kwargs,
        )
        self.plan = plan
        self.on_toggle = on_toggle
        self.bind(pos=self._update_bg, size=self._update_bg)

        color = _category_color(plan.get("category", ""))
        is_done = plan.get("status") == "done"

        # 左侧作物图标：优先用用户提供的作物插画；无对应图标时退回分类色方块
        icon_wrap = FloatLayout(size_hint=(None, 1), width=dp(40))
        crop = plan.get("crop", "")
        icon_file = CROP_ICONS.get(crop, "")
        icon_path = os.path.join(IMAGE_DIR, icon_file) if icon_file else ""
        if icon_path and os.path.exists(icon_path):
            icon_wrap.add_widget(Image(
                source=icon_path,
                size_hint=(None, None), size=(dp(38), dp(38)),
                allow_stretch=True, keep_ratio=True,
                pos_hint={"center_x": 0.5, "center_y": 0.5},
            ))
        else:
            with icon_wrap.canvas.before:
                Color(*color)
                self.icon_bg = RoundedRectangle(
                    pos=icon_wrap.pos, size=icon_wrap.size, radius=[dp(10)] * 4
                )
            icon_wrap.bind(
                pos=lambda i, *_: setattr(self.icon_bg, "pos", (i.x + dp(2), i.y + dp(2))),
                size=lambda i, *_: setattr(
                    self.icon_bg, "size", (i.width - dp(4), i.height - dp(4))
                ),
            )
            cat_text = plan.get("category", "")[:1]
            cat_label = Label(
                text=cat_text, font_size=sp(16), bold=True,
                color=(1, 1, 1, 1),
                size_hint=(1, 1),
                halign="center", valign="middle", **text_style(),
            )
            cat_label.bind(size=cat_label.setter("text_size"))
            icon_wrap.add_widget(cat_label)
        self.add_widget(icon_wrap)

        # 中间信息
        info_box = BoxLayout(orientation="vertical", spacing=dp(3), size_hint=(1, 1))
        title_color = (0.55, 0.55, 0.55, 1) if is_done else (0.12, 0.12, 0.12, 1)
        title_label = Label(
            text=plan.get("title", ""),
            font_size=sp(15), bold=True,
            color=title_color,
            size_hint=(1, 1),
            halign="left", valign="middle", **text_style(),
        )
        title_label.bind(size=title_label.setter("text_size"))
        info_box.add_widget(title_label)

        meta_label = Label(
            text=f"{plan.get('date', '')}  {plan.get('time', '')}  ·  {plan.get('plot', '')}",
            font_size=sp(12),
            color=(0.55, 0.55, 0.55, 1),
            size_hint=(1, 1),
            halign="left", valign="middle", **text_style(),
        )
        meta_label.bind(size=meta_label.setter("text_size"))
        info_box.add_widget(meta_label)
        self.add_widget(info_box)

        # 右侧状态标签
        self.status_label = Label(
            text="", font_size=sp(12), bold=True,
            color=(1, 1, 1, 1),
            size_hint=(None, None), size=(dp(52), dp(24)),
            pos_hint={"center_y": 0.5},
            halign="center", valign="middle", **text_style(),
        )
        self.status_label.bind(size=self.status_label.setter("text_size"))
        self.add_widget(self.status_label)
        self.status_label.bind(pos=self._update_status_style, size=self._update_status_style)

        self.bind(on_press=self._toggle_status)
        self._update_status_style()

    def _update_bg(self, *_args):
        self.canvas.before.clear()
        with self.canvas.before:
            Color(1, 1, 1, 1)
            RoundedRectangle(pos=self.pos, size=self.size, radius=[dp(14)] * 4)

    def _update_status_style(self, *_args):
        is_done = self.plan.get("status") == "done"
        self.status_label.canvas.before.clear()
        with self.status_label.canvas.before:
            if is_done:
                Color(0.55, 0.75, 0.55, 1)
            else:
                Color(0.95, 0.65, 0.25, 1)
            RoundedRectangle(
                pos=self.status_label.pos,
                size=self.status_label.size,
                radius=[dp(12)] * 4,
            )
        self.status_label.text = "已完成" if is_done else "待办"

    def _toggle_status(self, *_args):
        new_status = "done" if self.plan.get("status") != "done" else "pending"
        self.plan["status"] = new_status
        self._update_status_style()
        if self.on_toggle:
            self.on_toggle(self.plan)


class FarmingPlanScreen(Screen):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.name = "farming_plan"
        self.selected_date = datetime.now()
        self.plans = [dict(p) for p in FARMING_PLANS]
        self.build_ui()

    def build_ui(self):
        self.layout = FloatLayout()
        self.add_widget(self.layout)

        # 页面背景
        with self.layout.canvas.before:
            Color(0.95, 0.98, 0.95, 1)
            self.bg_rect = Rectangle(pos=self.layout.pos, size=self.layout.size)
        self.layout.bind(pos=self._update_bg, size=self._update_bg)

        # 顶部标题栏（白底 + 绿色标题）
        self.top_bar = FloatLayout(
            size_hint=(1, None), height=dp(56),
            pos_hint={"x": 0, "top": 1},
        )
        with self.top_bar.canvas.before:
            Color(1, 1, 1, 1)
            self.top_bar_rect = Rectangle(
                pos=self.top_bar.pos, size=self.top_bar.size)
            Color(0.88, 0.92, 0.88, 1)
            self.top_bar_line = Line(
                points=[self.top_bar.x, self.top_bar.y,
                        self.top_bar.right, self.top_bar.y], width=dp(1))
        self.top_bar.bind(pos=self._update_top_bar, size=self._update_top_bar)
        self.layout.add_widget(self.top_bar)

        self.back_btn = Button(
            text="<", font_size=sp(26), color=(0.22, 0.22, 0.22, 1),
            background_normal="", background_down="",
            background_color=(0, 0, 0, 0),
            size_hint=(None, None), size=(dp(44), dp(44)),
            pos_hint={"x": 0.02, "center_y": 0.5},
            **text_style(),
        )
        self.back_btn.bind(on_press=lambda *_: setattr(self.manager, "current", "home"))
        self.top_bar.add_widget(self.back_btn)

        self.title_label = Label(
            text="农事计划", font_size=sp(18), bold=True,
            color=(0.12, 0.12, 0.12, 1),
            size_hint=(0.5, None), height=dp(34),
            pos_hint={"center_x": 0.5, "center_y": 0.5},
            halign="center", valign="middle", **text_style(),
        )
        self.title_label.bind(size=self.title_label.setter("text_size"))
        self.top_bar.add_widget(self.title_label)

        self.add_btn = Button(
            text="+", font_size=sp(28), color=(1, 1, 1, 1),
            background_normal="", background_down="",
            background_color=(0, 0, 0, 0),
            size_hint=(None, None), size=(dp(32), dp(32)),
            pos_hint={"right": 0.97, "center_y": 0.5},
            **text_style(),
        )
        self.add_btn.bind(pos=self._draw_add_circle, size=self._draw_add_circle)
        self.add_btn.bind(on_press=self._show_add_plan)
        self.top_bar.add_widget(self.add_btn)

        # 内容滚动区
        self.scroll = ScrollView(
            size_hint=(1, None), do_scroll_x=False,
            pos_hint={"x": 0, "y": 0},
        )
        self.layout.add_widget(self.scroll)
        self.content_box = BoxLayout(
            orientation="vertical",
            spacing=dp(12),
            padding=(dp(10), dp(10), dp(10), dp(14)),
            size_hint=(1, None),
        )
        self.content_box.bind(minimum_height=self.content_box.setter("height"))
        self.scroll.add_widget(self.content_box)

        self.content_box.add_widget(self._build_calendar_card())
        self.content_box.add_widget(self._build_stats_card())
        self.content_box.add_widget(self._build_plan_list())

        bind_deferred_layout(self.layout, self._update_layout)
        Clock.schedule_once(lambda dt: self._update_layout(), 0)

    def _update_bg(self, *_args):
        self.bg_rect.pos = self.layout.pos
        self.bg_rect.size = self.layout.size

    def _update_top_bar(self, *_args):
        self.top_bar_rect.pos = self.top_bar.pos
        self.top_bar_rect.size = self.top_bar.size
        self.top_bar_line.points = [
            self.top_bar.x, self.top_bar.y,
            self.top_bar.right, self.top_bar.y,
        ]

    def _draw_add_circle(self, instance, *_args):
        instance.canvas.before.clear()
        with instance.canvas.before:
            Color(*GREEN)
            Ellipse(pos=instance.pos, size=instance.size)

    def _update_layout(self, *_args):
        top_h = self.top_bar.height
        available = max(dp(200), self.height - top_h)
        self.scroll.height = available
        self.scroll.pos = (0, 0)
        self.top_bar.pos = (0, self.height - top_h)
        self.top_bar.size = (self.width, top_h)

    # ---------------- 日历卡片（现成 MDDatePicker + 7 等分周视图） ----------------
    def _build_calendar_card(self):
        card = BoxLayout(
            orientation="vertical", spacing=dp(6),
            padding=(dp(10), dp(12), dp(10), dp(12)),
            size_hint=(1, None),
        )
        card.bind(minimum_height=card.setter("height"))
        with card.canvas.before:
            Color(1, 1, 1, 1)
            bg = RoundedRectangle(pos=card.pos, size=card.size, radius=[dp(16)] * 4)
        card.bind(pos=lambda i, r=bg, *_: setattr(r, "pos", i.pos),
                  size=lambda i, r=bg, *_: setattr(r, "size", i.size))

        # 1) 年月 + 左右切周
        month_bar = BoxLayout(size_hint=(1, None), height=dp(30))
        prev_btn = Button(
            text="<", font_size=sp(16), color=GREEN,
            background_normal="", background_down="",
            background_color=(0, 0, 0, 0),
            size_hint=(None, 1), width=dp(32),
            **text_style(),
        )
        prev_btn.bind(on_press=self._prev_week)
        next_btn = Button(
            text=">", font_size=sp(16), color=GREEN,
            background_normal="", background_down="",
            background_color=(0, 0, 0, 0),
            size_hint=(None, 1), width=dp(32),
            **text_style(),
        )
        next_btn.bind(on_press=self._next_week)
        # 标题按钮：点击弹出完整月历（KivyMD MDDatePicker）
        self.month_btn = Button(
            text=self.selected_date.strftime("%Y年%m月"),
            font_size=sp(16), bold=True, color=(0.12, 0.12, 0.12, 1),
            background_normal="", background_down="",
            background_color=(0, 0, 0, 0),
            size_hint=(1, 1),
            halign="center", valign="middle", **text_style(),
        )
        self.month_btn.bind(size=self.month_btn.setter("text_size"))
        self.month_btn.bind(on_press=self._open_date_picker)
        month_bar.add_widget(prev_btn)
        month_bar.add_widget(self.month_btn)
        month_bar.add_widget(next_btn)
        card.add_widget(month_bar)

        # 2) 星期表头
        head_row = GridLayout(
            cols=7, size_hint=(1, None), height=dp(18), spacing=dp(3),
        )
        for text in WEEK_CN:
            is_weekend = text in ("六", "日")
            lbl = Label(
                text=text, font_size=sp(10),
                color=(0.85, 0.42, 0.42, 1) if is_weekend else (0.62, 0.62, 0.62, 1),
                halign="center", valign="middle", **text_style(),
            )
            lbl.bind(size=lbl.setter("text_size"))
            head_row.add_widget(lbl)
        card.add_widget(head_row)

        # 3) 日期网格：7 等分，无横向滚动
        self.dates_grid = GridLayout(
            cols=7, rows=1, size_hint=(1, None), height=dp(46), spacing=dp(3),
        )
        self._render_date_cells()
        card.add_widget(self.dates_grid)

        # 4) 提示行
        self.date_hint = Label(
            text="点击上方月份可打开完整日历选择日期",
            font_size=sp(10), color=(0.66, 0.66, 0.66, 1),
            size_hint=(1, None), height=dp(16),
            halign="center", valign="middle", **text_style(),
        )
        self.date_hint.bind(size=self.date_hint.setter("text_size"))
        card.add_widget(self.date_hint)

        return card

    def _render_date_cells(self):
        self.dates_grid.clear_widgets()
        week_start = self.selected_date - timedelta(days=self.selected_date.weekday())
        for i in range(7):
            day = week_start + timedelta(days=i)
            self.dates_grid.add_widget(DateCell(
                day,
                is_selected=day.date() == self.selected_date.date(),
                is_today=day.date() == datetime.now().date(),
                on_select=self._on_date_cell_pressed,
            ))

    def _on_date_cell_pressed(self, day):
        self.selected_date = day
        self._sync_calendar_ui()

    def _sync_calendar_ui(self):
        self.month_btn.text = self.selected_date.strftime("%Y年%m月")
        self._render_date_cells()
        self._refresh_plan_list()

    # ---------------- 完整日历（KivyMD MDDatePicker） ----------------
    def _build_picker_class(self):
        """构造一个把文案汉化过的 MDDatePicker 子类。"""
        from datetime import date as _date
        from kivymd.uix.pickers import MDDatePicker

        class ChineseDatePicker(MDDatePicker):
            week_cn = WEEK_CN

            def set_text_full_date(self, year, month, day, orientation):
                # 原版返回 "Mon, Sep 14"，这里改成中文并设置中文字体
                try:
                    picked = _date(year, month, day)
                except Exception:
                    return ""
                return f"{self.week_cn[picked.weekday()]}, {picked.year}年{picked.month}月{picked.day}日"

        return ChineseDatePicker

    def _open_date_picker(self, *_args):
        try:
            theme = ensure_md_theme()
            picker_cls = self._build_picker_class()
        except Exception as exc:
            print("[calendar] 日历组件加载失败:", exc)
            show_toast("日历组件不可用，可通过左右箭头切换周")
            return
        if theme is None:
            show_toast("日历组件不可用，可通过左右箭头切换周")
            return
        try:
            dialog = picker_cls(
                year=self.selected_date.year,
                month=self.selected_date.month,
                day=self.selected_date.day,
                firstweekday=0,
                theme_cls=theme,
                font_name=text_style().get("font_name", "Roboto"),
                primary_color=GREEN,
                accent_color=GREEN,
                selector_color=GREEN,
                text_button_color=GREEN,
                text_color=(0.12, 0.12, 0.12, 1),
                text_current_color=GREEN,
                text_weekday_color=(0.62, 0.62, 0.62, 1),
            )
        except Exception as exc:
            print("[calendar] 日历创建失败:", exc)
            show_toast("日历打开失败，请重试")
            return

        dialog.title = "选择日期"
        dialog.bind(on_save=self._on_date_picked, on_cancel=lambda *a: None)
        dialog.open()

        # 等 KV 完成一帧后把英文文案汉化（标题、月份选择器、星期表头、按钮）
        Clock.schedule_once(
            lambda dt, d=dialog: self._localize_datepicker(d), 0.05
        )

    def _localize_datepicker(self, dialog):
        font = text_style().get("font_name")
        # 按钮：OK / CANCEL → 确定 / 取消
        for key, text in (("ok_button", "确定"), ("cancel_button", "取消")):
            btn = dialog.ids.get(key)
            if btn is not None:
                btn.text = text
                if font:
                    btn.font_name = font
        # 顶部标题
        label_title = dialog.ids.get("label_title")
        if label_title is not None:
            label_title.text = dialog.title
            if font:
                label_title.font_name = font
        # 月份选择器：September 2026 → 2026年09月
        month_sel = dialog.ids.get("label_month_selector")
        if month_sel is not None:
            month_sel.text = f"{dialog.year}年{dialog.month:02d}月"
            if font:
                month_sel.font_name = font
        # 星期表头：M T W T F S S → 一 二 三 四 五 六 日
        calendar_layout = getattr(dialog, "_calendar_layout", None)
        if calendar_layout is not None:
            weekday_labels = [
                w for w in calendar_layout.children
                if type(w).__name__ == "DatePickerWeekdayLabel"
            ]
            # GridLayout 子控件顺序是后添加的在前面；weekday 先添加，所以在末尾
            for idx, w in enumerate(reversed(weekday_labels)):
                if idx < 7:
                    w.text = WEEK_CN[idx]
                    if font:
                        w.font_name = font

    def _on_date_picked(self, instance, value, date_range):
        self.selected_date = datetime.combine(value, datetime.min.time())
        self._sync_calendar_ui()

    def _prev_week(self, *_args):
        self.selected_date -= timedelta(days=7)
        self._sync_calendar_ui()

    def _next_week(self, *_args):
        self.selected_date += timedelta(days=7)
        self._sync_calendar_ui()

    # ---------------- 统计卡片 ----------------
    def _build_stats_card(self):
        card = BoxLayout(
            orientation="horizontal", spacing=dp(10),
            size_hint=(1, None), height=dp(74),
        )
        with card.canvas.before:
            Color(1, 1, 1, 1)
            bg = RoundedRectangle(pos=card.pos, size=card.size, radius=[dp(16)] * 4)
        card.bind(pos=lambda i, r=bg, *_: setattr(r, "pos", i.pos),
                  size=lambda i, r=bg, *_: setattr(r, "size", i.size))

        pending = sum(1 for p in self.plans if p.get("status") == "pending")
        done = sum(1 for p in self.plans if p.get("status") == "done")
        overdue = 0

        for label, value, color in [
            ("待完成", pending, (0.95, 0.62, 0.22, 1)),
            ("已完成", done, (0.45, 0.75, 0.35, 1)),
            ("已逾期", overdue, (0.95, 0.45, 0.45, 1)),
        ]:
            item = BoxLayout(orientation="vertical", spacing=dp(2))
            dot = Label(
                text="●", font_size=sp(10),
                color=color,
                size_hint=(1, None), height=dp(14),
                halign="center", valign="middle", **text_style(),
            )
            val_label = Label(
                text=str(value), font_size=sp(22), bold=True,
                color=color,
                size_hint=(1, 1),
                halign="center", valign="middle", **text_style(),
            )
            val_label.bind(size=val_label.setter("text_size"))
            name_label = Label(
                text=label, font_size=sp(11),
                color=(0.55, 0.55, 0.55, 1),
                size_hint=(1, 1),
                halign="center", valign="middle", **text_style(),
            )
            name_label.bind(size=name_label.setter("text_size"))
            item.add_widget(dot)
            item.add_widget(val_label)
            item.add_widget(name_label)
            card.add_widget(item)
        return card

    # ---------------- 计划列表 ----------------
    def _build_plan_list(self):
        wrapper = BoxLayout(orientation="vertical", spacing=dp(8),
                            size_hint=(1, None))
        wrapper.bind(minimum_height=wrapper.setter("height"))

        header = BoxLayout(size_hint=(1, None), height=dp(32),
                           padding=(dp(4), 0, 0, 0))
        title = Label(
            text="今日计划", font_size=sp(16), bold=True,
            color=(0.08, 0.08, 0.08, 1),
            halign="left", valign="middle", **text_style(),
        )
        title.bind(size=title.setter("text_size"))
        header.add_widget(title)
        wrapper.add_widget(header)

        self.plan_list_box = BoxLayout(
            orientation="vertical", spacing=dp(10),
            size_hint=(1, None),
        )
        self.plan_list_box.bind(
            minimum_height=self.plan_list_box.setter("height")
        )
        self._refresh_plan_list()
        wrapper.add_widget(self.plan_list_box)

        return wrapper

    def _refresh_plan_list(self):
        self.plan_list_box.clear_widgets()
        is_today = self.selected_date.date() == datetime.now().date()
        visible_plans = self.plans if is_today else []
        if not visible_plans:
            empty_label = Label(
                text="暂无农事计划\n点击右上角 + 添加",
                font_size=sp(14),
                color=(0.55, 0.55, 0.55, 1),
                size_hint=(1, None), height=dp(80),
                halign="center", valign="middle", **text_style(),
            )
            empty_label.bind(size=empty_label.setter("text_size"))
            self.plan_list_box.add_widget(empty_label)
            return
        for plan in visible_plans:
            card = PlanItemCard(plan, on_toggle=self._on_plan_toggle)
            self.plan_list_box.add_widget(card)

    def _on_plan_toggle(self, plan):
        show_toast(f"{plan['title']} 已标记为 {('已完成' if plan['status'] == 'done' else '待完成')}")

    def _show_add_plan(self, *_args):
        open_text_popup(
            "添加农事计划",
            "当前为演示界面，添加功能可在后续版本对接后端后实现。",
        )


# 保持与旧命名兼容
PlanScreen = FarmingPlanScreen

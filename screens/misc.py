import io
import math
import os
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed

import requests
from PIL import Image as PILImage
from kivy.app import App
from kivy.clock import Clock
from kivy.graphics import Color, Ellipse, Line, Rectangle, RoundedRectangle
from kivy.metrics import dp, sp
from kivy.uix.behaviors import ButtonBehavior
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.floatlayout import FloatLayout
from kivy.uix.image import Image
from kivy.uix.label import Label
from kivy.uix.modalview import ModalView
from kivy.uix.textinput import TextInput

from config import GREEN, IMAGE_DIR
from database.store_db import STORE_DB
from screens.account_pages import AccountPage, INK, MUTED, _text
from utils import BaseScreen, open_text_popup, show_toast, text_style
from widgets.base_widgets import CircleImage, RoundedButton


MAP_CENTER = (23.1291, 113.2644)
MAP_ZOOM = 9
MAP_TILE_URL = "https://tile.openstreetmap.org/{z}/{x}/{y}.png"
MAP_USER_AGENT = "PlantDoctor/1.0 (+https://github.com/hahahachaoge/PlantDoctor)"
MAP_CACHE_DIR = os.path.join(os.path.dirname(IMAGE_DIR), "photos", "map_tiles")

# 广州市现辖 11 个行政区。这里使用行政区中心附近的 WGS84 参考位置帮助用户
# 理解全市范围；这些点不是病虫害发生记录，不参与用户观察统计。
REFERENCE_POINTS = (
    {"location_name": "越秀区", "latitude": 23.1291, "longitude": 113.2668},
    {"location_name": "荔湾区", "latitude": 23.1259, "longitude": 113.2442},
    {"location_name": "海珠区", "latitude": 23.0833, "longitude": 113.3172},
    {"location_name": "天河区", "latitude": 23.1247, "longitude": 113.3612},
    {"location_name": "白云区", "latitude": 23.1579, "longitude": 113.2732},
    {"location_name": "黄埔区", "latitude": 23.1814, "longitude": 113.4805},
    {"location_name": "花都区", "latitude": 23.4042, "longitude": 113.2205},
    {"location_name": "番禺区", "latitude": 22.9377, "longitude": 113.3841},
    {"location_name": "南沙区", "latitude": 22.8016, "longitude": 113.5252},
    {"location_name": "从化区", "latitude": 23.5483, "longitude": 113.5874},
    {"location_name": "增城区", "latitude": 23.2614, "longitude": 113.8109},
)


def _world_pixel(latitude, longitude, zoom):
    """Convert a WGS84 coordinate to an OSM Web-Mercator pixel."""
    latitude = max(-85.05112878, min(85.05112878, float(latitude)))
    scale = 256 * (2 ** zoom)
    x = (float(longitude) + 180.0) / 360.0 * scale
    sin_lat = math.sin(math.radians(latitude))
    y = (0.5 - math.log((1 + sin_lat) / (1 - sin_lat)) / (4 * math.pi)) * scale
    return x, y


def _pixel_geo(x, y, zoom):
    """Convert an OSM Web-Mercator pixel back to WGS84 coordinates."""
    scale = 256 * (2 ** zoom)
    longitude = float(x) / scale * 360.0 - 180.0
    mercator = math.pi * (1 - 2 * float(y) / scale)
    latitude = math.degrees(math.atan(math.sinh(mercator)))
    return latitude, longitude


def _tile_path(zoom, x, y):
    return os.path.join(MAP_CACHE_DIR, str(zoom), str(x), f"{y}.png")


def _read_tile(zoom, x, y):
    """Read a cached tile or fetch one current-view tile from OSM."""
    target = _tile_path(zoom, x, y)
    if os.path.exists(target):
        try:
            return PILImage.open(target).convert("RGB")
        except OSError:
            pass

    response = requests.get(
        MAP_TILE_URL.format(z=zoom, x=x, y=y),
        headers={"User-Agent": MAP_USER_AGENT}, timeout=10,
    )
    response.raise_for_status()
    tile = PILImage.open(io.BytesIO(response.content)).convert("RGB")
    os.makedirs(os.path.dirname(target), exist_ok=True)
    tile.save(target, "PNG")
    return tile


def compose_osm_view(latitude, longitude, zoom, width, height):
    """Compose only the visible OSM tiles into a Kivy-friendly local image."""
    width = max(360, min(int(width), 1080))
    height = max(640, min(int(height), 1600))
    center_x, center_y = _world_pixel(latitude, longitude, zoom)
    left = center_x - width / 2
    top = center_y - height / 2
    first_x = math.floor(left / 256)
    last_x = math.floor((left + width - 1) / 256)
    first_y = math.floor(top / 256)
    last_y = math.floor((top + height - 1) / 256)
    tile_count = 2 ** zoom

    result = PILImage.new("RGB", (width, height), (230, 233, 226))
    jobs = []
    for tile_x in range(first_x, last_x + 1):
        for tile_y in range(first_y, last_y + 1):
            if 0 <= tile_y < tile_count:
                jobs.append((tile_x, tile_y, tile_x % tile_count))

    loaded = 0
    # 一个手机屏幕通常需要 8—15 张瓦片；并行读取/下载能避免首次进入时
    # 按顺序等待十几次网络往返。
    with ThreadPoolExecutor(max_workers=min(6, len(jobs) or 1)) as executor:
        futures = {
            executor.submit(_read_tile, zoom, wrapped_x, tile_y): (tile_x, tile_y)
            for tile_x, tile_y, wrapped_x in jobs
        }
        for future in as_completed(futures):
            tile_x, tile_y = futures[future]
            try:
                tile = future.result()
            except (OSError, requests.RequestException, ValueError):
                continue
            paste_x = round(tile_x * 256 - left)
            paste_y = round(tile_y * 256 - top)
            result.paste(tile, (paste_x, paste_y))
            loaded += 1
    if not loaded:
        raise RuntimeError("当前网络无法加载地图瓦片")

    os.makedirs(MAP_CACHE_DIR, exist_ok=True)
    output = os.path.join(
        MAP_CACHE_DIR,
        f"view_{zoom}_{latitude:.5f}_{longitude:.5f}_{width}x{height}.png",
    )
    result.save(output, "PNG")
    return output, width, height


def _rounded_background(widget, color, radius=16):
    with widget.canvas.before:
        Color(*color)
        rectangle = RoundedRectangle(pos=widget.pos, size=widget.size,
                                     radius=[dp(radius)] * 4)
    widget.bind(pos=lambda instance, *_: setattr(rectangle, "pos", instance.pos))
    widget.bind(size=lambda instance, *_: setattr(rectangle, "size", instance.size))
    return rectangle


def _field(hint, **kwargs):
    options = dict(
        hint_text=hint, multiline=False, size_hint=(1, None), height=dp(43),
        padding=(dp(10), dp(10)), font_size=sp(14),
        foreground_color=(0.12, 0.12, 0.12, 1),
        background_normal="", background_active="",
        background_color=(0.95, 0.97, 0.95, 1),
    )
    options.update(text_style())
    options.update(kwargs)
    return TextInput(**options)


def _pest_image(pest_name):
    for extension in ("png", "jpg", "jpeg"):
        candidate = os.path.join(IMAGE_DIR, f"pest_{pest_name}.{extension}")
        if os.path.exists(candidate):
            return candidate
    return ""


class MapMarker(ButtonBehavior, FloatLayout):
    def __init__(self, report, on_open, is_reference=False, **kwargs):
        super().__init__(size_hint=(None, None), size=(dp(56), dp(66)), **kwargs)
        self.report = report
        self.on_open = on_open
        self.is_reference = is_reference
        self.anchor_point = None
        self.dot_color = ((0.93, 0.48, 0.16, 1) if is_reference else GREEN)

        picture_source = _pest_image(report.get("pest_name", ""))
        if picture_source:
            self.picture = CircleImage(
                source=picture_source, size_hint=(None, None), size=(dp(28), dp(28)),
                pos_hint={"center_x": 0.5, "top": 0.92},
            )
            self.add_widget(self.picture)
        self.label = Label(
            text=(report.get("location_name", "位置参考") if is_reference
                  else report.get("pest_name", "观察点")),
            size_hint=(1, None), height=dp(23), pos_hint={"x": 0, "y": 0},
            font_size=sp(10), bold=True, color=(0.10, 0.16, 0.12, 1),
            halign="center", valign="middle", shorten=True, shorten_from="right",
            **text_style(),
        )
        self.label.bind(size=self.label.setter("text_size"))
        _rounded_background(self.label, (1, 1, 1, 0.94), 8)
        self.add_widget(self.label)
        self.bind(pos=self._draw_marker, size=self._draw_marker)
        Clock.schedule_once(self._draw_marker, 0)

    def _draw_marker(self, *_args):
        self.canvas.before.clear()
        with self.canvas.before:
            if self.anchor_point:
                distance = math.hypot(
                    self.center_x - self.anchor_point[0],
                    self.y + dp(21) - self.anchor_point[1])
                if distance > dp(4):
                    Color(self.dot_color[0], self.dot_color[1], self.dot_color[2], 0.72)
                    Line(points=[self.anchor_point[0], self.anchor_point[1],
                                 self.center_x, self.y + dp(21)], width=dp(1))
            Color(1, 1, 1, 0.98)
            Ellipse(pos=(self.x + dp(12), self.y + dp(25)), size=(dp(32), dp(32)))
            Color(*self.dot_color)
            Ellipse(pos=(self.x + dp(16), self.y + dp(29)), size=(dp(24), dp(24)))
            Line(points=[self.center_x, self.y + dp(29), self.center_x, self.y + dp(21)],
                 width=dp(2))

    def on_release(self):
        self.on_open(self.report, self.is_reference)


class MapScreen(BaseScreen):
    def __init__(self, **kwargs):
        kwargs.setdefault("name", "map")
        super().__init__(**kwargs)
        self.center_lat, self.center_lon = MAP_CENTER
        self.zoom = MAP_ZOOM
        self._load_serial = 0
        self._map_pixel_size = (360, 800)
        self._reports = []
        self._markers = []
        self._drag_start = None
        self._drag_base_map_pos = None
        self._drag_base_marker_pos = None

        self.layout = FloatLayout()
        self.add_widget(self.layout)
        with self.layout.canvas.before:
            Color(0.90, 0.93, 0.89, 1)
            self.map_background = Rectangle(pos=self.layout.pos, size=self.layout.size)
        self.layout.bind(
            pos=lambda item, *_: setattr(self.map_background, "pos", item.pos),
            size=lambda item, *_: setattr(self.map_background, "size", item.size),
        )
        self.map_image = Image(
            source="",
            allow_stretch=True, keep_ratio=False, size_hint=(1, 1),
        )
        self.layout.add_widget(self.map_image)

        self.marker_layer = FloatLayout(size_hint=(1, 1))
        self.layout.add_widget(self.marker_layer)
        self.marker_layer.bind(pos=self._position_markers, size=self._position_markers)

        self._build_top_bar()
        self._build_bottom_bar()

        self.status = Label(
            text="按住左键可上下左右拖动地图", size_hint=(0.86, None), height=dp(28),
            pos_hint={"center_x": 0.5, "y": 0.142},
            font_size=sp(11), color=(0.20, 0.20, 0.20, 1),
            halign="center", valign="middle", **text_style(),
        )
        self.status.bind(size=self.status.setter("text_size"))
        _rounded_background(self.status, (1, 1, 1, 0.88), 10)
        self.layout.add_widget(self.status)

    def _build_top_bar(self):
        back = RoundedButton(
            text="‹  首页", size_hint=(None, None), size=(dp(82), dp(42)),
            pos_hint={"x": 0.035, "top": 0.965}, font_size=sp(15),
            color=(0.12, 0.12, 0.12, 1), fill_color=(1, 1, 1, 0.93),
            **text_style(),
        )
        back.bind(on_release=lambda *_: self._go_home())
        self.layout.add_widget(back)

        area = Label(
            text="广州市全域", size_hint=(None, None), size=(dp(150), dp(42)),
            pos_hint={"center_x": 0.5, "top": 0.965}, font_size=sp(16), bold=True,
            color=(0.08, 0.08, 0.08, 1), halign="center", valign="middle",
            **text_style(),
        )
        area.bind(size=area.setter("text_size"))
        _rounded_background(area, (1, 1, 1, 0.94), 18)
        self.layout.add_widget(area)

    def _build_bottom_bar(self):
        bar = BoxLayout(
            orientation="horizontal", spacing=dp(7), padding=(dp(9), dp(9)),
            size_hint=(0.96, None), height=dp(68),
            pos_hint={"center_x": 0.5, "y": 0.025},
        )
        _rounded_background(bar, (1, 1, 1, 0.96), 22)
        self.bottom_bar = bar
        actions = (
            ("添加地点", self.open_add_report, 1.15),
            ("回到广州", self.go_nearby, 1.0),
            ("分布数据", self.open_statistics, 1.15),
        )
        for caption, callback, width_hint in actions:
            button = RoundedButton(
                text=caption, size_hint=(width_hint, 1), font_size=sp(12),
                color=((1, 1, 1, 1) if "添加" in caption else GREEN),
                fill_color=(GREEN if "添加" in caption else (0.90, 0.97, 0.92, 1)),
                **text_style(),
            )
            button.bind(on_release=callback)
            bar.add_widget(button)
        self.layout.add_widget(bar)

    def on_pre_enter(self, *_args):
        self.refresh_reports()
        self.load_map()

    def _go_home(self):
        if self.manager:
            self.manager.current = "home"

    def refresh_reports(self):
        try:
            self._reports = STORE_DB.get_pest_reports()
        except Exception as exc:
            self._reports = []
            self.status.text = f"读取上报记录失败：{exc}"
        self.marker_layer.clear_widgets()
        self._markers = []
        for report in REFERENCE_POINTS:
            reference = dict(report)
            reference.update(
                pest_name="行政区位置参考", crop="—", severity="—",
                username="—", created_at="—", source_type="行政区位置参考",
                note="用于标示广州市行政区位置，不代表当地发生病虫害。",
            )
            self._add_marker(reference, True)
        for report in self._reports:
            self._add_marker(report, False)
        self._position_markers()

    def _add_marker(self, report, is_reference):
        marker = MapMarker(report, self.open_marker_detail, is_reference)
        self._markers.append(marker)
        self.marker_layer.add_widget(marker)

    def _position_markers(self, *_args):
        if not self._markers or self.marker_layer.width <= 1:
            return
        center_x, center_y = _world_pixel(self.center_lat, self.center_lon, self.zoom)
        view_w, view_h = self._map_pixel_size
        scale_x = self.marker_layer.width / view_w
        scale_y = self.marker_layer.height / view_h
        raw_positions = []
        for marker in sorted(self._markers, key=lambda item: item.is_reference):
            point_x, point_y = _world_pixel(
                marker.report["latitude"], marker.report["longitude"], self.zoom)
            screen_x = self.marker_layer.center_x + (point_x - center_x) * scale_x
            screen_y = self.marker_layer.center_y - (point_y - center_y) * scale_y
            raw_positions.append((marker, screen_x, screen_y))

        offsets = (
            (0, 0), (-64, 0), (64, 0), (0, -74), (0, 74),
            (-64, -74), (64, -74), (-64, 74), (64, 74),
            (-128, 0), (128, 0), (0, -148), (0, 148),
        )
        occupied = []
        for marker, raw_x, raw_y in raw_positions:
            in_view = (
                self.marker_layer.x - marker.width < raw_x < self.marker_layer.right + marker.width
                and self.marker_layer.y - marker.height < raw_y < self.marker_layer.top + marker.height
            )
            marker.opacity = 1 if in_view else 0
            marker.label.opacity = marker.opacity
            marker.anchor_point = (raw_x, raw_y)
            if not in_view:
                marker.center = (raw_x, raw_y)
                continue
            placed = False
            for offset_x, offset_y in offsets:
                candidate_x = max(
                    self.marker_layer.x + marker.width / 2,
                    min(self.marker_layer.right - marker.width / 2, raw_x + dp(offset_x)))
                candidate_y = max(
                    self.marker_layer.y + dp(150),
                    min(self.marker_layer.top - dp(78), raw_y + dp(offset_y)))
                box = (
                    candidate_x - marker.width / 2 - dp(3),
                    candidate_y - marker.height / 2 - dp(3),
                    candidate_x + marker.width / 2 + dp(3),
                    candidate_y + marker.height / 2 + dp(3),
                )
                overlaps = any(
                    box[0] < other[2] and box[2] > other[0]
                    and box[1] < other[3] and box[3] > other[1]
                    for other in occupied
                )
                if not overlaps:
                    marker.center = (candidate_x, candidate_y)
                    occupied.append(box)
                    placed = True
                    break
            if not placed:
                marker.center = (raw_x, raw_y)
                marker.label.opacity = 0
            marker._draw_marker()

    def load_map(self):
        self._load_serial += 1
        serial = self._load_serial
        self.status.text = "正在加载真实地图…"
        width = self.width or 360
        height = self.height or 800

        def worker():
            try:
                result = compose_osm_view(
                    self.center_lat, self.center_lon, self.zoom, width, height)
            except Exception as exc:
                message = str(exc)
                Clock.schedule_once(
                    lambda _dt, s=serial, msg=message: self._map_failed(s, msg), 0)
                return
            Clock.schedule_once(
                lambda _dt, s=serial, data=result: self._apply_map(s, data), 0)

        threading.Thread(target=worker, daemon=True).start()

    def _apply_map(self, serial, result):
        if serial != self._load_serial:
            return
        source, width, height = result
        self._map_pixel_size = (width, height)
        self.map_image.source = source
        self.map_image.reload()
        self.status.text = "按住左键拖动地图，松开即可停止"
        self._position_markers()

    def _map_failed(self, serial, message):
        if serial != self._load_serial:
            return
        self.status.text = f"离线地图模式：{message}"

    def go_nearby(self, *_args):
        self.center_lat, self.center_lon = MAP_CENTER
        self._position_markers()
        self.load_map()

    def open_marker_detail(self, report, is_reference=False):
        source = report.get("source_type") or "用户上报"
        location_line = (
            f"位置：{report.get('location_name')}\n" if report.get("location_name") else ""
        )
        body = (
            f"{location_line}"
            f"病虫害：{report.get('pest_name') or '未填写'}\n"
            f"作物：{report.get('crop') or '未填写'}\n"
            f"程度：{report.get('severity') or '未填写'}\n"
            f"坐标（WGS84）：{float(report['latitude']):.6f}, "
            f"{float(report['longitude']):.6f}\n"
            f"记录时间：{report.get('created_at') or '未填写'}\n"
            f"数据来源：{source}\n"
            f"说明：{report.get('note') or '无'}"
        )
        if is_reference:
            body += "\n\n此橙色点是行政区位置参考，不是病虫害发生记录。"
        open_text_popup("观察点详情", body, height=430)

    def on_touch_down(self, touch):
        button = getattr(touch, "button", None)
        if button not in (None, "left"):
            return super().on_touch_down(touch)
        if not self.collide_point(*touch.pos):
            return super().on_touch_down(touch)
        if (hasattr(self, "bottom_bar") and self.bottom_bar.collide_point(*touch.pos)) \
                or touch.y > self.top - dp(72):
            return super().on_touch_down(touch)
        for marker in reversed(self._markers):
            if marker.opacity and marker.collide_point(*touch.pos):
                return super().on_touch_down(touch)
        self._drag_start = touch.pos
        self._drag_base_map_pos = self.map_image.pos
        self._drag_base_marker_pos = self.marker_layer.pos
        touch.grab(self)
        return True

    def on_touch_move(self, touch):
        if touch.grab_current is not self or not self._drag_start:
            return super().on_touch_move(touch)
        dx = touch.x - self._drag_start[0]
        dy = touch.y - self._drag_start[1]
        self.map_image.pos = (
            self._drag_base_map_pos[0] + dx,
            self._drag_base_map_pos[1] + dy,
        )
        self.marker_layer.pos = (
            self._drag_base_marker_pos[0] + dx,
            self._drag_base_marker_pos[1] + dy,
        )
        self.status.text = "拖动中，松开左键停止并加载当前位置"
        return True

    def on_touch_up(self, touch):
        if touch.grab_current is not self or not self._drag_start:
            return super().on_touch_up(touch)
        touch.ungrab(self)
        dx = touch.x - self._drag_start[0]
        dy = touch.y - self._drag_start[1]
        moved = abs(dx) > dp(2) or abs(dy) > dp(2)
        if moved and self.marker_layer.width > 1 and self.marker_layer.height > 1:
            center_x, center_y = _world_pixel(
                self.center_lat, self.center_lon, self.zoom)
            view_w, view_h = self._map_pixel_size
            center_x -= dx * view_w / self.marker_layer.width
            center_y -= dy * view_h / self.marker_layer.height
            latitude, longitude = _pixel_geo(center_x, center_y, self.zoom)
            # 保持在广州市及邻近边缘，避免误拖到无关省市。
            self.center_lat = max(22.35, min(23.95, latitude))
            self.center_lon = max(112.70, min(114.30, longitude))
        self.map_image.pos = self.layout.pos
        self.marker_layer.pos = self.layout.pos
        self._drag_start = None
        self._position_markers()
        if moved:
            self.load_map()
        else:
            self.status.text = "地图已停止；按住左键可继续拖动"
        return True

    def open_add_report(self, *_args):
        popup = ModalView(
            size_hint=(0.90, None), height=dp(570), background="",
            background_color=(0, 0, 0, 0), overlay_color=(0, 0, 0, 0.48),
        )
        panel = BoxLayout(orientation="vertical", spacing=dp(9), padding=dp(16))
        _rounded_background(panel, (1, 1, 1, 1), 18)
        title = Label(
            text="添加病虫害观察点", size_hint=(1, None), height=dp(34),
            font_size=sp(19), bold=True, color=(0.10, 0.10, 0.10, 1),
            halign="center", valign="middle", **text_style(),
        )
        title.bind(size=title.setter("text_size"))
        panel.add_widget(title)

        pest = _field("病虫害名称（必填）")
        crop = _field("作物名称")
        latitude = _field("纬度 WGS84，例如 23.1870", input_filter="float")
        longitude = _field("经度 WGS84，例如 113.3695", input_filter="float")
        note = _field("观察说明（症状、范围等）", multiline=True, height=dp(72))
        severity_state = {"value": "中"}
        severity = BoxLayout(
            orientation="horizontal", spacing=dp(6),
            size_hint=(1, None), height=dp(43),
        )
        severity_buttons = {}

        def select_severity(value):
            severity_state["value"] = value
            for option, button in severity_buttons.items():
                selected = option == value
                button.fill_color = GREEN if selected else (0.90, 0.97, 0.92, 1)
                button.color = (1, 1, 1, 1) if selected else (0.12, 0.30, 0.18, 1)
                button._update_canvas()

        for option in ("轻", "中", "重", "待核实"):
            button = RoundedButton(
                text=option, font_size=sp(13),
                color=((1, 1, 1, 1) if option == "中" else (0.12, 0.30, 0.18, 1)),
                fill_color=(GREEN if option == "中" else (0.90, 0.97, 0.92, 1)),
                **text_style(),
            )
            button.bind(on_release=lambda _button, value=option: select_severity(value))
            severity_buttons[option] = button
            severity.add_widget(button)
        for caption, field in (
                ("", pest), ("", crop), ("", latitude), ("", longitude),
                ("发生程度", severity), ("", note)):
            if caption:
                panel.add_widget(Label(
                    text=caption, size_hint=(1, None), height=dp(22),
                    font_size=sp(13), color=(0.28, 0.28, 0.28, 1),
                    halign="left", valign="middle", **text_style()))
            panel.add_widget(field)

        hint = Label(
            text="请提交现场观察与真实坐标；记录将标为“用户上报”，不等同于官方监测结论。",
            size_hint=(1, None), height=dp(42), font_size=sp(11),
            color=(0.43, 0.43, 0.43, 1), halign="left", valign="middle",
            **text_style(),
        )
        hint.bind(size=hint.setter("text_size"))
        panel.add_widget(hint)

        buttons = BoxLayout(spacing=dp(10), size_hint=(1, None), height=dp(44))
        cancel = RoundedButton(text="取消", color=GREEN,
                               fill_color=(0.90, 0.97, 0.92, 1), **text_style())
        save = RoundedButton(text="保存观察点", color=(1, 1, 1, 1), **text_style())
        cancel.bind(on_release=lambda *_: popup.dismiss())
        save.bind(on_release=lambda *_: self._save_report(
            popup, pest.text, crop.text, latitude.text, longitude.text,
            severity_state["value"], note.text))
        buttons.add_widget(cancel)
        buttons.add_widget(save)
        panel.add_widget(buttons)
        popup.add_widget(panel)
        popup.open()

    def _save_report(self, popup, pest, crop, latitude, longitude, severity, note):
        pest = (pest or "").strip()
        if not pest:
            show_toast("请填写病虫害名称")
            return
        try:
            latitude = float(latitude)
            longitude = float(longitude)
        except (TypeError, ValueError):
            show_toast("请输入有效的经纬度")
            return
        if not (-90 <= latitude <= 90 and -180 <= longitude <= 180):
            show_toast("经纬度超出有效范围")
            return
        app = App.get_running_app()
        current_user = getattr(app, "current_user", None) or {}
        username = current_user.get("username", "游客")
        try:
            STORE_DB.add_pest_report(
                username, pest, latitude, longitude, crop.strip(), severity,
                note.strip())
        except Exception as exc:
            show_toast(f"保存失败：{exc}")
            return
        popup.dismiss()
        self.refresh_reports()
        show_toast("观察点已保存")

    def open_statistics(self, *_args):
        if self.manager and self.manager.has_screen("map_data"):
            self.manager.current = "map_data"


class MapDataScreen(AccountPage):
    title = "分布数据"
    subtitle = ""

    def __init__(self, **kwargs):
        kwargs.setdefault("name", "map_data")
        super().__init__(**kwargs)

    def go_back(self, *_args):
        if self.manager:
            self.manager.current = "map"

    def on_pre_enter(self, *_args):
        self.refresh_points()

    def refresh_points(self):
        self.body.clear_widgets()
        try:
            reports = STORE_DB.get_pest_reports()
        except Exception:
            reports = []
        summary = self.card(116, color=(0.84, 0.95, 0.87, 1))
        summary.add_widget(_text("广州市标记点清单", 19, INK, 32, True))
        summary.add_widget(_text(
            f"行政区位置参考 {len(REFERENCE_POINTS)} 个 · 用户观察点 {len(reports)} 个",
            12, (0.18, 0.43, 0.26, 1), 26))
        summary.add_widget(_text(
            "橙色为行政区定位参考，绿色才是用户提交的现场观察。",
            11, MUTED, 32))
        self.body.add_widget(summary)

        self.body.add_widget(_text("行政区位置参考", 17, INK, 38, True))
        for index, point in enumerate(REFERENCE_POINTS, start=1):
            card = self.card(106, padding=12, spacing=3)
            heading = BoxLayout(size_hint=(1, None), height=dp(28))
            heading.add_widget(_text(
                f"{index}. {point['location_name']}", 15, INK, 28, True))
            heading.add_widget(_text(
                "位置参考", 11, (0.93, 0.48, 0.16, 1), 28, True, "right",
                size_hint=(None, None), width=dp(76)))
            card.add_widget(heading)
            card.add_widget(_text(
                f"WGS84：{point['latitude']:.6f}, {point['longitude']:.6f}",
                12, MUTED, 28))
            card.add_widget(_text(
                "用于定位行政区，不代表病虫害发生。", 11, MUTED, 24))
            self.body.add_widget(card)

        self.body.add_widget(_text("用户观察点", 17, INK, 38, True))
        if not reports:
            self.body.add_widget(_text(
                "暂无用户提交的现场观察点。", 12, MUTED, 62, halign="center"))
        for index, report in enumerate(reports, start=1):
            card = self.card(128, padding=12, spacing=3)
            heading = BoxLayout(size_hint=(1, None), height=dp(28))
            heading.add_widget(_text(
                f"{index}. {report.get('pest_name') or '未命名观察点'}",
                15, INK, 28, True))
            heading.add_widget(_text(
                report.get("severity") or "待核实", 11, GREEN, 28, True, "right",
                size_hint=(None, None), width=dp(62)))
            card.add_widget(heading)
            card.add_widget(_text(
                f"位置：{float(report['latitude']):.6f}, "
                f"{float(report['longitude']):.6f}", 12, MUTED, 28))
            card.add_widget(_text(
                f"作物：{report.get('crop') or '未填写'} · "
                f"提交人：{report.get('username') or '游客'}", 11, MUTED, 24))
            card.add_widget(_text(
                f"记录时间：{(report.get('created_at') or '未知').replace('T', ' ')}",
                10, MUTED, 22))
            self.body.add_widget(card)
        self.scroll.scroll_y = 1

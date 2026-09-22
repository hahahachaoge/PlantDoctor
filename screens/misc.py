import math
import os
import threading
import time
from concurrent.futures import ThreadPoolExecutor, as_completed

import requests
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
MAP_ZOOM = 10
MAP_USER_AGENT = "PlantDoctor/1.0 (+https://github.com/hahahachaoge/PlantDoctor)"
# Both providers below render current OpenStreetMap data.  The German community
# endpoint is tried first because it is reachable from the project's mainland
# mobile network, while the Foundation endpoint remains the fail-over.  Keeping
# the providers as data (rather than adding a native map SDK) also avoids a new
# Android binary dependency and an API-key requirement.
MAP_TILE_SOURCES = (
    ("OpenStreetMap DE", "https://tile.openstreetmap.de/{z}/{x}/{y}.png"),
    ("OpenStreetMap", "https://tile.openstreetmap.org/{z}/{x}/{y}.png"),
)
MAP_TILE_SIZE = 256
MAP_CACHE_SECONDS = 7 * 24 * 60 * 60
_TILE_HTTP = threading.local()

# 广州市现辖 11 个行政区。以下 WGS84 坐标用于在“病虫害位置”图层中提供
# 全市区域展示；它们不是现场发生记录，也不参与用户观察统计。
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


def _map_cache_dir():
    """Return an app-private, writable tile cache on Android and desktop."""
    app = App.get_running_app()
    try:
        user_dir = getattr(app, "user_data_dir", "") if app else ""
    except OSError:
        # A locked-down Windows account may deny Kivy's roaming-data folder.
        # Android normally uses its writable app-private files directory.
        user_dir = ""
    if not user_dir:
        user_dir = os.path.join(os.path.dirname(IMAGE_DIR), "photos")
    return os.path.join(user_dir, "map_tiles")


def _tile_path(cache_dir, zoom, x, y):
    return os.path.join(cache_dir, str(zoom), str(x), f"{y}.png")


def _read_tile(cache_dir, zoom, x, y):
    """Return a cached tile path, otherwise download it from a live provider."""
    target = _tile_path(cache_dir, zoom, x, y)
    cached = os.path.isfile(target) and os.path.getsize(target) > 100
    if cached and time.time() - os.path.getmtime(target) < MAP_CACHE_SECONDS:
        return target, "本地缓存"

    last_error = None
    headers = {
        "User-Agent": MAP_USER_AGENT,
        "Accept": "image/avif,image/webp,image/png,image/*;q=0.8,*/*;q=0.5",
    }
    session = getattr(_TILE_HTTP, "session", None)
    if session is None:
        session = requests.Session()
        session.trust_env = False
        _TILE_HTTP.session = session
    for provider, template in MAP_TILE_SOURCES:
        try:
            response = session.get(
                template.format(z=zoom, x=x, y=y),
                headers=headers,
                timeout=(4, 10),
            )
            response.raise_for_status()
            content_type = response.headers.get("Content-Type", "").lower()
            if "image" not in content_type or len(response.content) <= 100:
                raise ValueError("地图服务未返回有效图片")
            os.makedirs(os.path.dirname(target), exist_ok=True)
            temporary = f"{target}.{threading.get_ident()}.part"
            with open(temporary, "wb") as tile_file:
                tile_file.write(response.content)
            os.replace(temporary, target)
            return target, provider
        except (OSError, requests.RequestException, ValueError) as exc:
            last_error = exc
    if cached:
        # A stale real tile is still more useful than a blank screen while the
        # phone is temporarily offline; the next entry will try refreshing it.
        return target, "离线缓存"
    raise RuntimeError(str(last_error or "地图服务不可用"))


def _visible_tiles(latitude, longitude, zoom, width, height):
    """Describe visible Web-Mercator tiles and their viewport origin."""
    width = max(1, int(width))
    height = max(1, int(height))
    # Android exposes physical pixels while Kivy controls are density-aware.
    # Rendering a 256 px map tile as up to 512 physical pixels keeps labels
    # readable and avoids requesting 40-60 tiny tiles on a high-DPI phone.
    display_scale = max(1.0, min(2.0, float(dp(1))))
    world_width = width / display_scale
    world_height = height / display_scale
    center_x, center_y = _world_pixel(latitude, longitude, zoom)
    left = center_x - world_width / 2
    top = center_y - world_height / 2
    first_x = math.floor(left / MAP_TILE_SIZE)
    last_x = math.floor((left + world_width - 1) / MAP_TILE_SIZE)
    first_y = math.floor(top / MAP_TILE_SIZE)
    last_y = math.floor((top + world_height - 1) / MAP_TILE_SIZE)
    tile_count = 2 ** zoom
    tiles = []
    for tile_x in range(first_x, last_x + 1):
        for tile_y in range(first_y, last_y + 1):
            if 0 <= tile_y < tile_count:
                tiles.append((tile_x, tile_y, tile_x % tile_count))
    return tiles, left, top, world_width, world_height, display_scale


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
            text=(report.get("location_name", "病虫害位置") if is_reference
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
        self._drag_tile_positions = []
        self._drag_marker_positions = []
        self._drag_cancelled_load = False
        self._tile_widgets = []
        self._loaded_tile_count = 0
        self._map_cache = ""
        self._resize_event = None

        self.layout = FloatLayout()
        self.add_widget(self.layout)
        with self.layout.canvas.before:
            Color(0.90, 0.93, 0.89, 1)
            self.map_background = Rectangle(pos=self.layout.pos, size=self.layout.size)
        self.layout.bind(
            pos=lambda item, *_: setattr(self.map_background, "pos", item.pos),
            size=lambda item, *_: setattr(self.map_background, "size", item.size),
        )
        # Tiles are individual Image widgets.  They appear as soon as each
        # download finishes, instead of waiting for one large PIL composite.
        # This is important on Android: a slow/blocked tile must not leave the
        # whole screen blank.
        self.tile_layer = FloatLayout(size_hint=(1, 1))
        self.layout.add_widget(self.tile_layer)

        self.map_message = RoundedButton(
            text="正在连接在线地图…", size_hint=(None, None),
            size=(dp(264), dp(96)), pos_hint={"center_x": 0.5, "center_y": 0.52},
            font_size=sp(13), color=(0.18, 0.28, 0.20, 1),
            fill_color=(1, 1, 1, 0.94), disabled=True, **text_style(),
        )
        self.map_message.bind(on_release=lambda *_: self.load_map())

        self.marker_layer = FloatLayout(size_hint=(1, 1))
        self.layout.add_widget(self.marker_layer)
        self.marker_layer.bind(pos=self._position_markers, size=self._position_markers)
        self.layout.add_widget(self.map_message)

        self._build_top_bar()
        self._build_bottom_bar()
        self._build_zoom_controls()

        self.status = Label(
            text="按住地图可上下左右拖动", size_hint=(0.86, None), height=dp(28),
            pos_hint={"center_x": 0.5, "y": 0.142},
            font_size=sp(11), color=(0.20, 0.20, 0.20, 1),
            halign="center", valign="middle", **text_style(),
        )
        self.status.bind(size=self.status.setter("text_size"))
        _rounded_background(self.status, (1, 1, 1, 0.88), 10)
        self.layout.add_widget(self.status)

        self.attribution = Label(
            text="", size_hint=(None, None), size=(dp(180), dp(18)),
            pos_hint={"right": 0.985, "y": 0.112}, font_size=sp(8),
            color=(0.22, 0.22, 0.22, 0.82), halign="right", valign="middle",
            **text_style(),
        )
        self.attribution.bind(size=self.attribution.setter("text_size"))
        self.layout.add_widget(self.attribution)
        self.layout.bind(size=self._schedule_viewport_reload)

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
            text="广州市城区", size_hint=(None, None), size=(dp(150), dp(42)),
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

    def _build_zoom_controls(self):
        controls = BoxLayout(
            orientation="vertical", spacing=dp(5), size_hint=(None, None),
            size=(dp(42), dp(89)), pos_hint={"right": 0.965, "center_y": 0.48},
        )
        for caption, delta in (("+", 1), ("−", -1)):
            button = RoundedButton(
                text=caption, font_size=sp(20), color=(0.10, 0.34, 0.18, 1),
                fill_color=(1, 1, 1, 0.95), **text_style(),
            )
            button.bind(on_release=lambda _button, step=delta: self.change_zoom(step))
            controls.add_widget(button)
        self.zoom_controls = controls
        self.layout.add_widget(controls)

    def on_pre_enter(self, *_args):
        self.refresh_reports()
        self._queue_viewport_reload(0.12)

    def _schedule_viewport_reload(self, *_args):
        if self.width <= 1 or self.height <= 1:
            return
        if self.manager is not None and self.manager.current != self.name:
            return
        self._queue_viewport_reload(0.25)

    def _queue_viewport_reload(self, delay):
        """Debounce enter/resize events so the phone downloads each tile once."""
        if self._resize_event is not None:
            self._resize_event.cancel()
        self._resize_event = Clock.schedule_once(
            self._run_viewport_reload, max(0, delay))

    def _run_viewport_reload(self, _dt):
        self._resize_event = None
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
                pest_name="病虫害位置", crop="—", severity="—",
                username="—", created_at="—", source_type="区域展示点",
                note="用于展示广州市各区域，便于查看和录入观察；不代表实际发生记录。",
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
        if hasattr(self, "zoom_controls"):
            controls = self.zoom_controls
            occupied.append((
                controls.x - dp(8), controls.y - dp(8),
                controls.right + dp(8), controls.top + dp(8),
            ))
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
        if self.layout.width <= 1 or self.layout.height <= 1:
            Clock.schedule_once(lambda _dt: self.load_map(), 0.1)
            return
        self._load_serial += 1
        serial = self._load_serial
        self.status.text = "正在加载真实地图…"
        self.map_message.text = "正在连接在线地图…"
        self.map_message.disabled = True
        self.map_message.opacity = 1
        self.attribution.text = ""
        self.tile_layer.clear_widgets()
        self._tile_widgets = []
        self._loaded_tile_count = 0
        self._map_cache = _map_cache_dir()
        cache_dir = self._map_cache
        zoom = self.zoom
        tiles, left, top, width, height, display_scale = _visible_tiles(
            self.center_lat, self.center_lon, zoom,
            self.layout.width, self.layout.height,
        )
        self._map_pixel_size = (width, height)
        self._position_markers()

        def worker():
            loaded = 0
            failures = []
            with ThreadPoolExecutor(max_workers=min(6, len(tiles) or 1)) as executor:
                futures = {
                    executor.submit(
                        _read_tile, cache_dir, zoom, wrapped_x, tile_y
                    ): (tile_x, tile_y)
                    for tile_x, tile_y, wrapped_x in tiles
                }
                for future in as_completed(futures):
                    tile_x, tile_y = futures[future]
                    try:
                        source, provider = future.result()
                    except Exception as exc:
                        failures.append(str(exc))
                        continue
                    loaded += 1
                    Clock.schedule_once(
                        lambda _dt, s=serial, path=source, x=tile_x, y=tile_y,
                               l=left, t=top, w=width, h=height,
                               scale=display_scale, p=provider: self._apply_tile(
                                   s, path, x, y, l, t, w, h, scale, p),
                        0,
                    )
            message = failures[0] if failures else ""
            Clock.schedule_once(
                lambda _dt, s=serial, count=loaded, total=len(tiles), msg=message:
                    self._tiles_finished(s, count, total, msg),
                0,
            )

        threading.Thread(target=worker, daemon=True).start()

    def _apply_tile(self, serial, source, tile_x, tile_y,
                    left, top, width, height, display_scale, provider):
        if serial != self._load_serial:
            return
        image = Image(
            source=source, allow_stretch=True, keep_ratio=False,
            size_hint=(None, None),
            size=(MAP_TILE_SIZE * display_scale, MAP_TILE_SIZE * display_scale),
        )
        image.pos = (
            self.layout.x + (tile_x * MAP_TILE_SIZE - left) * display_scale,
            self.layout.y + (
                height - ((tile_y + 1) * MAP_TILE_SIZE - top)
            ) * display_scale,
        )
        self.tile_layer.add_widget(image)
        self._tile_widgets.append(image)
        self._loaded_tile_count += 1
        self.map_message.opacity = 0
        self.map_message.disabled = True
        self.attribution.text = "© OpenStreetMap contributors"
        if self._loaded_tile_count == 1:
            self.status.text = "在线地图已显示，可拖动或缩放"

    def _tiles_finished(self, serial, loaded, total, message):
        if serial != self._load_serial:
            return
        if not loaded:
            self._map_failed(serial, message or "请检查手机网络连接")
            return
        if loaded < total:
            self.status.text = f"已显示地图，{total - loaded} 个区域加载失败，可重新进入加载"
        else:
            self.status.text = "按住地图可自由拖动，使用 +/− 缩放"

    def _map_failed(self, serial, message):
        if serial != self._load_serial:
            return
        # Do not leave the Android screen as an unexplained blank panel.
        raw_message = (message or "网络不可用").strip().replace("\n", " ")
        lowered = raw_message.lower()
        if any(key in lowered for key in (
                "connection", "timeout", "ssl", "proxy", "name resolution")):
            short_message = "无法连接地图服务，请检查手机网络"
        else:
            short_message = raw_message
            if len(short_message) > 24:
                short_message = short_message[:24] + "…"
        self.map_message.text = f"在线地图暂时无法加载\n{short_message}\n点击重试"
        self.map_message.disabled = False
        self.map_message.opacity = 1
        self.status.text = "地图连接失败，请检查网络后点击中间按钮重试"

    def change_zoom(self, delta):
        new_zoom = max(8, min(15, self.zoom + int(delta)))
        if new_zoom == self.zoom:
            show_toast("已到当前地图缩放范围")
            return
        self.zoom = new_zoom
        self._position_markers()
        self.load_map()

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
            body += "\n\n此橙色点是病虫害位置的区域展示点，不代表现场发生记录或官方疫情结论。"
        open_text_popup("观察点详情", body, height=430)

    def on_touch_down(self, touch):
        button = getattr(touch, "button", None)
        if button in ("scrollup", "scrolldown") and self.collide_point(*touch.pos):
            self.change_zoom(1 if button == "scrollup" else -1)
            return True
        if button not in (None, "left"):
            return super().on_touch_down(touch)
        if not self.collide_point(*touch.pos):
            return super().on_touch_down(touch)
        if (hasattr(self, "bottom_bar") and self.bottom_bar.collide_point(*touch.pos)) \
                or touch.y > self.top - dp(72):
            return super().on_touch_down(touch)
        if (hasattr(self, "zoom_controls")
                and self.zoom_controls.collide_point(*touch.pos)):
            return super().on_touch_down(touch)
        if (self.map_message.opacity > 0
                and self.map_message.collide_point(*touch.pos)):
            return super().on_touch_down(touch)
        for marker in reversed(self._markers):
            if marker.opacity and marker.collide_point(*touch.pos):
                return super().on_touch_down(touch)
        self._drag_start = touch.pos
        # Kivy child positions are absolute; moving only the FloatLayout does
        # not translate its existing children on Android.  Snapshot every
        # visible tile/marker and move those widgets directly during the drag.
        self._drag_tile_positions = [
            (tile, tuple(tile.pos)) for tile in self._tile_widgets
        ]
        self._drag_marker_positions = [
            (marker, tuple(marker.pos), marker.anchor_point) for marker in self._markers
        ]
        self._drag_cancelled_load = False
        touch.grab(self)
        return True

    def on_touch_move(self, touch):
        if touch.grab_current is not self or not self._drag_start:
            return super().on_touch_move(touch)
        dx = touch.x - self._drag_start[0]
        dy = touch.y - self._drag_start[1]
        if (not self._drag_cancelled_load
                and (abs(dx) > dp(2) or abs(dy) > dp(2))):
            self._load_serial += 1  # ignore tiles finishing for the old viewport
            self._drag_tile_positions = [
                (tile, tuple(tile.pos)) for tile in self._tile_widgets
            ]
            self._drag_marker_positions = [
                (marker, tuple(marker.pos), marker.anchor_point)
                for marker in self._markers
            ]
            self._drag_cancelled_load = True
        for widget, base_pos in self._drag_tile_positions:
            widget.pos = (base_pos[0] + dx, base_pos[1] + dy)
        for widget, base_pos, base_anchor in self._drag_marker_positions:
            if base_anchor:
                widget.anchor_point = (base_anchor[0] + dx, base_anchor[1] + dy)
            widget.pos = (base_pos[0] + dx, base_pos[1] + dy)
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
        self._drag_start = None
        self._drag_tile_positions = []
        self._drag_marker_positions = []
        self._drag_cancelled_load = False
        self._position_markers()
        if moved:
            self.load_map()
        else:
            self.status.text = "地图已停止；按住地图可继续拖动"
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
        summary = self.card(
            146, padding=14, spacing=6, color=(0.84, 0.95, 0.87, 1))
        summary.add_widget(_text("广州市病虫害位置清单", 19, INK, 32, True))
        summary.add_widget(_text(
            f"病虫害位置 {len(REFERENCE_POINTS)} 个 · 覆盖广州 11 个区",
            12, (0.18, 0.43, 0.26, 1), 30))
        summary.add_widget(_text(
            "橙色为区域展示点，绿色为用户提交的现场观察；地图展示不等于官方疫情结论。",
            11, MUTED, 44))
        self.body.add_widget(summary)

        self.body.add_widget(_text("病虫害位置", 17, INK, 38, True))
        for index, point in enumerate(REFERENCE_POINTS, start=1):
            card = self.card(86, padding=12, spacing=3)
            heading = BoxLayout(size_hint=(1, None), height=dp(28))
            heading.add_widget(_text(
                f"{index}. {point['location_name']}", 15, INK, 28, True))
            heading.add_widget(_text(
                "区域展示", 11, (0.93, 0.48, 0.16, 1), 28, True, "right",
                size_hint=(None, None), width=dp(76)))
            card.add_widget(heading)
            card.add_widget(_text(
                f"WGS84：{point['latitude']:.6f}, {point['longitude']:.6f}",
                12, MUTED, 28))
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

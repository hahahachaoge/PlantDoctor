import json
import math
import os
import re
import threading

from kivy.app import App
from kivy.clock import Clock
from kivy.graphics import Color, Ellipse, Rectangle, RoundedRectangle, Line
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

from config import GREEN, HOME_REMINDERS, IMAGE_DIR
from database.store_db import STORE_DB
from utils import (text_style, show_toast, open_text_popup,
                   update_nav_rect, bind_deferred_layout)
from widgets.base_widgets import UnderlineLabel, RoundedButton

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

# 城市拼音 / 英文名 → 中国天气网城市代码（用于 itboy 免费接口）
_CITY_CODES = {
    "guangzhou": "101280101",
    "beijing": "101010100",
    "shanghai": "101020100",
    "shenzhen": "101280601",
    "wuhan": "101200101",
    "changsha": "101250101",
    "chengdu": "101270101",
    "hangzhou": "101210101",
    "xian": "101110101",
    "chongqing": "101040100",
    "tianjin": "101030100",
    "nanjing": "101190101",
    "zhengzhou": "101180101",
    "suzhou": "101190401",
    "qingdao": "101120201",
    "xiamen": "101230201",
    "kunming": "101290101",
    "shenyang": "101070101",
    "harbin": "101050101",
    "jinan": "101120101",
    "ningbo": "101210401",
    "hefei": "101220101",
    "fuzhou": "101230101",
    "guiyang": "101260101",
    "nanchang": "101240101",
    "haikou": "101310101",
    "lanzhou": "101160101",
    "yinchuan": "101170101",
    "xining": "101150101",
    "wulumuqi": "101130101",
    "lasa": "101140101",
    "nanning": "101300101",
    "taiyuan": "101100101",
    "shijiazhuang": "101090101",
    "changchun": "101060101",
    "huhehaote": "101080101",
}


def _city_to_code(city):
    """把用户保存的拼音/英文名转成天气网城市代码。

    如果用户已经输入纯数字代码，则直接使用；
    未识别时返回 None，由调用方决定是提示还是使用默认城市。
    """
    city = (city or "").strip().lower()
    if not city:
        return None
    if city.isdigit():
        return city
    return _CITY_CODES.get(city)


# wttr.in 英文天气描述 → 中文（按关键词匹配，从上到下优先）
WEATHER_DESC_ZH = [
    ("thunder", "雷阵雨"),
    ("heavy rain shower", "大雨"),
    ("moderate or heavy rain shower", "阵雨"),
    ("light rain shower", "阵雨"),
    ("rain shower", "阵雨"),
    ("heavy rain", "大雨"),
    ("moderate rain", "中雨"),
    ("light rain", "小雨"),
    ("sleet", "雨夹雪"),
    ("heavy snow", "大雪"),
    ("light snow", "小雪"),
    ("drizzle", "毛毛雨"),
    ("overcast", "阴"),
    ("partly cloudy", "多云"),
    ("cloudy", "多云"),
    ("sunny", "晴"),
    ("clear", "晴"),
    ("mist", "薄雾"),
    ("fog", "雾"),
    ("haze", "霾"),
]


def _zh_weather_desc(desc):
    """把英文天气描述转成简短中文；未匹配时截断，保证不溢出一行。"""
    if not desc:
        return "晴"
    if any("\u4e00" <= ch <= "\u9fff" for ch in desc):
        return desc  # 已是中文，直接用
    low = desc.lower()
    for key, zh in WEATHER_DESC_ZH:
        if key in low:
            return zh
    return desc[:6] + "…" if len(desc) > 7 else desc

# 常用城市中文显示名
CITY_NAMES = {
    "guangzhou": "广州", "beijing": "北京", "shanghai": "上海",
    "shenzhen": "深圳", "wuhan": "武汉", "changsha": "长沙",
    "chengdu": "成都", "hangzhou": "杭州", "xian": "西安",
    "chongqing": "重庆", "tianjin": "天津", "nanjing": "南京",
}


def _update_camera_btn(instance, *_args):
    """绿色凸起圆（community/mypage/store 底部导航仍在复用）。"""
    instance.canvas.before.clear()
    with instance.canvas.before:
        Color(*GREEN)
        Ellipse(pos=instance.pos, size=instance.size)


# 首页拍照按钮用的浅绿色（GREEN 混入约 30% 白）
CAM_LIGHT_GREEN = (0.42, 0.78, 0.55, 1)

WEATHER_SHORT_TEXT = {
    "sun": "晴", "sun_cloud": "多云", "cloud": "阴",
    "rain": "雨", "snow": "雪",
}

# ---------- 以下为 UI/1.jpg 效果图取色，仅作用于首页 ----------
CARD_BG = (0.937, 1.0, 0.961, 1)        # #EFFFF5 浅绿卡片底（今日提醒 / 我的工具）
WEATHER_GREEN = (0.38, 0.82, 0.55, 1)    # #61D18C 天气卡绿（比原 #43BD70 更亮）

# 「今日适宜:」后面的雨滴图标：用户放在 image/雨滴.png（深橄榄描边），
# 染色成白色以匹配同一行的白色文字。想用原图颜色就把 TINT 改成 None。
DROP_ICON = os.path.join(IMAGE_DIR, "雨滴.png")
DROP_ICON_TINT = (1.0, 1.0, 1.0)

# 新版 UI 图标里「图层 8.png」就是相机图标（PS 默认图层名，未重命名）。
# 它自带一层绿底 #6CD896（比首页工具里另外几个的浅绿底 #C5ECD2 深一档）；
# 而首页底部中间的拍照按钮本身就是浅绿圆（CAM_LIGHT_GREEN），
# 直接叠上去会「方块套圆」，所以先把这层底抠掉、只留白色相机线条。
CAM_ICON = os.path.join(IMAGE_DIR, "图层 8.png")
CAM_ICON_BG = (0.424, 0.847, 0.588, 1)          # #6CD896


def _update_camera_btn_light(instance, *_args):
    """首页拍照按钮：浅绿色圆形。（其他页面用 _update_camera_btn 保持原绿）"""
    instance.canvas.before.clear()
    with instance.canvas.before:
        Color(*CAM_LIGHT_GREEN)
        Ellipse(pos=instance.pos, size=instance.size)


def _transparent_png(source):
    """把「白底无透明通道」的图标烤成透明底并缓存，返回可用路径。

    首页卡片改成浅绿底后，白底图标会在卡片上露出白色方块；这里按亮度
    生成 alpha（越接近白色越透明），缓存到 image/_rounded/，只做一次。
    """
    if not source or not os.path.exists(source):
        return source
    cache_dir = os.path.join(IMAGE_DIR, "_rounded")
    try:
        os.makedirs(cache_dir, exist_ok=True)
    except OSError:
        return source
    base = os.path.splitext(os.path.basename(source))[0]
    out = os.path.join(cache_dir, f"{base}_alpha.png")
    if os.path.exists(out):
        return out
    try:
        from PIL import Image as PILImage
        src = PILImage.open(source)
        if "A" in src.getbands():
            return source          # 本身就有透明通道，不用处理
        im = src.convert("RGBA")
        lut = [max(0, min(255, int((250 - v) * 255 / 55))) for v in range(256)]
        im.putalpha(im.convert("L").point(lut))
        im.save(out)
    except Exception:
        return source
    return out


class _IconButton(ButtonBehavior, Image):
    """可点击的图片图标。"""
    pass


class _HBarButton(ButtonBehavior, BoxLayout):
    """可点击的水平布局。"""
    pass


def _draw_search_icon(instance, *_args):
    """用 canvas 画一个放大镜图标，避免字体缺字显示方框。"""
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


def _paint_sun(cx, cy, r):
    """画太阳：圆心 + 8 条光芒。调用方需先进入 canvas 上下文。"""
    Color(1, 0.88, 0.35, 1)
    for i in range(8):
        ang = math.pi * i / 4
        x1 = cx + math.cos(ang) * r * 1.30
        y1 = cy + math.sin(ang) * r * 1.30
        x2 = cx + math.cos(ang) * r * 1.80
        y2 = cy + math.sin(ang) * r * 1.80
        Line(points=[x1, y1, x2, y2], width=dp(3), cap="round")
    Color(1, 0.93, 0.45, 1)
    Ellipse(pos=(cx - r, cy - r), size=(r * 2, r * 2))


def _paint_cloud(cx, cy, w):
    """画白云：三个圆 + 底部矩形补平，cx/cy 为云的中心。"""
    Color(0.97, 0.99, 1.0, 0.96)
    Ellipse(pos=(cx - 0.32 * w - 0.22 * w, cy - 0.22 * w),
            size=(0.44 * w, 0.44 * w))
    Ellipse(pos=(cx + 0.02 * w - 0.30 * w, cy + 0.14 * w - 0.30 * w),
            size=(0.60 * w, 0.60 * w))
    Ellipse(pos=(cx + 0.32 * w - 0.22 * w, cy - 0.22 * w),
            size=(0.44 * w, 0.44 * w))
    Rectangle(pos=(cx - 0.32 * w, cy - 0.22 * w), size=(0.64 * w, 0.30 * w))


def _paint_rain(cx, cy, w):
    """画雨滴：三条斜线，起点藏在云底，长短略有差异更自然。"""
    Color(0.72, 0.92, 1.0, 1)
    for off, ln in ((-0.34, 0.30), (0.0, 0.24), (0.34, 0.30)):
        x = cx + off * w
        Line(points=[x, cy, x - w * 0.12, cy - w * ln],
             width=dp(2.4), cap="round")


def _paint_snow(cx, cy, w):
    """画雪花：六角星 + 每个末端两个小分叉（不叠云，避免看着像蒙了一层）。"""
    Color(1, 1, 1, 0.98)
    a = w * 0.32
    for i in range(6):
        ang = math.pi * i / 3
        ux, uy = math.cos(ang), math.sin(ang)
        Line(points=[cx, cy, cx + ux * a, cy + uy * a],
             width=dp(2.6), cap="round")
        for rot in (0.55, -0.55):
            bx, by = cx + ux * a * 0.62, cy + uy * a * 0.62
            t = ang + rot
            Line(points=[bx, by,
                         bx + math.cos(t) * a * 0.34,
                         by + math.sin(t) * a * 0.34],
                 width=dp(2.0), cap="round")


def _weather_icon_kind(desc):
    """中文天气描述 → 图标类型：sun / sun_cloud / cloud / rain / snow。

    优先级从特殊到一般：雪 → 雨 → 多云 → 晴 → 阴/雾 → 兜底晴。
    """
    d = (desc or "").strip()
    if not d:
        return "sun"
    if "雪" in d or "冰雹" in d:
        return "snow"
    if any(k in d for k in ("雷", "阵雨", "暴雨", "大雨", "中雨", "小雨",
                            "毛毛雨", "雨")):
        return "rain"
    if "多云" in d:
        return "sun_cloud"
    if "晴" in d and any(k in d for k in ("云", "阴", "转")):
        return "sun_cloud"
    if "晴" in d:
        return "sun"
    if any(k in d for k in ("云", "阴", "雾", "霾", "沙尘", "浮尘")):
        return "cloud"
    return "sun"


def _draw_weather_icon(instance, *_args):
    """按 instance.weather_type 重画天气卡左侧大图标。

    原先这里固定绑 _draw_sun，所以「小雨 / 阴天」也顶着个大太阳。
    """
    instance.canvas.clear()
    kind = getattr(instance, "weather_type", "sun") or "sun"
    cx, cy = instance.center
    w, h = instance.width, instance.height
    r = min(w, h) * 0.26
    with instance.canvas:
        if kind == "sun":
            _paint_sun(cx, cy + h * 0.04, r)
        elif kind == "sun_cloud":
            _paint_sun(cx + r * 0.62, cy + h * 0.20, r * 0.60)
            _paint_cloud(cx - r * 0.28, cy - h * 0.10, w * 0.52)
        elif kind == "rain":
            _paint_cloud(cx, cy + h * 0.10, w * 0.62)
            _paint_rain(cx - w * 0.02, cy - h * 0.02, w * 0.58)
        elif kind == "snow":
            # 雪花单独画，比「云 + 雪花」在 74dp 尺寸下更清楚
            _paint_snow(cx, cy, w * 0.92)
        else:                                   # cloud / 阴 / 雾
            _paint_cloud(cx, cy + h * 0.02, w * 0.70)


def _draw_sun(instance, *_args):
    """兼容旧引用的太阳画法；新代码请用 _draw_weather_icon。"""
    instance.canvas.clear()
    cx, cy = instance.center
    r = min(instance.width, instance.height) * 0.26
    with instance.canvas:
        _paint_sun(cx, cy, r)


def _draw_drop(instance, *_args):
    """用 canvas 画一个小水滴（找不到图片图标时的兜底画法）。"""
    instance.canvas.clear()
    cx, cy = instance.center_x, instance.center_y - dp(1)
    r = min(instance.width, instance.height) * 0.24
    with instance.canvas:
        Color(1, 1, 1, 0.95)
        Ellipse(pos=(cx - r, cy - r), size=(r * 2, r * 2))
        Line(
            points=[cx - r * 0.80, cy + r * 0.50,
                    cx, cy + r * 2.20,
                    cx + r * 0.80, cy + r * 0.50],
            width=dp(2), cap="round", joint="round",
        )


def _fit_label_width(instance, texture_size):
    """把 Label 的宽度收紧到文字自然宽度（用于让「雨」贴紧「30°」）。

    前提：该 Label 的 text_size 宽度必须是 None。Kivy 的 render() 里有
    `if uw: w = uw` —— text_size 宽度一旦给定，纹理宽度就等于它，这时再用
    texture_size 反推控件宽度会每轮 +dp(2) 无限增长，触发 Clock 的
    "too much iteration" 死循环。这里加一道防御：纹理宽度和控件宽度一样，
    说明 text_size 被固定住了，直接退出。
    """
    natural = texture_size[0]
    if natural <= 1:
        return
    if abs(natural - instance.width) <= dp(1):
        return                      # 纹理跟着控件走 → 反推会死循环，放弃
    w = natural + dp(2)
    if abs(instance.width - w) > 0.5:
        instance.width = w


def _tinted_png(source, rgb, out_name):
    """把单色线性图标的 RGB 换成指定颜色、保留原 alpha，输出到 image/_rounded/。

    用于用户提供的 image/雨滴.png：那是深橄榄色描边（约 #333300），直接放在
    绿色天气卡上会和「今日适宜」的白色文字撞色，所以统一染成白色再用。
    输出文件名固定为 ASCII（drop_white.png），避免个别加载器处理中文路径出问题。
    """
    if not source or not os.path.exists(source):
        return ""
    cache_dir = os.path.join(IMAGE_DIR, "_rounded")
    try:
        os.makedirs(cache_dir, exist_ok=True)
    except OSError:
        return source
    out = os.path.join(cache_dir, out_name)
    if os.path.exists(out):
        return out
    try:
        from PIL import Image as PILImage
        src = PILImage.open(source).convert("RGBA")
        solid = PILImage.new(
            "RGBA", src.size,
            (int(rgb[0] * 255), int(rgb[1] * 255), int(rgb[2] * 255), 255))
        solid.putalpha(src.getchannel("A"))
        solid.save(out)
    except Exception:
        return source
    return out


def _strip_color_bg(source, rgb, out_name, tol=42):
    """抠掉图标自带的纯色圆角底，图形统一转白，返回缓存后的路径。

    新版「图层 8.png」是「浅绿圆角方块 + 白色相机」，而首页底部中间的拍照
    按钮底色本来就是浅绿圆（CAM_LIGHT_GREEN），直接叠上去会变成方块套圆。
    这里按「与底色 #C5ECD2 的色差」判定：
      - 色差很小 → 判定为底色 → alpha 置 0（透明）
      - 色差在过渡区 → alpha 按比例衰减，保住抗锯齿边缘不出现硬锯齿
      - 色差够大 → 判定为图形本身 → 保留 alpha，RGB 统一改成白色
    结果缓存到 image/_rounded/，输出名固定 ASCII。
    """
    if not source or not os.path.exists(source):
        return ""
    cache_dir = os.path.join(IMAGE_DIR, "_rounded")
    try:
        os.makedirs(cache_dir, exist_ok=True)
    except OSError:
        return source
    out = os.path.join(cache_dir, out_name)
    if os.path.exists(out):
        return out
    try:
        from PIL import Image as PILImage
        src = PILImage.open(source).convert("RGBA")
        tr, tg, tb = int(rgb[0] * 255), int(rgb[1] * 255), int(rgb[2] * 255)
        w, h = src.size
        px = src.load()
        low, high = tol * 0.6, tol
        for y in range(h):
            for x in range(w):
                r, g, b, a = px[x, y]
                if a == 0:
                    continue
                dist = max(abs(r - tr), abs(g - tg), abs(b - tb))
                if dist <= low:
                    px[x, y] = (255, 255, 255, 0)
                else:
                    fade = min(1.0, (dist - low) / (high - low))
                    px[x, y] = (255, 255, 255, int(a * fade))
        src.save(out)
    except Exception:
        return source
    return out


def fetch_weather(city, on_success, on_error):
    """获取天气信息。

    使用国内可直接访问的 itboy 天气接口（http://t.weather.itboy.net），
    不使用系统代理，避免本机 HTTP_PROXY 导致请求被拦截或超时。
    """

    def _extract_number(text):
        if not text:
            return "--"
        m = re.search(r"(\d+)", str(text))
        return m.group(1) if m else "--"

    def _fallback_wttr(city_en):
        """wttr.in 备用（部分网络环境可用）。"""
        import urllib.request
        url = f"https://wttr.in/{city_en}?format=j1&lang=zh"
        req = urllib.request.Request(
            url,
            headers={"User-Agent": "Mozilla/5.0", "Accept": "application/json"},
        )
        opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))
        with opener.open(req, timeout=8) as resp:
            raw = resp.read().decode("utf-8")
        data = json.loads(raw)
        current = data["current_condition"][0]
        lang_zh_list = current.get("lang_zh", [])
        weather_desc = ""
        if lang_zh_list and isinstance(lang_zh_list, list):
            weather_desc = lang_zh_list[0].get("value", "")
        if not weather_desc:
            desc_list = current.get("weatherDesc", [])
            weather_desc = desc_list[0].get("value", "晴") if desc_list else "晴"
        today = data["weather"][0]
        return {
            "temp": current.get("temp_C", "24"),
            "desc": weather_desc,
            "max": today.get("maxtempC", "26"),
            "min": today.get("mintempC", "21"),
            "city": city_en,
        }

    def run():
        try:
            import urllib.request

            code = _city_to_code(city)
            if code is None:
                # 尝试用输入当拼音走 wttr.in 备用
                try:
                    result = _fallback_wttr(city)
                    Clock.schedule_once(lambda dt: on_success(result))
                    return
                except Exception as exc:
                    err_msg = f"暂不支持该城市：{city}"
                    Clock.schedule_once(lambda dt: on_error(err_msg))
                    return

            url = f"http://t.weather.itboy.net/api/weather/city/{code}"
            req = urllib.request.Request(
                url, headers={"User-Agent": "Mozilla/5.0"}
            )
            # 绕过系统代理，避免本机 HTTP_PROXY 拦截公网请求
            opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))
            with opener.open(req, timeout=8) as resp:
                raw = resp.read().decode("utf-8")
            data = json.loads(raw)

            if data.get("status") != 200:
                raise RuntimeError(data.get("message", "天气接口返回异常"))

            city_info = data.get("cityInfo", {})
            weather_data = data.get("data", {})
            forecast = weather_data.get("forecast", [])
            today = forecast[0] if forecast else {}

            city_display = city_info.get("city") or city_info.get("parent") or city
            # 去掉「市/县/区」后缀，让顶部城市名更简洁
            city_display = city_display.rstrip("市县区")
            result = {
                "temp": _extract_number(weather_data.get("wendu")),
                "desc": today.get("type", "晴"),
                "max": _extract_number(today.get("high")),
                "min": _extract_number(today.get("low")),
                "city": city_display,
            }
            Clock.schedule_once(lambda dt: on_success(result))
        except Exception as exc:
            err_msg = str(exc)
            Clock.schedule_once(lambda dt: on_error(err_msg))

    threading.Thread(target=run, daemon=True).start()



def _nav_notch_widget(diameter=dp(84)):
    """中间拍照按钮底下的白色凹槽圆（营造导航条被挖开的效果）。"""
    w = Widget(size_hint=(None, None), size=(diameter, diameter))

    def _redraw(inst, *_args):
        inst.canvas.clear()
        with inst.canvas:
            Color(1, 1, 1, 1)
            Ellipse(pos=inst.pos, size=inst.size)

    w.bind(pos=_redraw, size=_redraw)
    return w


class HomeToolCard(ButtonBehavior, BoxLayout):
    """首页工具卡片：白色圆角背景，图标+文字垂直居中。"""

    def __init__(self, icon_source="", icon_text="", title="", **kwargs):
        super().__init__(
            orientation="vertical",
            spacing=dp(6),
            padding=(dp(6), dp(10), dp(6), dp(10)),
            **kwargs,
        )
        self.size_hint = (1, None)
        self.height = dp(78)

        icon_wrap = FloatLayout(size_hint=(1, 1))
        if icon_source and os.path.exists(icon_source):
            icon = Image(
                source=icon_source,
                size_hint=(None, None), size=(dp(36), dp(36)),
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
            text=title, font_size=sp(11),
            color=(0.22, 0.22, 0.22, 1),
            size_hint=(1, None), height=dp(16),
            **text_style(),
        )
        self.add_widget(title_label)

    def _update_bg(self, *_args):
        # 效果图里工具项直接浮在浅绿卡片上，不再单独画白色圆角底
        self.canvas.before.clear()


class HomeScreen(Screen):
    # 天气图标类型，加载完成后由 _load_weather 更新（默认晴天）
    _weather_kind = "sun"

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.name = "home"
        self.build_ui()

    def build_ui(self):
        self.layout = FloatLayout()
        self.add_widget(self.layout)

        # 页面背景：效果图为纯白，浅绿卡片浮在白底上
        with self.layout.canvas.before:
            Color(1, 1, 1, 1)
            self.bg_rect = Rectangle(pos=self.layout.pos, size=self.layout.size)
        self.layout.bind(pos=self._update_bg, size=self._update_bg)

        self.top_bar = self._build_top_bar()
        self.layout.add_widget(self.top_bar)

        self.content_scroll = ScrollView(
            size_hint=(1, None), do_scroll_x=False,
            # 注意：不能设置 pos_hint，否则 FloatLayout 布局时会
            # 覆盖 _update_layout 中手动设置的 pos=(0, nav_h)，
            # 导致内容区下移、顶部出现大段空白。
        )
        self.layout.add_widget(self.content_scroll)
        self.content_box = BoxLayout(
            orientation="vertical", spacing=dp(8),
            padding=(dp(12), dp(8), dp(12), dp(10)),
            size_hint=(1, None),
        )
        self.content_box.bind(minimum_height=self.content_box.setter("height"))
        self.content_scroll.add_widget(self.content_box)

        self.content_box.add_widget(self._build_weather_card())
        self.content_box.add_widget(self._build_reminder_card())
        self.content_box.add_widget(self._build_tool_section())

        self.bottom_nav = self._build_bottom_nav()
        self.layout.add_widget(self.bottom_nav)

        bind_deferred_layout(self.layout, self._update_layout)
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

    # ---------------- 顶部栏 ----------------
    def _build_top_bar(self):
        bar = BoxLayout(
            size_hint=(1, None), height=dp(56),
            pos_hint={"x": 0, "top": 1},
            spacing=dp(6),
            padding=(dp(12), dp(8), dp(12), dp(8)),
        )
        with bar.canvas.before:
            Color(1, 1, 1, 1)
            self.top_bar_bg = Rectangle(pos=bar.pos, size=bar.size)
        bar.bind(
            pos=lambda i, *_: setattr(self.top_bar_bg, "pos", i.pos),
            size=lambda i, *_: setattr(self.top_bar_bg, "size", i.size),
        )

        # 定位图标 + 城市（点击切换城市）
        # 说明：左侧城市块与右侧扫码块宽度必须一致，搜索框才会在顶栏正中。
        # 宽度取 dp(50) 刚好装下「图标 dp(18) + 间距 dp(2) + 两字城市 dp(28)」，
        # 再宽就会在搜索框左侧留出不必要的大空隙（搜索框也变短）。
        city_wrap = _HBarButton(
            size_hint=(None, 1), width=dp(50), spacing=dp(2),
        )
        loc_icon_path = os.path.join(IMAGE_DIR, "icon_map.png")
        if os.path.exists(loc_icon_path):
            loc_icon = Image(
                source=loc_icon_path,
                size_hint=(None, 1), width=dp(18),
                allow_stretch=True, keep_ratio=True,
            )
        else:
            loc_icon = Widget(size_hint=(None, 1), width=dp(18))
        self.city_label = Label(
            text=CITY_NAMES.get(WEATHER_CITY, WEATHER_CITY),
            font_size=sp(14), bold=True,
            color=(0.18, 0.18, 0.18, 1),
            size_hint=(1, 1),
            halign="left", valign="middle",
            shorten=True, shorten_from="right", **text_style(),
        )
        self.city_label.bind(size=self.city_label.setter("text_size"))
        city_wrap.add_widget(loc_icon)
        city_wrap.add_widget(self.city_label)
        city_wrap.bind(on_press=self._show_city_picker)
        bar.add_widget(city_wrap)

        # 搜索框（浅绿色边框 + 白底）
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
                radius=[dp(20)] * 4)

        def _update_search_border(*_):
            self.search_border.pos = search_wrap.pos
            self.search_border.size = search_wrap.size
            self.search_bg.pos = (search_wrap.x + dp(1), search_wrap.y + dp(1))
            self.search_bg.size = (
                search_wrap.width - dp(2), search_wrap.height - dp(2)
            )

        search_wrap.bind(
            pos=lambda i, *_: setattr(self.search_border, "pos", i.pos),
            size=lambda i, *_: setattr(self.search_border, "size", i.size),
        )
        search_wrap.bind(pos=_update_search_border, size=_update_search_border)

        # 搜索图标（canvas 绘制放大镜，避免字体缺字）
        search_icon = Widget(
            size_hint=(None, 1), width=dp(30),
        )
        search_icon.bind(pos=_draw_search_icon, size=_draw_search_icon)
        self.home_search_input = TextInput(
            hint_text="搜索你感兴趣的内容、关键词",
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
        self.home_search_input.bind(on_text_validate=self.search_pests)
        search_wrap.add_widget(search_icon)
        search_wrap.add_widget(self.home_search_input)
        bar.add_widget(search_wrap)

        # 右侧扫码图标：块宽收紧到 dp(34)（= 图标 dp(30) + 4dp 余量），
        # 让搜索框能一直往右延伸，不再留出一大段空白。代价是搜索框中心会比
        # 屏幕中心右偏约 8dp —— 城市块（图标+「深圳」）最少要 dp(48) 才放得下，
        # 而扫码图标只要 dp(30)，要绝对居中就必须两边等宽，右侧空白就消不掉。
        scan_wrap = BoxLayout(size_hint=(None, 1), width=dp(34))
        # 用用户新给的「扫一扫.png」（紫底 + 白色扫描框）。
        # 不再加 color=GREEN —— 那会把整张图标（含底色）染成绿色，丢掉原配色。
        qr_path = os.path.join(IMAGE_DIR, "扫一扫.png")
        scan_btn = _IconButton(
            source=qr_path if os.path.exists(qr_path) else "",
            size_hint=(None, 1), width=dp(30),
            allow_stretch=True, keep_ratio=True,
        )
        scan_btn.bind(
            on_press=lambda *_: App.get_running_app().open_qr_scanner("home"))
        scan_wrap.add_widget(Widget())      # 左侧空白占位，图标靠右
        scan_wrap.add_widget(scan_btn)
        bar.add_widget(scan_wrap)
        return bar

    # ---------------- 天气卡片 ----------------
    def _build_weather_card(self):
        card = BoxLayout(
            orientation="vertical",
            size_hint=(1, None), height=dp(178),
            padding=(dp(14), dp(10), dp(14), dp(10)),
            spacing=dp(2),
        )
        with card.canvas.before:
            Color(*WEATHER_GREEN)
            self.weather_bg = RoundedRectangle(
                pos=card.pos, size=card.size, radius=[dp(20)] * 4)
        card.bind(
            pos=lambda i, *_: setattr(self.weather_bg, "pos", i.pos),
            size=lambda i, *_: setattr(self.weather_bg, "size", i.size),
        )

        # 第一行：天气图标（晴/多云/雨/雪自动切换）+ 温度 + 天气简述
        top_row = BoxLayout(
            orientation="horizontal",
            size_hint=(1, None), height=dp(74), spacing=dp(8),
        )
        icon_widget = Widget(
            size_hint=(None, 1), width=dp(74),
        )
        icon_widget.weather_type = getattr(self, "_weather_kind", "sun")
        icon_widget.bind(pos=_draw_weather_icon, size=_draw_weather_icon)
        self._weather_icon_widget = icon_widget
        top_row.add_widget(icon_widget)

        self.temp_label = Label(
            text="--°", font_size=sp(40), bold=True,
            color=(1, 1, 1, 1), size_hint=(None, 1), width=dp(88),
            halign="left", valign="middle", **text_style(),
        )
        # 注意 text_size 的宽度必须留 None（不能绑成控件宽度）：
        # Kivy core/text/__init__.py 的 render() 里有
        #     if uw: w = uw      # text_size 宽度一旦给定，纹理宽度就等于它
        # 所以只有宽度为 None 时 texture_size[0] 才是「文字自然宽度」，
        # 才能用它反推控件宽度。否则每轮 width += dp(2) 无限膨胀，
        # 每帧都在重算纹理，就会刷屏
        # "too much iteration done before the next frame" 并卡住界面。
        # 高度固定成 top_row 的高度，valign='middle' 才会生效。
        self.temp_label.text_size = (None, dp(74))
        # 把宽度收紧到「30°」的实际宽度：原来固定 width=dp(88)，温度只占左边
        # 一小半，剩下的空白把后面的「雨」顶到卡片中间，像两个独立元素。
        self.temp_label.bind(texture_size=_fit_label_width)
        self._weather_icon_label = Label(
            text="晴", font_size=sp(16),
            color=(1, 1, 1, 0.95),
            size_hint=(1, 1),
            halign="left", valign="center", **text_style(),
        )
        self._weather_icon_label.bind(
            size=self._weather_icon_label.setter("text_size"))
        top_row.add_widget(self.temp_label)
        top_row.add_widget(self._weather_icon_label)
        card.add_widget(top_row)

        # 第二行：最高最低温（效果图为左对齐，和上面的温度起始位置对齐）
        desc_row = BoxLayout(size_hint=(1, None), height=dp(20))
        # 太阳图标 dp(74) + top_row 的 dp(8) 间距，标签左边缘正好对齐温度
        desc_row.add_widget(Widget(size_hint=(None, 1), width=dp(82)))
        self.desc_label = Label(
            text="天气加载中...",
            font_size=sp(12), color=(0.92, 1, 0.92, 1),
            size_hint=(1, 1),
            halign="left", valign="middle",
            shorten=True, shorten_from="right", **text_style(),
        )
        self.desc_label.bind(size=self.desc_label.setter("text_size"))
        desc_row.add_widget(self.desc_label)
        card.add_widget(desc_row)

        # 第三行：气象预警信息条（可点击）
        warning_btn = Button(
            text="   气象预警信息",
            font_size=sp(15),
            color=(1, 1, 1, 0.95),
            background_normal="", background_down="",
            background_color=(0, 0, 0, 0),
            size_hint=(1, None), height=dp(32),
            halign="left", valign="middle", **text_style(),
        )

        def _update_warning_bg(instance, *_args):
            instance.canvas.before.clear()
            with instance.canvas.before:
                Color(1, 1, 1, 0.22)
                RoundedRectangle(
                    pos=instance.pos, size=instance.size,
                    radius=[dp(17)] * 4)

        warning_btn.bind(pos=_update_warning_bg, size=_update_warning_bg)
        warning_btn.bind(size=warning_btn.setter("text_size"))
        warning_btn.bind(on_press=lambda *_: open_text_popup(
            "气象预警", "气象台发布暴雨蓝色预警，请注意防范。"))
        card.add_widget(warning_btn)

        # 第四行：今日适宜标签（参考图：一行排开、标签间距紧凑，不拉通整行）
        suitable_box = BoxLayout(
            size_hint=(1, None), height=dp(26),
            padding=(dp(4), 0, 0, 0), spacing=dp(8),
        )
        suitable_title = Label(
            text="今日适宜:", font_size=sp(13),
            color=(0.92, 1, 0.92, 1),
            size_hint=(None, 1), width=dp(66),
            halign="left", valign="middle", **text_style(),
        )
        suitable_title.bind(size=suitable_title.setter("text_size"))
        suitable_box.add_widget(suitable_title)

        # 效果图里「今日适宜:」后面有一个小雨滴 —— 用用户提供的 image/雨滴.png。
        # 该图是深橄榄色描边，直接放到绿卡上和白色文字不搭，所以先染成白色；
        # 万一图片读不到，退回 canvas 画的水滴，保证这一行不会塌掉。
        drop_src = _tinted_png(DROP_ICON, DROP_ICON_TINT, "drop_white.png")
        if drop_src and os.path.exists(drop_src):
            suitable_box.add_widget(Image(
                source=drop_src, size_hint=(None, 1), width=dp(15),
                allow_stretch=True, keep_ratio=True, color=(1, 1, 1, 1),
            ))
        else:
            drop = Widget(size_hint=(None, 1), width=dp(16))
            drop.bind(pos=_draw_drop, size=_draw_drop)
            suitable_box.add_widget(drop)

        for item in ["浇灌", "种植", "除虫", "巡田"]:
            tag = Label(
                text=item, font_size=sp(13),
                color=(1, 1, 1, 1),
                size_hint=(None, 1), width=dp(30),
                halign="center", valign="middle", **text_style(),
            )
            tag.bind(size=tag.setter("text_size"))
            suitable_box.add_widget(tag)
        suitable_box.add_widget(Widget())
        card.add_widget(suitable_box)
        return card

    # ---------------- 城市选择弹窗 ----------------
    def _show_city_picker(self, _instance=None):
        from kivy.uix.modalview import ModalView
        from kivy.uix.textinput import TextInput
        from utils import _update_popup_rect
        from kivy.graphics import Color, RoundedRectangle

        popup = ModalView(
            size_hint=(0.88, None), height=dp(320),
            overlay_color=(0, 0, 0, 0.35),
            background="", background_color=(0, 0, 0, 0),
        )
        box = BoxLayout(orientation="vertical", spacing=dp(12), padding=dp(18))
        with box.canvas.before:
            Color(1, 1, 1, 1)
            bg = RoundedRectangle(
                pos=box.pos, size=box.size, radius=[dp(16)] * 4)
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

        city_input = TextInput(
            hint_text="输入城市拼音",
            text=WEATHER_CITY,
            multiline=False, input_type="text",
            background_normal="", background_active="",
            background_color=(0.94, 0.94, 0.94, 1),
            padding=(dp(12), dp(10)),
            font_size=sp(16),
            size_hint=(1, None), height=dp(48),
            **text_style(),
        )
        box.add_widget(city_input)

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
            self.city_label.text = CITY_NAMES.get(new_city, new_city)
            self.temp_label.text = "--°"
            self.desc_label.text = "天气加载中..."
            popup.dismiss()
            self._load_weather()

        confirm_btn.bind(on_press=confirm)
        cancel_btn.bind(on_press=lambda *_: popup.dismiss())
        btn_row.add_widget(confirm_btn)
        btn_row.add_widget(cancel_btn)
        box.add_widget(btn_row)
        popup.add_widget(box)
        popup.open()

    def _load_weather(self):
        def on_success(data):
            self.temp_label.text = f"{data['temp']}°"
            desc = _zh_weather_desc(data["desc"])
            # 整句控制在 20 字以内，防止换行溢出卡片
            line = f"最高{data['max']}° 最低{data['min']}° | 今天{desc}"
            if len(line) > 20:
                line = f"{data['max']}/{data['min']}° | 今天{desc}"
            if len(line) > 20:
                line = f"今天{desc}"
            self.desc_label.text = line
            city = data.get("city", WEATHER_CITY)
            self.city_label.text = CITY_NAMES.get(city, city)
            # 左侧大图标跟着天气走（原来这里固定是太阳，雨天也画太阳）
            kind = _weather_icon_kind(desc)
            self._weather_kind = kind
            self._weather_icon_label.text = WEATHER_SHORT_TEXT.get(kind, "晴")
            icon_w = getattr(self, "_weather_icon_widget", None)
            if icon_w is not None:
                icon_w.weather_type = kind
                _draw_weather_icon(icon_w)

        def on_error(msg):
            self.temp_label.text = "--°"
            self.desc_label.text = "网络异常，无法获取天气"
            # 取不到天气时把图标复位成晴天，避免残留上一次的雨/雪图标
            icon_w = getattr(self, "_weather_icon_widget", None)
            if icon_w is not None:
                icon_w.weather_type = "sun"
                _draw_weather_icon(icon_w)

        fetch_weather(WEATHER_CITY, on_success, on_error)

    # ---------------- 卡片标题（今日提醒 / 我的工具 共用） ----------------
    def _build_card_header(self, title_text, on_view_all):
        """效果图样式标题：大标题 + 右侧「查看全部」+ 标题下的绿色短线。"""
        wrap = BoxLayout(orientation="vertical", size_hint=(1, None),
                         height=dp(38))
        row = BoxLayout(size_hint=(1, 1))
        title = Label(
            text=title_text, font_size=sp(19), bold=True,
            color=(0.08, 0.08, 0.08, 1),
            halign="left", valign="middle", **text_style(),
        )
        title.bind(size=title.setter("text_size"))
        row.add_widget(title)

        view_all = UnderlineLabel(
            text="查看全部", color=GREEN, font_size=sp(12),
            size_hint=(None, 1), width=dp(66),
            halign="right", valign="middle", **text_style(),
        )
        view_all.bind(size=view_all.setter("text_size"))
        view_all.bind(on_press=lambda *_: on_view_all())
        row.add_widget(view_all)
        wrap.add_widget(row)

        # 标题下的绿色短线（宽度约等于四字标题宽度，效果图样式）
        line_row = BoxLayout(size_hint=(1, None), height=dp(3))
        line = Widget(size_hint=(None, 1), width=dp(74))

        def _redraw(inst, *_args):
            inst.canvas.clear()
            with inst.canvas:
                Color(*GREEN)
                RoundedRectangle(pos=inst.pos, size=inst.size,
                                 radius=[dp(2)] * 4)

        line.bind(pos=_redraw, size=_redraw)
        line_row.add_widget(line)
        line_row.add_widget(Widget())
        wrap.add_widget(line_row)
        return wrap

    # ---------------- 今日提醒 ----------------
    def _build_reminder_card(self):
        card = BoxLayout(
            orientation="vertical",
            padding=(dp(12), dp(8), dp(12), dp(8)),
            size_hint=(1, None),
        )
        card.bind(minimum_height=card.setter("height"))
        with card.canvas.before:
            Color(*CARD_BG)
            reminder_bg = RoundedRectangle(
                pos=card.pos, size=card.size, radius=[dp(14)] * 4)
        card.bind(
            pos=lambda i, *_: setattr(reminder_bg, "pos", i.pos),
            size=lambda i, *_: setattr(reminder_bg, "size", i.size),
        )

        card.add_widget(self._build_card_header(
            "今日提醒",
            lambda: open_text_popup("更多提醒", "\n".join(HOME_REMINDERS))))

        # 每条提醒只占一行，行高 = 文字行高 + 0.8 行间距（sp14 → 约 25dp），
        # 不再画分割线，避免行与行之间被撑开。
        # shorten 保证超长提醒在 360dp 窗口下也只显示一行（右侧省略号）。
        for reminder in HOME_REMINDERS:
            row = BoxLayout(size_hint=(1, None), height=dp(35), spacing=dp(8))

            label = Label(
                text=reminder, font_size=sp(14),
                color=(0.16, 0.16, 0.16, 1),
                size_hint=(1, 1),
                halign="left", valign="middle",
                shorten=True, shorten_from="right", **text_style(),
            )
            label.bind(size=label.setter("text_size"))
            row.add_widget(label)

            detail_btn = UnderlineLabel(
                text="查看详情",
                color=GREEN, font_size=sp(12),
                size_hint=(None, 1), width=dp(54),
                halign="right", valign="middle", **text_style(),
            )
            detail_btn.bind(size=detail_btn.setter("text_size"))
            detail_btn.bind(
                on_press=lambda *_, r=reminder: open_text_popup("提醒详情", r))
            row.add_widget(detail_btn)
            card.add_widget(row)
        return card

    # ---------------- 我的工具 ----------------
    def _build_tool_section(self):
        card = BoxLayout(
            orientation="vertical",
            padding=(dp(14), dp(8), dp(14), dp(10)),
            spacing=dp(8),
            size_hint=(1, None),
        )
        card.bind(minimum_height=card.setter("height"))
        with card.canvas.before:
            Color(*CARD_BG)
            tool_bg = RoundedRectangle(
                pos=card.pos, size=card.size, radius=[dp(14)] * 4)
        card.bind(
            pos=lambda i, *_: setattr(tool_bg, "pos", i.pos),
            size=lambda i, *_: setattr(tool_bg, "size", i.size),
        )

        card.add_widget(self._build_card_header(
            "我的工具",
            lambda: open_text_popup("更多工具", "土壤分析\n农资识别\n作物生长监测")))

        # 工具列表（共6个，4列网格）
        # 图标统一走 _transparent_png：白底 PNG 在浅绿卡片上会露出白方块
        def _ic(name):
            return _transparent_png(os.path.join(IMAGE_DIR, name))

        tools = [
            (_ic("农事计划.png"), "计划", "农事计划",
             lambda *_: setattr(self.manager, "current", "farming_plan")),
            (_ic("虫害百科.png"), "百科", "虫害百科",
             lambda *_: setattr(self.manager, "current", "encyclopedia")),
            (_ic("我的收藏.png"), "收藏", "我的收藏",
             lambda *_: setattr(self.manager, "current", "favorite")),
            (_ic("病虫害分布图.png"), "地图", "病虫害分布图",
             lambda *_: setattr(self.manager, "current", "map")),
            # 「图层 8.png」就是用户新给的相机图标（PS 默认图层名，未重命名）
            (_ic("图层 8.png"), "拍照", "拍照识别",
             lambda *_: App.get_running_app().show_capture_menu()),
            (_ic("更多工具.png"), "更多", "更多工具",
             lambda *_: open_text_popup("更多工具", "土壤分析\n农资识别\n作物生长监测")),
        ]

        # 补齐到 4 的整数倍：第二行只有 2 个工具时用透明占位补满 4 列。
        # 否则 Kivy 的 BoxLayout 会把 2 个卡片按 size_hint 均分成各占一半宽，
        # 看起来就是“第二行图标被放大、和第一行不对齐”。
        while len(tools) % 4:
            tools.append(None)

        grid = BoxLayout(orientation="vertical", spacing=dp(8),
                         size_hint=(1, None))
        grid.bind(minimum_height=grid.setter("height"))
        row = None
        for idx, item in enumerate(tools):
            if idx % 4 == 0:
                row = BoxLayout(spacing=dp(8), size_hint=(1, None), height=dp(78))
                grid.add_widget(row)
            if item is None:
                # 透明占位，保证列宽与第一行一致
                row.add_widget(Widget(size_hint=(1, 1)))
                continue
            icon_src, icon_txt, title_txt, callback = item
            card_widget = HomeToolCard(
                icon_source=icon_src,
                icon_text=icon_txt,
                title=title_txt,
            )
            card_widget.bind(on_press=callback)
            row.add_widget(card_widget)
        card.add_widget(grid)
        return card

    # ---------------- 底部导航 ----------------
    def _build_bottom_nav(self):
        container = FloatLayout(
            size_hint=(1, None), height=dp(98),
            pos_hint={"x": 0, "y": 0},
        )

        # 白色导航条（容器底部，高度 72dp）
        bar = BoxLayout(
            orientation="horizontal",
            size_hint=(1, None), height=dp(72),
            pos_hint={"x": 0, "y": 0},
            padding=(dp(10), dp(6), dp(10), dp(5)),
        )
        with bar.canvas.before:
            Color(1, 1, 1, 1)
            bar.bg_rect = Rectangle(pos=bar.pos, size=bar.size)
        bar.bind(
            pos=lambda inst, *_: update_nav_rect(inst),
            size=lambda inst, *_: update_nav_rect(inst),
        )
        container.add_widget(bar)

        from kivy.uix.behaviors import ButtonBehavior

        class NavItem(ButtonBehavior, BoxLayout):
            pass

        # 底部导航图标（用户提供的新版 UI 图标，文件放在 image/ 下；
        # 「我的」暂用旧图标 —— 新图标里没有对应的 tab 图标）
        # tab 的高亮不做硬编码：按当前页面名判断，落在哪个页就点亮哪个 tab。
        current_screen = getattr(self, "name", "home")
        items = [
            ("首页", "首页.png", "home"),
            ("社区", "社区.png", "community"),
            ("百科", "虫害百科.png", "store"),
            ("我的", "icon_my.png", "mypage"),
        ]

        # 左侧两个 + 右侧两个，中间留给凸起的拍照按钮
        left_box = BoxLayout(spacing=0, size_hint=(0.4, 1))
        right_box = BoxLayout(spacing=0, size_hint=(0.4, 1))
        bar.add_widget(left_box)
        bar.add_widget(Widget(size_hint=(0.2, 1)))
        bar.add_widget(right_box)

        for idx, (title, icon_file, target) in enumerate(items):
            is_active = (current_screen == target)
            callback = (lambda *_, t=target: setattr(self.manager, "current", t))
            item = NavItem(
                orientation="vertical", spacing=dp(2),
                size_hint=(1, 1), padding=(0, dp(2), 0, dp(2)),
            )
            item.bind(on_press=callback)

            icon_path = os.path.join(IMAGE_DIR, icon_file)
            if os.path.exists(icon_path):
                icon_widget = Image(
                    source=icon_path,
                    size_hint=(1, None), height=dp(36),
                    allow_stretch=True, keep_ratio=True,
                )
            else:
                icon_widget = Widget(size_hint=(1, None), height=dp(36))
            item.add_widget(icon_widget)

            lbl = Label(
                text=title, font_size=sp(12), bold=is_active,
                color=(GREEN if is_active else (0.42, 0.46, 0.50, 1)),
                size_hint=(1, None), height=dp(16),
                halign="center", valign="middle",
                **text_style(),
            )
            lbl.bind(size=lbl.setter("text_size"))
            item.add_widget(lbl)

            (left_box if idx < 2 else right_box).add_widget(item)

        # 中间凸起的拍照识别按钮：白色凹槽圆 + 浅绿色圆 + 原相机图标
        # 注意：FloatLayout 的 pos_hint 是相对比例（0~1），
        # 容器高 98dp，按钮圆心要落在导航条顶边（72dp）处 → 72/98。
        _cy = 72.0 / 98.0
        notch = _nav_notch_widget(diameter=dp(84))
        notch.pos_hint = {"center_x": 0.5, "center_y": _cy}
        container.add_widget(notch)

        cam_circle = Widget(
            size_hint=(None, None), size=(dp(64), dp(64)),
            pos_hint={"center_x": 0.5, "center_y": _cy},
        )
        cam_circle.bind(pos=_update_camera_btn_light,
                        size=_update_camera_btn_light)
        container.add_widget(cam_circle)

        # 拍照按钮图标：直接使用用户提供的「图层 8.png」，保持其原样（含浅绿圆角底）
        cam_icon_path = CAM_ICON
        if os.path.exists(cam_icon_path):
            cam_icon = Image(
                source=cam_icon_path,
                size_hint=(None, None), size=(dp(30), dp(30)),
                allow_stretch=True, keep_ratio=True,
                pos_hint={"center_x": 0.5, "center_y": _cy},
            )
            container.add_widget(cam_icon)

        # 相机按钮下方的文字（圆心 72dp，半径 32dp，文字放在 y≈17dp 处）
        cam_label = Label(
            text="拍照识别", font_size=sp(12),
            color=(0.42, 0.46, 0.50, 1),
            size_hint=(None, None), size=(dp(80), dp(18)),
            pos_hint={"center_x": 0.5, "center_y": 17.0 / 98.0},
            **text_style(),
        )
        container.add_widget(cam_label)

        hit_btn = Button(
            text="", background_normal="", background_down="",
            background_color=(0, 0, 0, 0),
            size_hint=(None, None), size=(dp(72), dp(72)),
            pos_hint={"center_x": 0.5, "center_y": _cy},
        )
        hit_btn.bind(
            on_press=lambda *_: App.get_running_app().show_capture_menu())
        container.add_widget(hit_btn)

        return container

    def search_pests(self, _instance=None):
        keyword = self.home_search_input.text.strip()
        if not keyword:
            show_toast("请输入搜索关键词")
            return
        results_screen = self.manager.get_screen("search_results")
        results_screen.show_results(keyword)
        self.home_search_input.focus = False
        self.manager.current = "search_results"

    def cancel_home_search(self, _instance=None):
        self.home_search_input.text = ""
        self.home_search_input.focus = False

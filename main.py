import os
import sqlite3
import shutil
import threading
from datetime import datetime
from importlib import import_module

os.environ.setdefault("KIVY_NO_FILELOG", "1")
os.environ.setdefault("KIVY_NO_CONSOLELOG", "1")

from kivy.app import App
from kivy.clock import Clock
from kivy.core.window import Window
from kivy.factory import Factory
from kivy.graphics import Color, Ellipse, Line, PopMatrix, PushMatrix, Rectangle, Rotate, RoundedRectangle, StencilPop, \
    StencilPush, StencilUnUse, StencilUse
from kivy.metrics import dp, sp
from kivy.properties import NumericProperty, ObjectProperty, StringProperty
from kivy.uix.behaviors import ButtonBehavior
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.button import Button
from kivy.uix.filechooser import FileChooserListView
from kivy.uix.floatlayout import FloatLayout
from kivy.uix.image import Image
from kivy.uix.label import Label
from kivy.uix.popup import Popup
from kivy.uix.recycleview.views import RecycleDataViewBehavior
from kivy.uix.recycleboxlayout import RecycleBoxLayout
from kivy.uix.recycleview import RecycleView
from kivy.uix.screenmanager import Screen, ScreenManager
from kivy.uix.scrollview import ScrollView
from kivy.uix.textinput import TextInput
from kivy.uix.togglebutton import ToggleButton
from kivy.uix.widget import Widget
from kivy.utils import platform as kivy_platform

try:
    from kivy.core.text import LabelBase
except Exception:
    LabelBase = None

try:
    from PIL import Image as PILImage
except Exception:
    PILImage = None

API_BASE_URL = os.environ.get("PLANT_API_URL", "http://192.168.1.100:8000")
GREEN = (0.12, 0.58, 0.30, 1)
FONT_NAME = None
STORE_DB_PATH = os.path.join(os.path.dirname(__file__), "smart_agri.db")
AVATAR_DIR = os.path.join(os.path.dirname(__file__), "avatars")
IMAGE_DIR = os.path.join(os.path.dirname(__file__), "image")
HOME_TOOL_ICONS = {
    "专家服务": os.path.join(IMAGE_DIR, "专家.jpg"),
    "农事计划": os.path.join(IMAGE_DIR, "农事计划.jpg"),
    "虫害百科": os.path.join(IMAGE_DIR, "虫害百科.jpg"),
    "病虫害分布图": os.path.join(IMAGE_DIR, "病虫害分布.png"),
}
COMMUNITY_FOCUS_ICONS = {
    "种植经验": os.path.join(IMAGE_DIR, "种植经验.jpg"),
    "防治技巧": os.path.join(IMAGE_DIR, "防治经验.jpg"),
}
LIKE_ICON_OFF = os.path.join(IMAGE_DIR, "点赞（未点赞状态）.jpg")
LIKE_ICON_ON = os.path.join(IMAGE_DIR, "点赞（点赞状态）.jpg")
STORE_TABS = ["精选好物", "热销榜单", "肥料", "杀虫剂"]
DEFAULT_COMMENT_USER = "开心的菜园伯伯"
STORE_CATALOG_VERSION = "2026-05-10-v4"
STORE_PRODUCTS_SEED = [
    {"id": 2001, "name": "复合微生物菌剂", "category": "精选好物", "sub_category": "精选", "specification": "5kg",
     "price": 65.0, "sold_count": 0, "stock": 999, "image": "gray_placeholder",
     "description": "改善土壤环境，促进作物根系健壮生长。", "is_hot": 0, "is_featured": 1},
    {"id": 2002, "name": "高效氯氟氰菊酯", "category": "精选好物", "sub_category": "精选", "specification": "500ml",
     "price": 35.0, "sold_count": 0, "stock": 999, "image": "gray_placeholder",
     "description": "适合多种刺吸式害虫的日常防治。", "is_hot": 0, "is_featured": 1},
    {"id": 2003, "name": "电动背负式喷雾器", "category": "精选好物", "sub_category": "精选", "specification": "20L",
     "price": 189.0, "sold_count": 0, "stock": 300, "image": "gray_placeholder",
     "description": "容量充足，适合大棚和果园喷施作业。", "is_hot": 0, "is_featured": 1},
    {"id": 2004, "name": "农用粘虫板（黄色）", "category": "精选好物", "sub_category": "精选", "specification": "20张/包",
     "price": 15.0, "sold_count": 0, "stock": 500, "image": "gray_placeholder",
     "description": "用于诱杀蚜虫、白粉虱等小型飞虫。", "is_hot": 0, "is_featured": 1},
    {"id": 2005, "name": "修枝剪+园艺手套套装", "category": "精选好物", "sub_category": "精选", "specification": "套装",
     "price": 45.0, "sold_count": 0, "stock": 280, "image": "gray_placeholder",
     "description": "适合日常修枝、整形和园艺维护。", "is_hot": 0, "is_featured": 1},
    {"id": 2101, "name": "草铵膦", "category": "精选好物", "sub_category": "热销", "specification": "1000ml",
     "price": 45.0, "sold_count": 0, "stock": 999, "image": "gray_placeholder",
     "description": "常用于田间杂草防除，使用方便。", "is_hot": 1, "is_featured": 0},
    {"id": 2102, "name": "吡虫啉", "category": "精选好物", "sub_category": "热销", "specification": "100g",
     "price": 12.0, "sold_count": 0, "stock": 999, "image": "gray_placeholder",
     "description": "防治蚜虫、飞虱等常见刺吸式害虫。", "is_hot": 1, "is_featured": 0},
    {"id": 2103, "name": "阿维菌素", "category": "精选好物", "sub_category": "热销", "specification": "200ml",
     "price": 28.0, "sold_count": 0, "stock": 999, "image": "gray_placeholder",
     "description": "适合红蜘蛛、潜叶害虫等防控使用。", "is_hot": 1, "is_featured": 0},
    {"id": 2104, "name": "硫酸钾复合肥", "category": "精选好物", "sub_category": "热销", "specification": "50kg",
     "price": 180.0, "sold_count": 0, "stock": 260, "image": "gray_placeholder",
     "description": "氮磷钾均衡补充，适合多种作物。", "is_hot": 1, "is_featured": 0},
    {"id": 2105, "name": "电动果树修剪机", "category": "精选好物", "sub_category": "热销", "specification": "锂电池",
     "price": 299.0, "sold_count": 0, "stock": 120, "image": "gray_placeholder",
     "description": "适合果树修枝整形，提高作业效率。", "is_hot": 1, "is_featured": 0},
    {"id": 2201, "name": "硫酸钾复合肥", "category": "精选好物", "sub_category": "肥料", "specification": "50kg",
     "price": 180.0, "sold_count": 0, "stock": 260, "image": "gray_placeholder",
     "description": "适合作物整个生育期基础追肥管理。", "is_hot": 0, "is_featured": 0},
    {"id": 2202, "name": "磷酸二氢钾", "category": "精选好物", "sub_category": "肥料", "specification": "1000g",
     "price": 25.0, "sold_count": 0, "stock": 999, "image": "gray_placeholder",
     "description": "花果期补磷补钾，提高作物长势。", "is_hot": 0, "is_featured": 0},
    {"id": 2203, "name": "生物有机肥", "category": "精选好物", "sub_category": "肥料", "specification": "40kg",
     "price": 95.0, "sold_count": 0, "stock": 500, "image": "gray_placeholder",
     "description": "富含有机质，适合改良土壤结构。", "is_hot": 0, "is_featured": 0},
    {"id": 2204, "name": "大量元素水溶肥（平衡型）", "category": "精选好物", "sub_category": "肥料", "specification": "5kg",
     "price": 65.0, "sold_count": 0, "stock": 420, "image": "gray_placeholder",
     "description": "平衡补充氮磷钾，适合滴灌冲施。", "is_hot": 0, "is_featured": 0},
    {"id": 2205, "name": "腐植酸水溶肥", "category": "精选好物", "sub_category": "肥料", "specification": "10kg",
     "price": 80.0, "sold_count": 0, "stock": 380, "image": "gray_placeholder",
     "description": "促进养分吸收，缓解黄叶弱苗。", "is_hot": 0, "is_featured": 0},
    {"id": 2206, "name": "枯草芽孢杆菌微生物菌剂", "category": "精选好物", "sub_category": "肥料", "specification": "1kg",
     "price": 38.0, "sold_count": 0, "stock": 460, "image": "gray_placeholder",
     "description": "调节根际环境，增强作物抗逆能力。", "is_hot": 0, "is_featured": 0},
    {"id": 2301, "name": "吡虫啉", "category": "精选好物", "sub_category": "杀虫剂", "specification": "100g",
     "price": 12.0, "sold_count": 0, "stock": 999, "image": "gray_placeholder",
     "description": "适合防治蚜虫、飞虱、粉虱等害虫。", "is_hot": 0, "is_featured": 0},
    {"id": 2302, "name": "甲维盐", "category": "精选好物", "sub_category": "杀虫剂", "specification": "100ml",
     "price": 22.0, "sold_count": 0, "stock": 999, "image": "gray_placeholder",
     "description": "适合鳞翅目幼虫防治使用。", "is_hot": 0, "is_featured": 0},
    {"id": 2303, "name": "氯虫苯甲酰胺", "category": "精选好物", "sub_category": "杀虫剂", "specification": "100ml",
     "price": 58.0, "sold_count": 0, "stock": 680, "image": "gray_placeholder",
     "description": "持效较长，适合咀嚼式害虫防控。", "is_hot": 0, "is_featured": 0},
    {"id": 2304, "name": "阿维菌素", "category": "精选好物", "sub_category": "杀虫剂", "specification": "200ml",
     "price": 28.0, "sold_count": 0, "stock": 999, "image": "gray_placeholder",
     "description": "适合潜叶虫和螨类害虫综合防治。", "is_hot": 0, "is_featured": 0},
    {"id": 2305, "name": "噻虫嗪", "category": "精选好物", "sub_category": "杀虫剂", "specification": "100g",
     "price": 18.0, "sold_count": 0, "stock": 999, "image": "gray_placeholder",
     "description": "内吸传导性较强，适合苗期管理。", "is_hot": 0, "is_featured": 0},
    {"id": 2306, "name": "高效氯氟氰菊酯", "category": "精选好物", "sub_category": "杀虫剂", "specification": "500ml",
     "price": 35.0, "sold_count": 0, "stock": 999, "image": "gray_placeholder",
     "description": "触杀效果明显，适合害虫暴发初期。", "is_hot": 0, "is_featured": 0},
    {"id": 2401, "name": "敌敌畏", "category": "商城首页", "sub_category": "广告", "specification": "500ml",
     "price": 26.0, "sold_count": 0, "stock": 500, "image": "gray_placeholder", "description": "经典常见农药示例商品。",
     "is_hot": 1, "is_featured": 0},
    {"id": 2402, "name": "乙酰甲胺磷", "category": "热销榜单", "sub_category": "热销榜单", "specification": "500ml",
     "price": 33.0, "sold_count": 0, "stock": 500, "image": "gray_placeholder",
     "description": "商城首页热销榜单展示商品。", "is_hot": 1, "is_featured": 0},
    {"id": 2403, "name": "乙蒜素", "category": "热销榜单", "sub_category": "热销榜单", "specification": "300ml",
     "price": 29.0, "sold_count": 0, "stock": 500, "image": "gray_placeholder",
     "description": "商城首页热销榜单展示商品。", "is_hot": 1, "is_featured": 0},
    {"id": 2404, "name": "百草枯", "category": "热销榜单", "sub_category": "热销榜单", "specification": "500ml",
     "price": 31.0, "sold_count": 0, "stock": 500, "image": "gray_placeholder",
     "description": "商城首页热销榜单展示商品。", "is_hot": 1, "is_featured": 0},
    {"id": 2405, "name": "乐果", "category": "热销榜单", "sub_category": "热销榜单", "specification": "500ml",
     "price": 24.0, "sold_count": 0, "stock": 500, "image": "gray_placeholder",
     "description": "商城首页热销榜单展示商品。", "is_hot": 1, "is_featured": 0},
    {"id": 2406, "name": "镁立硼复合肥料40kg", "category": "肥料", "sub_category": "肥料推荐",
     "specification": "40kg", "price": 168.0, "sold_count": 0, "stock": 300, "image": "gray_placeholder",
     "description": "商城首页肥料推荐展示商品。", "is_hot": 0, "is_featured": 0},
    {"id": 2407, "name": "镁立硼复合肥料25kg", "category": "肥料", "sub_category": "肥料推荐",
     "specification": "25kg", "price": 118.0, "sold_count": 0, "stock": 300, "image": "gray_placeholder",
     "description": "商城首页肥料推荐展示商品。", "is_hot": 0, "is_featured": 0},
    {"id": 2408, "name": "杀虫饵剂", "category": "杀虫剂", "sub_category": "杀虫剂推荐", "specification": "500g",
     "price": 19.0, "sold_count": 0, "stock": 400, "image": "gray_placeholder",
     "description": "商城首页杀虫剂推荐展示商品。", "is_hot": 0, "is_featured": 0},
    {"id": 2409, "name": "吡虫啉", "category": "杀虫剂", "sub_category": "杀虫剂推荐", "specification": "100g",
     "price": 12.0, "sold_count": 0, "stock": 400, "image": "gray_placeholder",
     "description": "商城首页杀虫剂推荐展示商品。", "is_hot": 0, "is_featured": 0},
]
DEFAULT_USERS = [
    {"username": "test", "password": "123456", "role": "free", "avatar_path": "", "recognize_count": 0,
     "last_recognize_date": "", "nick_name": "开心菜园阿伯", "signature": "欢迎光临我的开心菜园！", "following_count": 8,
     "followers_count": 12, "share_count": 6},
    {"username": "vip", "password": "123456", "role": "vip", "avatar_path": "", "recognize_count": 0,
     "last_recognize_date": "", "nick_name": "开心菜园阿伯", "signature": "欢迎光临我的开心菜园！",
     "following_count": 18, "followers_count": 26, "share_count": 13},
]
HOME_REMINDERS = [
    "【农事计划】今日需要施肥哟！",
    "【数据异常】地块2有虫情！",
    "【农事计划】稻飞虱预警，请注意防范！",
]
COMMUNITY_POSTS = [
    {
        "id": 1,
        "username": "老农民张叔",
        "title": "经典农药配方，防治95%虫害！",
        "summary": "甲维盐和虫螨腈混配，具有虫螨双杀的作用...",
        "full_text": "甲维盐和虫螨腈混配，具有虫螨双杀的作用，针对鳞翅目害虫和螨类害虫都有较好的防治效果，适合在虫口密度较高时轮换使用。",
        "likes": 999,
        "comments": "877",
    },
    {
        "id": 2,
        "username": "柑橘大王",
        "title": "4月柑橘！病虫害预防攻略！",
        "summary": "现在4月柑橘进入盛花期...",
        "full_text": "现在4月柑橘进入盛花期，重点关注蚜虫、木虱、红蜘蛛和溃疡病等问题，建议提前做好清园、修剪和药剂轮换，避免坐果率下降。",
        "likes": 999,
        "comments": "999+",
    },
]
for _post in COMMUNITY_POSTS:
    _post.setdefault("key", f"post:{_post['id']}")

COMMUNITY_ARTICLES = {
    "article:planting": {
        "id": 101,
        "key": "article:planting",
        "username": "智农慧眼",
        "title": "种植经验",
        "summary": "围绕播种、施肥、灌溉和病虫害预防的实用经验整理。",
        "full_text": "种植经验：\n1. 播种前先检查土壤墒情，避免土壤过湿或过干。\n2. 幼苗期以稳根促苗为主，少量多次补水。\n3. 追肥优先结合天气与作物长势，避免高温正午施肥。\n4. 病虫害防治要坚持预防为主，发现早期症状及时处理。\n5. 田间管理尽量保持通风透光，减少高湿环境带来的病害风险。",
    },
    "article:control": {
        "id": 102,
        "key": "article:control",
        "username": "智农慧眼",
        "title": "防治技巧",
        "summary": "从农业防治到药剂轮换，整理常见病虫害综合防治要点。",
        "full_text": "防治技巧：\n1. 先清理病残体和田间杂草，减少初侵染源。\n2. 合理轮作、控氮增钾、避免长期高湿，是减少病害发生的基础。\n3. 药剂使用应根据对象病虫害轮换成分，避免长期单一用药。\n4. 喷施时重点照顾叶背、嫩梢和病斑周围区域，保证覆盖均匀。\n5. 连续阴雨、高温高湿等天气来临前，应提前做好预防性用药和巡田检查。",
    },
}
PEST_ENTRIES = [
    {"id": 1, "name": "番茄晚疫病",
     "intro": "番茄晚疫病由致病疫霉引起，主要危害叶片和青果，湿度大时病健交界处可见白色霉层。",
     "treatment": "及时清除病残体，合理轮作；发病初期可用58%甲霜灵锰锌500倍液、霜霉威盐酸盐等药剂轮换喷雾。"},
    {"id": 2, "name": "番茄早疫病",
     "intro": "番茄早疫病由链格孢菌引起，叶片病斑常有明显同心轮纹，严重时可导致叶片枯黄脱落。",
     "treatment": "与非茄科作物轮作，增施磷钾肥；发病初期可用70%代森锰锌500倍液，每5至7天喷一次。"},
    {"id": 3, "name": "番茄叶霉病", "intro": "番茄叶霉病主要危害叶片，叶背出现灰白色到灰褐色霉层，高温高湿条件下发展快。",
     "treatment": "加强通风降湿，合理密植；可用嘧菌酯、苯醚甲环唑等药剂喷雾防治。"},
    {"id": 4, "name": "番茄斑枯病", "intro": "番茄斑枯病病斑近圆形，后期中心灰白，边缘深褐，并散生黑色小点。",
     "treatment": "清除病残体，减少侵染源；发病初期可用苯醚甲环唑、代森锰锌等药剂。"},
    {"id": 5, "name": "番茄细菌性斑点病",
     "intro": "该病由细菌侵染，病斑暗褐至黑色，周围常有黄色晕圈，果实表面病斑可稍隆起。",
     "treatment": "选用无病种子，加强通风；发病初期可用噻菌铜、中生菌素等药剂。"},
    {"id": 6, "name": "番茄黄化曲叶病毒病", "intro": "该病由烟粉虱传播，病株矮化、黄化、卷叶明显，严重影响产量。",
     "treatment": "培育无病壮苗，使用防虫网，及时清除杂草和病株；重点防治烟粉虱，可用吡虫啉、啶虫脒。"},
    {"id": 7, "name": "番茄花叶病毒病", "intro": "病叶花叶斑驳，叶片皱缩，病株矮化，果实着色不均。",
     "treatment": "选用抗病品种，种子消毒，避免汁液传播；可用氨基寡糖素、香菇多糖等病毒抑制剂。"},
    {"id": 8, "name": "番茄红蜘蛛", "intro": "红蜘蛛刺吸叶背汁液，叶片初现小白点，严重时整叶发黄干枯。",
     "treatment": "清除田间杂草，合理灌溉；可用阿维菌素、哒螨灵、螺螨酯等重点喷叶背。"},
    {"id": 9, "name": "健康番茄", "intro": "植株生长健壮，叶片正常绿色，无明显病虫害症状。",
     "treatment": "继续保持良好田间管理，合理水肥，预防病虫害发生。"},
    {"id": 10, "name": "马铃薯早疫病", "intro": "主要危害叶片和块茎，叶片病斑暗褐色，有同心轮纹。",
     "treatment": "轮作倒茬，增施钾肥；发病初期可用代森锰锌、苯醚甲环唑等喷雾。"},
    {"id": 11, "name": "马铃薯晚疫病", "intro": "马铃薯晚疫病可造成毁灭性危害，叶片出现水渍状病斑，湿度大时叶背生白霉。",
     "treatment": "选用抗病品种，防止田间积水；中心病株出现后用烯酰吗啉、霜脲氰等药剂防治。"},
    {"id": 12, "name": "健康马铃薯", "intro": "植株生长正常，叶色均匀，无明显病害症状。",
     "treatment": "注意预防早晚疫病发生，合理轮作，选用脱毒种薯。"},
    {"id": 13, "name": "健康甜椒", "intro": "叶片浓绿，果实发育正常，无明显病虫害症状。",
     "treatment": "注意防治蚜虫、红蜘蛛等害虫，预防疫病和病毒病。"},
    {"id": 14, "name": "玉米锈病", "intro": "玉米锈病多发生在生长后期，叶片出现黄褐色病斑并散出锈粉。",
     "treatment": "种植抗病品种，合理密植；可用三唑酮、戊唑醇、嘧菌酯等药剂喷雾。"},
    {"id": 15, "name": "稻瘟病", "intro": "稻瘟病在整个生育期均可发生，叶瘟病斑呈纺锤形，穗颈瘟可导致白穗。",
     "treatment": "选用抗病品种，避免偏施氮肥；破口期和齐穗期可用三环唑、稻瘟灵等防治。"},
]
PEST_ENTRIES_EXTRA = [
    {"id": 16, "name": "玉米大斑病", "intro": "主要危害玉米叶片，病斑大而长，灰褐色或黄褐色。",
     "treatment": "选用抗病品种，合理密植；发病初期可用吡唑醚菌酯、戊唑醇等防治。"},
    {"id": 17, "name": "玉米小斑病", "intro": "叶片病斑小而多，椭圆形或长圆形，褐色边缘。",
     "treatment": "加强田间管理，增施磷钾肥；可用百菌清、代森锰锌等防治。"},
    {"id": 18, "name": "小麦赤霉病", "intro": "主要危害穗部，造成枯白穗，影响产量和品质。",
     "treatment": "抽穗扬花期遇雨及时用药，可用戊唑醇、氰烯菌酯等防治。"},
    {"id": 19, "name": "小麦锈病", "intro": "叶片出现锈褐色粉末状孢子堆，严重时叶片干枯。",
     "treatment": "选用抗病品种，合理施肥；可用三唑酮、戊唑醇等防治。"},
    {"id": 20, "name": "稻飞虱", "intro": "成虫和若虫群集稻株基部刺吸汁液，造成倒伏枯死。",
     "treatment": "保持田间湿润，减少产卵；可用吡虫啉、噻虫嗪、烯啶虫胺等防治。"},
    {"id": 21, "name": "稻纵卷叶螟", "intro": "幼虫吐丝纵卷叶片取食叶肉，影响光合作用。",
     "treatment": "可用甲维盐、氯虫苯甲酰胺、茚虫威等药剂防治。"},
    {"id": 22, "name": "玉米螟", "intro": "幼虫钻蛀茎秆和果穗，造成折秆和减产。",
     "treatment": "可用Bt乳剂、氯虫苯甲酰胺、甲维盐等防治。"},
]
ALL_PEST_ENTRIES = PEST_ENTRIES + PEST_ENTRIES_EXTRA


def get_api_base_url():
    config_path = os.path.join(os.path.dirname(__file__), "api_url.txt")
    if os.path.exists(config_path):
        try:
            with open(config_path, "r", encoding="utf-8") as file_obj:
                value = file_obj.read().strip()
            if value:
                return value.rstrip("/")
        except Exception:
            pass
    return API_BASE_URL.rstrip("/")


def register_chinese_font():
    global FONT_NAME
    if LabelBase is None:
        return
    for font_path in (
            "C:/Windows/Fonts/msyh.ttc",
            "/system/fonts/NotoSansCJK-Regular.ttc",
            "/system/fonts/NotoSansSC-Regular.otf",
            "/system/fonts/DroidSansFallback.ttf",
    ):
        if os.path.exists(font_path):
            LabelBase.register(name="ChineseFont", fn_regular=font_path)
            FONT_NAME = "ChineseFont"
            return


def text_style():
    return {"font_name": FONT_NAME} if FONT_NAME else {}


def normalize_comment_text(raw_text):
    text = (raw_text or "").replace("\r", "").replace("\n", " ").strip()
    if not text:
        return ""
    first_cjk = -1
    for idx, char in enumerate(text):
        if "\u4e00" <= char <= "\u9fff":
            first_cjk = idx
            break
    if first_cjk > 0:
        prefix = text[:first_cjk].strip()
        suffix = text[first_cjk:].strip()
        if prefix and all(ch.isalpha() or ch.isspace() for ch in prefix):
            return suffix
    return text


def is_android():
    return kivy_platform == "android"


register_chinese_font()
Window.softinput_mode = "below_target"
if not is_android():
    Window.size = (360, 800)


class IconButton(ButtonBehavior, Label):
    pass


class UnderlineLabel(ButtonBehavior, Label):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.markup = True


class ClickableBox(ButtonBehavior, BoxLayout):
    pass


class RoundedButton(Button):
    def __init__(self, radius=18, fill_color=GREEN, **kwargs):
        self.radius = radius
        self.fill_color = fill_color
        super().__init__(
            background_normal="",
            background_down="",
            background_color=(0, 0, 0, 0),
            border=(0, 0, 0, 0),
            **kwargs,
        )
        self.bind(pos=self._update_canvas, size=self._update_canvas)
        Clock.schedule_once(lambda dt: self._update_canvas(), 0)

    def _update_canvas(self, *_args):
        self.canvas.before.clear()
        with self.canvas.before:
            Color(*self.fill_color)
            RoundedRectangle(pos=self.pos, size=self.size, radius=[self.radius] * 4)


class GrayPlaceholder(Widget):
    def __init__(self, radius=0, **kwargs):
        super().__init__(**kwargs)
        self.radius = radius
        self.bind(pos=self._update_canvas, size=self._update_canvas)

    def _update_canvas(self, *_args):
        self.canvas.before.clear()
        with self.canvas.before:
            Color(0.82, 0.82, 0.82, 1)
            if self.radius:
                Ellipse(pos=self.pos, size=self.size)
            else:
                Rectangle(pos=self.pos, size=self.size)


class CircleImage(Image):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.allow_stretch = True
        self.keep_ratio = False
        self.bind(pos=self._update_canvas, size=self._update_canvas)

    def _update_canvas(self, *_args):
        self.canvas.before.clear()
        self.canvas.after.clear()
        with self.canvas.before:
            StencilPush()
            Ellipse(pos=self.pos, size=self.size)
            StencilUse()
        with self.canvas.after:
            StencilUnUse()
            StencilPop()


class SimpleToast(Popup):
    def __init__(self, message, **kwargs):
        super().__init__(
            title="",
            separator_height=0,
            size_hint=(0.52, None),
            height=dp(112),
            auto_dismiss=True,
            background="",
            background_color=(0, 0, 0, 0),
            **kwargs,
        )
        content = BoxLayout(padding=dp(12))
        label = Label(
            text=message,
            color=(1, 1, 1, 1),
            halign="center",
            valign="middle",
            **text_style(),
        )
        label.bind(size=label.setter("text_size"))
        with content.canvas.before:
            Color(0.10, 0.10, 0.10, 0.86)
            self.bg_rect = Rectangle(pos=content.pos, size=content.size)
        content.bind(pos=self._update_bg, size=self._update_bg)
        content.add_widget(label)
        self.content = content

    def _update_bg(self, instance, *_args):
        self.bg_rect.pos = instance.pos
        self.bg_rect.size = instance.size


def show_toast(message, duration=1.1):
    popup = SimpleToast(message)
    popup.open()
    Clock.schedule_once(lambda dt: popup.dismiss(), duration)


def save_avatar_image(source_path, username):
    if not source_path or not os.path.exists(source_path):
        return ""
    os.makedirs(AVATAR_DIR, exist_ok=True)
    target_path = os.path.join(AVATAR_DIR, f"{username}.png")
    try:
        if PILImage is not None:
            image = PILImage.open(source_path).convert("RGBA")
            width, height = image.size
            side = min(width, height)
            left = (width - side) // 2
            top = (height - side) // 2
            image = image.crop((left, top, left + side, top + side))
            image.save(target_path)
        else:
            shutil.copyfile(source_path, target_path)
        return target_path
    except Exception:
        return source_path


class UserDatabase:
    def __init__(self, db_path=STORE_DB_PATH):
        self.db_path = db_path
        self._initialize()

    def _connect(self):
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def _initialize(self):
        os.makedirs(os.path.dirname(self.db_path) or ".", exist_ok=True)
        with self._connect() as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS users (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    username TEXT UNIQUE NOT NULL,
                    password TEXT NOT NULL,
                    role TEXT NOT NULL,
                    avatar_path TEXT DEFAULT '',
                    recognize_count INTEGER NOT NULL DEFAULT 0,
                    last_recognize_date TEXT DEFAULT '',
                    nick_name TEXT DEFAULT '开心菜园阿伯',
                    signature TEXT DEFAULT '欢迎光临我的开心菜园！',
                    following_count INTEGER DEFAULT 0,
                    followers_count INTEGER DEFAULT 0,
                    share_count INTEGER DEFAULT 0
                )
                """
            )
            self._ensure_column(conn, "users", "nick_name", "TEXT DEFAULT '开心菜园阿伯'")
            self._ensure_column(conn, "users", "signature", "TEXT DEFAULT '欢迎光临我的开心菜园！'")
            self._ensure_column(conn, "users", "following_count", "INTEGER DEFAULT 0")
            self._ensure_column(conn, "users", "followers_count", "INTEGER DEFAULT 0")
            self._ensure_column(conn, "users", "share_count", "INTEGER DEFAULT 0")
            conn.commit()

    @staticmethod
    def _ensure_column(conn, table_name, column_name, column_def):
        columns = [row["name"] for row in conn.execute(f"PRAGMA table_info({table_name})").fetchall()]
        if column_name not in columns:
            conn.execute(f"ALTER TABLE {table_name} ADD COLUMN {column_name} {column_def}")

    @staticmethod
    def _row_to_user(row):
        if not row:
            return None
        return {
            "id": row["id"],
            "username": row["username"],
            "password": row["password"],
            "role": row["role"],
            "avatar_path": row["avatar_path"] or "",
            "recognize_count": int(row["recognize_count"]),
            "last_recognize_date": row["last_recognize_date"] or "",
            "nick_name": row["nick_name"] or "开心菜园阿伯",
            "signature": row["signature"] or "欢迎光临我的开心菜园！",
            "following_count": int(row["following_count"] or 0),
            "followers_count": int(row["followers_count"] or 0),
            "share_count": int(row["share_count"] or 0),
        }

    def get_user(self, username):
        with self._connect() as conn:
            row = conn.execute(
                "SELECT * FROM users WHERE username = ?",
                (username,),
            ).fetchone()
        return self._row_to_user(row)

    def authenticate_user(self, username, password):
        with self._connect() as conn:
            row = conn.execute(
                "SELECT * FROM users WHERE username = ? AND password = ?",
                (username, password),
            ).fetchone()
        return self._row_to_user(row)

    def username_exists(self, username):
        return self.get_user(username) is not None

    def create_user(self, username, password, role, avatar_path=""):
        with self._connect() as conn:
            conn.execute(
                """
                INSERT INTO users (
                    username, password, role, avatar_path, recognize_count, last_recognize_date,
                    nick_name, signature, following_count, followers_count, share_count
                )
                VALUES (?, ?, ?, ?, 0, '', '开心菜园阿伯', '欢迎光临我的开心菜园！', 0, 0, 0)
                """,
                (username, password, role, avatar_path),
            )
            conn.commit()
        return self.get_user(username)

    def reset_users(self):
        with self._connect() as conn:
            conn.execute("DELETE FROM users")
            conn.commit()

    def update_profile(self, username, nick_name=None, signature=None):
        user = self.get_user(username)
        if not user:
            return None
        nick_name = nick_name if nick_name is not None else user["nick_name"]
        signature = signature if signature is not None else user["signature"]
        with self._connect() as conn:
            conn.execute(
                "UPDATE users SET nick_name = ?, signature = ? WHERE username = ?",
                (nick_name, signature, username),
            )
            conn.commit()
        return self.get_user(username)

    def update_avatar(self, username, avatar_path):
        with self._connect() as conn:
            conn.execute(
                "UPDATE users SET avatar_path = ? WHERE username = ?",
                (avatar_path, username),
            )
            conn.commit()

    def reset_daily_recognize_if_needed(self, username):
        today = datetime.now().strftime("%Y-%m-%d")
        user = self.get_user(username)
        if not user:
            return None
        if user["last_recognize_date"] != today:
            with self._connect() as conn:
                conn.execute(
                    """
                    UPDATE users
                    SET recognize_count = 0, last_recognize_date = ?
                    WHERE username = ?
                    """,
                    (today, username),
                )
                conn.commit()
            user = self.get_user(username)
        return user

    def can_recognize_today(self, username):
        user = self.reset_daily_recognize_if_needed(username)
        if not user:
            return False, None
        if user["role"] == "vip":
            return True, user
        return user["recognize_count"] < 3, user

    def increase_recognize_count(self, username):
        today = datetime.now().strftime("%Y-%m-%d")
        with self._connect() as conn:
            conn.execute(
                """
                UPDATE users
                SET recognize_count = recognize_count + 1, last_recognize_date = ?
                WHERE username = ?
                """,
                (today, username),
            )
            conn.commit()
        return self.get_user(username)


USER_DB = UserDatabase()


class StoreDatabase:
    def __init__(self, db_path=STORE_DB_PATH):
        self.db_path = db_path
        self._initialize()

    def _connect(self):
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def _initialize(self):
        os.makedirs(os.path.dirname(self.db_path) or ".", exist_ok=True)
        with self._connect() as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS store_products (
                    id INTEGER PRIMARY KEY,
                    name TEXT NOT NULL,
                    category TEXT NOT NULL,
                    sub_category TEXT,
                    specification TEXT NOT NULL,
                    price REAL NOT NULL,
                    sold_count INTEGER NOT NULL DEFAULT 0,
                    stock INTEGER NOT NULL DEFAULT 0,
                    image TEXT,
                    description TEXT,
                    is_hot INTEGER NOT NULL DEFAULT 0,
                    is_featured INTEGER NOT NULL DEFAULT 0
                )
                """
            )
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS store_favorites (
                    username TEXT NOT NULL,
                    product_id INTEGER NOT NULL,
                    PRIMARY KEY (username, product_id)
                )
                """
            )
            favorite_columns = {
                row["name"] for row in conn.execute("PRAGMA table_info(store_favorites)").fetchall()
            }
            if favorite_columns != {"username", "product_id"}:
                conn.execute("DROP TABLE IF EXISTS store_favorites_legacy")
                conn.execute("ALTER TABLE store_favorites RENAME TO store_favorites_legacy")
                conn.execute(
                    """
                    CREATE TABLE store_favorites (
                        username TEXT NOT NULL,
                        product_id INTEGER NOT NULL,
                        PRIMARY KEY (username, product_id)
                    )
                    """
                )
                legacy_columns = {
                    row["name"] for row in conn.execute("PRAGMA table_info(store_favorites_legacy)").fetchall()
                }
                if {"username", "product_id"}.issubset(legacy_columns):
                    conn.execute(
                        """
                        INSERT OR IGNORE INTO store_favorites (username, product_id)
                        SELECT username, product_id FROM store_favorites_legacy
                        """
                    )
                conn.execute("DROP TABLE store_favorites_legacy")
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS store_comments (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    product_id INTEGER NOT NULL,
                    username TEXT NOT NULL,
                    comment TEXT NOT NULL,
                    comment_date TEXT NOT NULL,
                    created_at TEXT NOT NULL
                )
                """
            )
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS community_likes (
                    username TEXT NOT NULL,
                    post_id INTEGER NOT NULL,
                    PRIMARY KEY (username, post_id)
                )
                """
            )
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS community_post_stats (
                    post_key TEXT PRIMARY KEY,
                    view_count INTEGER NOT NULL DEFAULT 0
                )
                """
            )
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS community_comments (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    post_key TEXT NOT NULL,
                    username TEXT NOT NULL,
                    comment TEXT NOT NULL,
                    comment_date TEXT NOT NULL,
                    created_at TEXT NOT NULL
                )
                """
            )
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS store_orders (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    username TEXT NOT NULL,
                    product_id INTEGER NOT NULL,
                    order_date TEXT NOT NULL,
                    delivery_date TEXT NOT NULL,
                    created_at TEXT NOT NULL
                )
                """
            )
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS pest_entries (
                    id INTEGER PRIMARY KEY,
                    name TEXT NOT NULL,
                    intro TEXT NOT NULL,
                    treatment TEXT NOT NULL
                )
                """
            )
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS user_pest_reports (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    username TEXT,
                    pest_name TEXT,
                    latitude REAL,
                    longitude REAL,
                    created_at TEXT
                )
                """
            )
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS app_meta (
                    meta_key TEXT PRIMARY KEY,
                    meta_value TEXT
                )
                """
            )
            version_row = conn.execute(
                "SELECT meta_value FROM app_meta WHERE meta_key = 'store_catalog_version'"
            ).fetchone()
            current_version = version_row["meta_value"] if version_row else None
            if current_version != STORE_CATALOG_VERSION:
                conn.execute("DELETE FROM store_products")
                conn.execute("DELETE FROM store_favorites")
                conn.execute("DELETE FROM pest_entries")
                conn.executemany(
                    """
                    INSERT INTO store_products (
                        id, name, category, sub_category, specification, price, sold_count,
                        stock, image, description, is_hot, is_featured
                    ) VALUES (
                        :id, :name, :category, :sub_category, :specification, :price, :sold_count,
                        :stock, :image, :description, :is_hot, :is_featured
                    )
                    """,
                    STORE_PRODUCTS_SEED,
                )
                conn.executemany(
                    "INSERT INTO pest_entries (id, name, intro, treatment) VALUES (:id, :name, :intro, :treatment)",
                    ALL_PEST_ENTRIES,
                )
                conn.execute(
                    """
                    INSERT OR REPLACE INTO app_meta (meta_key, meta_value)
                    VALUES ('store_catalog_version', ?)
                    """,
                    (STORE_CATALOG_VERSION,),
                )
            conn.execute("UPDATE store_products SET sold_count = 0")
            conn.execute("UPDATE store_products SET category = '精选好物', sub_category = '精选' WHERE id IN (2001, 2002, 2003, 2004, 2005)")
            conn.execute("UPDATE store_products SET category = '热销榜单', sub_category = '热销' WHERE id IN (2101, 2102, 2103, 2104, 2105)")
            conn.execute("UPDATE store_products SET category = '肥料', sub_category = '肥料' WHERE id IN (2201, 2202, 2203, 2204, 2205, 2206)")
            conn.execute("UPDATE store_products SET category = '杀虫剂', sub_category = '杀虫剂' WHERE id IN (2301, 2302, 2303, 2304, 2305, 2306)")
            conn.execute("UPDATE store_products SET category = '商城首页', sub_category = '广告' WHERE id = 2401")
            conn.execute("UPDATE store_products SET category = '热销榜单', sub_category = '热销榜单' WHERE id IN (2402, 2403, 2404, 2405)")
            conn.execute("UPDATE store_products SET category = '肥料', sub_category = '肥料推荐' WHERE id IN (2406, 2407)")
            conn.execute("UPDATE store_products SET category = '杀虫剂', sub_category = '杀虫剂推荐' WHERE id IN (2408, 2409)")
            conn.commit()

    @staticmethod
    def _row_to_product(row):
        return {
            "id": row["id"],
            "name": row["name"],
            "category": row["category"],
            "sub_category": row["sub_category"] or "",
            "specification": row["specification"],
            "price": float(row["price"]),
            "sold_count": int(row["sold_count"]),
            "stock": int(row["stock"]),
            "image": row["image"] or "",
            "description": row["description"] or "",
            "is_hot": bool(row["is_hot"]),
            "is_featured": bool(row["is_featured"]),
        }

    @staticmethod
    def _normalize_product_name(name):
        if not name:
            return ""
        aliases = {
            "高效氯氟氰菊酯": "高效氯氟氰菊酯",
            "吡虫啉": "吡虫啉",
            "阿维菌素": "阿维菌素",
            "硫酸钾复合肥": "硫酸钾复合肥",
        }
        return aliases.get(name, name)

    def _canonicalize_row(self, conn, row):
        if not row:
            return None
        name = row["name"]
        canonical = conn.execute(
            """
            SELECT *
            FROM store_products
            WHERE name = ?
            ORDER BY CASE WHEN category = '商城首页' THEN 1 ELSE 0 END, sold_count DESC, id
            LIMIT 1
            """,
            (name,),
        ).fetchone()
        return canonical or row

    def get_products_by_tab(self, tab_name):
        with self._connect() as conn:
            rows = conn.execute(
                "SELECT * FROM store_products WHERE category = ? ORDER BY id",
                (tab_name,),
            ).fetchall()
        seen = set()
        products = []
        with self._connect() as conn:
            for row in rows:
                product = self._row_to_product(self._canonicalize_row(conn, row))
                key = self._normalize_product_name(product["name"])
                if key in seen:
                    continue
                seen.add(key)
                products.append(product)
        return products

    def get_product(self, product_id):
        with self._connect() as conn:
            row = conn.execute(
                "SELECT * FROM store_products WHERE id = ?",
                (product_id,),
            ).fetchone()
            row = self._canonicalize_row(conn, row)
        return self._row_to_product(row) if row else None

    def increment_sold_count(self, product_id):
        with self._connect() as conn:
            row = conn.execute(
                "SELECT * FROM store_products WHERE id = ?",
                (product_id,),
            ).fetchone()
            row = self._canonicalize_row(conn, row)
            if not row:
                return None
            conn.execute(
                "UPDATE store_products SET sold_count = sold_count + 1 WHERE id = ?",
                (row["id"],),
            )
            conn.commit()
        return self.get_product(row["id"])

    def is_favorite(self, product_id):
        app = App.get_running_app()
        username = app.current_user["username"] if app and app.current_user else ""
        if not username:
            return False
        with self._connect() as conn:
            row = conn.execute(
                "SELECT * FROM store_products WHERE id = ?",
                (product_id,),
            ).fetchone()
            row = self._canonicalize_row(conn, row)
            canonical_id = row["id"] if row else product_id
            row = conn.execute(
                "SELECT 1 FROM store_favorites WHERE username = ? AND product_id = ?",
                (username, canonical_id),
            ).fetchone()
        return bool(row)

    def toggle_favorite(self, product_id):
        app = App.get_running_app()
        username = app.current_user["username"] if app and app.current_user else ""
        if not username:
            return False
        with self._connect() as conn:
            row = conn.execute(
                "SELECT * FROM store_products WHERE id = ?",
                (product_id,),
            ).fetchone()
            row = self._canonicalize_row(conn, row)
            canonical_id = row["id"] if row else product_id
            existing = conn.execute(
                "SELECT 1 FROM store_favorites WHERE username = ? AND product_id = ?",
                (username, canonical_id),
            ).fetchone()
            if existing:
                conn.execute("DELETE FROM store_favorites WHERE username = ? AND product_id = ?",
                             (username, canonical_id))
                conn.commit()
                return False
            conn.execute("INSERT OR REPLACE INTO store_favorites (username, product_id) VALUES (?, ?)",
                         (username, canonical_id))
            conn.commit()
            return True

    def get_comments(self, product_id):
        with self._connect() as conn:
            rows = conn.execute(
                """
                SELECT username, comment, comment_date
                FROM store_comments
                WHERE product_id = ?
                ORDER BY id DESC
                """,
                (product_id,),
            ).fetchall()
        return [
            {
                "username": row["username"],
                "comment": row["comment"],
                "comment_date": row["comment_date"],
            }
            for row in rows
        ]

    def add_comment(self, product_id, comment_text, username=DEFAULT_COMMENT_USER):
        today = datetime.now().strftime("%Y-%m-%d")
        created_at = datetime.now().isoformat()
        with self._connect() as conn:
            conn.execute(
                """
                INSERT INTO store_comments (product_id, username, comment, comment_date, created_at)
                VALUES (?, ?, ?, ?, ?)
                """,
                (product_id, username, comment_text, today, created_at),
            )
            conn.commit()
        return {
            "username": username,
            "comment": comment_text,
            "comment_date": today,
        }

    def get_favorite_products(self, username):
        with self._connect() as conn:
            rows = conn.execute(
                """
                SELECT p.*
                FROM store_products p
                INNER JOIN store_favorites f ON p.id = f.product_id
                WHERE f.username = ?
                ORDER BY p.id
                """,
                (username,),
            ).fetchall()
            seen = set()
            products = []
            for row in rows:
                product = self._row_to_product(self._canonicalize_row(conn, row))
                key = self._normalize_product_name(product["name"])
                if key in seen:
                    continue
                seen.add(key)
                products.append(product)
        return products

    def get_products_by_ids(self, product_ids):
        if not product_ids:
            return []
        placeholders = ",".join("?" for _ in product_ids)
        with self._connect() as conn:
            rows = conn.execute(
                f"SELECT * FROM store_products WHERE id IN ({placeholders}) ORDER BY id",
                tuple(product_ids),
            ).fetchall()
            seen = set()
            products = []
            for row in rows:
                product = self._row_to_product(self._canonicalize_row(conn, row))
                key = self._normalize_product_name(product["name"])
                if key in seen:
                    continue
                seen.add(key)
                products.append(product)
        return products

    def search_products(self, keyword):
        with self._connect() as conn:
            rows = conn.execute(
                "SELECT * FROM store_products WHERE name LIKE ? ORDER BY id",
                (f"%{keyword}%",),
            ).fetchall()
            seen = set()
            products = []
            for row in rows:
                product = self._row_to_product(self._canonicalize_row(conn, row))
                key = self._normalize_product_name(product["name"])
                if key in seen:
                    continue
                seen.add(key)
                products.append(product)
        return products

    def get_products_for_home(self, sub_category):
        with self._connect() as conn:
            rows = conn.execute(
                "SELECT * FROM store_products WHERE sub_category = ? ORDER BY id",
                (sub_category,),
            ).fetchall()
            seen = set()
            products = []
            for row in rows:
                product = self._row_to_product(self._canonicalize_row(conn, row))
                key = self._normalize_product_name(product["name"])
                if key in seen:
                    continue
                seen.add(key)
                products.append(product)
        return products

    def toggle_post_like(self, username, post_id):
        if not username:
            return False
        with self._connect() as conn:
            row = conn.execute(
                "SELECT 1 FROM community_likes WHERE username = ? AND post_id = ?",
                (username, post_id),
            ).fetchone()
            if row:
                conn.execute("DELETE FROM community_likes WHERE username = ? AND post_id = ?", (username, post_id))
                conn.commit()
                return False
            conn.execute("INSERT INTO community_likes (username, post_id) VALUES (?, ?)", (username, post_id))
            conn.commit()
            return True

    def has_liked_post(self, username, post_id):
        if not username:
            return False
        with self._connect() as conn:
            row = conn.execute(
                "SELECT 1 FROM community_likes WHERE username = ? AND post_id = ?",
                (username, post_id),
            ).fetchone()
        return bool(row)

    def get_post_like_count(self, post_id):
        with self._connect() as conn:
            row = conn.execute(
                "SELECT COUNT(*) AS count FROM community_likes WHERE post_id = ?",
                (post_id,),
            ).fetchone()
        return int(row["count"]) if row else 0

    def increment_post_view(self, post_key):
        with self._connect() as conn:
            conn.execute(
                """
                INSERT INTO community_post_stats (post_key, view_count)
                VALUES (?, 1)
                ON CONFLICT(post_key) DO UPDATE SET view_count = view_count + 1
                """,
                (post_key,),
            )
            conn.commit()
            row = conn.execute(
                "SELECT view_count FROM community_post_stats WHERE post_key = ?",
                (post_key,),
            ).fetchone()
        return int(row["view_count"]) if row else 0

    def get_post_view_count(self, post_key):
        with self._connect() as conn:
            row = conn.execute(
                "SELECT view_count FROM community_post_stats WHERE post_key = ?",
                (post_key,),
            ).fetchone()
        return int(row["view_count"]) if row else 0

    def get_post_comments(self, post_key):
        with self._connect() as conn:
            rows = conn.execute(
                """
                SELECT username, comment, comment_date
                FROM community_comments
                WHERE post_key = ?
                ORDER BY id DESC
                """,
                (post_key,),
            ).fetchall()
        return [
            {
                "username": row["username"],
                "comment": row["comment"],
                "comment_date": row["comment_date"],
            }
            for row in rows
        ]

    def add_post_comment(self, post_key, comment_text, username):
        today = datetime.now().strftime("%Y-%m-%d")
        created_at = datetime.now().isoformat()
        with self._connect() as conn:
            conn.execute(
                """
                INSERT INTO community_comments (post_key, username, comment, comment_date, created_at)
                VALUES (?, ?, ?, ?, ?)
                """,
                (post_key, username, comment_text, today, created_at),
            )
            conn.commit()
        return {
            "username": username,
            "comment": comment_text,
            "comment_date": today,
        }

    def add_order(self, username, product_id):
        order_dt = datetime.now()
        delivery_dt = order_dt.replace(hour=0, minute=0, second=0, microsecond=0)
        from datetime import timedelta
        delivery_dt = delivery_dt + timedelta(days=3)
        order_date = order_dt.strftime("%Y-%m-%d")
        delivery_date = delivery_dt.strftime("%Y-%m-%d")
        created_at = order_dt.isoformat()
        with self._connect() as conn:
            conn.execute(
                """
                INSERT INTO store_orders (username, product_id, order_date, delivery_date, created_at)
                VALUES (?, ?, ?, ?, ?)
                """,
                (username, product_id, order_date, delivery_date, created_at),
            )
            conn.commit()

    def get_orders(self, username):
        with self._connect() as conn:
            rows = conn.execute(
                """
                SELECT o.id, o.product_id, o.order_date, o.delivery_date, o.created_at, p.*
                FROM store_orders o
                INNER JOIN store_products p ON p.id = o.product_id
                WHERE o.username = ?
                ORDER BY o.created_at DESC, o.id DESC
                """,
                (username,),
            ).fetchall()
        orders = []
        for row in rows:
            product = self._row_to_product(row)
            orders.append(
                {
                    "id": row["id"],
                    "product_id": product["id"],
                    "name": product["name"],
                    "specification": product["specification"],
                    "price": product["price"],
                    "order_date": row["order_date"],
                    "delivery_date": row["delivery_date"],
                    "created_at": row["created_at"],
                }
            )
        return orders

    def get_pest_entries(self):
        with self._connect() as conn:
            rows = conn.execute("SELECT * FROM pest_entries ORDER BY id").fetchall()
        return [dict(row) for row in rows]

    def get_pest_entry(self, pest_id):
        with self._connect() as conn:
            row = conn.execute("SELECT * FROM pest_entries WHERE id = ?", (pest_id,)).fetchone()
        return dict(row) if row else None


STORE_DB = StoreDatabase()


class ProductRow(RecycleDataViewBehavior, ButtonBehavior, BoxLayout):
    product_id = NumericProperty(0)
    name_text = StringProperty("")
    specification_text = StringProperty("")
    price_text = StringProperty("")
    sold_text = StringProperty("")
    from_tab_text = StringProperty("")
    return_screen_name = StringProperty("store_category")
    screen_ref = ObjectProperty(None, allownone=True)

    def __init__(self, **kwargs):
        super().__init__(orientation="horizontal", spacing=dp(12), padding=(dp(14), dp(10)), **kwargs)
        self.size_hint_y = None
        self.height = dp(116)
        self.bind(pos=self._update_canvas, size=self._update_canvas)
        self._build_ui()

    def _build_ui(self):
        self.thumb_wrap = FloatLayout(size_hint=(None, None), size=(dp(80), dp(80)))
        self.thumb = GrayPlaceholder(size_hint=(1, 1))
        self.thumb_wrap.add_widget(self.thumb)
        self.add_widget(self.thumb_wrap)

        self.info_box = BoxLayout(orientation="vertical", spacing=0, size_hint=(1, 1), padding=(0, dp(8), 0, dp(10)))
        self.info_box.canvas.before.clear()
        self.name_label = Label(
            text="",
            color=(0.1, 0.1, 0.1, 1),
            halign="left",
            valign="top",
            font_size=sp(17),
            size_hint=(1, None),
            height=dp(50),
            **text_style(),
        )
        self.name_label.bind(size=self.name_label.setter("text_size"))
        self.info_box.add_widget(self.name_label)
        self.info_box.add_widget(Widget(size_hint=(1, None), height=dp(10)))

        self.meta_label = Label(
            text="",
            color=(0.42, 0.42, 0.42, 1),
            halign="left",
            valign="middle",
            font_size=sp(13),
            size_hint=(1, None),
            height=dp(22),
            **text_style(),
        )
        self.meta_label.bind(size=self.meta_label.setter("text_size"))
        self.info_box.add_widget(self.meta_label)
        self.add_widget(self.info_box)

        self.right_box = BoxLayout(
            orientation="vertical",
            spacing=dp(8),
            size_hint=(None, 1),
            width=dp(92),
            padding=(0, dp(12), 0, dp(12)),
        )
        self.right_box.canvas.before.clear()
        self.price_label = Label(
            text="",
            color=(0.88, 0.32, 0.18, 1),
            halign="right",
            valign="middle",
            font_size=sp(16),
            bold=True,
            size_hint=(1, None),
            height=dp(28),
            **text_style(),
        )
        self.price_label.bind(size=self.price_label.setter("text_size"))
        self.right_box.add_widget(self.price_label)

        self.sold_label = Label(
            text="",
            color=(0.45, 0.45, 0.45, 1),
            halign="right",
            valign="middle",
            font_size=sp(12),
            size_hint=(1, None),
            height=dp(22),
            **text_style(),
        )
        self.sold_label.bind(size=self.sold_label.setter("text_size"))
        self.right_box.add_widget(self.sold_label)
        self.add_widget(self.right_box)
        self.refresh_view()

    def _update_canvas(self, *_args):
        self.canvas.before.clear()
        self.canvas.after.clear()
        with self.canvas.after:
            Color(0.90, 0.90, 0.90, 1)
            Line(points=[self.x, self.y, self.right, self.y], width=1)

    def refresh_view(self):
        self.name_label.text = self.name_text
        self.meta_label.text = self.specification_text
        self.price_label.text = self.price_text
        self.sold_label.text = self.sold_text

    def refresh_view_attrs(self, rv, index, data):
        result = super().refresh_view_attrs(rv, index, data)
        Clock.schedule_once(lambda dt: self.refresh_view(), 0)
        return result

    def on_release(self):
        try:
            app = App.get_running_app()
            if app and hasattr(app, "open_product_detail_screen") and self.product_id:
                app.open_product_detail_screen(
                    self.product_id,
                    from_tab=self.from_tab_text or "精选好物",
                    return_screen=self.return_screen_name or "store_category",
                )
                return
            if self.screen_ref and hasattr(self.screen_ref, "open_product_detail"):
                self.screen_ref.open_product_detail(self.product_id)
        except Exception as exc:
            show_toast(f"打开商品失败: {exc}")


Factory.register("ProductRow", cls=ProductRow)


class IconStat(ButtonBehavior, BoxLayout):
    def __init__(self, icon_text="", icon_source="", title="", value="", **kwargs):
        super().__init__(orientation="vertical", spacing=dp(4), **kwargs)
        self.size_hint = (1, 1)
        if icon_source and os.path.exists(icon_source):
            self.icon_widget = Image(
                source=icon_source,
                size_hint=(1, None),
                height=dp(34),
                allow_stretch=True,
                keep_ratio=True,
            )
        else:
            self.icon_widget = Label(
                text=icon_text,
                font_size=sp(24),
                color=GREEN,
                size_hint=(1, None),
                height=dp(28),
                halign="center",
                valign="middle",
                **text_style(),
            )
            self.icon_widget.bind(size=self.icon_widget.setter("text_size"))
        self.add_widget(self.icon_widget)
        self.title_label = Label(
            text=title,
            font_size=sp(13),
            color=(0.2, 0.2, 0.2, 1),
            size_hint=(1, None),
            height=dp(22),
            halign="center",
            valign="middle",
            **text_style(),
        )
        self.title_label.bind(size=self.title_label.setter("text_size"))
        self.add_widget(self.title_label)
        self.value_label = Label(
            text=value,
            font_size=sp(12),
            color=(0.45, 0.45, 0.45, 1),
            size_hint=(1, None),
            height=dp(20),
            halign="center",
            valign="middle",
            **text_style(),
        )
        self.value_label.bind(size=self.value_label.setter("text_size"))
        self.add_widget(self.value_label)


class ToolCard(ButtonBehavior, BoxLayout):
    def __init__(self, icon_text="", icon_source="", title="", **kwargs):
        super().__init__(orientation="vertical", spacing=dp(8), padding=dp(10), **kwargs)
        self.size_hint = (1, 1)
        self.bind(pos=self._update_bg, size=self._update_bg)
        icon_source = icon_source or HOME_TOOL_ICONS.get(title, "") or COMMUNITY_FOCUS_ICONS.get(title, "")
        if icon_source and os.path.exists(icon_source):
            self.icon_widget = Image(
                source=icon_source,
                size_hint=(1, None),
                height=dp(36),
                allow_stretch=True,
                keep_ratio=True,
            )
        else:
            self.icon_widget = Label(
                text=icon_text,
                font_size=sp(26),
                color=GREEN,
                size_hint=(1, None),
                height=dp(30),
                halign="center",
                valign="middle",
                **text_style(),
            )
            self.icon_widget.bind(size=self.icon_widget.setter("text_size"))
        self.add_widget(self.icon_widget)
        self.title_label = Label(
            text=title,
            font_size=sp(13),
            color=(0.12, 0.12, 0.12, 1),
            size_hint=(1, None),
            height=dp(24),
            halign="center",
            valign="middle",
            **text_style(),
        )
        self.title_label.bind(size=self.title_label.setter("text_size"))
        self.add_widget(self.title_label)

    def _update_bg(self, *_args):
        self.canvas.before.clear()
        with self.canvas.before:
            Color(1, 1, 1, 1)
            RoundedRectangle(pos=self.pos, size=self.size, radius=[dp(14)] * 4)


class LikeImageButton(ButtonBehavior, Image):
    def __init__(self, source_off="", source_on="", liked=False, **kwargs):
        kwargs.pop("text", None)
        kwargs.pop("background_normal", None)
        kwargs.pop("background_down", None)
        kwargs.pop("background_color", None)
        kwargs.pop("color", None)
        kwargs.pop("halign", None)
        kwargs.pop("valign", None)
        kwargs.pop("font_size", None)
        kwargs.pop("border", None)
        self.source_off = source_off or LIKE_ICON_OFF
        self.source_on = source_on or LIKE_ICON_ON
        super().__init__(**kwargs)
        self.allow_stretch = True
        self.keep_ratio = True
        if not self.size_hint and not kwargs.get("size"):
            self.size = (dp(24), dp(24))
        self.set_liked(liked)

    def set_liked(self, liked):
        if liked and self.source_on and os.path.exists(self.source_on):
            self.source = self.source_on
        else:
            self.source = self.source_off


class HomeStoreItem(ButtonBehavior, BoxLayout):
    def __init__(self, product, on_open=None, **kwargs):
        super().__init__(orientation="vertical", spacing=dp(6), size_hint=(None, 1), width=dp(128),
                         padding=(0, dp(8), 0, dp(8)), **kwargs)
        self.product = product
        self.on_open = on_open
        self.thumb = GrayPlaceholder(size_hint=(1, None), height=dp(82))
        self.add_widget(self.thumb)
        self.name_label = Label(
            text=product["name"],
            font_size=sp(13),
            color=(0.12, 0.12, 0.12, 1),
            size_hint=(1, None),
            height=dp(34),
            halign="left",
            valign="top",
            **text_style(),
        )
        self.name_label.bind(size=self.name_label.setter("text_size"))
        self.add_widget(self.name_label)
        self.price_label = Label(
            text=f"￥{product['price']:.2f}",
            font_size=sp(13),
            color=(0.88, 0.34, 0.18, 1),
            size_hint=(1, None),
            height=dp(20),
            halign="left",
            valign="middle",
            **text_style(),
        )
        self.price_label.bind(size=self.price_label.setter("text_size"))
        self.add_widget(self.price_label)

    def on_release(self):
        if self.on_open:
            self.on_open(self.product["id"])


class PestListRow(ButtonBehavior, BoxLayout):
    def __init__(self, pest_data, on_open=None, **kwargs):
        super().__init__(orientation="horizontal", spacing=dp(12), padding=(dp(14), dp(10)), size_hint_y=None,
                         height=dp(96), **kwargs)
        self.pest_data = pest_data
        self.on_open = on_open
        self.bind(pos=self._update_bg, size=self._update_bg)
        self.thumb = GrayPlaceholder(size_hint=(None, None), size=(dp(76), dp(76)))
        self.add_widget(self.thumb)
        self.label = Label(
            text=pest_data["name"],
            font_size=sp(17),
            color=(0.12, 0.12, 0.12, 1),
            halign="left",
            valign="middle",
            **text_style(),
        )
        self.label.bind(size=self.label.setter("text_size"))
        self.add_widget(self.label)

    def _update_bg(self, *_args):
        self.canvas.before.clear()
        self.canvas.after.clear()
        with self.canvas.before:
            Color(1, 1, 1, 1)
            Rectangle(pos=self.pos, size=self.size)
        with self.canvas.after:
            Color(0.9, 0.9, 0.9, 1)
            Line(points=[self.x, self.y, self.right, self.y], width=1)

    def on_release(self):
        if self.on_open:
            self.on_open(self.pest_data["id"])


def open_text_popup(title, body):
    popup = Popup(title="", separator_height=0, size_hint=(0.84, None), height=dp(260))
    content = BoxLayout(orientation="vertical", spacing=dp(14), padding=dp(16))
    with content.canvas.before:
        Color(0.16, 0.16, 0.16, 0.96)
        bg_rect = RoundedRectangle(pos=content.pos, size=content.size, radius=[dp(16)] * 4)
    content.bind(pos=lambda instance, *_: _update_popup_rect(instance, bg_rect),
                 size=lambda instance, *_: _update_popup_rect(instance, bg_rect))
    title_label = Label(
        text=title,
        font_size=sp(18),
        color=(1, 1, 1, 1),
        size_hint=(1, None),
        height=dp(30),
        halign="center",
        valign="middle",
        **text_style(),
    )
    title_label.bind(size=title_label.setter("text_size"))
    content.add_widget(title_label)
    body_label = Label(
        text=body,
        font_size=sp(15),
        color=(1, 1, 1, 1),
        size_hint=(1, 1),
        halign="center",
        valign="middle",
        **text_style(),
    )
    body_label.bind(size=body_label.setter("text_size"))
    content.add_widget(body_label)
    ok_btn = RoundedButton(text="知道了", color=(1, 1, 1, 1), size_hint=(1, None), height=dp(44), **text_style())
    ok_btn.bind(on_press=lambda *_: popup.dismiss())
    content.add_widget(ok_btn)
    popup.content = content
    popup.open()
    return popup


def _update_popup_rect(instance, rect):
    rect.pos = instance.pos
    rect.size = instance.size


def is_android_permission_granted(permission_name):
    if not is_android():
        return True
    try:
        permissions_module = import_module("android.permissions")
        check_permission_func = getattr(permissions_module, "check_permission")
        return bool(check_permission_func(permission_name))
    except Exception:
        return False


def update_nav_rect(nav):
    if hasattr(nav, "bg_rect"):
        nav.bg_rect.pos = nav.pos
        nav.bg_rect.size = nav.size


class BaseScreen(Screen):
    def setup_background(self, image_source):
        self.layout = FloatLayout()
        self.add_widget(self.layout)
        self.background = Image(
            source=image_source,
            allow_stretch=True,
            keep_ratio=False,
            size_hint=(1, 1),
            pos_hint={"x": 0, "y": 0},
        )
        self.layout.add_widget(self.background)

    def is_in_relative_area(self, x, y, rel_area):
        rel_x1, rel_y1, rel_x2, rel_y2 = rel_area
        width = self.width or Window.width
        height = self.height or Window.height
        return rel_x1 * width <= x <= rel_x2 * width and rel_y1 * height <= y <= rel_y2 * height

    def get_relative_pos(self, x, y):
        width = self.width or Window.width
        height = self.height or Window.height
        if width <= 0 or height <= 0:
            return 0, 0
        return x / width, y / height

    def open_camera(self):
        app = App.get_running_app()
        app.previous_before_camera = self.name
        app.camera_mode = "recognize"
        self.manager.current = "camera"

    def open_capture_menu(self, after_action=None):
        app = App.get_running_app()
        if not hasattr(app, "show_capture_menu"):
            return
        app.show_capture_menu(after_action=after_action)


class LoginScreen(Screen):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.name = "login"
        self.build_ui()

    def build_ui(self):
        self.layout = FloatLayout()
        self.add_widget(self.layout)

        with self.layout.canvas.before:
            Color(1, 1, 1, 1)
            self.bg_rect = Rectangle(pos=self.layout.pos, size=self.layout.size)
        self.layout.bind(pos=self._update_bg, size=self._update_bg)

        self.title_label = Label(
            text="欢迎使用农智慧眼APP，请登录",
            color=GREEN,
            font_size=sp(22),
            size_hint=(0.86, None),
            height=dp(40),
            pos_hint={"center_x": 0.5, "top": 0.82},
            halign="center",
            valign="middle",
            **text_style(),
        )
        self.title_label.bind(size=self.title_label.setter("text_size"))
        self.layout.add_widget(self.title_label)

        self.username_input = TextInput(
            hint_text="请输入用户名",
            multiline=False,
            size_hint=(0.84, None),
            height=dp(52),
            pos_hint={"center_x": 0.5, "top": 0.70},
            background_normal="",
            background_active="",
            background_color=(0.94, 0.94, 0.94, 1),
            padding=(dp(14), dp(14), dp(14), dp(14)),
            font_size=sp(15),
            input_type="text",
            **text_style(),
        )
        self.layout.add_widget(self.username_input)

        self.password_input = TextInput(
            hint_text="请输入密码",
            multiline=False,
            password=True,
            size_hint=(0.84, None),
            height=dp(52),
            pos_hint={"center_x": 0.5, "top": 0.61},
            background_normal="",
            background_active="",
            background_color=(0.94, 0.94, 0.94, 1),
            padding=(dp(14), dp(14), dp(14), dp(14)),
            font_size=sp(15),
            input_type="text",
            keyboard_suggestions=False,
            **text_style(),
        )
        self.layout.add_widget(self.password_input)

        self.login_btn = RoundedButton(
            text="登录",
            color=(1, 1, 1, 1),
            font_size=sp(18),
            size_hint=(0.84, None),
            height=dp(52),
            pos_hint={"center_x": 0.5, "top": 0.51},
            **text_style(),
        )
        self.login_btn.bind(on_press=self.login)
        self.layout.add_widget(self.login_btn)

        self.register_link = UnderlineLabel(
            text="[u]没有账户？注册一个！[/u]",
            color=GREEN,
            font_size=sp(14),
            size_hint=(None, None),
            size=(dp(180), dp(28)),
            pos_hint={"center_x": 0.5, "y": 0.04},
            halign="center",
            valign="middle",
            **text_style(),
        )
        self.register_link.bind(size=self.register_link.setter("text_size"))
        self.register_link.bind(on_press=self.open_register)
        self.layout.add_widget(self.register_link)

    def _update_bg(self, *_args):
        self.bg_rect.pos = self.layout.pos
        self.bg_rect.size = self.layout.size

    def on_leave(self, *args):
        self.username_input.text = ""
        self.password_input.text = ""
        return super().on_leave(*args)

    def open_register(self, _instance=None):
        self.manager.current = "register"

    def login(self, _instance=None):
        username = self.username_input.text.strip()
        password = self.password_input.text
        if not username or not password:
            show_toast("请输入用户名和密码")
            return
        user = USER_DB.authenticate_user(username, password)
        if not user:
            show_toast("用户名或密码错误，请重试")
            return
        app = App.get_running_app()
        app.set_current_user(user)
        self.manager.current = "home"


class RegisterScreen(Screen):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.name = "register"
        self.selected_avatar_source = ""
        self.selected_role = "free"
        self.build_ui()

    def build_ui(self):
        self.layout = FloatLayout()
        self.add_widget(self.layout)

        with self.layout.canvas.before:
            Color(1, 1, 1, 1)
            self.bg_rect = Rectangle(pos=self.layout.pos, size=self.layout.size)
        self.layout.bind(pos=self._update_bg, size=self._update_bg)

        self.top_bar = FloatLayout(size_hint=(1, None), height=dp(92), pos_hint={"x": 0, "top": 1})
        with self.top_bar.canvas.before:
            Color(*GREEN)
            self.top_bar_rect = Rectangle(pos=self.top_bar.pos, size=self.top_bar.size)
        self.top_bar.bind(pos=self._update_top_bar, size=self._update_top_bar)
        self.layout.add_widget(self.top_bar)

        self.back_btn = IconButton(
            text="<",
            font_size=sp(34),
            color=(0, 0, 0, 1),
            size_hint=(None, None),
            size=(dp(56), dp(56)),
            pos_hint={"x": 0.03, "center_y": 0.42},
            **text_style(),
        )
        self.back_btn.bind(on_press=lambda *_: setattr(self.manager, "current", "login"))
        self.top_bar.add_widget(self.back_btn)

        self.top_title = Label(
            text="注册新账号",
            color=(1, 1, 1, 1),
            font_size=sp(20),
            size_hint=(0.5, None),
            height=dp(34),
            pos_hint={"center_x": 0.52, "center_y": 0.42},
            halign="center",
            valign="middle",
            **text_style(),
        )
        self.top_title.bind(size=self.top_title.setter("text_size"))
        self.top_bar.add_widget(self.top_title)

        self.avatar_preview = GrayPlaceholder(
            radius=1,
            size_hint=(None, None),
            size=(dp(112), dp(112)),
            pos_hint={"center_x": 0.5, "top": 0.82},
        )
        self.layout.add_widget(self.avatar_preview)

        self.avatar_image = CircleImage(
            source="",
            size_hint=(None, None),
            size=(dp(112), dp(112)),
            pos_hint={"center_x": 0.5, "top": 0.82},
        )

        self.avatar_link = UnderlineLabel(
            text="[u]点击选头像框[/u]",
            color=GREEN,
            font_size=sp(14),
            size_hint=(None, None),
            size=(dp(140), dp(28)),
            pos_hint={"center_x": 0.5, "top": 0.66},
            halign="center",
            valign="middle",
            **text_style(),
        )
        self.avatar_link.bind(size=self.avatar_link.setter("text_size"))
        self.avatar_link.bind(on_press=self.show_avatar_menu)
        self.layout.add_widget(self.avatar_link)

        self.username_input = TextInput(
            hint_text="请输入用户名",
            multiline=False,
            size_hint=(0.84, None),
            height=dp(52),
            pos_hint={"center_x": 0.5, "top": 0.58},
            background_normal="",
            background_active="",
            background_color=(0.94, 0.94, 0.94, 1),
            padding=(dp(14), dp(14), dp(14), dp(14)),
            font_size=sp(15),
            input_type="text",
            **text_style(),
        )
        self.layout.add_widget(self.username_input)

        self.password_input = TextInput(
            hint_text="请输入密码",
            multiline=False,
            password=True,
            size_hint=(0.84, None),
            height=dp(52),
            pos_hint={"center_x": 0.5, "top": 0.49},
            background_normal="",
            background_active="",
            background_color=(0.94, 0.94, 0.94, 1),
            padding=(dp(14), dp(14), dp(14), dp(14)),
            font_size=sp(15),
            input_type="text",
            keyboard_suggestions=False,
            **text_style(),
        )
        self.layout.add_widget(self.password_input)

        self.role_box = BoxLayout(
            orientation="horizontal",
            spacing=dp(18),
            size_hint=(0.84, None),
            height=dp(44),
            pos_hint={"center_x": 0.5, "top": 0.40},
        )
        self.layout.add_widget(self.role_box)

        self.free_toggle = ToggleButton(
            text="免费",
            group="role_group",
            state="down",
            background_normal="",
            background_down="",
            background_color=(0.92, 0.92, 0.92, 1),
            color=(0.1, 0.1, 0.1, 1),
            **text_style(),
        )
        self.free_toggle.bind(on_press=lambda *_: self._set_role("free"))
        self.role_box.add_widget(self.free_toggle)

        self.vip_toggle = ToggleButton(
            text="VIP（399元/年）",
            group="role_group",
            background_normal="",
            background_down="",
            background_color=(0.92, 0.92, 0.92, 1),
            color=(0.1, 0.1, 0.1, 1),
            **text_style(),
        )
        self.vip_toggle.bind(on_press=lambda *_: self._set_role("vip"))
        self.role_box.add_widget(self.vip_toggle)

        self.confirm_btn = RoundedButton(
            text="确定",
            color=(1, 1, 1, 1),
            font_size=sp(18),
            size_hint=(0.84, None),
            height=dp(52),
            pos_hint={"center_x": 0.5, "top": 0.30},
            **text_style(),
        )
        self.confirm_btn.bind(on_press=self.submit_register)
        self.layout.add_widget(self.confirm_btn)

    def _update_bg(self, *_args):
        self.bg_rect.pos = self.layout.pos
        self.bg_rect.size = self.layout.size

    def _update_top_bar(self, *_args):
        self.top_bar_rect.pos = self.top_bar.pos
        self.top_bar_rect.size = self.top_bar.size

    def _set_role(self, role_name):
        self.selected_role = role_name
        if role_name == "free":
            self.free_toggle.state = "down"
            self.vip_toggle.state = "normal"
            self.free_toggle.background_color = (0.68, 0.88, 0.68, 1)
            self.vip_toggle.background_color = (0.92, 0.92, 0.92, 1)
        else:
            self.free_toggle.state = "normal"
            self.vip_toggle.state = "down"
            self.free_toggle.background_color = (0.92, 0.92, 0.92, 1)
            self.vip_toggle.background_color = (0.68, 0.88, 0.68, 1)

    def _show_selected_avatar(self):
        if self.selected_avatar_source and os.path.exists(self.selected_avatar_source):
            if self.avatar_preview.parent:
                self.layout.remove_widget(self.avatar_preview)
            self.avatar_image.source = self.selected_avatar_source
            self.avatar_image.reload()
            if self.avatar_image.parent is None:
                self.layout.add_widget(self.avatar_image)
        else:
            if self.avatar_image.parent:
                self.layout.remove_widget(self.avatar_image)
            if self.avatar_preview.parent is None:
                self.layout.add_widget(self.avatar_preview)

    def show_avatar_menu(self, _instance=None):
        popup = Popup(
            title="",
            separator_height=0,
            size_hint=(0.82, None),
            height=dp(220),
        )
        content = BoxLayout(orientation="vertical", spacing=dp(12), padding=dp(14))
        with content.canvas.before:
            Color(0.16, 0.16, 0.16, 0.96)
            bg_rect = RoundedRectangle(pos=content.pos, size=content.size, radius=[dp(16)] * 4)
        content.bind(pos=lambda instance, *_: _update_popup_rect(instance, bg_rect),
                     size=lambda instance, *_: _update_popup_rect(instance, bg_rect))
        title_label = Label(
            text="选择头像",
            color=(1, 1, 1, 1),
            font_size=sp(18),
            size_hint=(1, None),
            height=dp(28),
            halign="center",
            valign="middle",
            **text_style(),
        )
        title_label.bind(size=title_label.setter("text_size"))
        content.add_widget(title_label)
        use_camera_btn = RoundedButton(text="使用相机", color=(1, 1, 1, 1), size_hint=(1, None), height=dp(44),
                                       **text_style())
        use_album_btn = RoundedButton(text="使用照片", color=(1, 1, 1, 1), size_hint=(1, None), height=dp(44),
                                      **text_style())
        cancel_btn = RoundedButton(text="取消", color=(1, 1, 1, 1), size_hint=(1, None), height=dp(44),
                                   fill_color=(0.65, 0.65, 0.65, 1), **text_style())
        use_camera_btn.bind(on_press=lambda *_: self._use_camera_for_avatar(popup))
        use_album_btn.bind(on_press=lambda *_: self._open_file_picker(popup))
        cancel_btn.bind(on_press=lambda *_: popup.dismiss())
        content.add_widget(use_camera_btn)
        content.add_widget(use_album_btn)
        content.add_widget(cancel_btn)
        popup.content = content
        popup.open()

    def _use_camera_for_avatar(self, popup):
        popup.dismiss()
        app = App.get_running_app()
        app.previous_before_camera = "register"
        app.camera_mode = "avatar"
        self.manager.current = "camera"

    def _open_file_picker(self, popup):
        popup.dismiss()
        App.get_running_app()._open_photo_from_menu(
            popup=None,
            after_action=lambda _mode, image_path: self._set_avatar_from_file(image_path),
        )

    def _set_avatar_from_file(self, image_path):
        self.selected_avatar_source = image_path
        self._show_selected_avatar()

    def _validate_register_form(self):
        username = self.username_input.text.strip()
        password = self.password_input.text
        if not username or not password:
            show_toast("请输入用户名和密码")
            return None, None
        if USER_DB.username_exists(username):
            show_toast("用户名已存在，请更换用户名")
            return None, None
        return username, password

    def submit_register(self, _instance=None):
        username, password = self._validate_register_form()
        if not username:
            return
        self.selected_role = "vip" if self.vip_toggle.state == "down" else "free"
        if self.selected_role == "vip":
            self._confirm_vip_register(username, password)
            return
        self._create_account(username, password, "free")

    def _confirm_vip_register(self, username, password):
        popup = Popup(
            title="",
            separator_height=0,
            size_hint=(0.82, None),
            height=dp(220),
        )
        content = BoxLayout(orientation="vertical", spacing=dp(16), padding=dp(16))
        with content.canvas.before:
            Color(0.16, 0.16, 0.16, 0.96)
            bg_rect = RoundedRectangle(pos=content.pos, size=content.size, radius=[dp(16)] * 4)
        content.bind(pos=lambda instance, *_: _update_popup_rect(instance, bg_rect),
                     size=lambda instance, *_: _update_popup_rect(instance, bg_rect))
        title_label = Label(
            text="确认注册VIP",
            color=(1, 1, 1, 1),
            font_size=sp(18),
            size_hint=(1, None),
            height=dp(28),
            halign="center",
            valign="middle",
            **text_style(),
        )
        title_label.bind(size=title_label.setter("text_size"))
        label = Label(
            text="您已选择VIP服务，需付费399元/年",
            color=(1, 1, 1, 1),
            halign="center",
            valign="middle",
            **text_style(),
        )
        label.bind(size=label.setter("text_size"))
        content.add_widget(title_label)
        content.add_widget(label)
        button_bar = BoxLayout(size_hint=(1, None), height=dp(46), spacing=dp(12))
        ok_btn = RoundedButton(text="确定", color=(1, 1, 1, 1), **text_style())
        cancel_btn = RoundedButton(text="取消", color=(1, 1, 1, 1), fill_color=(0.65, 0.65, 0.65, 1), **text_style())
        ok_btn.bind(on_press=lambda *_: self._confirm_register_and_close(popup, username, password))
        cancel_btn.bind(on_press=lambda *_: popup.dismiss())
        button_bar.add_widget(ok_btn)
        button_bar.add_widget(cancel_btn)
        content.add_widget(button_bar)
        popup.content = content
        popup.open()

    def _confirm_register_and_close(self, popup, username, password):
        popup.dismiss()
        self._create_account(username, password, "vip")

    def _create_account(self, username, password, role):
        avatar_path = save_avatar_image(self.selected_avatar_source, username) if self.selected_avatar_source else ""
        USER_DB.create_user(username, password, role, avatar_path)
        show_toast("注册成功")
        self.clear_form()
        self.manager.current = "login"

    def clear_form(self):
        self.username_input.text = ""
        self.password_input.text = ""
        self.selected_avatar_source = ""
        self.selected_role = None
        self.free_toggle.state = "normal"
        self.vip_toggle.state = "normal"
        self.free_toggle.background_color = (0.92, 0.92, 0.92, 1)
        self.vip_toggle.background_color = (0.92, 0.92, 0.92, 1)
        self._show_selected_avatar()

    def on_leave(self, *args):
        self.clear_form()
        return super().on_leave(*args)


class HomeScreen(Screen):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.name = "home"
        self.build_ui()

    def build_ui(self):
        self.layout = FloatLayout()
        self.add_widget(self.layout)
        with self.layout.canvas.before:
            Color(0.96, 0.98, 0.96, 1)
            self.bg_rect = Rectangle(pos=self.layout.pos, size=self.layout.size)
        self.layout.bind(pos=self._update_bg, size=self._update_bg)

        self.search_bar = self._build_search_bar()
        self.layout.add_widget(self.search_bar)
        self.search_bar.size_hint = (1, None)
        self.search_bar.pos_hint = {"x": 0, "top": 0.985}
        self.search_bar.z = 1000

        self.content_scroll = ScrollView(size_hint=(1, None), do_scroll_x=False, pos_hint={"x": 0, "y": 0.12})
        self.layout.add_widget(self.content_scroll)
        self.content_box = BoxLayout(orientation="vertical", spacing=dp(14), padding=(dp(14), dp(18), dp(14), dp(18)),
                                     size_hint=(1, None))
        self.content_box.bind(minimum_height=self.content_box.setter("height"))
        self.content_scroll.add_widget(self.content_box)

        self.weather_card = BoxLayout(orientation="vertical", spacing=dp(6), padding=dp(14), size_hint=(1, None),
                                      height=dp(116))
        self.weather_card.bind(pos=self._paint_card, size=self._paint_card)
        self.content_box.add_widget(self.weather_card)
        weather_title = Label(text="广州  24°  晴", font_size=sp(24), color=GREEN, size_hint=(1, None), height=dp(34),
                              halign="left", valign="middle", **text_style())
        weather_title.bind(size=weather_title.setter("text_size"))
        self.weather_card.add_widget(weather_title)
        weather_sub = Label(text="最高26° 最低21°，比昨天低2°", font_size=sp(14), color=(0.28, 0.28, 0.28, 1),
                            size_hint=(1, None), height=dp(24), halign="left", valign="middle", **text_style())
        weather_sub.bind(size=weather_sub.setter("text_size"))
        self.weather_card.add_widget(weather_sub)
        warning_btn = RoundedButton(text="气象预警", color=(1, 1, 1, 1), size_hint=(None, None), size=(dp(110), dp(38)),
                                    **text_style())
        warning_btn.bind(on_press=lambda *_: open_text_popup("气象预警", "气象台发布暴雨蓝色预警"))
        self.weather_card.add_widget(warning_btn)

        reminder_header = BoxLayout(size_hint=(1, None), height=dp(28))
        reminder_title = Label(text="今日提醒", font_size=sp(18), color=(0.12, 0.12, 0.12, 1), halign="left",
                               valign="middle", **text_style())
        reminder_title.bind(size=reminder_title.setter("text_size"))
        reminder_header.add_widget(reminder_title)
        view_all = UnderlineLabel(text="[u]查看全部[/u]", color=GREEN, font_size=sp(13), size_hint=(None, 1),
                                  width=dp(80), halign="right", valign="middle", **text_style())
        view_all.bind(size=view_all.setter("text_size"))
        view_all.bind(on_press=lambda *_: open_text_popup("更多提醒", "\n".join(HOME_REMINDERS)))
        reminder_header.add_widget(view_all)
        self.content_box.add_widget(reminder_header)

        reminder_box = BoxLayout(orientation="vertical", spacing=dp(8), padding=dp(12), size_hint=(1, None),
                                 height=dp(132))
        reminder_box.bind(pos=self._paint_card, size=self._paint_card)
        for reminder in HOME_REMINDERS:
            label = Label(text=reminder, font_size=sp(14), color=(0.16, 0.16, 0.16, 1), size_hint=(1, None),
                          height=dp(24), halign="left", valign="middle", **text_style())
            label.bind(size=label.setter("text_size"))
            reminder_box.add_widget(label)
        self.content_box.add_widget(reminder_box)

        tool_title = Label(text="常用工具", font_size=sp(18), color=(0.12, 0.12, 0.12, 1), size_hint=(1, None),
                           height=dp(28), halign="left", valign="middle", **text_style())
        tool_title.bind(size=tool_title.setter("text_size"))
        self.content_box.add_widget(tool_title)

        self.tool_grid = BoxLayout(orientation="vertical", spacing=dp(10), size_hint=(1, None), height=dp(212))
        row1 = BoxLayout(spacing=dp(10))
        row2 = BoxLayout(spacing=dp(10))
        tools = [
            ("⚕", "专家服务", lambda *_: setattr(self.manager, "current", "expert")),
            ("☰", "农事计划", lambda *_: open_text_popup("农事计划", "即将推出")),
            ("❖", "虫害百科", lambda *_: setattr(self.manager, "current", "encyclopedia")),
            ("★", "我的收藏", lambda *_: setattr(self.manager, "current", "favorite")),
            ("⌖", "病虫害分布图", lambda *_: setattr(self.manager, "current", "map")),
            ("…", "更多工具", lambda *_: open_text_popup("更多工具", "土壤分析\n农资识别\n作物生长监测")),
        ]
        for idx, (icon, title, callback) in enumerate(tools):
            card = ToolCard(icon_text=icon, icon_source=HOME_TOOL_ICONS.get(title, ""), title=title)
            card.bind(on_press=callback)
            (row1 if idx < 3 else row2).add_widget(card)
        self.tool_grid.add_widget(row1)
        self.tool_grid.add_widget(row2)
        self.content_box.add_widget(self.tool_grid)

        self.bottom_nav = self._build_bottom_nav("home")
        self.layout.add_widget(self.bottom_nav)
        self.layout.bind(size=self._update_layout)
        Clock.schedule_once(lambda dt: self._update_layout(), 0)

    def _paint_card(self, instance, *_args):
        instance.canvas.before.clear()
        with instance.canvas.before:
            Color(1, 1, 1, 1)
            RoundedRectangle(pos=instance.pos, size=instance.size, radius=[dp(16)] * 4)

    def _build_search_bar(self):
        bar = BoxLayout(
            size_hint=(1, None),
            height=dp(56),
            pos_hint={"x": 0, "top": 0.985},
            spacing=dp(8),
            padding=(dp(14), dp(8), dp(14), dp(8)),
        )
        self.home_search_input = TextInput(
            hint_text="🔍 搜索病虫害名称",
            multiline=False,
            input_type="text",
            keyboard_suggestions=True,
            background_normal="",
            background_active="",
            background_color=(0.94, 0.94, 0.94, 1),
            padding=(dp(14), dp(10), dp(14), dp(10)),
            foreground_color=(0.12, 0.12, 0.12, 1),
            cursor_color=(0.12, 0.12, 0.12, 1),
            **text_style(),
        )
        self.home_search_input.bind(on_text_validate=self.search_pests, text=self._on_home_search_text)
        bar.add_widget(self.home_search_input)
        search_btn = Button(text="搜索", size_hint=(None, 1), width=dp(54), background_normal="", background_down="",
                            background_color=(0, 0, 0, 0), color=GREEN, **text_style())
        search_btn.bind(on_press=self.search_pests)
        bar.add_widget(search_btn)
        cancel_btn = Button(text="取消", size_hint=(None, 1), width=dp(54), background_normal="", background_down="",
                            background_color=(0, 0, 0, 0), color=GREEN, **text_style())
        cancel_btn.bind(on_press=self.cancel_home_search)
        bar.add_widget(cancel_btn)
        return bar

    def _build_bottom_nav(self, current_name):
        nav = BoxLayout(orientation="horizontal", size_hint=(1, None), height=dp(74), pos_hint={"x": 0, "y": 0},
                        padding=(0, dp(6), 0, dp(6)))
        with nav.canvas.before:
            Color(1, 1, 1, 1)
            nav.bg_rect = Rectangle(pos=nav.pos, size=nav.size)
        nav.bind(pos=lambda inst, *_: update_nav_rect(inst), size=lambda inst, *_: update_nav_rect(inst))
        items = [
            ("⌂", "首页", lambda *_: setattr(self.manager, "current", "home")),
            ("☷", "社区", lambda *_: setattr(self.manager, "current", "community")),
            ("◎", "拍照", lambda *_: App.get_running_app().show_capture_menu()),
            ("◫", "商城", lambda *_: setattr(self.manager, "current", "store")),
            ("☺", "我的", lambda *_: setattr(self.manager, "current", "mypage")),
        ]
        for _icon, title, callback in items:
            btn = Button(text=title, background_normal="", background_down="", background_color=(0, 0, 0, 0),
                         color=GREEN if title == "首页" else (0.32, 0.32, 0.32, 1), **text_style())
            btn.bind(on_press=callback)
            nav.add_widget(btn)
        return nav

    def _update_bg(self, *_args):
        self.bg_rect.pos = self.layout.pos
        self.bg_rect.size = self.layout.size

    def _update_layout(self, *_args):
        vertical_gap = dp(6)
        available_height = self.height - self.bottom_nav.height - self.search_bar.height - vertical_gap
        self.content_scroll.height = max(dp(200), available_height)
        self.content_scroll.pos = (0, self.bottom_nav.height)

    def _on_home_search_text(self, _instance, value):
        if not value.strip():
            return

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


class CommunityScreen(Screen):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.name = "community"
        self.build_ui()

    def build_ui(self):
        self.layout = FloatLayout()
        self.add_widget(self.layout)
        with self.layout.canvas.before:
            Color(0.97, 0.97, 0.97, 1)
            self.bg_rect = Rectangle(pos=self.layout.pos, size=self.layout.size)
        self.layout.bind(pos=self._update_bg, size=self._update_bg)

        self.search_bar = self._build_search_bar()
        self.layout.add_widget(self.search_bar)
        self.search_bar.size_hint = (1, None)
        self.search_bar.pos_hint = {"x": 0, "top": 0.985}
        self.search_bar.z = 1000

        self.scroll = ScrollView(size_hint=(1, None), do_scroll_x=False, pos_hint={"x": 0, "y": 0.12})
        self.layout.add_widget(self.scroll)
        self.content_box = BoxLayout(orientation="vertical", spacing=dp(14), padding=(dp(14), dp(36), dp(14), dp(18)),
                                     size_hint=(1, None))
        self.content_box.bind(minimum_height=self.content_box.setter("height"))
        self.scroll.add_widget(self.content_box)
        self.refresh_default_content()

        self.bottom_nav = HomeScreen._build_bottom_nav(self, "community")
        for child in self.bottom_nav.children:
            if isinstance(child, Button) and child.text == "社区":
                child.color = GREEN
            elif isinstance(child, Button):
                child.color = (0.32, 0.32, 0.32, 1)
        self.layout.add_widget(self.bottom_nav)
        self.layout.bind(size=self._update_layout)
        Clock.schedule_once(lambda dt: self._update_layout(), 0)

    def _paint_card(self, instance, *_args):
        instance.canvas.before.clear()
        with instance.canvas.before:
            Color(1, 1, 1, 1)
            RoundedRectangle(pos=instance.pos, size=instance.size, radius=[dp(16)] * 4)

    def _build_search_bar(self):
        bar = BoxLayout(
            size_hint=(1, None),
            height=dp(56),
            pos_hint={"x": 0, "top": 0.985},
            spacing=dp(8),
            padding=(dp(14), dp(8), dp(14), dp(8)),
        )
        self.community_search_input = TextInput(
            hint_text="🔍 搜索帖子标题或内容",
            multiline=False,
            input_type="text",
            keyboard_suggestions=True,
            background_normal="",
            background_active="",
            background_color=(0.94, 0.94, 0.94, 1),
            padding=(dp(14), dp(10), dp(14), dp(10)),
            foreground_color=(0.12, 0.12, 0.12, 1),
            cursor_color=(0.12, 0.12, 0.12, 1),
            **text_style(),
        )
        self.community_search_input.bind(on_text_validate=self.search_posts, text=self._on_search_text)
        bar.add_widget(self.community_search_input)
        search_btn = Button(text="搜索", size_hint=(None, 1), width=dp(54), background_normal="", background_down="",
                            background_color=(0, 0, 0, 0), color=GREEN, **text_style())
        search_btn.bind(on_press=self.search_posts)
        bar.add_widget(search_btn)
        cancel_btn = Button(text="取消", size_hint=(None, 1), width=dp(54), background_normal="", background_down="",
                            background_color=(0, 0, 0, 0), color=GREEN, **text_style())
        cancel_btn.bind(on_press=self.cancel_search)
        bar.add_widget(cancel_btn)
        return bar

    def refresh_default_content(self):
        self.content_box.clear_widgets()
        hot_box = BoxLayout(orientation="vertical", spacing=dp(10), padding=dp(12), size_hint=(1, None), height=dp(118))
        hot_box.bind(pos=self._paint_card, size=self._paint_card)
        hot_title = Label(text="热门用户", font_size=sp(18), color=(0.12, 0.12, 0.12, 1), size_hint=(1, None),
                          height=dp(24), halign="left", valign="middle", **text_style())
        hot_title.bind(size=hot_title.setter("text_size"))
        hot_box.add_widget(hot_title)
        users_row = BoxLayout(spacing=dp(8))
        for name in ["用户A", "用户B", "用户C", "用户D", "用户E"]:
            item = IconStat(icon_text="●", title=name, value="")
            users_row.add_widget(item)
        hot_box.add_widget(users_row)
        self.content_box.add_widget(hot_box)

        for post in COMMUNITY_POSTS:
            self.content_box.add_widget(self._build_post_card(post))

        focus_box = BoxLayout(spacing=dp(12), size_hint=(1, None), height=dp(116))
        focus_left = ToolCard(icon_text="✿", title="种植经验")
        focus_right = ToolCard(icon_text="✦", title="防治技巧")
        focus_left.bind(on_press=lambda *_: self.open_community_detail(COMMUNITY_ARTICLES["article:planting"]))
        focus_right.bind(on_press=lambda *_: self.open_community_detail(COMMUNITY_ARTICLES["article:control"]))
        focus_box.add_widget(focus_left)
        focus_box.add_widget(focus_right)
        self.content_box.add_widget(focus_box)

    def _build_search_result_card(self, post):
        card = BoxLayout(orientation="vertical", spacing=dp(8), padding=dp(14), size_hint=(1, None), height=dp(132))
        card.bind(pos=self._paint_card, size=self._paint_card)
        user_label = Label(text=post["username"], font_size=sp(14), color=GREEN, size_hint=(1, None), height=dp(22),
                           halign="left", valign="middle", **text_style())
        user_label.bind(size=user_label.setter("text_size"))
        card.add_widget(user_label)
        title = Label(text=post["title"], font_size=sp(17), bold=True, color=(0.12, 0.12, 0.12, 1), size_hint=(1, None),
                      height=dp(26), halign="left", valign="middle", **text_style())
        title.bind(size=title.setter("text_size"))
        card.add_widget(title)
        summary = Label(text=post["summary"], font_size=sp(14), color=(0.32, 0.32, 0.32, 1), size_hint=(1, None),
                        height=dp(42), halign="left", valign="top", **text_style())
        summary.bind(size=summary.setter("text_size"))
        card.add_widget(summary)
        opener = Button(text="点击查看全部内容", size_hint=(1, None), height=dp(24), background_normal="",
                        background_down="", background_color=(0, 0, 0, 0), color=GREEN, halign="left", **text_style())
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
            if keyword_lower in post["title"].lower() or keyword_lower in post["full_text"].lower() or keyword_lower in
               post["summary"].lower()
        ]
        self.content_box.clear_widgets()
        header = Label(
            text=f"找到{len(results)}条关于“{keyword}”的帖子" if results else "未找到相关帖子",
            font_size=sp(16),
            color=(0.25, 0.25, 0.25, 1),
            size_hint=(1, None),
            height=dp(34),
            halign="left",
            valign="middle",
            **text_style(),
        )
        header.bind(size=header.setter("text_size"))
        self.content_box.add_widget(header)
        for post in results:
            self.content_box.add_widget(self._build_search_result_card(post))

    def cancel_search(self, _instance=None):
        self.community_search_input.text = ""
        self.community_search_input.focus = False
        self.refresh_default_content()

    def sync_product_views(self, tab_name=None):
        self.refresh_default_content()

    def _build_post_card(self, post):
        card = BoxLayout(orientation="vertical", spacing=dp(10), padding=dp(14), size_hint=(1, None), height=dp(252))
        card.bind(pos=self._paint_card, size=self._paint_card)
        user_label = Label(text=post["username"], font_size=sp(14), color=GREEN, size_hint=(1, None), height=dp(22),
                           halign="left", valign="middle", **text_style())
        user_label.bind(size=user_label.setter("text_size"))
        card.add_widget(user_label)
        title = Label(text=post["title"], font_size=sp(18), bold=True, color=(0.12, 0.12, 0.12, 1), size_hint=(1, None),
                      height=dp(64), halign="left", valign="top", **text_style())
        title.bind(size=title.setter("text_size"))
        card.add_widget(title)
        summary = Label(text=post["summary"], font_size=sp(14), color=(0.28, 0.28, 0.28, 1), size_hint=(1, None),
                        height=dp(54), halign="left", valign="top", **text_style())
        summary.bind(size=summary.setter("text_size"))
        card.add_widget(summary)
        full_link = UnderlineLabel(text="[u]点击查看全部内容[/u]", color=GREEN, font_size=sp(13), size_hint=(1, None),
                                   height=dp(24), halign="left", valign="middle", **text_style())
        full_link.bind(size=full_link.setter("text_size"))
        full_link.bind(on_press=lambda *_: self.open_community_detail(post))
        card.add_widget(full_link)
        footer = BoxLayout(size_hint=(1, None), height=dp(32), padding=(0, dp(4), 0, 0))
        liked = self._is_post_liked(post["id"])
        like_btn = LikeImageButton(
            source_off=LIKE_ICON_OFF,
            source_on=LIKE_ICON_ON,
            liked=liked,
            size_hint=(None, None),
            size=(dp(14), dp(14)),
            pos_hint={"center_y": 0.5},
        )
        like_btn.bind(on_press=lambda *_: self._toggle_like(post, like_btn))
        footer.add_widget(like_btn)
        like_count = Label(
            text=self._display_like_text(post),
            size_hint=(None, 1),
            width=dp(44),
            color=(0.35, 0.35, 0.35, 1),
            halign="left",
            valign="middle",
            **text_style(),
        )
        like_count.bind(size=like_count.setter("text_size"))
        like_count.text_size = (dp(44), None)
        like_btn.count_label = like_count
        footer.add_widget(like_count)
        view_label = Label(
            text=f"浏览量 {STORE_DB.get_post_view_count(self._post_key(post))}",
            color=(0.35, 0.35, 0.35, 1),
            halign="left",
            valign="middle",
            **text_style(),
        )
        view_label.bind(size=view_label.setter("text_size"))
        footer.add_widget(view_label)
        card.add_widget(footer)
        return card

    def _display_like_text(self, post):
        return str(STORE_DB.get_post_like_count(post["id"]))

    @staticmethod
    def _post_key(post):
        return post.get("key") or f"post:{post['id']}"

    def _is_post_liked(self, post_id):
        app = App.get_running_app()
        username = app.current_user["username"] if app.current_user else ""
        return STORE_DB.has_liked_post(username, post_id)

    def _toggle_like(self, post, button):
        app = App.get_running_app()
        username = app.current_user["username"] if app.current_user else ""
        liked = STORE_DB.toggle_post_like(username, post["id"])
        if hasattr(button, "set_liked"):
            button.set_liked(liked)
        if hasattr(button, "count_label"):
            button.count_label.text = self._display_like_text(post)
        self.refresh_default_content()

    def open_community_detail(self, post):
        detail_data = dict(post)
        detail_data["key"] = self._post_key(detail_data)
        detail_screen = self.manager.get_screen("community_detail")
        detail_screen.set_item(detail_data, return_screen="community")
        self.manager.current = "community_detail"

    def _update_bg(self, *_args):
        self.bg_rect.pos = self.layout.pos
        self.bg_rect.size = self.layout.size

    def _update_layout(self, *_args):
        self.scroll.height = self.height - self.bottom_nav.height - self.search_bar.height - dp(6)
        self.scroll.pos = (0, self.bottom_nav.height)


class StoreRecycleView(ScrollView):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.do_scroll_x = False
        self.bar_width = dp(4)
        self.scroll_type = ["bars", "content"]
        self._data = []
        self.content_box = BoxLayout(
            orientation="vertical",
            size_hint=(1, None),
            spacing=0,
        )
        self.content_box.bind(minimum_height=self.content_box.setter("height"))
        self.add_widget(self.content_box)

    @property
    def data(self):
        return self._data

    @data.setter
    def data(self, items):
        self._data = list(items or [])
        self.content_box.clear_widgets()
        for item in self._data:
            row = ProductRow(
                product_id=item.get("product_id", 0),
                name_text=item.get("name_text", ""),
                specification_text=item.get("specification_text", ""),
                price_text=item.get("price_text", ""),
                sold_text=item.get("sold_text", ""),
                screen_ref=item.get("screen_ref"),
            )
            self.content_box.add_widget(row)
        Clock.schedule_once(lambda dt: self._reset_scroll(), 0)

    def _reset_scroll(self):
        self.scroll_y = 1


class StoreScreen(BaseScreen):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.name = "store"
        self.store_result_list = None
        self.build_ui()

    def sync_product_views(self, tab_name=None):
        return None

    def build_ui(self):
        self.layout = FloatLayout()
        self.add_widget(self.layout)
        with self.layout.canvas.before:
            Color(0.97, 0.97, 0.97, 1)
            self.bg_rect = Rectangle(pos=self.layout.pos, size=self.layout.size)
        self.layout.bind(pos=self._update_bg, size=self._update_bg)

        self.search_bar = self._build_search_bar()
        self.layout.add_widget(self.search_bar)
        self.search_bar.size_hint = (1, None)
        self.search_bar.pos_hint = {"x": 0, "top": 0.985}
        self.search_bar.z = 1000

        self.scroll = ScrollView(size_hint=(1, None), do_scroll_x=False, pos_hint={"x": 0, "y": 0.12})
        self.layout.add_widget(self.scroll)
        self.content_box = BoxLayout(orientation="vertical", spacing=dp(14), padding=(dp(14), dp(30), dp(14), dp(18)),
                                     size_hint=(1, None))
        self.content_box.bind(minimum_height=self.content_box.setter("height"))
        self.scroll.add_widget(self.content_box)
        self.refresh_default_view()

        self.bottom_nav = HomeScreen._build_bottom_nav(self, "store")
        for child in self.bottom_nav.children:
            if isinstance(child, Button) and child.text == "商城":
                child.color = GREEN
            elif isinstance(child, Button):
                child.color = (0.32, 0.32, 0.32, 1)
        self.layout.add_widget(self.bottom_nav)
        self.layout.bind(size=self._update_layout)
        Clock.schedule_once(lambda dt: self._update_layout(), 0)

    def _update_bg(self, *_args):
        self.bg_rect.pos = self.layout.pos
        self.bg_rect.size = self.layout.size

    def _update_layout(self, *_args):
        self.scroll.height = self.height - self.bottom_nav.height - self.search_bar.height - dp(6)
        self.scroll.pos = (0, self.bottom_nav.height)

    def _paint_card(self, instance, *_args):
        instance.canvas.before.clear()
        with instance.canvas.before:
            Color(1, 1, 1, 1)
            RoundedRectangle(pos=instance.pos, size=instance.size, radius=[dp(16)] * 4)

    def _build_section(self, title, category_name, products):
        wrapper = BoxLayout(orientation="vertical", spacing=dp(10), padding=dp(12), size_hint=(1, None), height=dp(228))
        wrapper.bind(pos=self._paint_card, size=self._paint_card)
        header = BoxLayout(size_hint=(1, None), height=dp(28))
        title_label = Label(text=title, font_size=sp(18), color=(0.12, 0.12, 0.12, 1), halign="left", valign="middle",
                            **text_style())
        title_label.bind(size=title_label.setter("text_size"))
        header.add_widget(title_label)
        more_link = UnderlineLabel(text="[u]更多 >>[/u]", color=GREEN, font_size=sp(13), size_hint=(None, 1),
                                   width=dp(78), halign="right", valign="middle", **text_style())
        more_link.bind(size=more_link.setter("text_size"))
        more_link.bind(on_press=lambda *_: self.open_category(category_name))
        header.add_widget(more_link)
        wrapper.add_widget(header)
        row = BoxLayout(spacing=dp(10))
        for product in products:
            row.add_widget(HomeStoreItem(product, on_open=self.open_product_detail))
        wrapper.add_widget(row)
        return wrapper

    def _build_search_bar(self):
        bar = BoxLayout(
            size_hint=(1, None),
            height=dp(56),
            pos_hint={"x": 0, "top": 0.985},
            spacing=dp(8),
            padding=(dp(14), dp(8), dp(14), dp(8)),
        )
        self.search_input = TextInput(
            hint_text="🔍 搜索商品名称",
            multiline=False,
            input_type="text",
            keyboard_suggestions=True,
            background_normal="",
            background_active="",
            background_color=(0.94, 0.94, 0.94, 1),
            padding=(dp(14), dp(10), dp(14), dp(10)),
            foreground_color=(0.12, 0.12, 0.12, 1),
            cursor_color=(0.12, 0.12, 0.12, 1),
            **text_style(),
        )
        self.search_input.bind(on_text_validate=self.search_product, text=self._on_search_text)
        bar.add_widget(self.search_input)
        search_btn = Button(text="搜索", size_hint=(None, 1), width=dp(54), background_normal="", background_down="",
                            background_color=(0, 0, 0, 0), color=GREEN, **text_style())
        search_btn.bind(on_press=self.search_product)
        bar.add_widget(search_btn)
        cancel_btn = Button(text="取消", size_hint=(None, 1), width=dp(54), background_normal="", background_down="",
                            background_color=(0, 0, 0, 0), color=GREEN, **text_style())
        cancel_btn.bind(on_press=self.cancel_search)
        bar.add_widget(cancel_btn)
        return bar

    def _on_search_text(self, _instance, value):
        keyword = value.strip()
        if not keyword:
            self.refresh_default_view()
            return
        self.show_search_results(STORE_DB.search_products(keyword), keyword)

    def refresh_default_view(self):
        self.content_box.clear_widgets()
        banner = BoxLayout(orientation="horizontal", spacing=dp(12), padding=dp(12), size_hint=(1, None),
                           height=dp(138))
        banner.bind(pos=self._paint_card, size=self._paint_card)
        banner.add_widget(GrayPlaceholder(size_hint=(None, 1), width=dp(120)))
        banner_text = BoxLayout(orientation="vertical", spacing=dp(6))
        ad_title = Label(text="精选好物广告图", font_size=sp(16), color=GREEN, size_hint=(1, None), height=dp(24),
                         halign="left", valign="middle", **text_style())
        ad_title.bind(size=ad_title.setter("text_size"))
        banner_text.add_widget(ad_title)
        ad_name = Label(text="敌敌畏", font_size=sp(22), color=(0.12, 0.12, 0.12, 1), size_hint=(1, None),
                        height=dp(32), halign="left", valign="middle", **text_style())
        ad_name.bind(size=ad_name.setter("text_size"))
        banner_text.add_widget(ad_name)
        ad_desc = Label(text="经典常见商品展示", font_size=sp(14), color=(0.35, 0.35, 0.35, 1), size_hint=(1, None),
                        height=dp(24), halign="left", valign="middle", **text_style())
        ad_desc.bind(size=ad_desc.setter("text_size"))
        banner_text.add_widget(ad_desc)
        banner.add_widget(banner_text)
        self.content_box.add_widget(banner)
        self.content_box.add_widget(
            self._build_section("精选好物", "精选好物", STORE_DB.get_products_by_tab("精选好物")[:4]))
        self.content_box.add_widget(
            self._build_section("热销榜单", "热销榜单", STORE_DB.get_products_for_home("热销榜单")))
        self.content_box.add_widget(self._build_section("肥料", "肥料", STORE_DB.get_products_for_home("肥料推荐")))
        self.content_box.add_widget(
            self._build_section("杀虫剂", "杀虫剂", STORE_DB.get_products_for_home("杀虫剂推荐")))

    def show_search_results(self, results, keyword):
        self.content_box.clear_widgets()
        header = Label(
            text=f"找到{len(results)}个关于“{keyword}”的商品" if results else "未找到相关商品",
            font_size=sp(16),
            color=(0.25, 0.25, 0.25, 1),
            size_hint=(1, None),
            height=dp(34),
            halign="left",
            valign="middle",
            **text_style(),
        )
        header.bind(size=header.setter("text_size"))
        self.content_box.add_widget(header)
        if not results:
            return
        if self.store_result_list is None:
            self.store_result_list = StoreRecycleView(size_hint=(1, None))
        result_height = max(dp(120), dp(100) * len(results))
        self.store_result_list.size_hint = (1, None)
        self.store_result_list.height = result_height
        self.store_result_list.data = [
            {
                "product_id": product["id"],
                "name_text": product["name"],
                "specification_text": product["specification"],
                "price_text": f"￥{product['price']:.2f}",
                "sold_text": f"已售 {product['sold_count']}",
                "from_tab_text": "商城搜索",
                "return_screen_name": "store",
                "screen_ref": self,
            }
            for product in results
        ]
        self.content_box.add_widget(self.store_result_list)

    def open_category(self, category_name):
        category_screen = self.manager.get_screen("store_category")
        category_screen.set_category(category_name)
        self.manager.current = "store_category"

    def open_product_detail(self, product_id):
        try:
            detail_screen = self.manager.get_screen("product_detail")
            detail_screen.set_product(product_id, from_tab="商城首页", return_screen="store")
            self.manager.current = "product_detail"
        except Exception as exc:
            show_toast(f"打开商品失败: {exc}")

    def search_product(self, _instance=None):
        keyword = self.search_input.text.strip()
        if not keyword:
            self.refresh_default_view()
            return
        results = STORE_DB.search_products(keyword)
        self.show_search_results(results, keyword)

    def cancel_search(self, _instance=None):
        self.search_input.text = ""
        self.search_input.focus = False
        self.refresh_default_view()

    def focus_search(self):
        self.search_input.focus = True


class StoreCategoryScreen(Screen):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.name = "store_category"
        self.current_category = "精选好物"
        self.build_ui()

    def build_ui(self):
        self.layout = FloatLayout()
        self.add_widget(self.layout)

        with self.layout.canvas.before:
            Color(0.97, 0.97, 0.97, 1)
            self.bg_rect = Rectangle(pos=self.layout.pos, size=self.layout.size)
        self.layout.bind(pos=self._update_bg, size=self._update_bg)

        self.top_bar = FloatLayout(size_hint=(1, None), height=dp(92), pos_hint={"x": 0, "top": 1})
        with self.top_bar.canvas.before:
            Color(*GREEN)
            self.top_bar_rect = Rectangle(pos=self.top_bar.pos, size=self.top_bar.size)
        self.top_bar.bind(pos=self._update_top_bar, size=self._update_top_bar)
        self.layout.add_widget(self.top_bar)

        self.back_btn = IconButton(
            text="<",
            font_size=sp(34),
            color=(0, 0, 0, 1),
            size_hint=(None, None),
            size=(dp(56), dp(56)),
            pos_hint={"x": 0.03, "center_y": 0.42},
            **text_style(),
        )
        self.back_btn.bind(on_press=self.go_back)
        self.top_bar.add_widget(self.back_btn)

        self.title_label = Label(
            text=self.current_category,
            font_size=sp(22),
            bold=True,
            color=(1, 1, 1, 1),
            size_hint=(0.7, None),
            height=dp(36),
            pos_hint={"center_x": 0.52, "center_y": 0.42},
            halign="center",
            valign="middle",
            **text_style(),
        )
        self.title_label.bind(size=self.title_label.setter("text_size"))
        self.top_bar.add_widget(self.title_label)

        self.list_container = FloatLayout(size_hint=(1, None), pos_hint={"x": 0, "y": 0})
        self.layout.add_widget(self.list_container)

        self.product_rv = StoreRecycleView(size_hint=(1, 1), pos_hint={"x": 0, "y": 0})
        self.list_container.add_widget(self.product_rv)

        self.layout.bind(size=self._update_content_height)
        Clock.schedule_once(lambda dt: self._update_content_height(), 0)

    def _update_bg(self, *_args):
        self.bg_rect.pos = self.layout.pos
        self.bg_rect.size = self.layout.size

    def _update_top_bar(self, *_args):
        self.top_bar_rect.pos = self.top_bar.pos
        self.top_bar_rect.size = self.top_bar.size

    def _update_content_height(self, *_args):
        available_height = max(dp(200), self.height - self.top_bar.height)
        self.list_container.size = (self.width, available_height)
        self.list_container.pos = (0, 0)
        self.product_rv.size = self.list_container.size

    def _go_screen(self, screen_name):
        self.manager.current = screen_name

    def set_category(self, category_name):
        self.current_category = category_name
        self.title_label.text = category_name
        self.refresh_products()

    def refresh_products(self):
        products = STORE_DB.get_products_by_tab(self.current_category)
        self.product_rv.data = [
            {
                "product_id": product["id"],
                "name_text": product["name"],
                "specification_text": product["specification"],
                "price_text": f"￥{product['price']:.2f}",
                "sold_text": f"已售 {product['sold_count']}",
                "from_tab_text": self.current_category,
                "return_screen_name": "store_category",
                "screen_ref": self,
            }
            for product in products
        ]

    def open_product_detail(self, product_id):
        try:
            detail_screen = self.manager.get_screen("product_detail")
            detail_screen.set_product(product_id, from_tab=self.current_category, return_screen="store_category")
            self.manager.current = "product_detail"
        except Exception as exc:
            show_toast(f"打开商品失败: {exc}")

    def sync_product_views(self, tab_name=None):
        if tab_name:
            self.current_category = tab_name
            self.title_label.text = tab_name
        self.refresh_products()

    def go_back(self, _instance=None):
        self.manager.current = "store"


class ProductDetailScreen(Screen):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.name = "product_detail"
        self.product_id = None
        self.return_tab = "精选好物"
        self.return_screen = "store"
        self.build_ui()

    def build_ui(self):
        self.layout = FloatLayout()
        self.add_widget(self.layout)

        with self.layout.canvas.before:
            Color(1, 1, 1, 1)
            self.bg_rect = Rectangle(pos=self.layout.pos, size=self.layout.size)
        self.layout.bind(pos=self._update_bg, size=self._update_bg)

        self.top_bar = FloatLayout(size_hint=(1, None), height=dp(92), pos_hint={"x": 0, "top": 1})
        with self.top_bar.canvas.before:
            Color(*GREEN)
            self.top_bar_rect = Rectangle(pos=self.top_bar.pos, size=self.top_bar.size)
        self.top_bar.bind(pos=self._update_top_bar, size=self._update_top_bar)
        self.layout.add_widget(self.top_bar)

        self.back_btn = IconButton(
            text="<",
            font_size=sp(34),
            color=(0, 0, 0, 1),
            size_hint=(None, None),
            size=(dp(56), dp(56)),
            pos_hint={"x": 0.03, "center_y": 0.42},
            **text_style(),
        )
        self.back_btn.bind(on_press=self.go_back)
        self.top_bar.add_widget(self.back_btn)

        self.scroll_view = ScrollView(
            size_hint=(1, None),
            pos_hint={"x": 0, "y": 0},
            do_scroll_x=False,
            bar_width=dp(4),
            scroll_type=["bars", "content"],
        )
        self.layout.add_widget(self.scroll_view)

        self.content_box = BoxLayout(
            orientation="vertical",
            spacing=dp(14),
            padding=(dp(16), 0, dp(16), dp(100)),
            size_hint=(1, None),
        )
        self.content_box.bind(minimum_height=self._sync_detail_content_height)
        self.scroll_view.add_widget(self.content_box)
        self.scroll_view.bind(height=self._sync_detail_content_height)

        self.image_wrap = FloatLayout(size_hint=(1, None), height=dp(220))
        self.large_placeholder = GrayPlaceholder(size_hint=(None, None), size=(dp(220), dp(220)))
        self.large_placeholder.pos_hint = {"center_x": 0.5, "center_y": 0.5}
        self.image_wrap.add_widget(self.large_placeholder)
        self.content_box.add_widget(self.image_wrap)

        self.product_name_label = Label(
            text="",
            font_size=sp(24),
            bold=True,
            color=(0.08, 0.08, 0.08, 1),
            size_hint=(1, None),
            halign="left",
            valign="top",
            **text_style(),
        )
        self.product_name_label.bind(texture_size=self._sync_dynamic_label, width=self._sync_label_width)
        self.content_box.add_widget(self.product_name_label)

        self.spec_label = Label(
            text="",
            font_size=sp(15),
            color=(0.4, 0.4, 0.4, 1),
            size_hint=(1, None),
            height=dp(24),
            halign="left",
            valign="middle",
            **text_style(),
        )
        self.spec_label.bind(size=self.spec_label.setter("text_size"))
        self.content_box.add_widget(self.spec_label)

        self.price_label = Label(
            text="",
            font_size=sp(22),
            color=(0.88, 0.34, 0.18, 1),
            bold=True,
            size_hint=(1, None),
            height=dp(34),
            halign="left",
            valign="middle",
            **text_style(),
        )
        self.price_label.bind(size=self.price_label.setter("text_size"))
        self.content_box.add_widget(self.price_label)

        self.sold_label = Label(
            text="",
            font_size=sp(14),
            color=(0.35, 0.35, 0.35, 1),
            size_hint=(1, None),
            height=dp(24),
            halign="left",
            valign="middle",
            **text_style(),
        )
        self.sold_label.bind(size=self.sold_label.setter("text_size"))
        self.content_box.add_widget(self.sold_label)

        self.description_title = Label(
            text="商品简介",
            font_size=sp(18),
            bold=True,
            color=(0.08, 0.08, 0.08, 1),
            size_hint=(1, None),
            height=dp(28),
            halign="left",
            valign="middle",
            **text_style(),
        )
        self.description_title.bind(size=self.description_title.setter("text_size"))
        self.content_box.add_widget(self.description_title)

        self.description_label = Label(
            text="",
            font_size=sp(15),
            color=(0.18, 0.18, 0.18, 1),
            size_hint=(1, None),
            halign="left",
            valign="top",
            **text_style(),
        )
        self.description_label.bind(texture_size=self._sync_dynamic_label, width=self._sync_label_width)
        self.content_box.add_widget(self.description_label)

        self.action_box = BoxLayout(orientation="horizontal", size_hint=(1, None), height=dp(48), spacing=dp(12))
        self.favorite_btn = Button(
            text="☆ 收藏",
            font_size=sp(16),
            background_normal="",
            background_down="",
            background_color=(1, 1, 1, 1),
            color=GREEN,
            border=(0, 0, 0, 0),
            **text_style(),
        )
        self.favorite_btn.bind(on_press=self.toggle_favorite)
        self.favorite_btn.bind(pos=self._update_favorite_button_border, size=self._update_favorite_button_border)
        self.action_box.add_widget(self.favorite_btn)

        self.buy_btn = Button(
            text="立即购买",
            font_size=sp(16),
            background_normal="",
            background_down="",
            background_color=GREEN,
            color=(1, 1, 1, 1),
            border=(0, 0, 0, 0),
            **text_style(),
        )
        self.buy_btn.bind(on_press=self.buy_now)
        self.action_box.add_widget(self.buy_btn)
        self.content_box.add_widget(self.action_box)

        self.recognize_btn = RoundedButton(
            text="拍照识别",
            color=(1, 1, 1, 1),
            size_hint=(1, None),
            height=dp(44),
            **text_style(),
        )
        self.recognize_btn.bind(on_press=lambda *_: App.get_running_app().show_capture_menu())
        self.content_box.add_widget(self.recognize_btn)

        self.comment_title = Label(
            text="用户评价",
            font_size=sp(18),
            bold=True,
            color=(0.08, 0.08, 0.08, 1),
            size_hint=(1, None),
            height=dp(30),
            halign="left",
            valign="middle",
            **text_style(),
        )
        self.comment_title.bind(size=self.comment_title.setter("text_size"))
        self.content_box.add_widget(self.comment_title)

        self.comment_list = BoxLayout(orientation="vertical", spacing=dp(10), size_hint=(1, None))
        self.comment_list.bind(minimum_height=self.comment_list.setter("height"))
        self.content_box.add_widget(self.comment_list)

        self.comment_input_bar = BoxLayout(
            orientation="horizontal",
            size_hint=(1, None),
            height=dp(64),
            spacing=dp(10),
            padding=(dp(12), dp(10), dp(12), dp(10)),
            pos_hint={"x": 0, "y": 0},
        )
        with self.comment_input_bar.canvas.before:
            Color(1, 1, 1, 1)
            self.input_bar_rect = Rectangle(pos=self.comment_input_bar.pos, size=self.comment_input_bar.size)
        self.comment_input_bar.bind(pos=self._update_input_bar, size=self._update_input_bar)
        self.layout.add_widget(self.comment_input_bar)

        self.comment_input = TextInput(
            hint_text="写下你的评价",
            multiline=True,
            size_hint=(1, 1),
            padding=(dp(12), dp(12), dp(12), dp(12)),
            font_size=sp(15),
            input_type="text",
            keyboard_suggestions=True,
            write_tab=False,
            **text_style(),
        )
        self.comment_input_bar.add_widget(self.comment_input)

        self.publish_btn = Button(
            text="发表",
            size_hint=(None, 1),
            width=dp(88),
            font_size=sp(15),
            background_normal="",
            background_down="",
            background_color=GREEN,
            color=(1, 1, 1, 1),
            border=(0, 0, 0, 0),
            **text_style(),
        )
        self.publish_btn.bind(on_press=self.publish_comment)
        self.comment_input_bar.add_widget(self.publish_btn)

        self.layout.bind(size=self._update_scroll_height)
        Clock.schedule_once(lambda dt: self._update_scroll_height(), 0)

    def _update_bg(self, *_args):
        self.bg_rect.pos = self.layout.pos
        self.bg_rect.size = self.layout.size

    def _update_top_bar(self, *_args):
        self.top_bar_rect.pos = self.top_bar.pos
        self.top_bar_rect.size = self.top_bar.size

    def _update_input_bar(self, *_args):
        self.input_bar_rect.pos = self.comment_input_bar.pos
        self.input_bar_rect.size = self.comment_input_bar.size

    def _update_favorite_button_border(self, *_args):
        self.favorite_btn.canvas.after.clear()
        with self.favorite_btn.canvas.after:
            Color(*GREEN)
            Line(
                rectangle=(self.favorite_btn.x, self.favorite_btn.y, self.favorite_btn.width, self.favorite_btn.height),
                width=dp(1.2))

    def _update_scroll_height(self, *_args):
        self.scroll_view.height = max(dp(200), self.height - self.top_bar.height - self.comment_input_bar.height)
        self.scroll_view.pos = (0, self.comment_input_bar.height)
        self._sync_detail_content_height()

    def _sync_label_width(self, instance, _value):
        instance.text_size = (instance.width, None)

    def _sync_dynamic_label(self, instance, _value):
        instance.height = max(dp(28), instance.texture_size[1] + dp(6))

    def _sync_detail_content_height(self, *_args):
        minimum_height = getattr(self.content_box, "minimum_height", 0)
        viewport_height = self.scroll_view.height if hasattr(self, "scroll_view") else 0
        self.content_box.height = max(minimum_height, viewport_height)

    def _build_comment_widget(self, comment):
        wrapper = BoxLayout(
            orientation="vertical",
            spacing=dp(4),
            padding=(dp(12), dp(10), dp(12), dp(10)),
            size_hint=(1, None),
        )
        wrapper.bind(minimum_height=wrapper.setter("height"))
        with wrapper.canvas.before:
            Color(0.96, 0.96, 0.96, 1)
            bg_rect = Rectangle(pos=wrapper.pos, size=wrapper.size)
        wrapper.bind(pos=lambda instance, *_args: self._update_comment_rect(instance, bg_rect),
                     size=lambda instance, *_args: self._update_comment_rect(instance, bg_rect))

        header = Label(
            text=f"{comment['username']}  {comment['comment_date']}",
            font_size=sp(13),
            color=(0.32, 0.32, 0.32, 1),
            size_hint=(1, None),
            height=dp(22),
            halign="left",
            valign="middle",
            **text_style(),
        )
        header.bind(size=header.setter("text_size"))
        wrapper.add_widget(header)

        body = Label(
            text=comment["comment"],
            font_size=sp(15),
            color=(0.1, 0.1, 0.1, 1),
            size_hint=(1, None),
            halign="left",
            valign="top",
            **text_style(),
        )
        body.bind(width=self._sync_label_width, texture_size=self._sync_dynamic_label)
        wrapper.add_widget(body)
        return wrapper

    @staticmethod
    def _update_comment_rect(instance, rect):
        rect.pos = instance.pos
        rect.size = instance.size

    def set_product(self, product_id, from_tab="精选好物", return_screen="store"):
        self.product_id = product_id
        self.return_tab = from_tab
        self.return_screen = return_screen
        self.refresh_product()
        self.refresh_comments()
        self.refresh_recognize_btn()
        self.scroll_view.scroll_y = 1

    def refresh_recognize_btn(self):
        pass

    def refresh_product(self):
        product = STORE_DB.get_product(self.product_id)
        if not product:
            return
        self.product_name_label.text = product["name"]
        self.spec_label.text = f"规格：{product['specification']}"
        self.price_label.text = f"￥{product['price']:.2f}"
        self.sold_label.text = f"已售 {product['sold_count']}"
        self.description_label.text = product["description"] or "暂无商品简介"
        self._refresh_favorite_button()

    def _refresh_favorite_button(self):
        is_favorite = STORE_DB.is_favorite(self.product_id)
        if is_favorite:
            self.favorite_btn.background_color = (1, 1, 1, 1)
            self.favorite_btn.color = GREEN
            self.favorite_btn.text = "★ 收藏"
        else:
            self.favorite_btn.background_color = (1, 1, 1, 1)
            self.favorite_btn.color = GREEN
            self.favorite_btn.text = "☆ 收藏"
        self._update_favorite_button_border()

    def refresh_comments(self):
        self.comment_list.clear_widgets()
        comments = STORE_DB.get_comments(self.product_id)
        if not comments:
            empty_label = Label(
                text="暂无评论，快去评价吧",
                font_size=sp(15),
                color=(0.45, 0.45, 0.45, 1),
                size_hint=(1, None),
                height=dp(34),
                halign="left",
                valign="middle",
                **text_style(),
            )
            empty_label.bind(size=empty_label.setter("text_size"))
            self.comment_list.add_widget(empty_label)
            return
        for comment in comments:
            self.comment_list.add_widget(self._build_comment_widget(comment))

    def toggle_favorite(self, _instance=None):
        app = App.get_running_app()
        if not app.current_user or app.current_user.get("role") != "vip":
            show_toast("升级VIP可收藏商品")
            return
        is_favorite = STORE_DB.toggle_favorite(self.product_id)
        self._refresh_favorite_button()
        if self.manager and self.manager.has_screen("favorite"):
            self.manager.get_screen("favorite").refresh_products()
        show_toast("收藏成功" if is_favorite else "取消收藏")

    def buy_now(self, _instance=None):
        app = App.get_running_app()
        if not app.current_user:
            show_toast("请先登录")
            return
        product = STORE_DB.increment_sold_count(self.product_id)
        STORE_DB.add_order(app.current_user["username"], product["id"])
        self.refresh_product()
        if self.manager.has_screen(self.return_screen):
            return_screen = self.manager.get_screen(self.return_screen)
            return_screen.sync_product_views(self.return_tab)
        if self.manager.has_screen("order"):
            self.manager.get_screen("order").refresh_orders()
        show_toast(f"购买成功，已售 {product['sold_count']}")

    def publish_comment(self, _instance=None):
        comment_text = normalize_comment_text(self.comment_input.text)
        if not comment_text:
            show_toast("请输入评价内容")
            return
        app = App.get_running_app()
        username = app.current_user["username"] if app and app.current_user else DEFAULT_COMMENT_USER
        STORE_DB.add_comment(self.product_id, comment_text, username=username)
        self.comment_input.text = ""
        self.refresh_comments()
        self.scroll_view.scroll_y = 0
        show_toast("评价已发表")

    def go_back(self, _instance=None):
        if self.manager.has_screen(self.return_screen):
            return_screen = self.manager.get_screen(self.return_screen)
            return_screen.sync_product_views(self.return_tab)
            self.manager.current = self.return_screen


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

        self.top_bar = FloatLayout(size_hint=(1, None), height=dp(92), pos_hint={"x": 0, "top": 1})
        with self.top_bar.canvas.before:
            Color(*GREEN)
            self.top_bar_rect = Rectangle(pos=self.top_bar.pos, size=self.top_bar.size)
        self.top_bar.bind(pos=self._update_top_bar, size=self._update_top_bar)
        self.layout.add_widget(self.top_bar)

        self.back_btn = IconButton(
            text="<",
            font_size=sp(34),
            color=(0, 0, 0, 1),
            size_hint=(None, None),
            size=(dp(56), dp(56)),
            pos_hint={"x": 0.03, "center_y": 0.42},
            **text_style(),
        )
        self.back_btn.bind(on_press=self.go_back)
        self.top_bar.add_widget(self.back_btn)

        self.title_label = Label(
            text="社区详情",
            font_size=sp(22),
            bold=True,
            color=(1, 1, 1, 1),
            size_hint=(0.7, None),
            height=dp(36),
            pos_hint={"center_x": 0.52, "center_y": 0.42},
            halign="center",
            valign="middle",
            **text_style(),
        )
        self.title_label.bind(size=self.title_label.setter("text_size"))
        self.top_bar.add_widget(self.title_label)

        self.scroll_view = ScrollView(
            size_hint=(1, None),
            pos_hint={"x": 0, "y": 0},
            do_scroll_x=False,
            bar_width=dp(4),
            scroll_type=["bars", "content"],
        )
        self.layout.add_widget(self.scroll_view)

        self.content_box = BoxLayout(
            orientation="vertical",
            spacing=dp(14),
            padding=(dp(16), dp(12), dp(16), dp(110)),
            size_hint=(1, None),
        )
        self.content_box.bind(minimum_height=self._sync_detail_content_height)
        self.scroll_view.add_widget(self.content_box)
        self.scroll_view.bind(height=self._sync_detail_content_height)

        self.author_label = Label(
            text="",
            font_size=sp(14),
            color=GREEN,
            size_hint=(1, None),
            height=dp(24),
            halign="left",
            valign="middle",
            **text_style(),
        )
        self.author_label.bind(size=self.author_label.setter("text_size"))
        self.content_box.add_widget(self.author_label)

        self.post_title_label = Label(
            text="",
            font_size=sp(22),
            bold=True,
            color=(0.08, 0.08, 0.08, 1),
            size_hint=(1, None),
            halign="left",
            valign="top",
            **text_style(),
        )
        self.post_title_label.bind(width=self._sync_label_width, texture_size=self._sync_dynamic_label)
        self.content_box.add_widget(self.post_title_label)

        self.body_label = Label(
            text="",
            font_size=sp(15),
            color=(0.12, 0.12, 0.12, 1),
            size_hint=(1, None),
            halign="left",
            valign="top",
            **text_style(),
        )
        self.body_label.bind(width=self._sync_label_width, texture_size=self._sync_dynamic_label)
        self.content_box.add_widget(self.body_label)

        self.comment_title = Label(
            text="历史评论",
            font_size=sp(18),
            bold=True,
            color=(0.08, 0.08, 0.08, 1),
            size_hint=(1, None),
            height=dp(30),
            halign="left",
            valign="middle",
            **text_style(),
        )
        self.comment_title.bind(size=self.comment_title.setter("text_size"))
        self.content_box.add_widget(self.comment_title)

        self.comment_list = BoxLayout(orientation="vertical", spacing=dp(10), size_hint=(1, None))
        self.comment_list.bind(minimum_height=self.comment_list.setter("height"))
        self.content_box.add_widget(self.comment_list)

        self.action_bar = BoxLayout(
            orientation="horizontal",
            size_hint=(1, None),
            height=dp(68),
            spacing=dp(10),
            padding=(dp(12), dp(10), dp(12), dp(10)),
            pos_hint={"x": 0, "y": 0},
        )
        with self.action_bar.canvas.before:
            Color(1, 1, 1, 1)
            self.action_bar_rect = Rectangle(pos=self.action_bar.pos, size=self.action_bar.size)
        self.action_bar.bind(pos=self._update_action_bar, size=self._update_action_bar)
        self.layout.add_widget(self.action_bar)

        self.comment_input = TextInput(
            hint_text="写下你的评论",
            multiline=False,
            size_hint=(0.56, 1),
            padding=(dp(12), dp(10), dp(12), dp(10)),
            font_size=sp(15),
            input_type="text",
            keyboard_suggestions=True,
            write_tab=False,
            **text_style(),
        )
        self.action_bar.add_widget(self.comment_input)

        self.publish_btn = Button(
            text="发表",
            size_hint=(0.18, 1),
            font_size=sp(15),
            background_normal="",
            background_down="",
            background_color=GREEN,
            color=(1, 1, 1, 1),
            border=(0, 0, 0, 0),
            **text_style(),
        )
        self.publish_btn.bind(on_press=self.publish_comment)
        self.action_bar.add_widget(self.publish_btn)

        self.like_btn = LikeImageButton(
            source_off=LIKE_ICON_OFF,
            source_on=LIKE_ICON_ON,
            size_hint=(None, 1),
            width=dp(18),
        )
        self.like_btn.bind(on_press=self.toggle_like)
        self.action_bar.add_widget(self.like_btn)

        self.like_count_label = Label(
            text="0",
            size_hint=(None, 1),
            width=dp(34),
            color=(0.2, 0.2, 0.2, 1),
            halign="center",
            valign="middle",
            **text_style(),
        )
        self.like_count_label.bind(size=self.like_count_label.setter("text_size"))
        self.action_bar.add_widget(self.like_count_label)

        self.view_label = Label(
            text="浏览量 0",
            size_hint=(None, 1),
            width=dp(96),
            color=(0.35, 0.35, 0.35, 1),
            halign="left",
            valign="middle",
            **text_style(),
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
        self.scroll_view.height = max(dp(200), self.height - self.top_bar.height - self.action_bar.height)
        self.scroll_view.pos = (0, self.action_bar.height)
        self._sync_detail_content_height()

    def _sync_label_width(self, instance, _value):
        instance.text_size = (instance.width, None)

    def _sync_dynamic_label(self, instance, _value):
        instance.height = max(dp(28), instance.texture_size[1] + dp(6))

    def _sync_detail_content_height(self, *_args):
        minimum_height = getattr(self.content_box, "minimum_height", 0)
        viewport_height = self.scroll_view.height if hasattr(self, "scroll_view") else 0
        self.content_box.height = max(minimum_height, viewport_height)

    def _build_comment_widget(self, comment):
        wrapper = BoxLayout(
            orientation="vertical",
            spacing=dp(4),
            padding=(dp(12), dp(10), dp(12), dp(10)),
            size_hint=(1, None),
        )
        wrapper.bind(minimum_height=wrapper.setter("height"))
        with wrapper.canvas.before:
            Color(0.96, 0.96, 0.96, 1)
            bg_rect = Rectangle(pos=wrapper.pos, size=wrapper.size)
        wrapper.bind(pos=lambda instance, *_args: self._update_comment_rect(instance, bg_rect),
                     size=lambda instance, *_args: self._update_comment_rect(instance, bg_rect))
        header = Label(
            text=f"{comment['username']}  {comment['comment_date']}",
            font_size=sp(13),
            color=(0.32, 0.32, 0.32, 1),
            size_hint=(1, None),
            height=dp(22),
            halign="left",
            valign="middle",
            **text_style(),
        )
        header.bind(size=header.setter("text_size"))
        wrapper.add_widget(header)
        body = Label(
            text=comment["comment"],
            font_size=sp(15),
            color=(0.1, 0.1, 0.1, 1),
            size_hint=(1, None),
            halign="left",
            valign="top",
            **text_style(),
        )
        body.bind(width=self._sync_label_width, texture_size=self._sync_dynamic_label)
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
        self.like_count_label.text = str(STORE_DB.get_post_like_count(self.item_data["id"]))
        self.view_label.text = f"浏览量 {STORE_DB.get_post_view_count(self.item_data['key'])}"

    def refresh_comments(self):
        self.comment_list.clear_widgets()
        if not self.item_data:
            return
        comments = STORE_DB.get_post_comments(self.item_data["key"])
        if not comments:
            empty_label = Label(
                text="暂无评论，快来抢沙发",
                font_size=sp(15),
                color=(0.45, 0.45, 0.45, 1),
                size_hint=(1, None),
                height=dp(34),
                halign="left",
                valign="middle",
                **text_style(),
            )
            empty_label.bind(size=empty_label.setter("text_size"))
            self.comment_list.add_widget(empty_label)
            return
        for comment in comments:
            self.comment_list.add_widget(self._build_comment_widget(comment))

    def publish_comment(self, _instance=None):
        comment_text = normalize_comment_text(self.comment_input.text)
        if not comment_text or not self.item_data:
            show_toast("请输入评论内容")
            return
        app = App.get_running_app()
        username = app.current_user["username"] if app and app.current_user else DEFAULT_COMMENT_USER
        STORE_DB.add_post_comment(self.item_data["key"], comment_text, username)
        self.comment_input.text = ""
        self.refresh_comments()
        self.scroll_view.scroll_y = 0
        show_toast("评论已发表")

    def toggle_like(self, _instance=None):
        if not self.item_data:
            return
        app = App.get_running_app()
        username = app.current_user["username"] if app and app.current_user else ""
        if not username:
            show_toast("请先登录")
            return
        STORE_DB.toggle_post_like(username, self.item_data["id"])
        self.refresh_stats()
        community_screen = self.manager.get_screen("community") if self.manager and self.manager.has_screen(
            "community") else None
        if community_screen:
            if community_screen.community_search_input.text.strip():
                community_screen.search_posts()
            else:
                community_screen.refresh_default_content()

    def go_back(self, _instance=None):
        if self.manager and self.manager.has_screen(self.return_screen):
            self.manager.current = self.return_screen


class OrderRow(ButtonBehavior, BoxLayout):
    def __init__(self, order_data, on_open=None, **kwargs):
        super().__init__(orientation="horizontal", spacing=dp(12), padding=(dp(14), dp(10)), size_hint_y=None,
                         height=dp(118), **kwargs)
        self.order_data = order_data
        self.on_open = on_open
        self.bind(pos=self._update_canvas, size=self._update_canvas)
        thumb_wrap = FloatLayout(size_hint=(None, None), size=(dp(80), dp(80)))
        thumb_wrap.add_widget(GrayPlaceholder(size_hint=(1, 1)))
        self.add_widget(thumb_wrap)
        info_box = BoxLayout(orientation="vertical", spacing=dp(4))
        self.add_widget(info_box)
        for text, size, color in [
            (order_data["name"], sp(16), (0.1, 0.1, 0.1, 1)),
            (f"规格：{order_data['specification']}", sp(13), (0.42, 0.42, 0.42, 1)),
            (f"下单时间：{order_data['order_date']}", sp(13), (0.42, 0.42, 0.42, 1)),
            (f"预计送达：{order_data['delivery_date']}", sp(13), (0.42, 0.42, 0.42, 1)),
        ]:
            label = Label(text=text, font_size=size, color=color, size_hint=(1, None), height=dp(22), halign="left",
                          valign="middle", **text_style())
            label.bind(size=label.setter("text_size"))
            info_box.add_widget(label)
        price_label = Label(text=f"￥{order_data['price']:.2f}", font_size=sp(16), color=(0.88, 0.32, 0.18, 1),
                            size_hint=(None, 1), width=dp(88), halign="right", valign="middle", **text_style())
        price_label.bind(size=price_label.setter("text_size"))
        self.add_widget(price_label)

    def _update_canvas(self, *_args):
        self.canvas.after.clear()
        with self.canvas.after:
            Color(0.90, 0.90, 0.90, 1)
            Line(points=[self.x, self.y, self.right, self.y], width=1)

    def on_release(self):
        if self.on_open:
            self.on_open(self.order_data["product_id"])


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

        self.top_bar = FloatLayout(size_hint=(1, None), height=dp(92), pos_hint={"x": 0, "top": 1})
        with self.top_bar.canvas.before:
            Color(*GREEN)
            self.top_bar_rect = Rectangle(pos=self.top_bar.pos, size=self.top_bar.size)
        self.top_bar.bind(pos=self._update_top_bar, size=self._update_top_bar)
        self.layout.add_widget(self.top_bar)

        self.back_btn = IconButton(text="<", font_size=sp(34), color=(0, 0, 0, 1), size_hint=(None, None),
                                   size=(dp(56), dp(56)), pos_hint={"x": 0.03, "center_y": 0.42}, **text_style())
        self.back_btn.bind(on_press=self.go_back)
        self.top_bar.add_widget(self.back_btn)

        self.title_label = Label(text="我的订单", font_size=sp(22), bold=True, color=(1, 1, 1, 1),
                                 size_hint=(0.7, None), height=dp(36), pos_hint={"center_x": 0.52, "center_y": 0.42},
                                 halign="center", valign="middle", **text_style())
        self.title_label.bind(size=self.title_label.setter("text_size"))
        self.top_bar.add_widget(self.title_label)

        self.scroll = ScrollView(size_hint=(1, None), do_scroll_x=False, pos_hint={"x": 0, "y": 0})
        self.layout.add_widget(self.scroll)
        self.content_box = BoxLayout(orientation="vertical", spacing=0, size_hint=(1, None))
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

    def refresh_orders(self):
        self.content_box.clear_widgets()
        app = App.get_running_app()
        username = app.current_user["username"] if app and app.current_user else ""
        orders = STORE_DB.get_orders(username)
        if not orders:
            empty = Label(text="暂无订单", font_size=sp(16), color=(0.45, 0.45, 0.45, 1), size_hint=(1, None),
                          height=dp(60), halign="center", valign="middle", **text_style())
            empty.bind(size=empty.setter("text_size"))
            self.content_box.add_widget(empty)
            return
        for order in orders:
            self.content_box.add_widget(OrderRow(order, on_open=self.open_product_detail))

    def open_product_detail(self, product_id):
        detail_screen = self.manager.get_screen("product_detail")
        detail_screen.set_product(product_id, from_tab="我的订单", return_screen="order")
        self.manager.current = "product_detail"

    def sync_product_views(self, tab_name=None):
        self.refresh_orders()

    def go_back(self, _instance=None):
        if self.manager and self.manager.has_screen(self.return_screen):
            self.manager.current = self.return_screen


class MyPageScreen(Screen):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.name = "mypage"
        self.build_ui()

    def build_ui(self):
        self.layout = FloatLayout()
        self.add_widget(self.layout)
        with self.layout.canvas.before:
            Color(0.97, 0.98, 0.97, 1)
            self.bg_rect = Rectangle(pos=self.layout.pos, size=self.layout.size)
        self.layout.bind(pos=self._update_bg, size=self._update_bg)

        self.scroll = ScrollView(size_hint=(1, None), do_scroll_x=False, pos_hint={"x": 0, "y": 0.10})
        self.layout.add_widget(self.scroll)
        self.content_box = BoxLayout(orientation="vertical", spacing=dp(14), padding=(dp(14), dp(56), dp(14), dp(18)),
                                     size_hint=(1, None))
        self.content_box.bind(minimum_height=self.content_box.setter("height"))
        self.scroll.add_widget(self.content_box)

        self.profile_card = BoxLayout(orientation="horizontal", spacing=dp(12), padding=(dp(14), dp(20), dp(14), dp(14)), size_hint=(1, None),
                                      height=dp(100))
        self.profile_card.bind(pos=self._paint_card, size=self._paint_card)

        avatar_container = FloatLayout(size_hint=(None, 1), width=dp(78))
        self.avatar_placeholder = GrayPlaceholder(radius=1, size_hint=(None, None), size=(dp(78), dp(78)))
        self.avatar_placeholder.pos_hint = {"center_x": 0.5, "center_y": 0.5}
        self.avatar_image = CircleImage(source="", size_hint=(None, None), size=(dp(78), dp(78)))
        self.avatar_image.pos_hint = {"center_x": 0.5, "center_y": 0.5}
        avatar_container.add_widget(self.avatar_placeholder)
        self.avatar_box = avatar_container
        self.avatar_box.bind(
            on_press=lambda *_: App.get_running_app().show_capture_menu(after_action=self._on_avatar_captured))
        self.profile_card.add_widget(self.avatar_box)

        text_container = BoxLayout(orientation="vertical", spacing=dp(4), size_hint=(1, 1))
        text_container.add_widget(Widget(size_hint=(1, None), height=dp(16)))

        self.nick_label = UnderlineLabel(
            text="[u]test[/u]",
            color=GREEN,
            font_size=sp(19),
            size_hint=(1, None),
            height=dp(30),
            halign="left",
            valign="middle",
            **text_style()
        )
        self.nick_label.bind(size=self.nick_label.setter("text_size"))
        self.nick_label.bind(on_press=lambda *_: self.edit_profile_field("nick_name", "编辑昵称", self.nick_name))
        text_container.add_widget(self.nick_label)

        self.signature_label = UnderlineLabel(
            text="[u]欢迎光临我的开心菜园！[/u]",
            color=(0.28, 0.28, 0.28, 1),
            font_size=sp(14),
            size_hint=(1, None),
            height=dp(26),
            halign="left",
            valign="middle",
            **text_style()
        )
        self.signature_label.bind(size=self.signature_label.setter("text_size"))
        self.signature_label.bind(on_press=lambda *_: self.edit_profile_field("signature", "编辑签名", self.signature))
        text_container.add_widget(self.signature_label)

        self.stats_row = BoxLayout(size_hint=(1, None), height=dp(24), spacing=dp(12))
        text_container.add_widget(self.stats_row)
        text_container.add_widget(Widget(size_hint=(1, None), height=dp(6)))

        self.profile_card.add_widget(text_container)
        self.content_box.add_widget(self.profile_card)

        self.menu_box = BoxLayout(orientation="vertical", spacing=dp(8), padding=dp(12), size_hint=(1, None),
                                  height=dp(280))
        self.menu_box.bind(pos=self._paint_card, size=self._paint_card)
        for title, callback in [
            ("我的档案", self.open_profile_editor),
            ("我的订单", self.open_orders),
            ("我的反馈", lambda *_: open_text_popup("我的反馈", "即将推出")),
            ("客服服务", lambda *_: open_text_popup("客服服务", "即将推出")),
            ("退出登录", self.logout),
        ]:
            btn = Button(
                text=title,
                background_normal="",
                background_down="",
                background_color=(0, 0, 0, 0),
                color=(0.12, 0.12, 0.12, 1),
                halign="left",
                **text_style()
            )
            btn.bind(on_press=callback)
            self.menu_box.add_widget(btn)
        self.content_box.add_widget(self.menu_box)

        self.bottom_nav = HomeScreen._build_bottom_nav(self, "mypage")
        for child in self.bottom_nav.children:
            if isinstance(child, Button) and child.text == "我的":
                child.color = GREEN
            elif isinstance(child, Button):
                child.color = (0.32, 0.32, 0.32, 1)
        self.layout.add_widget(self.bottom_nav)
        self.layout.bind(size=self._update_layout)
        Clock.schedule_once(lambda dt: self._update_layout(), 0)

    def on_pre_enter(self, *args):
        self.refresh_profile()
        return super().on_pre_enter(*args)

    def _update_bg(self, *_args):
        self.bg_rect.pos = self.layout.pos
        self.bg_rect.size = self.layout.size

    def _update_layout(self, *_args):
        self.scroll.height = self.height - self.bottom_nav.height
        self.scroll.pos = (0, self.bottom_nav.height)

    def _paint_card(self, instance, *_args):
        instance.canvas.before.clear()
        with instance.canvas.before:
            Color(1, 1, 1, 1)
            RoundedRectangle(pos=instance.pos, size=instance.size, radius=[dp(16)] * 4)

    def refresh_profile(self):
        app = App.get_running_app()
        user = app.refresh_current_user()
        self.nick_name = user["username"] if user else "test"
        self.signature = user["signature"] if user else "欢迎光临我的开心菜园！"
        self.nick_label.text = f"[u]{self.nick_name}[/u]"
        self.signature_label.text = f"[u]{self.signature}[/u]"
        self.stats_row.clear_widgets()
        following = user["following_count"] if user else 0
        followers = user["followers_count"] if user else 0
        share = user["share_count"] if user else 0
        for text in [f"关注 {following}", f"粉丝 {followers}", f"分享 {share}"]:
            label = Label(text=text, font_size=sp(12), color=(0.45, 0.45, 0.45, 1), **text_style())
            self.stats_row.add_widget(label)
        avatar_path = user["avatar_path"] if user else ""
        if avatar_path and os.path.exists(avatar_path):
            if self.avatar_placeholder.parent == self.avatar_box:
                self.avatar_box.clear_widgets()
                self.avatar_box.add_widget(self.avatar_image)
            self.avatar_image.source = avatar_path
            self.avatar_image.reload()
        else:
            if self.avatar_image.parent == self.avatar_box:
                self.avatar_box.clear_widgets()
                self.avatar_box.add_widget(self.avatar_placeholder)

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
        popup = Popup(title="", separator_height=0, size_hint=(0.84, None), height=dp(240))
        box = BoxLayout(orientation="vertical", spacing=dp(12), padding=dp(16))
        with box.canvas.before:
            Color(0.16, 0.16, 0.16, 0.96)
            bg_rect = RoundedRectangle(pos=box.pos, size=box.size, radius=[dp(16)] * 4)
        box.bind(pos=lambda instance, *_: _update_popup_rect(instance, bg_rect),
                 size=lambda instance, *_: _update_popup_rect(instance, bg_rect))
        title_label = Label(
            text=title,
            font_size=sp(18),
            color=(1, 1, 1, 1),
            size_hint=(1, None),
            height=dp(28),
            halign="center",
            valign="middle",
            **text_style()
        )
        title_label.bind(size=title_label.setter("text_size"))
        box.add_widget(title_label)
        input_box = TextInput(
            text=current_value,
            multiline=False,
            input_type="text",
            keyboard_suggestions=True,
            background_normal="",
            background_active="",
            background_color=(0.94, 0.94, 0.94, 1),
            **text_style()
        )
        box.add_widget(input_box)
        save_btn = RoundedButton(text="保存", color=(1, 1, 1, 1), size_hint=(1, None), height=dp(44), **text_style())

        def save_value(_instance=None):
            app = App.get_running_app()
            if not app.current_user:
                popup.dismiss()
                return
            value = input_box.text.strip()
            if field_name == "nick_name":
                USER_DB.update_profile(app.current_user["username"], nick_name=value or "开心菜园阿伯")
            else:
                USER_DB.update_profile(app.current_user["username"], signature=value or "欢迎光临我的开心菜园！")
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


class FavoriteScreen(StoreCategoryScreen):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.name = "favorite"
        self.title_label.text = "我的收藏"

    def on_pre_enter(self, *args):
        self.refresh_products()
        return super().on_pre_enter(*args)

    def set_category(self, category_name="我的收藏"):
        self.current_category = "我的收藏"
        self.title_label.text = "我的收藏"
        self.refresh_products()

    def refresh_products(self):
        app = App.get_running_app()
        username = app.current_user["username"] if app.current_user else ""
        products = STORE_DB.get_favorite_products(username)
        if not products:
            self.product_rv.data = []
            self.product_rv.content_box.clear_widgets()
            empty = Label(text="暂无收藏商品", font_size=sp(16), color=(0.45, 0.45, 0.45, 1), size_hint=(1, None),
                          height=dp(60), halign="center", valign="middle", **text_style())
            empty.bind(size=empty.setter("text_size"))
            self.product_rv.content_box.add_widget(empty)
            return
        self.product_rv.data = [
            {
                "product_id": product["id"],
                "name_text": product["name"],
                "specification_text": product["specification"],
                "price_text": f"￥{product['price']:.2f}",
                "sold_text": f"已售 {product['sold_count']}",
                "from_tab_text": "我的收藏",
                "return_screen_name": "favorite",
                "screen_ref": self,
            }
            for product in products
        ]

    def open_product_detail(self, product_id):
        detail_screen = self.manager.get_screen("product_detail")
        detail_screen.set_product(product_id, from_tab="我的收藏", return_screen="favorite")
        self.manager.current = "product_detail"

    def go_back(self, _instance=None):
        self.manager.current = "home"


class EncyclopediaScreen(Screen):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.name = "encyclopedia"
        self.build_ui()

    def build_ui(self):
        self.layout = FloatLayout()
        self.add_widget(self.layout)
        with self.layout.canvas.before:
            Color(0.97, 0.97, 0.97, 1)
            self.bg_rect = Rectangle(pos=self.layout.pos, size=self.layout.size)
        self.layout.bind(pos=self._update_bg, size=self._update_bg)
        self.top_bar = FloatLayout(size_hint=(1, None), height=dp(92), pos_hint={"x": 0, "top": 1})
        with self.top_bar.canvas.before:
            Color(*GREEN)
            self.top_bar_rect = Rectangle(pos=self.top_bar.pos, size=self.top_bar.size)
        self.top_bar.bind(pos=self._update_top_bar, size=self._update_top_bar)
        self.layout.add_widget(self.top_bar)
        self.back_btn = IconButton(text="<", font_size=sp(34), color=(0, 0, 0, 1), size_hint=(None, None),
                                   size=(dp(56), dp(56)), pos_hint={"x": 0.03, "center_y": 0.42}, **text_style())
        self.back_btn.bind(on_press=lambda *_: setattr(self.manager, "current", "home"))
        self.top_bar.add_widget(self.back_btn)
        self.title_label = Label(text="虫害百科", font_size=sp(22), color=(1, 1, 1, 1), size_hint=(0.6, None),
                                 height=dp(36), pos_hint={"center_x": 0.52, "center_y": 0.42}, halign="center",
                                 valign="middle", **text_style())
        self.title_label.bind(size=self.title_label.setter("text_size"))
        self.top_bar.add_widget(self.title_label)
        self.scroll = ScrollView(size_hint=(1, None), do_scroll_x=False, pos_hint={"x": 0, "y": 0})
        self.layout.add_widget(self.scroll)
        self.content_box = BoxLayout(orientation="vertical", spacing=0, size_hint=(1, None))
        self.content_box.bind(minimum_height=self.content_box.setter("height"))
        self.scroll.add_widget(self.content_box)
        self.layout.bind(size=self._update_layout)
        Clock.schedule_once(lambda dt: self._update_layout(), 0)

    def on_pre_enter(self, *args):
        self.refresh_data()
        return super().on_pre_enter(*args)

    def _update_bg(self, *_args):
        self.bg_rect.pos = self.layout.pos
        self.bg_rect.size = self.layout.size

    def _update_top_bar(self, *_args):
        self.top_bar_rect.pos = self.top_bar.pos
        self.top_bar_rect.size = self.top_bar.size

    def _update_layout(self, *_args):
        self.scroll.height = self.height - self.top_bar.height

    def refresh_data(self):
        self.content_box.clear_widgets()
        pests = STORE_DB.get_pest_entries()
        if not pests:
            empty = Label(text="暂无数据", font_size=sp(16), color=(0.45, 0.45, 0.45, 1), size_hint=(1, None),
                          height=dp(60), halign="center", valign="middle", **text_style())
            empty.bind(size=empty.setter("text_size"))
            self.content_box.add_widget(empty)
            return
        for pest in pests:
            self.content_box.add_widget(PestListRow(pest, on_open=self.open_pest_detail))

    def open_pest_detail(self, pest_id):
        detail_screen = self.manager.get_screen("pest_detail")
        detail_screen.set_pest(pest_id)
        self.manager.current = "pest_detail"


class PestDetailScreen(Screen):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.name = "pest_detail"
        self.current_pest_id = None
        self.build_ui()

    def build_ui(self):
        self.layout = FloatLayout()
        self.add_widget(self.layout)
        with self.layout.canvas.before:
            Color(1, 1, 1, 1)
            self.bg_rect = Rectangle(pos=self.layout.pos, size=self.layout.size)
        self.layout.bind(pos=self._update_bg, size=self._update_bg)
        self.top_bar = FloatLayout(size_hint=(1, None), height=dp(92), pos_hint={"x": 0, "top": 1})
        with self.top_bar.canvas.before:
            Color(*GREEN)
            self.top_bar_rect = Rectangle(pos=self.top_bar.pos, size=self.top_bar.size)
        self.top_bar.bind(pos=self._update_top_bar, size=self._update_top_bar)
        self.layout.add_widget(self.top_bar)
        self.back_btn = IconButton(text="<", font_size=sp(34), color=(0, 0, 0, 1), size_hint=(None, None),
                                   size=(dp(56), dp(56)), pos_hint={"x": 0.03, "center_y": 0.42}, **text_style())
        self.back_btn.bind(on_press=lambda *_: setattr(self.manager, "current", "encyclopedia"))
        self.top_bar.add_widget(self.back_btn)
        self.title_label = Label(text="病虫害详情", font_size=sp(22), color=(1, 1, 1, 1), size_hint=(0.6, None),
                                 height=dp(36), pos_hint={"center_x": 0.52, "center_y": 0.42}, halign="center",
                                 valign="middle", **text_style())
        self.title_label.bind(size=self.title_label.setter("text_size"))
        self.top_bar.add_widget(self.title_label)
        self.scroll = ScrollView(size_hint=(1, None), do_scroll_x=False, pos_hint={"x": 0, "y": 0})
        self.layout.add_widget(self.scroll)
        self.content_box = BoxLayout(orientation="vertical", spacing=dp(14), padding=(dp(16), dp(12), dp(16), dp(20)),
                                     size_hint=(1, None))
        self.content_box.bind(minimum_height=self.content_box.setter("height"))
        self.scroll.add_widget(self.content_box)
        self.photo = GrayPlaceholder(size_hint=(1, None), height=dp(220))
        self.content_box.add_widget(self.photo)
        self.name_label = Label(text="", font_size=sp(24), bold=True, color=(0.12, 0.12, 0.12, 1), size_hint=(1, None),
                                height=dp(36), halign="left", valign="middle", **text_style())
        self.name_label.bind(size=self.name_label.setter("text_size"))
        self.content_box.add_widget(self.name_label)
        self.intro_label = Label(text="", font_size=sp(15), color=(0.18, 0.18, 0.18, 1), size_hint=(1, None),
                                 halign="left", valign="top", **text_style())
        self.intro_label.bind(texture_size=self._sync_label_height, width=self._sync_label_width)
        self.content_box.add_widget(self.intro_label)
        self.treatment_label = Label(text="", font_size=sp(15), color=(0.18, 0.18, 0.18, 1), size_hint=(1, None),
                                     halign="left", valign="top", **text_style())
        self.treatment_label.bind(texture_size=self._sync_label_height, width=self._sync_label_width)
        self.content_box.add_widget(self.treatment_label)
        action_box = BoxLayout(size_hint=(1, None), height=dp(48), spacing=dp(12))
        expert_btn = RoundedButton(text="问问专家", color=(1, 1, 1, 1), **text_style())
        expert_btn.bind(on_press=lambda *_: setattr(self.manager, "current", "expert"))
        action_box.add_widget(expert_btn)
        recognize_btn = RoundedButton(text="拍照识别", color=(1, 1, 1, 1), **text_style())
        recognize_btn.bind(on_press=lambda *_: App.get_running_app().show_capture_menu())
        action_box.add_widget(recognize_btn)
        self.content_box.add_widget(action_box)
        self.layout.bind(size=self._update_layout)
        Clock.schedule_once(lambda dt: self._update_layout(), 0)

    def _update_bg(self, *_args):
        self.bg_rect.pos = self.layout.pos
        self.bg_rect.size = self.layout.size

    def _update_top_bar(self, *_args):
        self.top_bar_rect.pos = self.top_bar.pos
        self.top_bar_rect.size = self.top_bar.size

    def _update_layout(self, *_args):
        self.scroll.height = self.height - self.top_bar.height

    def _sync_label_width(self, instance, _value):
        instance.text_size = (instance.width, None)

    def _sync_label_height(self, instance, _value):
        instance.height = max(dp(80), instance.texture_size[1] + dp(6))

    def set_pest(self, pest_id):
        self.current_pest_id = pest_id
        pest = STORE_DB.get_pest_entry(pest_id)
        if not pest:
            self.name_label.text = "暂无数据"
            self.intro_label.text = ""
            self.treatment_label.text = ""
            return
        self.name_label.text = pest["name"]
        self.intro_label.text = f"介绍：{pest['intro']}"
        self.treatment_label.text = f"防治方法：{pest['treatment']}"


class ExpertScreen(BaseScreen):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.name = "expert"
        self.setup_background("image/expert.jpg")

    def on_touch_down(self, touch):
        if self.is_in_relative_area(touch.x, touch.y, (0.0, 0.865, 0.2, 1.0)):
            self.manager.current = "home"
        return True


class MapScreen(BaseScreen):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.name = "map"
        self.setup_background("image/map.jpg")

    def on_touch_down(self, touch):
        if self.is_in_relative_area(touch.x, touch.y, (0.0, 0.865, 0.2, 1.0)):
            self.manager.current = "home"
        return True


class CameraScreen(Screen):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.name = "camera"
        self.camera = None
        self.camera_rotation = None
        self.capture_in_progress = False
        self.build_ui()

    def build_ui(self):
        self.layout = FloatLayout()
        self.add_widget(self.layout)

        self.camera_container = FloatLayout(size_hint=(1, 1), pos_hint={"x": 0, "y": 0})
        self.layout.add_widget(self.camera_container)

        self.status_label = Label(
            text="",
            font_size=sp(14),
            color=(1, 1, 1, 1),
            size_hint=(0.84, None),
            height=dp(36),
            pos_hint={"center_x": 0.5, "top": 0.90},
            halign="center",
            valign="middle",
            **text_style(),
        )
        self.status_label.bind(size=self.status_label.setter("text_size"))
        self.layout.add_widget(self.status_label)

        self.back_btn = IconButton(
            text="<",
            font_size=sp(34),
            color=(0, 0, 0, 1),
            size_hint=(None, None),
            size=(dp(56), dp(56)),
            pos_hint={"x": 0.03, "top": 0.98},
            **text_style(),
        )
        self.back_btn.bind(on_press=self.go_back)
        self.layout.add_widget(self.back_btn)

        self.capture_btn = Button(
            text="",
            background_normal="",
            background_down="",
            background_color=(0, 0, 0, 0),
            size_hint=(None, None),
            size=(dp(86), dp(86)),
            pos_hint={"center_x": 0.5, "y": 0.08},
            border=(0, 0, 0, 0),
        )
        self.capture_btn.bind(on_press=self.take_photo)
        self.capture_btn.bind(pos=self._update_capture_circle, size=self._update_capture_circle)
        self.layout.add_widget(self.capture_btn)

        self.capture_label = Label(
            text="点击拍照",
            font_size=sp(12),
            color=(1, 1, 1, 1),
            size_hint=(0.40, None),
            height=dp(24),
            pos_hint={"center_x": 0.5, "y": 0.035},
            halign="center",
            valign="middle",
            **text_style(),
        )
        self.capture_label.bind(size=self.capture_label.setter("text_size"))
        self.layout.add_widget(self.capture_label)

        Clock.schedule_once(lambda dt: self._update_capture_circle(), 0)

    def _update_capture_circle(self, *_args):
        self.capture_btn.canvas.before.clear()
        with self.capture_btn.canvas.before:
            Color(0, 0, 0, 1)
            Ellipse(pos=(self.capture_btn.x - dp(4), self.capture_btn.y - dp(4)),
                    size=(self.capture_btn.width + dp(8), self.capture_btn.height + dp(8)))
            Color(1, 1, 1, 0.96)
            Ellipse(pos=self.capture_btn.pos, size=self.capture_btn.size)

    def on_pre_enter(self, *args):
        self._force_portrait_preview()
        self._request_camera_permission()
        return super().on_pre_enter(*args)

    def on_leave(self, *args):
        if self.camera:
            self.camera.play = False
        return super().on_leave(*args)

    def _request_camera_permission(self):
        if not is_android():
            self._enable_camera()
            return
        try:
            permissions_module = import_module("android.permissions")
            permission_class = getattr(permissions_module, "Permission")
            check_permission_func = getattr(permissions_module, "check_permission")
            request_permissions_func = getattr(permissions_module, "request_permissions")
        except Exception as exc:
            self._show_status(f"相机权限模块加载失败: {exc}")
            return

        camera_permission = permission_class.CAMERA

        if check_permission_func(camera_permission):
            self._enable_camera()
            return

        def callback(_permissions, grants):
            if grants and grants[0]:
                Clock.schedule_once(lambda dt: self._enable_camera())
            else:
                Clock.schedule_once(lambda dt: self._show_status("未授予相机权限，无法拍照"))

        request_permissions_func([camera_permission], callback)

    def _force_portrait_preview(self):
        if not is_android():
            return
        try:
            autoclass = import_module("jnius").autoclass
            activity = autoclass("org.kivy.android.PythonActivity").mActivity
            activity_info = autoclass("android.content.pm.ActivityInfo")
            activity.setRequestedOrientation(activity_info.SCREEN_ORIENTATION_PORTRAIT)
        except Exception:
            pass

    def _layout_camera_preview(self, *_args):
        if not self.camera:
            return

        if not is_android():
            self.camera.size_hint = (1, 1)
            self.camera.pos_hint = {"x": 0, "y": 0}
            self.camera.canvas.before.clear()
            self.camera.canvas.after.clear()
            return

        width = self.camera_container.width or Window.width
        height = self.camera_container.height or Window.height
        if width <= 0 or height <= 0:
            return

        self.camera.size_hint = (None, None)
        self.camera.size = (height, width)
        self.camera.pos = (
            self.camera_container.center_x - self.camera.width / 2,
            self.camera_container.center_y - self.camera.height / 2,
        )

        self.camera.canvas.before.clear()
        self.camera.canvas.after.clear()
        with self.camera.canvas.before:
            PushMatrix()
            self.camera_rotation = Rotate(angle=-90, origin=self.camera.center)
        with self.camera.canvas.after:
            PopMatrix()

    def _update_camera_transform(self, *_args):
        if self.camera_rotation and self.camera:
            self.camera_rotation.origin = self.camera.center

    def _ensure_camera_widget(self):
        if self.camera is not None:
            return True
        try:
            from kivy.uix.camera import Camera

            self._force_portrait_preview()
            self.camera = Camera(
                resolution=(720, 1280),
                play=False,
                index=0,
                allow_stretch=True,
                keep_ratio=False,
                size_hint=(1, 1),
                pos_hint={"x": 0, "y": 0},
            )
            self.camera_container.clear_widgets()
            self.camera_container.add_widget(self.camera)
            self.camera.bind(pos=self._update_camera_transform, size=self._update_camera_transform)
            self.camera_container.bind(pos=self._layout_camera_preview, size=self._layout_camera_preview)
            Clock.schedule_once(self._layout_camera_preview, 0)
            return True
        except Exception as exc:
            self._show_status(f"摄像头组件加载失败: {exc}")
            return False

    def _enable_camera(self):
        if not self._ensure_camera_widget():
            return
        try:
            self._force_portrait_preview()
            self._layout_camera_preview()
            self.camera.play = True
            self._show_status("")
        except Exception as exc:
            self._show_status(f"打开摄像头失败: {exc}")

    def take_photo(self, _instance):
        if self.capture_in_progress:
            return
        app = App.get_running_app()
        if getattr(app, "camera_mode", "recognize") == "recognize" and not app.can_current_user_recognize():
            show_toast("免费用户每天限识别3次，升级VIP解锁无限次")
            return
        if not self.camera or not self.camera.texture:
            self._show_status("摄像头未就绪，请稍后再试")
            return
        self.capture_in_progress = True
        self.capture_btn.disabled = True
        self._show_status("正在识别...")
        Clock.schedule_once(lambda dt: self._capture_current_frame(), 0.05)

    def _build_photo_path(self):
        os.makedirs("photos", exist_ok=True)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        return os.path.abspath(os.path.join("photos", f"capture_{timestamp}.png"))

    def _capture_current_frame(self):
        image_path = self._build_photo_path()
        try:
            self.camera.export_to_png(image_path)
            app = App.get_running_app()
            if getattr(app, "camera_mode", "recognize") == "avatar":
                app.handle_avatar_capture(image_path)
                self._show_status("")
                self._finish_capture()
                return
            started = app.start_recognition_for_image(
                image_path,
                on_success=self._open_result,
                on_error=self._recognition_failed,
            )
            if not started:
                self._finish_capture()
        except Exception as exc:
            self._show_status(f"保存照片失败: {exc}")
            self._finish_capture()

    @staticmethod
    def _normalize_api_result(data):
        normalized = dict(data)
        confidence = normalized.get("confidence", 0)
        try:
            confidence = float(confidence)
        except Exception:
            confidence = 0
        if confidence > 1:
            confidence = round(confidence / 100, 4)
        normalized["confidence"] = confidence

        treatment = normalized.get("treatment")
        if isinstance(treatment, str):
            normalized["treatment"] = {"method": treatment}
        elif not isinstance(treatment, dict):
            normalized["treatment"] = {"method": normalized.get("treatment_text", "暂无防治建议")}

        normalized["pest_name"] = normalized.get("pest_name") or "未知病虫害"
        normalized["intro"] = normalized.get("intro") or "暂无简介"
        return normalized

    def _open_result(self, image_path, data):
        app = App.get_running_app()
        self._finish_capture()
        app.open_recognition_result(image_path, data)

    def _recognition_failed(self, message):
        self._show_status(message)
        self._finish_capture()

    def _finish_capture(self):
        self.capture_in_progress = False
        self.capture_btn.disabled = False

    def _show_status(self, text):
        self.status_label.text = text

    def go_back(self, _instance=None):
        app = App.get_running_app()
        self.manager.current = app.previous_before_camera or "home"


class ResultScreen(Screen):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.name = "result"
        self.photo_path = ""
        self.build_ui()

    def build_ui(self):
        self.layout = FloatLayout()
        self.add_widget(self.layout)

        with self.layout.canvas.before:
            Color(1, 1, 1, 1)
            self.bg_rect = Rectangle(pos=self.layout.pos, size=self.layout.size)
        self.layout.bind(pos=self._update_bg, size=self._update_bg)

        self.top_bar = FloatLayout(size_hint=(1, None), height=dp(88), pos_hint={"x": 0, "top": 1})
        with self.top_bar.canvas.before:
            Color(*GREEN)
            self.top_bar_rect = Rectangle(pos=self.top_bar.pos, size=self.top_bar.size)
        self.top_bar.bind(pos=self._update_top_bar, size=self._update_top_bar)
        self.layout.add_widget(self.top_bar)

        self.back_btn = IconButton(
            text="<",
            font_size=sp(34),
            color=(0, 0, 0, 1),
            size_hint=(None, None),
            size=(dp(56), dp(56)),
            pos_hint={"x": 0.03, "center_y": 0.42},
            **text_style(),
        )
        self.back_btn.bind(on_press=self.go_back)
        self.top_bar.add_widget(self.back_btn)

        self.name_label = Label(
            text="识别结果",
            font_size=sp(24),
            bold=True,
            color=(0.08, 0.08, 0.08, 1),
            size_hint=(0.88, None),
            height=dp(42),
            pos_hint={"center_x": 0.5, "top": 0.86},
            halign="center",
            valign="middle",
            **text_style(),
        )
        self.name_label.bind(size=self.name_label.setter("text_size"))
        self.layout.add_widget(self.name_label)

        self.photo = CircleImage(
            source="",
            size_hint=(None, None),
            size=(dp(168), dp(168)),
            pos_hint={"center_x": 0.5, "top": 0.72},
        )
        self.layout.add_widget(self.photo)

        self.placeholder = Label(
            text="",
            size_hint=(None, None),
            size=(dp(168), dp(168)),
            pos_hint={"center_x": 0.5, "top": 0.72},
        )
        with self.placeholder.canvas.before:
            Color(0, 0, 0, 1)
            self.placeholder_circle = Ellipse(pos=self.placeholder.pos, size=self.placeholder.size)
        self.placeholder.bind(pos=self._update_placeholder, size=self._update_placeholder)

        self.content_scroll = ScrollView(
            size_hint=(0.88, None),
            do_scroll_x=False,
            bar_width=dp(4),
            scroll_type=["bars", "content"],
            pos_hint={"center_x": 0.5, "y": 0.22},
        )
        self.layout.add_widget(self.content_scroll)

        self.content_box = BoxLayout(
            orientation="vertical",
            spacing=dp(14),
            padding=(0, dp(4), 0, dp(10)),
            size_hint=(1, None),
        )
        self.content_box.bind(minimum_height=self.content_box.setter("height"))
        self.content_scroll.add_widget(self.content_box)

        self.intro_label = Label(
            text="",
            font_size=sp(15),
            color=(0.12, 0.12, 0.12, 1),
            size_hint=(1, None),
            halign="left",
            valign="top",
            **text_style(),
        )
        self.intro_label.bind(texture_size=self._sync_intro_height, width=self._sync_label_width)
        self.content_box.add_widget(self.intro_label)

        self.treatment_label = Label(
            text="",
            font_size=sp(15),
            color=(0.12, 0.12, 0.12, 1),
            size_hint=(1, None),
            halign="left",
            valign="top",
            **text_style(),
        )
        self.treatment_label.bind(texture_size=self._sync_treatment_height, width=self._sync_label_width)
        self.content_box.add_widget(self.treatment_label)

        self.retake_btn = Button(
            text="再拍一个",
            font_size=sp(18),
            background_normal="",
            background_down="",
            background_color=(0, 0, 0, 0),
            color=(1, 1, 1, 1),
            size_hint=(None, None),
            size=(dp(112), dp(112)),
            pos_hint={"center_x": 0.5, "y": 0.04},
            border=(0, 0, 0, 0),
            **text_style(),
        )
        self.retake_btn.bind(on_press=self.retake)
        self.retake_btn.bind(pos=self._update_retake_circle, size=self._update_retake_circle)
        self.layout.add_widget(self.retake_btn)

        self.layout.bind(size=self._update_content_area)
        Clock.schedule_once(lambda dt: self._update_retake_circle(), 0)
        Clock.schedule_once(lambda dt: self._update_content_area(), 0)

    def _update_bg(self, *_args):
        self.bg_rect.pos = self.layout.pos
        self.bg_rect.size = self.layout.size

    def _update_top_bar(self, *_args):
        self.top_bar_rect.pos = self.top_bar.pos
        self.top_bar_rect.size = self.top_bar.size

    def _update_placeholder(self, *_args):
        self.placeholder_circle.pos = self.placeholder.pos
        self.placeholder_circle.size = self.placeholder.size

    def _update_retake_circle(self, *_args):
        self.retake_btn.canvas.before.clear()
        with self.retake_btn.canvas.before:
            Color(*GREEN)
            Ellipse(pos=self.retake_btn.pos, size=self.retake_btn.size)

    def _update_content_area(self, *_args):
        top_limit = self.photo.y - dp(22)
        bottom_limit = self.retake_btn.top + dp(18)
        available_height = max(dp(120), top_limit - bottom_limit)
        self.content_scroll.height = available_height
        self.content_scroll.pos = (self.layout.width * 0.06, bottom_limit)

    def _sync_label_width(self, instance, _value):
        instance.text_size = (instance.width, None)

    def _sync_intro_height(self, instance, _value):
        instance.height = max(dp(70), instance.texture_size[1] + dp(8))

    def _sync_treatment_height(self, instance, _value):
        instance.height = max(dp(110), instance.texture_size[1] + dp(8))

    def set_result(self, image_path, data):
        self.photo_path = image_path
        pest_name = data.get("pest_name", "未知病虫害")
        intro = data.get("intro", "暂无简介")
        treatment = data.get("treatment", {})
        treatment_text = treatment.get("method") or data.get("treatment_text") or "暂无防治建议"
        confidence = data.get("confidence", 0)

        try:
            confidence_text = f"{float(confidence) * 100:.1f}%"
        except Exception:
            confidence_text = str(confidence)

        self.name_label.text = f"{pest_name}  置信度 {confidence_text}"
        self.intro_label.text = f"简介：{intro}"
        self.treatment_label.text = f"防治方法：{treatment_text}"
        self.content_scroll.scroll_y = 1
        Clock.schedule_once(lambda dt: self._update_content_area(), 0)

        if image_path and os.path.exists(image_path):
            if self.placeholder.parent:
                self.layout.remove_widget(self.placeholder)
            self.photo.source = image_path
            self.photo.reload()
            if self.photo.parent is None:
                self.layout.add_widget(self.photo)
        else:
            if self.photo.parent:
                self.layout.remove_widget(self.photo)
            if self.placeholder.parent is None:
                self.layout.add_widget(self.placeholder)

    def go_back(self, _instance=None):
        app = App.get_running_app()
        self.manager.current = app.previous_before_camera or "home"

    def retake(self, _instance=None):
        App.get_running_app().show_capture_menu()


class MyApp(App):
    previous_before_camera = "home"
    current_user = None
    camera_mode = "recognize"

    def build(self):
        screen_manager = ScreenManager()
        screen_manager.add_widget(LoginScreen())
        screen_manager.add_widget(RegisterScreen())
        screen_manager.add_widget(HomeScreen())
        screen_manager.add_widget(CommunityScreen())
        screen_manager.add_widget(CommunityDetailScreen())
        screen_manager.add_widget(StoreScreen())
        screen_manager.add_widget(StoreCategoryScreen())
        screen_manager.add_widget(FavoriteScreen())
        screen_manager.add_widget(OrderScreen())
        screen_manager.add_widget(EncyclopediaScreen())
        screen_manager.add_widget(PestDetailScreen())
        screen_manager.add_widget(MyPageScreen())
        screen_manager.add_widget(ExpertScreen())
        screen_manager.add_widget(MapScreen())
        screen_manager.add_widget(CameraScreen())
        screen_manager.add_widget(ResultScreen())
        screen_manager.add_widget(ProductDetailScreen())
        screen_manager.current = "login"
        return screen_manager

    def set_current_user(self, user):
        self.current_user = dict(user) if user else None

    def open_product_detail_screen(self, product_id, from_tab="精选好物", return_screen="store"):
        try:
            detail_screen = self.root.get_screen("product_detail")
            detail_screen.set_product(product_id, from_tab=from_tab, return_screen=return_screen)
            self.root.current = "product_detail"
        except Exception as exc:
            show_toast(f"打开商品失败: {exc}")

    def refresh_current_user(self):
        if not self.current_user:
            return None
        user = USER_DB.get_user(self.current_user["username"])
        if user:
            self.current_user = user
        return self.current_user

    def can_current_user_recognize(self):
        if not self.current_user:
            show_toast("请先登录")
            return False
        allowed, user = USER_DB.can_recognize_today(self.current_user["username"])
        if user:
            self.current_user = user
        return allowed

    def mark_current_user_recognized(self):
        if not self.current_user:
            return
        self.current_user = USER_DB.increase_recognize_count(self.current_user["username"])

    def handle_avatar_capture(self, image_path):
        self.camera_mode = "recognize"
        register_screen = self.root.get_screen("register")
        register_screen.selected_avatar_source = image_path
        register_screen._show_selected_avatar()
        self.root.current = "register"

    def show_capture_menu(self, after_action=None):
        popup = Popup(title="", separator_height=0, size_hint=(0.82, None), height=dp(228))
        content = BoxLayout(orientation="vertical", spacing=dp(12), padding=dp(14))
        with content.canvas.before:
            Color(0.16, 0.16, 0.16, 0.96)
            bg_rect = RoundedRectangle(pos=content.pos, size=content.size, radius=[dp(16)] * 4)
        content.bind(pos=lambda instance, *_: _update_popup_rect(instance, bg_rect),
                     size=lambda instance, *_: _update_popup_rect(instance, bg_rect))
        title_label = Label(text="选择识别方式", font_size=sp(18), color=(1, 1, 1, 1), size_hint=(1, None),
                            height=dp(28), halign="center", valign="middle", **text_style())
        title_label.bind(size=title_label.setter("text_size"))
        content.add_widget(title_label)
        camera_btn = RoundedButton(text="使用相机", color=(1, 1, 1, 1), size_hint=(1, None), height=dp(44),
                                   **text_style())
        album_btn = RoundedButton(text="使用照片", color=(1, 1, 1, 1), size_hint=(1, None), height=dp(44),
                                  **text_style())
        cancel_btn = RoundedButton(text="取消", color=(1, 1, 1, 1), fill_color=(0.65, 0.65, 0.65, 1),
                                   size_hint=(1, None), height=dp(44), **text_style())
        camera_btn.bind(on_press=lambda *_: self._open_camera_from_menu(popup, after_action))
        album_btn.bind(on_press=lambda *_: self._open_photo_from_menu(popup, after_action))
        cancel_btn.bind(on_press=lambda *_: popup.dismiss())
        content.add_widget(camera_btn)
        content.add_widget(album_btn)
        content.add_widget(cancel_btn)
        popup.content = content
        popup.open()

    def _open_camera_from_menu(self, popup, after_action=None):
        popup.dismiss()
        if is_android() and not is_android_permission_granted("android.permission.CAMERA"):
            show_toast("相机使用失败")
            return
        self.camera_mode = "recognize"
        if callable(after_action):
            after_action("camera")
            return
        if self.root.current != "result":
            self.previous_before_camera = self.root.current
        self.root.current = "camera"

    def _open_photo_from_menu(self, popup, after_action=None):
        if popup is not None:
            popup.dismiss()
        if is_android() and not (is_android_permission_granted(
                "android.permission.READ_EXTERNAL_STORAGE") or is_android_permission_granted(
                "android.permission.READ_MEDIA_IMAGES")):
            show_toast("文件使用失败")
            return
        self.camera_mode = "recognize"
        chooser_popup = Popup(title="", separator_height=0, size_hint=(0.92, 0.82))
        wrapper = BoxLayout(orientation="vertical", spacing=dp(10), padding=dp(10))
        with wrapper.canvas.before:
            Color(0.16, 0.16, 0.16, 0.96)
            bg_rect = RoundedRectangle(pos=wrapper.pos, size=wrapper.size, radius=[dp(16)] * 4)
        wrapper.bind(pos=lambda instance, *_: _update_popup_rect(instance, bg_rect),
                     size=lambda instance, *_: _update_popup_rect(instance, bg_rect))
        title_label = Label(text="选择照片", font_size=sp(18), color=(1, 1, 1, 1), size_hint=(1, None), height=dp(28),
                            halign="center", valign="middle", **text_style())
        title_label.bind(size=title_label.setter("text_size"))
        chooser = FileChooserListView(path=os.path.expanduser("~"), filters=["*.png", "*.jpg", "*.jpeg", "*.bmp"])
        wrapper.add_widget(title_label)
        wrapper.add_widget(chooser)
        btn_row = BoxLayout(size_hint=(1, None), height=dp(44), spacing=dp(10))
        ok_btn = RoundedButton(text="确定", color=(1, 1, 1, 1), **text_style())
        cancel_btn = RoundedButton(text="取消", color=(1, 1, 1, 1), fill_color=(0.65, 0.65, 0.65, 1), **text_style())

        def confirm_pick(_instance=None):
            if not chooser.selection:
                chooser_popup.dismiss()
                return
            image_path = chooser.selection[0]
            chooser_popup.dismiss()
            if callable(after_action):
                after_action("album", image_path)
                return
            if self.root.current != "result":
                self.previous_before_camera = self.root.current
            self.recognize_image_from_file(image_path)

        ok_btn.bind(on_press=confirm_pick)
        cancel_btn.bind(on_press=lambda *_: chooser_popup.dismiss())
        btn_row.add_widget(ok_btn)
        btn_row.add_widget(cancel_btn)
        wrapper.add_widget(btn_row)
        chooser_popup.content = wrapper
        chooser_popup.open()

    def recognize_image_from_file(self, image_path):
        show_toast("正在识别...")
        self.start_recognition_for_image(image_path)

    def start_recognition_for_image(self, image_path, on_success=None, on_error=None):
        if not self.can_current_user_recognize():
            show_toast("免费用户每天限识别3次，升级VIP解锁无限次")
            return False
        threading.Thread(
            target=self._do_recognize_image,
            args=(image_path, on_success, on_error),
            daemon=True,
        ).start()
        return True

    def _do_recognize_image(self, image_path, on_success=None, on_error=None):
        try:
            requests = import_module("requests")
            api_base_url = get_api_base_url()
            with open(image_path, "rb") as file_obj:
                response = requests.post(
                    f"{api_base_url}/predict",
                    files={"file": (os.path.basename(image_path), file_obj, "image/png")},
                    timeout=45,
                )
            if response.status_code != 200:
                Clock.schedule_once(
                    lambda dt: self._handle_recognition_error(
                        f"识别服务返回异常: {response.status_code}",
                        on_error,
                    )
                )
                return

            data = response.json()
            if not data.get("success"):
                Clock.schedule_once(
                    lambda dt: self._handle_recognition_error(
                        f"识别失败: {data.get('error', '未知错误')}",
                        on_error,
                    )
                )
                return

            normalized_data = CameraScreen._normalize_api_result(data)
            Clock.schedule_once(
                lambda dt: self._handle_recognition_success(
                    image_path,
                    normalized_data,
                    on_success,
                )
            )
        except Exception as exc:
            error_message = f"请求失败: {exc}"
            Clock.schedule_once(
                lambda dt: self._handle_recognition_error(
                    error_message,
                    on_error,
                )
            )

    def _handle_recognition_success(self, image_path, data, on_success=None):
        self.mark_current_user_recognized()
        if callable(on_success):
            on_success(image_path, data)
            return
        self.open_recognition_result(image_path, data)

    def _handle_recognition_error(self, message, on_error=None):
        if callable(on_error):
            on_error(message)
            return
        show_toast(message)

    def open_recognition_result(self, image_path, data):
        try:
            if getattr(self, "camera_mode", "recognize") == "avatar":
                self.handle_avatar_capture(image_path)
                return
            if not self.root or not self.root.has_screen("result"):
                show_toast("识别结果页未准备好")
                return
            result_screen = self.root.get_screen("result")
            result_screen.set_result(image_path, data)
            self.root.current = "result"
        except Exception as exc:
            show_toast(f"跳转失败: {exc}")


if __name__ == "__main__":
    os.makedirs("photos", exist_ok=True)
    MyApp().run()

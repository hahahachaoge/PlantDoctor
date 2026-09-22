import os
import sys

# 打包后用exe所在目录，开发时用源码目录
if getattr(sys, 'frozen', False):
    # 打包后的运行路径
    _BASE_DIR = os.path.dirname(sys.executable)
else:
    # 开发时的源码路径
    _BASE_DIR = os.path.dirname(os.path.abspath(__file__))

API_BASE_URL = os.environ.get("PLANT_API_URL", "http://8.148.149.64:8000")
GREEN = (0.12, 0.58, 0.30, 1)
STORE_DB_PATH = os.path.join(_BASE_DIR, "smart_agri.db")
AVATAR_DIR = os.path.join(_BASE_DIR, "avatars")
IMAGE_DIR = os.path.join(_BASE_DIR, "image")
DISEASE_INFO_PATH = os.path.join(_BASE_DIR, "ai_model", "disease_info.json")
DISEASE_METADATA_PATH = os.path.join(_BASE_DIR, "ai_model", "disease_metadata.json")




# 首页「我的工具」图标（直接用用户提供的 UI 图标文件名）
HOME_TOOL_ICONS = {
    "农事计划": os.path.join(IMAGE_DIR, "农事计划.png"),
    "虫害百科": os.path.join(IMAGE_DIR, "虫害百科.png"),
    "我的收藏": os.path.join(IMAGE_DIR, "我的收藏.png"),
    "病虫害分布图": os.path.join(IMAGE_DIR, "病虫害分布图.png"),
}
COMMUNITY_FOCUS_ICONS = {
    "种植经验": os.path.join(IMAGE_DIR, "种植经验.jpg"),
    "防治技巧": os.path.join(IMAGE_DIR, "防治经验.jpg"),
}

# 点赞图标：用户提供的是「深灰描边大拇指」（透明底）。
# 未点赞直接用原色；已点赞需要区分状态，所以用 GREEN 生成一版染色图
# （保留原 alpha、只替换 RGB），缓存到 image/_rounded/ 下，只在缺失时生成一次。
LIKE_ICON_OFF = os.path.join(IMAGE_DIR, "点赞.png")
LIKE_ICON_ON = os.path.join(IMAGE_DIR, "_rounded", "like_on_green.png")


def _make_like_on_icon():
    """生成「已点赞」的绿色大拇指（幂等；失败时静默回退到未点赞图标）。"""
    if not os.path.exists(LIKE_ICON_OFF) or os.path.exists(LIKE_ICON_ON):
        return
    try:
        os.makedirs(os.path.dirname(LIKE_ICON_ON), exist_ok=True)
        from PIL import Image as _PILImage
        src = _PILImage.open(LIKE_ICON_OFF).convert("RGBA")
        solid = _PILImage.new(
            "RGBA", src.size,
            (int(GREEN[0] * 255), int(GREEN[1] * 255), int(GREEN[2] * 255), 255))
        solid.putalpha(src.getchannel("A"))
        solid.save(LIKE_ICON_ON)
    except Exception:
        pass


_make_like_on_icon()

KANDIAN_IMAGES = [
    os.path.join(IMAGE_DIR, "种植经验.jpg"),
    os.path.join(IMAGE_DIR, "防治经验.jpg"),
]
KANDIAN_TITLES = ["种植经验", "防治技巧"]

STORE_TABS = ["精选好物", "热销榜单", "肥料", "杀虫剂"]
DEFAULT_COMMENT_USER = "开心的菜园伯伯"
STORE_CATALOG_VERSION = "2026-05-10-v4"

STORE_PRODUCTS_SEED = [
    {"id": 2001, "name": "复合微生物菌剂", "category": "精选好物", "sub_category": "精选",
     "specification": "5kg", "price": 65.0, "sold_count": 0, "stock": 999,
     "image": "gray_placeholder", "description": "改善土壤环境，促进作物根系健壮生长。",
     "is_hot": 0, "is_featured": 1},
    {"id": 2002, "name": "高效氯氟氰菊酯", "category": "精选好物", "sub_category": "精选",
     "specification": "500ml", "price": 35.0, "sold_count": 0, "stock": 999,
     "image": "gray_placeholder", "description": "适合多种刺吸式害虫的日常防治。",
     "is_hot": 0, "is_featured": 1},
    {"id": 2003, "name": "电动背负式喷雾器", "category": "精选好物", "sub_category": "精选",
     "specification": "20L", "price": 189.0, "sold_count": 0, "stock": 300,
     "image": "gray_placeholder", "description": "容量充足，适合大棚和果园喷施作业。",
     "is_hot": 0, "is_featured": 1},
    {"id": 2004, "name": "农用粘虫板（黄色）", "category": "精选好物", "sub_category": "精选",
     "specification": "20张/包", "price": 15.0, "sold_count": 0, "stock": 500,
     "image": "gray_placeholder", "description": "用于诱杀蚜虫、白粉虱等小型飞虫。",
     "is_hot": 0, "is_featured": 1},
    {"id": 2005, "name": "修枝剪+园艺手套套装", "category": "精选好物", "sub_category": "精选",
     "specification": "套装", "price": 45.0, "sold_count": 0, "stock": 280,
     "image": "gray_placeholder", "description": "适合日常修枝、整形和园艺维护。",
     "is_hot": 0, "is_featured": 1},
    {"id": 2101, "name": "草铵膦", "category": "精选好物", "sub_category": "热销",
     "specification": "1000ml", "price": 45.0, "sold_count": 0, "stock": 999,
     "image": "gray_placeholder", "description": "常用于田间杂草防除，使用方便。",
     "is_hot": 1, "is_featured": 0},
    {"id": 2102, "name": "吡虫啉", "category": "精选好物", "sub_category": "热销",
     "specification": "100g", "price": 12.0, "sold_count": 0, "stock": 999,
     "image": "gray_placeholder", "description": "防治蚜虫、飞虱等常见刺吸式害虫。",
     "is_hot": 1, "is_featured": 0},
    {"id": 2103, "name": "阿维菌素", "category": "精选好物", "sub_category": "热销",
     "specification": "200ml", "price": 28.0, "sold_count": 0, "stock": 999,
     "image": "gray_placeholder", "description": "适合红蜘蛛、潜叶害虫等防控使用。",
     "is_hot": 1, "is_featured": 0},
    {"id": 2104, "name": "硫酸钾复合肥", "category": "精选好物", "sub_category": "热销",
     "specification": "50kg", "price": 180.0, "sold_count": 0, "stock": 260,
     "image": "gray_placeholder", "description": "氮磷钾均衡补充，适合多种作物。",
     "is_hot": 1, "is_featured": 0},
    {"id": 2105, "name": "电动果树修剪机", "category": "精选好物", "sub_category": "热销",
     "specification": "锂电池", "price": 299.0, "sold_count": 0, "stock": 120,
     "image": "gray_placeholder", "description": "适合果树修枝整形，提高作业效率。",
     "is_hot": 1, "is_featured": 0},
    {"id": 2201, "name": "硫酸钾复合肥", "category": "精选好物", "sub_category": "肥料",
     "specification": "50kg", "price": 180.0, "sold_count": 0, "stock": 260,
     "image": "gray_placeholder", "description": "适合作物整个生育期基础追肥管理。",
     "is_hot": 0, "is_featured": 0},
    {"id": 2202, "name": "磷酸二氢钾", "category": "精选好物", "sub_category": "肥料",
     "specification": "1000g", "price": 25.0, "sold_count": 0, "stock": 999,
     "image": "gray_placeholder", "description": "花果期补磷补钾，提高作物长势。",
     "is_hot": 0, "is_featured": 0},
    {"id": 2203, "name": "生物有机肥", "category": "精选好物", "sub_category": "肥料",
     "specification": "40kg", "price": 95.0, "sold_count": 0, "stock": 500,
     "image": "gray_placeholder", "description": "富含有机质，适合改良土壤结构。",
     "is_hot": 0, "is_featured": 0},
    {"id": 2204, "name": "大量元素水溶肥（平衡型）", "category": "精选好物", "sub_category": "肥料",
     "specification": "5kg", "price": 65.0, "sold_count": 0, "stock": 420,
     "image": "gray_placeholder", "description": "平衡补充氮磷钾，适合滴灌冲施。",
     "is_hot": 0, "is_featured": 0},
    {"id": 2205, "name": "腐植酸水溶肥", "category": "精选好物", "sub_category": "肥料",
     "specification": "10kg", "price": 80.0, "sold_count": 0, "stock": 380,
     "image": "gray_placeholder", "description": "促进养分吸收，缓解黄叶弱苗。",
     "is_hot": 0, "is_featured": 0},
    {"id": 2206, "name": "枯草芽孢杆菌微生物菌剂", "category": "精选好物", "sub_category": "肥料",
     "specification": "1kg", "price": 38.0, "sold_count": 0, "stock": 460,
     "image": "gray_placeholder", "description": "调节根际环境，增强作物抗逆能力。",
     "is_hot": 0, "is_featured": 0},
    {"id": 2301, "name": "吡虫啉", "category": "精选好物", "sub_category": "杀虫剂",
     "specification": "100g", "price": 12.0, "sold_count": 0, "stock": 999,
     "image": "gray_placeholder", "description": "适合防治蚜虫、飞虱、粉虱等害虫。",
     "is_hot": 0, "is_featured": 0},
    {"id": 2302, "name": "甲维盐", "category": "精选好物", "sub_category": "杀虫剂",
     "specification": "100ml", "price": 22.0, "sold_count": 0, "stock": 999,
     "image": "gray_placeholder", "description": "适合鳞翅目幼虫防治使用。",
     "is_hot": 0, "is_featured": 0},
    {"id": 2303, "name": "氯虫苯甲酰胺", "category": "精选好物", "sub_category": "杀虫剂",
     "specification": "100ml", "price": 58.0, "sold_count": 0, "stock": 680,
     "image": "gray_placeholder", "description": "持效较长，适合咀嚼式害虫防控。",
     "is_hot": 0, "is_featured": 0},
    {"id": 2304, "name": "阿维菌素", "category": "精选好物", "sub_category": "杀虫剂",
     "specification": "200ml", "price": 28.0, "sold_count": 0, "stock": 999,
     "image": "gray_placeholder", "description": "适合潜叶虫和螨类害虫综合防治。",
     "is_hot": 0, "is_featured": 0},
    {"id": 2305, "name": "噻虫嗪", "category": "精选好物", "sub_category": "杀虫剂",
     "specification": "100g", "price": 18.0, "sold_count": 0, "stock": 999,
     "image": "gray_placeholder", "description": "内吸传导性较强，适合苗期管理。",
     "is_hot": 0, "is_featured": 0},
    {"id": 2306, "name": "高效氯氟氰菊酯", "category": "精选好物", "sub_category": "杀虫剂",
     "specification": "500ml", "price": 35.0, "sold_count": 0, "stock": 999,
     "image": "gray_placeholder", "description": "触杀效果明显，适合害虫暴发初期。",
     "is_hot": 0, "is_featured": 0},
    {"id": 2401, "name": "敌敌畏", "category": "商城首页", "sub_category": "广告",
     "specification": "500ml", "price": 26.0, "sold_count": 0, "stock": 500,
     "image": "gray_placeholder", "description": "经典常见农药示例商品。",
     "is_hot": 1, "is_featured": 0},
    {"id": 2402, "name": "乙酰甲胺磷", "category": "热销榜单", "sub_category": "热销榜单",
     "specification": "500ml", "price": 33.0, "sold_count": 0, "stock": 500,
     "image": "gray_placeholder", "description": "商城首页热销榜单展示商品。",
     "is_hot": 1, "is_featured": 0},
    {"id": 2403, "name": "乙蒜素", "category": "热销榜单", "sub_category": "热销榜单",
     "specification": "300ml", "price": 29.0, "sold_count": 0, "stock": 500,
     "image": "gray_placeholder", "description": "商城首页热销榜单展示商品。",
     "is_hot": 1, "is_featured": 0},
    {"id": 2404, "name": "百草枯", "category": "热销榜单", "sub_category": "热销榜单",
     "specification": "500ml", "price": 31.0, "sold_count": 0, "stock": 500,
     "image": "gray_placeholder", "description": "商城首页热销榜单展示商品。",
     "is_hot": 1, "is_featured": 0},
    {"id": 2405, "name": "乐果", "category": "热销榜单", "sub_category": "热销榜单",
     "specification": "500ml", "price": 24.0, "sold_count": 0, "stock": 500,
     "image": "gray_placeholder", "description": "商城首页热销榜单展示商品。",
     "is_hot": 1, "is_featured": 0},
    {"id": 2406, "name": "镁立硼复合肥料40kg", "category": "肥料", "sub_category": "肥料推荐",
     "specification": "40kg", "price": 168.0, "sold_count": 0, "stock": 300,
     "image": "gray_placeholder", "description": "商城首页肥料推荐展示商品。",
     "is_hot": 0, "is_featured": 0},
    {"id": 2407, "name": "镁立硼复合肥料25kg", "category": "肥料", "sub_category": "肥料推荐",
     "specification": "25kg", "price": 118.0, "sold_count": 0, "stock": 300,
     "image": "gray_placeholder", "description": "商城首页肥料推荐展示商品。",
     "is_hot": 0, "is_featured": 0},
    {"id": 2408, "name": "杀虫饵剂", "category": "杀虫剂", "sub_category": "杀虫剂推荐",
     "specification": "500g", "price": 19.0, "sold_count": 0, "stock": 400,
     "image": "gray_placeholder", "description": "商城首页杀虫剂推荐展示商品。",
     "is_hot": 0, "is_featured": 0},
    {"id": 2409, "name": "吡虫啉", "category": "杀虫剂", "sub_category": "杀虫剂推荐",
     "specification": "100g", "price": 12.0, "sold_count": 0, "stock": 400,
     "image": "gray_placeholder", "description": "商城首页杀虫剂推荐展示商品。",
     "is_hot": 0, "is_featured": 0},
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
    {"id": 1, "name": "番茄晚疫病", "en_name": "Late blight", "crop": "番茄",
     "intro": "由致病疫霉引起，叶片出现水浸状病斑，后变褐色坏死。",
     "treatment": "发病初期喷施代森锰锌或甲霜灵，注意通风降湿。"},
    {"id": 2, "name": "番茄早疫病", "en_name": "Early blight", "crop": "番茄",
     "intro": "由链格孢菌引起，叶片出现同心轮纹褐斑。",
     "treatment": "喷施苯醚甲环唑或嘧菌酯，清除病残体。"},
    {"id": 3, "name": "番茄叶霉病", "en_name": "Leaf mold", "crop": "番茄",
     "intro": "叶片正面出现黄绿色病斑，背面有灰褐色霉层。",
     "treatment": "喷施腐霉利或嘧菌酯，降低棚内湿度。"},
    {"id": 4, "name": "番茄斑枯病", "en_name": "Septoria leaf spot", "crop": "番茄",
     "intro": "叶片出现圆形小斑，中央灰白色，边缘深褐色。",
     "treatment": "发病初期喷施代森锰锌，及时摘除病叶。"},
    {"id": 5, "name": "番茄细菌性斑点病", "en_name": "Bacterial speck", "crop": "番茄",
     "intro": "叶片出现水浸状小斑点，后变褐色，周围有黄晕。",
     "treatment": "喷施铜制剂或农用链霉素，避免植株受伤。"},
    {"id": 6, "name": "番茄黄化曲叶病毒病", "en_name": "TYLCV", "crop": "番茄",
     "intro": "叶片黄化上卷，植株矮化，由烟粉虱传播。",
     "treatment": "防治烟粉虱，选用抗病品种，清除病株。"},
    {"id": 7, "name": "番茄花叶病毒病", "en_name": "Mosaic virus", "crop": "番茄",
     "intro": "叶片出现花叶、皱缩、畸形等症状。",
     "treatment": "防治蚜虫传播，及时拔除病株，工具消毒。"},
    {"id": 8, "name": "番茄红蜘蛛", "en_name": "Spider mite", "crop": "番茄",
     "intro": "叶片出现黄白色小点，严重时叶片枯黄脱落。",
     "treatment": "喷施阿维菌素或哒螨灵，注意叶背喷药。"},
    {"id": 9, "name": "健康番茄", "en_name": "Healthy tomato", "crop": "番茄",
     "intro": "植株生长正常，叶色浓绿，无病虫害症状。",
     "treatment": "加强栽培管理，预防为主。"},
    {"id": 10, "name": "马铃薯早疫病", "en_name": "Early blight", "crop": "马铃薯",
     "intro": "叶片出现同心轮纹褐斑，严重时叶片枯死。",
     "treatment": "喷施苯醚甲环唑或代森锰锌，清除病残体。"},
    {"id": 11, "name": "马铃薯晚疫病", "en_name": "Late blight", "crop": "马铃薯",
     "intro": "叶片出现水浸状病斑，潮湿时有白色霉层。",
     "treatment": "喷施甲霜灵或嘧菌酯，注意排水降湿。"},
    {"id": 12, "name": "健康马铃薯", "en_name": "Healthy potato", "crop": "马铃薯",
     "intro": "植株生长正常，叶色浓绿，无病虫害症状。",
     "treatment": "加强栽培管理，预防为主。"},
    {"id": 13, "name": "健康甜椒", "en_name": "Healthy pepper", "crop": "甜椒",
     "intro": "植株生长正常，叶色浓绿，无病虫害症状。",
     "treatment": "加强栽培管理，预防为主。"},
    {"id": 14, "name": "玉米锈病", "en_name": "Corn rust", "crop": "玉米",
     "intro": "叶片出现黄褐色粉状锈斑，严重影响产量。",
     "treatment": "喷施三唑酮或烯唑醇，选用抗病品种。"},
    {"id": 15, "name": "稻瘟病", "en_name": "Rice blast", "crop": "水稻",
     "intro": "叶片出现梭形病斑，穗颈受害导致白穗。",
     "treatment": "喷施三环唑或稻瘟灵，注意氮肥用量。"},
]

PEST_ENTRIES_EXTRA = [
    {"id": 16, "name": "玉米大斑病", "crop": "玉米",
     "intro": "主要危害玉米叶片，病斑大而长，灰褐色或黄褐色。",
     "treatment": "选用抗病品种，合理密植；发病初期可用吡唑醚菌酯、戊唑醇等防治。"},
    {"id": 17, "name": "玉米小斑病", "crop": "玉米",
     "intro": "叶片病斑小而多，椭圆形或长圆形，褐色边缘。",
     "treatment": "加强田间管理，增施磷钾肥；可用百菌清、代森锰锌等防治。"},
    {"id": 18, "name": "小麦赤霉病", "crop": "小麦",
     "intro": "主要危害穗部，造成枯白穗，影响产量和品质。",
     "treatment": "抽穗扬花期遇雨及时用药，可用戊唑醇、氰烯菌酯等防治。"},
    {"id": 19, "name": "小麦锈病", "crop": "小麦",
     "intro": "叶片出现锈褐色粉末状孢子堆，严重时叶片干枯。",
     "treatment": "选用抗病品种，合理施肥；可用三唑酮、戊唑醇等防治。"},
    {"id": 20, "name": "稻飞虱", "crop": "水稻",
     "intro": "成虫和若虫群集稻株基部刺吸汁液，造成倒伏枯死。",
     "treatment": "保持田间湿润，减少产卵；可用吡虫啉、噻虫嗪、烯啶虫胺等防治。"},
    {"id": 21, "name": "稻纵卷叶螟", "crop": "水稻",
          "intro": "幼虫吐丝纵卷叶片取食叶肉，影响光合作用。",
     "treatment": "可用甲维盐、氯虫苯甲酰胺、茚虫威等药剂防治。"},
    {"id": 22, "name": "玉米螟", "crop": "玉米",
     "intro": "幼虫钻蛀茎秆和果穗，造成折秆和减产。",
     "treatment": "可用Bt乳剂、氯虫苯甲酰胺、甲维盐等防治。"},
]

ALL_PEST_ENTRIES = PEST_ENTRIES + PEST_ENTRIES_EXTRA

PESTICIDE_ENTRIES = [
    {"id": 1, "name": "吡虫啉", "type": "杀虫剂",
     "crops": "水稻、小麦、棉花、蔬菜",
     "target": "蚜虫、飞虱、粉虱、蓟马等刺吸式害虫",
     "method": "兑水稀释500-1000倍液均匀喷雾，重点喷施叶背和嫩梢部位，每隔7-10天喷一次，连续使用不超过2次。",
     "caution": "不可与碱性农药混用；对蜜蜂有毒，花期禁用；安全间隔期14天；避免高温时段施药。"},
    {"id": 2, "name": "阿维菌素", "type": "杀虫剂",
     "crops": "蔬菜、果树、棉花",
     "target": "红蜘蛛、潜叶蛾、根结线虫、小菜蛾",
     "method": "兑水稀释2000-3000倍液喷雾，重点喷叶背，早晨或傍晚施药效果最佳，间隔7天可重复使用。",
     "caution": "对鱼类高毒，勿污染水源；对蜜蜂有毒，花期禁用；安全间隔期7天；不可与铜制剂混用。"},
    {"id": 3, "name": "氯虫苯甲酰胺", "type": "杀虫剂",
     "crops": "水稻、玉米、蔬菜、果树",
     "target": "稻纵卷叶螟、二化螟、小菜蛾、棉铃虫等鳞翅目害虫",
     "method": "兑水稀释1500-2000倍液喷雾，在害虫卵孵化高峰期或低龄幼虫期施药效果最好。",
     "caution": "注意与其他杀虫剂轮换使用，避免产生抗性；安全间隔期14天；孕穗期慎用。"},
    {"id": 4, "name": "甲维盐", "type": "杀虫剂",
     "crops": "蔬菜、果树、水稻",
     "target": "小菜蛾、甜菜夜蛾、斜纹夜蛾、稻纵卷叶螟",
     "method": "兑水稀释1000-2000倍液喷雾，傍晚施药效果好，间隔5-7天可重复使用。",
     "caution": "对鱼类和蜜蜂高毒；安全间隔期7天；不可长期单一使用，需与其他药剂轮换。"},
    {"id": 5, "name": "噻虫嗪", "type": "杀虫剂",
     "crops": "水稻、小麦、蔬菜、果树",
     "target": "蚜虫、飞虱、白粉虱、蓟马",
     "method": "可拌种、灌根或喷雾使用。喷雾时稀释2000-3000倍，苗期灌根效果持效期长。",
     "caution": "对蜜蜂高毒，开花期禁用；安全间隔期14天；避免在强日照下施药。"},
    {"id": 6, "name": "高效氯氟氰菊酯", "type": "杀虫剂",
     "crops": "蔬菜、棉花、果树、大豆",
     "target": "蚜虫、棉铃虫、菜青虫、红蜘蛛",
     "method": "兑水稀释1500-2000倍液喷雾，均匀覆盖叶片正反面，害虫暴发初期施药效果最佳。",
     "caution": "对鱼类和蜜蜂高毒；安全间隔期7天；不可与碱性物质混用；连续使用不超过2次。"},
    {"id": 7, "name": "代森锰锌", "type": "杀菌剂",
     "crops": "蔬菜、果树、马铃薯",
     "target": "早疫病、晚疫病、霜霉病、炭疽病",
     "method": "兑水稀释500-800倍液喷雾，发病前或发病初期开始用药，每隔7天喷一次，连续2-3次。",
     "caution": "不可与碱性农药或含铜制剂混用；安全间隔期15天；高温多雨季节适当缩短间隔期。"},
    {"id": 8, "name": "苯醚甲环唑", "type": "杀菌剂",
     "crops": "蔬菜、果树、小麦、水稻",
     "target": "白粉病、锈病、斑枯病、炭疽病、黑星病",
     "method": "兑水稀释1000-1500倍液均匀喷雾，发病初期用药，间隔10-14天重复施药。",
     "caution": "安全间隔期14天；不可与强碱性物质混用；同一季节使用不超过3次。"},
    {"id": 9, "name": "嘧菌酯", "type": "杀菌剂",
     "crops": "蔬菜、果树、水稻、小麦",
     "target": "霜霉病、白粉病、炭疽病、稻瘟病",
     "method": "兑水稀释1000-1500倍液喷雾，预防性施药效果优于治疗，间隔7-10天施药一次。",
     "caution": "不可与有机硅助剂混用；安全间隔期14天；对水生生物有毒，避免污染水源。"},
    {"id": 10, "name": "三环唑", "type": "杀菌剂",
     "crops": "水稻",
     "target": "稻瘟病（叶瘟、穗颈瘟）",
     "method": "破口期前5-7天和齐穗期各喷一次，兑水稀释1000倍液均匀喷雾，重点喷施穗部。",
     "caution": "安全间隔期28天；仅用于水稻，不可用于其他作物；避免在大风天气施药。"},
    {"id": 11, "name": "霜霉威盐酸盐", "type": "杀菌剂",
     "crops": "蔬菜、烟草、花卉",
     "target": "霜霉病、疫病、猝倒病",
     "method": "兑水稀释600-800倍液喷雾或灌根，发病初期开始用药，间隔7天重复一次。",
     "caution": "安全间隔期3天；对鱼类低毒；不可与铜制剂混用；注意轮换用药避免抗性。"},
    {"id": 12, "name": "草铵膦", "type": "除草剂",
     "crops": "果园、茶园、非耕地",
     "target": "一年生和多年生杂草",
     "method": "兑水稀释100-150倍液定向喷雾，避免喷到作物叶片，在杂草旺盛生长期施药效果最好。",
     "caution": "避免药液接触作物；施药后6小时内降雨需重喷；安全间隔期14天；对眼睛有刺激性，施药时佩戴防护。"},
    {"id": 13, "name": "莠去津", "type": "除草剂",
     "crops": "玉米、高粱",
     "target": "阔叶杂草和禾本科杂草",
     "method": "播后苗前土壤喷雾处理，兑水稀释200-300倍，均匀喷洒土壤表面，施药后不要翻土。",
     "caution": "只能用于玉米和高粱田；对后茬敏感作物有影响，注意轮作；安全间隔期60天。"},
    {"id": 14, "name": "二甲戊灵", "type": "除草剂",
     "crops": "棉花、大豆、蔬菜、花生",
     "target": "一年生禾本科杂草和部分阔叶杂草",
     "method": "播后苗前或移栽前土壤处理，兑水稀释300-500倍均匀喷雾，施药后轻耙混土效果更好。",
     "caution": "施药时土壤需保持湿润；不可用于水稻田；安全间隔期45天；避免重复喷施。"},
    {"id": 15, "name": "烟嘧磺隆", "type": "除草剂",
     "crops": "玉米",
     "target": "禾本科杂草、阔叶杂草、莎草",
     "method": "玉米3-5叶期、杂草2-4叶期茎叶喷雾，兑水稀释1000-1500倍，均匀喷洒杂草茎叶。",
     "caution": "只适用于玉米田；甜玉米、爆裂玉米禁用；施药前后7天不可使用有机磷农药；安全间隔期30天。"},
    {"id": 23, "name": "敌敌畏", "type": "杀虫剂",
     "crops": "蔬菜、果树、棉花",
     "target": "蚜虫、红蜘蛛、蓟马、鳞翅目害虫",
     "method": "兑水稀释800-1000倍液喷雾，均匀喷施叶片正反面，傍晚施药效果最好。",
     "caution": "对人畜毒性较高，施药时做好防护；安全间隔期7天；不可与碱性农药混用。"},
    {"id": 24, "name": "硫酸钾复合肥", "type": "肥料",
     "crops": "蔬菜、果树、水稻、小麦",
     "target": "补充氮磷钾，促进作物生长",
     "method": "基肥每亩40-60kg，追肥每亩15-20kg，结合灌水或雨前施用效果最佳。",
     "caution": "避免与碱性肥料混用；施肥后及时浇水；不可过量施用，以免烧苗。"},
    {"id": 25, "name": "磷酸二氢钾", "type": "肥料",
     "crops": "蔬菜、果树、粮食作物",
     "target": "补充磷钾，促进开花结果",
     "method": "叶面喷施浓度0.2-0.3%，于花前花后各喷一次，傍晚或阴天施用。",
     "caution": "不可与碱性农药混用；浓度不宜过高；避免在高温强光下喷施。"},
    {"id": 26, "name": "生物有机肥", "type": "肥料",
     "crops": "各类蔬菜、果树、粮食作物",
     "target": "改善土壤结构，增加有机质",
     "method": "基施每亩100-200kg，与土壤充分混合，也可穴施或沟施。",
     "caution": "避免与杀菌剂同时使用；开袋后尽快用完；存放于阴凉干燥处。"},
    {"id": 27, "name": "乙酰甲胺磷", "type": "杀虫剂",
     "crops": "水稻、蔬菜、果树",
     "target": "蚜虫、飞虱、叶蝉、稻纵卷叶螟",
     "method": "兑水稀释1000-1500倍液喷雾，均匀喷施叶片，重点喷施叶背和嫩梢。",
     "caution": "安全间隔期14天；对蜜蜂有毒，花期禁用；不可与碱性物质混用。"},
    {"id": 28, "name": "乙蒜素", "type": "杀菌剂",
     "crops": "水稻、蔬菜、果树",
     "target": "纹枯病、稻瘟病、白粉病、灰霉病",
     "method": "兑水稀释1000-1500倍液喷雾，发病初期开始用药，间隔7-10天重复使用。",
     "caution": "安全间隔期7天；不可与碱性农药混用；避免高温下施药。"},
    {"id": 29, "name": "百草枯", "type": "除草剂",
     "crops": "果园、非耕地、免耕田",
     "target": "一年生和多年生杂草",
     "method": "兑水稀释100-200倍液定向喷雾，避免喷到作物，在晴天无风时施用。",
     "caution": "对人畜毒性高，严格防护；不可用于粮食作物田；安全间隔期10天。"},
    {"id": 30, "name": "乐果", "type": "杀虫剂",
     "crops": "蔬菜、果树、棉花",
     "target": "蚜虫、红蜘蛛、介壳虫、叶蝉",
     "method": "兑水稀释1000-1500倍液喷雾，均匀喷施叶片正反面。",
     "caution": "安全间隔期7天；十字花科蔬菜慎用；不可与碱性农药混用。"},
]

FERTILIZER_ENTRIES = [
    {"id": 1, "name": "尿素", "type": "氮肥",
     "crops": "水稻、小麦、玉米、蔬菜、果树等大多数作物",
     "effect": "提供氮素营养，促进作物茎叶生长，使叶色浓绿，提高光合作用效率。",
     "method": "可作基肥、追肥使用。追肥时兑水稀释后浇施或穴施覆土，每亩用量10-15kg，施后及时浇水。",
     "caution": "不可与碱性肥料混用；施用后不宜立即灌水；种肥同施时注意与种子隔开，避免烧种。"},
    {"id": 2, "name": "磷酸二铵", "type": "复合肥",
     "crops": "小麦、玉米、水稻、大豆、蔬菜、果树",
     "effect": "同时提供氮磷两种营养，促进根系发育和早期生长，增强作物抗旱能力。",
     "method": "主要作基肥使用，播种前翻入土层，每亩用量15-20kg。也可作种肥，但需与种子隔开。",
     "caution": "不可与碱性肥料混用；储存时防潮防湿；高温多雨季节注意防止结块。"},
    {"id": 3, "name": "硫酸钾", "type": "钾肥",
     "crops": "烟草、茶叶、葡萄、薯类、蔬菜等忌氯作物",
     "effect": "提供钾素营养，增强作物茎秆强度，提高抗病抗逆能力，改善果实品质和口感。",
     "method": "可作基肥或追肥。基肥每亩10-15kg翻入土中；追肥时穴施或沟施后覆土浇水。",
     "caution": "连续大量施用会使土壤酸化；忌与碱性肥料混合施用；石灰性土壤施用效果更好。"},
    {"id": 4, "name": "硫酸钾复合肥", "type": "复合肥",
     "crops": "蔬菜、果树、烟草、花卉等多种作物",
     "effect": "均衡提供氮磷钾三种营养元素，促进作物全面生长，提高产量和品质。",
     "method": "基肥每亩20-30kg，均匀撒施后翻入土中；追肥时每亩10-15kg，距根部5-10cm处沟施。",
     "caution": "不能与碱性肥料混用；叶面喷施时浓度不超过0.3%；长期单一施用注意补充微量元素。"},
    {"id": 5, "name": "磷酸二氢钾", "type": "磷钾肥",
     "crops": "蔬菜、果树、小麦、水稻、棉花",
     "effect": "同时补充磷钾营养，促进花芽分化，提高坐果率，增强抗逆性，改善果实品质。",
     "method": "主要用于叶面喷施，浓度0.2-0.3%，花前花后各喷一次效果最佳；也可随水冲施。",
     "caution": "不可与碱性农药混用；高温强光下避免叶面喷施；配制时先用少量水溶解再兑足水量。"},
    {"id": 6, "name": "生物有机肥", "type": "有机肥",
     "crops": "蔬菜、果树、花卉、粮食作物等各类作物",
     "effect": "改良土壤结构，增加土壤有机质，活化土壤中难溶养分，促进根系发育，提高作物抗病能力。",
     "method": "基肥每亩100-200kg，均匀撒施后翻入土中；育苗时混入基质中使用效果好。",
     "caution": "开袋后尽快使用；避免与杀菌剂同时施用；高温干旱时施用后及时浇水。"},
    {"id": 7, "name": "腐植酸水溶肥", "type": "水溶肥",
     "crops": "蔬菜、果树、花卉、草坪等各类作物",
     "effect": "刺激根系生长，改善土壤保水保肥能力，缓解黄叶弱苗，提高肥料利用率。",
     "method": "滴灌冲施每亩5-8kg，叶面喷施稀释800-1000倍，每7-10天使用一次。",
     "caution": "不可与强酸强碱性物质混用；避免在高温强光下叶面喷施；储存于阴凉干燥处。"},
    {"id": 8, "name": "复合微生物菌剂", "type": "微生物肥",
     "crops": "蔬菜、果树、粮食作物、经济作物",
     "effect": "固氮解磷解钾，改善根际微生物环境，抑制土传病害，促进养分吸收，增强作物长势。",
     "method": "拌种每公斤种子用菌剂20-30g；灌根每株50-100ml稀释液；基施每亩2-4kg。",
     "caution": "避免与杀菌剂同时使用；开袋后及时用完；存放于阴凉避光处，避免高温暴晒。"},
    {"id": 9, "name": "大量元素水溶肥", "type": "水溶肥",
     "crops": "蔬菜、果树、花卉等设施作物",
     "effect": "快速补充氮磷钾营养，适合滴灌冲施，吸收利用率高，见效快。",
     "method": "滴灌冲施每亩5-10kg，叶面喷施稀释500-800倍，每7-10天一次，全生育期均可使用。",
     "caution": "不可过量施用，以免烧根；与其他肥料混用前先做小量试验；储存防潮避免结块。"},
    {"id": 10, "name": "枯草芽孢杆菌微生物菌剂", "type": "微生物肥",
     "crops": "蔬菜、果树、粮食作物",
     "effect": "产生抗菌物质抑制土传病害，促进根系发育，分解土壤有机质，提高养分利用率。",
     "method": "灌根稀释500倍，每株200-300ml；拌种每公斤种子10-20g菌剂；苗床处理每平方米5-10g。",
     "caution": "不可与杀菌剂同时使用，至少间隔3天；紫外线会使菌剂失活，避免暴晒；低温储存效果更好。"},
]

ALL_FERTILIZER_ENTRIES = FERTILIZER_ENTRIES


def get_api_base_url():
    # 优先读取自动发现并缓存的地址
    config_path = os.path.join(os.path.dirname(__file__), "api_url.txt")
    if os.path.exists(config_path):
        try:
            with open(config_path, "r", encoding="utf-8") as f:
                value = f.read().strip()
            if value:
                return value.rstrip("/")
        except Exception:
            pass
    return API_BASE_URL.rstrip("/")


def set_api_base_url(url):
    """保存自动发现的服务器地址到本地缓存"""
    config_path = os.path.join(os.path.dirname(__file__), "api_url.txt")
    try:
        with open(config_path, "w", encoding="utf-8") as f:
            f.write(url.rstrip("/"))
    except Exception:
        pass



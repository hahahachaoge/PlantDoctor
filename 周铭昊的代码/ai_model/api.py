import io
import json
from pathlib import Path

import torch
import torch.nn as nn
from fastapi import FastAPI, File, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from PIL import Image
from torchvision import models, transforms
from torchvision.transforms import functional as TF

BASE_DIR = Path(__file__).resolve().parent
CLASS_FILE = BASE_DIR / "classes.json"
MODEL_FILE = BASE_DIR / "pest_model.pth"
DISEASE_FILE = BASE_DIR / "disease_info.json"

app = FastAPI(title="Plant Doctor API")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

print("加载病虫害识别模型...")

if not CLASS_FILE.exists():
    raise FileNotFoundError(f"找不到类别文件: {CLASS_FILE}")
if not MODEL_FILE.exists():
    raise FileNotFoundError(f"找不到模型文件: {MODEL_FILE}")

with CLASS_FILE.open("r", encoding="utf-8") as file_obj:
    class_names = json.load(file_obj)

device = torch.device("cpu")
model = models.convnext_base(weights=None)
model.classifier[2] = nn.Linear(model.classifier[2].in_features, len(class_names))
model.load_state_dict(torch.load(MODEL_FILE, map_location=device))
model = model.to(device)
model.eval()
print(f"模型加载成功，可识别 {len(class_names)} 类病虫害，其中昆虫 {sum(1 for c in class_names if c.startswith('Insect_'))} 类、作物病害 {sum(1 for c in class_names if not c.startswith('Insect_'))} 类")

# 加载病害详情库
DISEASE_INFO = {}
if DISEASE_FILE.exists():
    with DISEASE_FILE.open("r", encoding="utf-8") as f:
        DISEASE_INFO = json.load(f)
    print(f"已加载 {len(DISEASE_INFO)} 条病虫害详情")
else:
    print("未找到 disease_info.json，将使用默认提示")

transform = transforms.Compose(
    [
        transforms.Resize((256, 256)),
        transforms.CenterCrop(224),
        transforms.ToTensor(),
        transforms.Normalize(mean=[0.485, 0.456, 0.406], std=[0.229, 0.224, 0.225]),
    ]
)


# ── 181类中文名映射 ──────────────────────────────────────
ALIASES = {
    # ========== 昆虫 (100类) ==========
    "Insect_Adristyrannus": "苜蓿盲蝽",
    "Insect_Aleurocanthus_spiniferus": "黑刺粉虱",
    "Insect_Ampelophaga": "葡萄天蛾",
    "Insect_Aphis_citricola_Vander_Goot": "绣线菊蚜",
    "Insect_Apolygus_lucorum": "绿盲蝽",
    "Insect_Bactrocera_tsuneonis": "柑橘小实蝇",
    "Insect_Beet_spot_flies": "甜菜斑潜蝇",
    "Insect_Brevipoalpus_lewisi_McGregor": "刘氏短须螨",
    "Insect_Ceroplastes_rubens": "红蜡蚧",
    "Insect_Chlumetia_transversa": "芒果横线尾夜蛾",
    "Insect_Chrysomphalus_aonidum": "褐圆蚧",
    "Insect_Cicadella_viridis": "大青叶蝉",
    "Insect_Cicadellidae": "叶蝉科",
    "Insect_Colomerus_vitis": "葡萄缺节瘿螨",
    "Insect_Dacus_dorsalis(Hendel)": "橘小实蝇",
    "Insect_Dasineura_sp": "瘿蚊",
    "Insect_Deporaus_marginatus_Pascoe": "芒果切叶象甲",
    "Insect_Icerya_purchasi_Maskell": "吹绵蚧",
    "Insect_Lawana_imitata_Melichar": "白蛾蜡蝉",
    "Insect_Limacodidae": "刺蛾科",
    "Insect_Locustoidea": "蝗虫",
    "Insect_Lycorma_delicatula": "斑衣蜡蝉",
    "Insect_Mango_flat_beak_leafhopper": "芒果扁喙叶蝉",
    "Insect_Miridae": "盲蝽科",
    "Insect_Nipaecoccus_vastalor": "堆蜡粉蚧",
    "Insect_Panonchus_citri_McGregor": "柑橘全爪螨",
    "Insect_Papilio_xuthus": "柑橘凤蝶",
    "Insect_Phyllocnistis_citrella_Stainton": "柑橘潜叶蛾",
    "Insect_Phyllocoptes_oleiverus_ashmead": "柑橘锈壁虱",
    "Insect_Pieris_canidia": "东方菜粉蝶",
    "Insect_Polyphagotars_onemus_latus": "侧多食跗线螨",
    "Insect_Potosiabre_vitarsis": "白星花金龟",
    "Insect_Prodenia_litura": "斜纹夜蛾",
    "Insect_Pseudococcus_comstocki_Kuwana": "康氏粉蚧",
    "Insect_Rhytidodera_bowrinii_white": "芒果脊胸天牛",
    "Insect_Rice_Stemfly": "水稻秆蝇",
    "Insect_Salurnis_marginella_Guerr": "青蛾蜡蝉",
    "Insect_Scirtothrips_dorsalis_Hood": "茶黄蓟马",
    "Insect_Sternochetus_frigidus": "芒果果肉象甲",
    "Insect_Tetradacus_c_Bactrocera_minax": "柑橘大实蝇",
    "Insect_Thrips": "蓟马",
    "Insect_Toxoptera_aurantii": "橘二叉蚜",
    "Insect_Toxoptera_citricidus": "橘蚜",
    "Insect_Trialeurodes_vaporariorum": "温室白粉虱",
    "Insect_Unaspis_yanonensis": "矢尖蚧",
    "Insect_Viteus_vitifoliae": "葡萄根瘤蚜",
    "Insect_Xylotrechus": "虎天牛",
    "Insect_alfalfa_plant_bug": "苜蓿盲蝽",
    "Insect_alfalfa_seed_chalcid": "苜蓿籽蜂",
    "Insect_alfalfa_weevil": "苜蓿叶象甲",
    "Insect_aphids": "蚜虫",
    "Insect_army_worm": "黏虫",
    "Insect_asiatic_rice_borer": "二化螟",
    "Insect_beet_army_worm": "甜菜夜蛾",
    "Insect_beet_fly": "甜菜潜叶蝇",
    "Insect_beet_weevil": "甜菜象甲",
    "Insect_bird_cherry_oataphid": "禾谷缢管蚜",
    "Insect_black_cutworm": "小地老虎",
    "Insect_blister_beetle": "豆芫菁",
    "Insect_brown_plant_hopper": "褐飞虱",
    "Insect_cabbage_army_worm": "甘蓝夜蛾",
    "Insect_cerodonta_denticornis": "麦叶蜂",
    "Insect_corn_borer": "玉米螟",
    "Insect_english_grain_aphid": "麦长管蚜",
    "Insect_flax_budworm": "亚麻夜蛾",
    "Insect_flea_beetle": "黄曲条跳甲",
    "Insect_grain_spreader_thrips": "稻管蓟马",
    "Insect_green_bug": "麦二叉蚜",
    "Insect_grub": "蛴螬",
    "Insect_large_cutworm": "大地老虎",
    "Insect_legume_blister_beetle": "豆芫菁",
    "Insect_longlegged_spider_mite": "长腿红蜘蛛",
    "Insect_lytta_polita": "绿芫菁",
    "Insect_meadow_moth": "草地螟",
    "Insect_mole_cricket": "蝼蛄",
    "Insect_odontothrips_loti": "苜蓿蓟马",
    "Insect_oides_decempunctata": "十星瓢萤叶甲",
    "Insect_paddy_stem_maggot": "稻秆潜蝇",
    "Insect_parathrene_regalis": "葡萄透翅蛾",
    "Insect_peach_borer": "桃蛀螟",
    "Insect_penthaleus_major": "麦圆红蜘蛛",
    "Insect_red_spider": "红蜘蛛",
    "Insect_rice_gall_midge": "稻瘿蚊",
    "Insect_rice_leaf_caterpillar": "稻纵卷叶螟",
    "Insect_rice_leaf_roller": "稻纵卷叶螟",
    "Insect_rice_leafhopper": "稻叶蝉",
    "Insect_rice_shell_pest": "稻壳害虫",
    "Insect_rice_water_weevil": "稻水象甲",
    "Insect_sericaorient_alismots_chulsky": "东方绢金龟",
    "Insect_small_brown_plant_hopper": "灰飞虱",
    "Insect_tarnished_plant_bug": "牧草盲蝽",
    "Insect_therioaphis_maculata_Buckton": "苜蓿彩斑蚜",
    "Insect_wheat_blossom_midge": "小麦吸浆虫",
    "Insect_wheat_phloeothrips": "小麦皮蓟马",
    "Insect_wheat_sawfly": "小麦叶蜂",
    "Insect_white_backed_plant_hopper": "白背飞虱",
    "Insect_white_margined_moth": "白边夜蛾",
    "Insect_wireworm": "金针虫",
    "Insect_yellow_cutworm": "黄地老虎",
    "Insect_yellow_rice_borer": "三化螟",

    # ========== 作物病害 (81类) ==========
    "Apple_Healthy": "健康苹果",
    "Apple_Mosaic_Virus": "苹果花叶病毒病",
    "Apple_Rot": "苹果轮纹病",
    "Apple_Rotten": "苹果腐烂病",
    "Apple_Rust": "苹果锈病",
    "Apple_Scab": "苹果黑星病",
    "Apple_Spot": "苹果斑点病",
    "Banana_Healthy": "健康香蕉",
    "Banana_Rotten": "香蕉腐烂病",
    "Bellpepper_Healthy": "健康甜椒",
    "Bellpepper_Rotten": "甜椒腐烂病",
    "Blueberry_Healthy": "健康蓝莓",
    "Carrot_Healthy": "健康胡萝卜",
    "Carrot_Rotten": "胡萝卜腐烂病",
    "Cassava_Bacterial_Blight": "木薯细菌性枯萎病",
    "Cassava_Brown_Streak_Disease": "木薯褐条病",
    "Cassava_Green_Mottle": "木薯绿斑病",
    "Cassava_Healthy": "健康木薯",
    "Cassava_Mosaic_Disease": "木薯花叶病",
    "Cherry_Healthy": "健康樱桃",
    "Cherry_Powdery_Mildew": "樱桃白粉病",
    "Citrus_Canker": "柑橘溃疡病",
    "Citrus_Greening": "柑橘黄龙病",
    "Citrus_Healthy": "健康柑橘",
    "Citrus_Melanose": "柑橘黑点病",
    "Citrus_Scab": "柑橘疮痂病",
    "Corn_Blight": "玉米大斑病",
    "Corn_Healthy": "健康玉米",
    "Corn_Rust": "玉米锈病",
    "Corn_Spot": "玉米斑点病",
    "Cucumber_Healthy": "健康黄瓜",
    "Cucumber_Rotten": "黄瓜腐烂病",
    "Grape_Black_Measles": "葡萄黑麻疹病",
    "Grape_Blight": "葡萄叶枯病",
    "Grape_Healthy": "健康葡萄",
    "Grape_Rot": "葡萄腐烂病",
    "Grape_Rotten": "葡萄腐烂病",
    "Grape_Spot": "葡萄斑点病",
    "Guava_Healthy": "健康番石榴",
    "Guava_Rotten": "番石榴腐烂病",
    "Jujube_Healthy": "健康枣",
    "Jujube_Rotten": "枣腐烂病",
    "Mango_Anthracnose": "芒果炭疽病",
    "Mango_Bacterial_Canker": "芒果细菌性溃疡病",
    "Mango_Cutting_Weevil": "芒果象甲危害",
    "Mango_Die_Back": "芒果枯梢病",
    "Mango_Gall_Midge": "芒果瘿蚊危害",
    "Mango_Healthy": "健康芒果",
    "Mango_Powdery_Mildew": "芒果白粉病",
    "Mango_Rotten": "芒果腐烂病",
    "Mango_Sooty_Mould": "芒果煤污病",
    "Orange_Healthy": "健康橙子",
    "Orange_Rotten": "橙子腐烂病",
    "Peach_Healthy": "健康桃",
    "Peach_Spot": "桃斑点病",
    "Pepper_Healthy": "健康辣椒",
    "Pepper_Spot": "辣椒斑点病",
    "Pomegranate_Healthy": "健康石榴",
    "Pomegranate_Rotten": "石榴腐烂病",
    "Potato_Blight": "马铃薯疫病",
    "Potato_Healthy": "健康马铃薯",
    "Potato_Rotten": "马铃薯腐烂病",
    "Raspberry_Healthy": "健康树莓",
    "Soybean_Healthy": "健康大豆",
    "Squash_Powdery_Mildew": "南瓜白粉病",
    "Strawberry_Healthy": "健康草莓",
    "Strawberry_Leaf_Scorch": "草莓叶枯病",
    "Strawberry_Mold": "草莓灰霉病",
    "Strawberry_Powdery_Mildew": "草莓白粉病",
    "Strawberry_Rotten": "草莓腐烂病",
    "Strawberry_Spot": "草莓斑点病",
    "Tomato_Blight": "番茄疫病",
    "Tomato_Healthy": "健康番茄",
    "Tomato_Leaf_Curl": "番茄卷叶病",
    "Tomato_Mold": "番茄叶霉病",
    "Tomato_Mosaic_Virus": "番茄花叶病毒病",
    "Tomato_Powdery_Mildew": "番茄白粉病",
    "Tomato_Rotten": "番茄腐烂病",
    "Tomato_Septoria": "番茄斑枯病",
    "Tomato_Spot": "番茄斑点病",
    "Tomato_Target_Spot": "番茄靶斑病",
}


def _format_chinese(raw_name):
    """当 ALIASES 未覆盖时，自动生成可读的中文名。"""
    name = raw_name
    if name.startswith("Insect_"):
        name = name[7:]  # 去掉 Insect_ 前缀
    # 对作物病害格式 Crop_Disease，把下划线替换为空格
    name = name.replace("_", " ")
    return name


def get_info(raw_name):
    if raw_name in DISEASE_INFO:
        info = DISEASE_INFO[raw_name]
        return {
            "chinese_name": info.get("chinese_name", _format_chinese(raw_name)),
            "intro": info.get("intro", "暂无详细简介，请结合田间症状进一步确认。"),
            "method": info.get("method", "建议咨询当地农技人员，并根据病虫害类型选择合适的农业防治和药剂防治措施。"),
        }
    chinese_name = ALIASES.get(raw_name, _format_chinese(raw_name))
    return {
        "chinese_name": chinese_name,
        "intro": "暂无该类别的详细简介，请结合田间症状进一步确认。",
        "method": "建议咨询当地农技人员，并根据病虫害类型选择合适的农业防治和药剂防治措施。",
    }


@app.get("/")
async def root():
    return {"message": "病虫害识别 API 已启动"}


@app.post("/predict")
async def predict(file: UploadFile = File(...)):
    try:
        contents = await file.read()
        image = Image.open(io.BytesIO(contents)).convert("RGB")

        # TTA: 4 种翻转 → 平均概率。翻转与训练时 RandomFlip 一致
        tta_variants = [
            image,                          # 原图
            TF.hflip(image),                # 水平翻转
            TF.vflip(image),                # 垂直翻转
            TF.hflip(TF.vflip(image)),      # 水平+垂直翻转
        ]

        with torch.no_grad():
            # 收集 4 组 Top-5 概率
            all_top5_probs = {i: [] for i in range(5)}
            for variant in tta_variants:
                variant_tensor = transform(variant).unsqueeze(0).to(device)
                outputs = model(variant_tensor)
                probs = torch.nn.functional.softmax(outputs[0], dim=0)
                top5_conf_v, top5_idx_v = torch.topk(probs, 5)
                # 记录每个 class_id 对应的概率（4 次取平均时用到）
                for rank, (conf_v, idx_v) in enumerate(zip(top5_conf_v, top5_idx_v)):
                    all_top5_probs[rank].append((idx_v.item(), conf_v.item()))

            # 对每个 TTA 变体的结果按 class_id 合并，同 class_id 取平均
            merged = {}  # class_id -> avg_confidence
            for rank, pairs in all_top5_probs.items():
                for class_id, conf in pairs:
                    if class_id not in merged:
                        merged[class_id] = []
                    merged[class_id].append(conf)

            # 按平均置信度排序，取 Top-5
            avg_probs = [(cid, sum(confs) / len(confs)) for cid, confs in merged.items()]
            avg_probs.sort(key=lambda x: x[1], reverse=True)
            final_top5 = avg_probs[:5]

        # 主结果
        predicted = final_top5[0][0]
        confidence = final_top5[0][1]

        raw_name = class_names[predicted]
        info = get_info(raw_name)
        treatment = {
            "medicine": "-",
            "dosage": "-",
            "method": info["method"],
        }

        # 构建 Top-5 备选列表
        top5_list = []
        for class_id, conf in final_top5:
            raw = class_names[class_id]
            ti = get_info(raw)
            top5_list.append({
                "chinese_name": ti["chinese_name"],
                "raw_class": raw,
                "confidence": round(conf * 100, 2),
            })

        return {
            "success": True,
            "pest_name": info["chinese_name"],
            "confidence": round(confidence * 100, 2),
            "intro": info["intro"],
            "treatment": treatment,
            "treatment_text": info["method"],
            "raw_class": raw_name,
            "top5": top5_list,
            "low_confidence": confidence < 0.5,
            "warning": "置信度较低，结果仅供参考，Top-5中可能包含正确答案" if confidence < 0.5 else "",
        }
    except Exception as exc:
        return {"success": False, "error": str(exc)}


if __name__ == "__main__":
    import uvicorn

    print("=" * 50)
    print("启动病虫害识别 API")
    print("局域网访问示例: http://10.252.59.60:8000")
    print("=" * 50)
    uvicorn.run(app, host="0.0.0.0", port=8000)

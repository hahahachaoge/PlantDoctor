import io
import json
from pathlib import Path

import torch
import torch.nn as nn
from fastapi import FastAPI, File, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from PIL import Image
from torchvision import models, transforms

BASE_DIR = Path(__file__).resolve().parent
CLASS_FILE = BASE_DIR / "classes.json"
MODEL_FILE = BASE_DIR / "best_model.pth"

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
print(f"模型加载成功，可识别 {len(class_names)} 类病虫害")

transform = transforms.Compose(
    [
        transforms.Resize((224, 224)),
        transforms.ToTensor(),
        transforms.Normalize(mean=[0.485, 0.456, 0.406], std=[0.229, 0.224, 0.225]),
    ]
)

DISEASE_INFO = {
    "Tomato_Late_blight": {
        "chinese_name": "番茄晚疫病",
        "intro": "番茄晚疫病是真菌病害，由致病疫霉引起，主要危害叶片和青果。成株期叶片多从下部叶尖、叶缘开始发病，初为暗绿色水渍状病斑，湿度大时叶背病健交界处会长出白色霉层。青果受害后形成暗褐色硬斑，潮湿时腐烂。",
        "method": "农业防治：及时清除病残体，与非茄科作物轮作2年以上；合理密植，避免氮肥过量；保护地加强通风降湿。药剂防治：发病初期可选用58%甲霜灵锰锌500倍液、霜霉威盐酸盐、氟啶胺等药剂喷雾防治，连续施药2-3次，间隔7-10天，注意轮换用药避免抗药性。",
    },
    "Tomato_Early_blight": {
        "chinese_name": "番茄早疫病",
        "intro": "番茄早疫病由链格孢菌引起，主要侵害叶片、茎和果实。叶片病斑初期为褐色小点，后扩大成圆形或不规则形，病斑有明显的同心轮纹，边缘有黄色晕圈。严重时叶片枯黄脱落，果实受害后表面形成黑色凹陷病斑。",
        "method": "农业防治：与非茄科作物轮作；增施磷钾肥，提高植株抗病性；及时摘除病叶病果。药剂防治：发病初期用70%代森锰锌500倍液防治，5-7天喷一次，连喷3次。",
    },
    "Tomato_Leaf_Mold": {
        "chinese_name": "番茄叶霉病",
        "intro": "番茄叶霉病主要危害叶片，严重时也危害茎、花和果实。叶片背面出现灰白色霉层，后变为灰褐色，叶片正面出现黄色病斑。湿度大时病情发展迅速，高温高湿环境易流行。",
        "method": "农业防治：加强通风降湿，合理密植；选用抗病品种；避免过度密植和氮肥过量。药剂防治：可用嘧菌酯、苯醚甲环唑等药剂喷雾防治。",
    },
    "Tomato_Septoria_leaf_spot": {
        "chinese_name": "番茄斑枯病",
        "intro": "番茄斑枯病主要危害叶片，病斑圆形或近圆形，初为暗褐色，后变为灰白色，边缘深褐色，病斑上散生黑色小点（分生孢子器）。严重时叶片枯黄脱落，影响光合作用。",
        "method": "农业防治：清除病残体，减少初侵染源；轮作倒茬。药剂防治：发病初期可选用苯醚甲环唑、代森锰锌等药剂。",
    },
    "Tomato_Bacterial_spot": {
        "chinese_name": "番茄细菌性斑点病",
        "intro": "由丁香假单胞杆菌番茄致病变种引起，主要危害叶片、茎和果实。叶片病斑暗褐色至黑色，圆形或不规则形，周围有黄色晕圈。果实病斑稍隆起，边缘水渍状。",
        "method": "农业防治：选用无病种子；轮作；加强通风。药剂防治：发病初期可用噻菌铜、中生菌素等药剂。",
    },
    "Tomato__Tomato_YellowLeaf__Curl_Virus": {
        "chinese_name": "番茄黄化曲叶病毒病",
        "intro": "由烟粉虱传播的双生病毒引起。病株明显矮化，上部叶片黄化、变小、皱缩、卷曲，叶片边缘向上卷，叶背叶脉变紫。植株生长缓慢，开花结果减少，果实变小，严重影响产量。",
        "method": "农业防治：培育无病壮苗；使用防虫网；及时清除田间杂草和病株。虫害防治：防治烟粉虱是关键，可用吡虫啉、啶虫脒等药剂。",
    },
    "Tomato__Tomato_mosaic_virus": {
        "chinese_name": "番茄花叶病毒病",
        "intro": "病叶出现花叶、黄绿相间斑驳，叶片皱缩畸形；病株矮化，果实变小、畸形，着色不均。主要通过汁液接触和种子带毒传播。",
        "method": "农业防治：选用抗病品种；种子消毒；操作时避免汁液传播。药剂防治：发病前可用氨基寡糖素、香菇多糖等病毒抑制剂。",
    },
    "Tomato_Spider_mites_Two_spotted_spider_mite": {
        "chinese_name": "番茄红蜘蛛",
        "intro": "二斑叶螨危害，成虫和若虫在叶背刺吸汁液。叶片初期出现小白点，严重时叶片变黄、干枯、脱落，植株生长受阻。高温干旱季节发生严重。",
        "method": "农业防治：清除田间杂草；合理灌溉，避免干旱。药剂防治：可用阿维菌素、哒螨灵、螺螨酯等杀螨剂喷雾防治，重点喷施叶片背面。",
    },
    "Tomato_healthy": {
        "chinese_name": "健康番茄",
        "intro": "无明显病虫害症状，叶片正常绿色，植株生长健壮。",
        "method": "继续保持良好田间管理，合理水肥，预防病虫害发生。",
    },
    "Potato___Early_blight": {
        "chinese_name": "马铃薯早疫病",
        "intro": "由链格孢菌引起，主要危害叶片和块茎。叶片病斑暗褐色，有同心轮纹，边缘有时有黄色晕圈。严重时叶片枯死，块茎表面出现凹陷的暗褐色病斑。",
        "method": "农业防治：轮作倒茬；增施钾肥，提高抗病性。药剂防治：发病初期用代森锰锌、苯醚甲环唑等药剂喷雾。",
    },
    "Potato___Late_blight": {
        "chinese_name": "马铃薯晚疫病",
        "intro": "马铃薯晚疫病是马铃薯生产上的毁灭性病害，由致病疫霉引起。叶片出现暗绿色水渍状病斑，湿度大时叶背生出白色霉层。块茎受害后表面出现褐色凹陷病斑，切面可见红褐色坏死斑。",
        "method": "农业防治：选用抗病品种；轮作；加强田间管理，避免田间积水。药剂防治：发现中心病株立即用药，可用烯酰吗啉、霜脲氰、甲霜灵锰锌等药剂喷雾防治。",
    },
    "Potato___healthy": {
        "chinese_name": "健康马铃薯",
        "intro": "无明显病害症状，植株生长正常。",
        "method": "注意预防早晚疫病发生，合理轮作，选用脱毒种薯。",
    },
    "Pepper__bell___healthy": {
        "chinese_name": "健康甜椒",
        "intro": "无明显病虫害症状，叶片浓绿，果实发育正常。",
        "method": "注意防治蚜虫、红蜘蛛等害虫，预防疫病和病毒病。",
    },
    "Corn_(maize)___Common_rust_": {
        "chinese_name": "玉米锈病",
        "intro": "玉米锈病主要发生在玉米生长后期，侵害叶片，严重时果穗、苞叶也会受害。发病初期叶片两面散生淡黄色小斑，后扩展为圆形或椭圆形、黄褐色病斑，周围表皮翻起，散出铁锈色粉末。",
        "method": "农业防治：种植抗病品种；适时播种，合理密植；配方施肥，避免偏施氮肥，增施磷钾肥提高抗病性。药剂防治：可选用三唑酮、吡唑醚菌酯、戊唑醇、嘧菌酯等药剂喷雾防治。",
    },
    "Corn_(maize)___healthy": {
        "chinese_name": "健康玉米",
        "intro": "无明显病害症状，植株生长正常。",
        "method": "注意预防大斑病、小斑病、锈病和玉米螟等病虫害。",
    },
    "Rice___Rice_blast": {
        "chinese_name": "稻瘟病",
        "intro": "稻瘟病在水稻整个生育期均可发生，分为苗瘟、叶瘟、节瘟、穗颈瘟等。叶瘟病斑呈纺锤形，中间灰白色，边缘褐色，两端有坏死线；穗颈瘟发生于穗颈，病斑褐色，易造成白穗，严重减产。",
        "method": "农业防治：选用抗病品种；合理施肥，避免偏施氮肥；浅水勤灌，适时晒田。药剂防治：破口期和齐穗期用药，可用三环唑、稻瘟灵、吡唑醚菌酯等药剂。",
    },
}

ALIASES = {
    "Tomato__Target_Spot": "番茄靶斑病",
}


def get_info(raw_name):
    if raw_name in DISEASE_INFO:
        return DISEASE_INFO[raw_name]
    chinese_name = ALIASES.get(raw_name, raw_name.replace("_", " "))
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
        image_tensor = transform(image).unsqueeze(0).to(device)

        with torch.no_grad():
            outputs = model(image_tensor)
            probabilities = torch.nn.functional.softmax(outputs[0], dim=0)
            confidence, predicted = torch.max(probabilities, 0)

        raw_name = class_names[predicted.item()]
        info = get_info(raw_name)
        treatment = {
            "medicine": "-",
            "dosage": "-",
            "method": info["method"],
        }
        return {
            "success": True,
            "pest_name": info["chinese_name"],
            "confidence": round(confidence.item() * 100, 2),
            "intro": info["intro"],
            "treatment": treatment,
            "treatment_text": info["method"],
            "raw_class": raw_name,
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

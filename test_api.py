import requests

# API地址，默认uvicorn是 127.0.0.1:8000
url = "http://127.0.0.1:8000/predict"
# 替换成你本地测试图片路径
img_path = "image/pest_玉米大斑病.png"

with open(img_path, "rb") as f:
    files = {"file": f}
    resp = requests.post(url, files=files)

if resp.status_code == 200:
    print("✅ 识别成功")
    print(resp.json())
else:
    print("❌ 请求失败")
    print(resp.text)

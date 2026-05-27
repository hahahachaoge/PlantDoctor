import os
import urllib.request
import zipfile
import shutil

print("="*60)
print("开始下载PlantVillage病虫害数据集")
print("="*60)

# 创建data文件夹
if not os.path.exists('data'):
    os.makedirs('data')

# 下载链接
url = "https://github.com/spMohanty/PlantVillage-Dataset/raw/master/raw/color.zip"
filename = "color.zip"

print(f"正在下载 {url}")
print("文件大小约1GB，请耐心等待...")

# 下载
try:
    urllib.request.urlretrieve(url, filename)
    print("下载完成！")
except Exception as e:
    print(f"下载失败：{e}")
    print("\n如果下载失败，请手动下载：")
    print("1. 打开浏览器访问：https://github.com/spMohanty/PlantVillage-Dataset/raw/master/raw/color.zip")
    print("2. 下载 color.zip")
    print("3. 把 color.zip 放到 D:\\pycharm\\PythonProject1\\ai_model 文件夹")
    exit()

# 解压
print("正在解压...")
with zipfile.ZipFile(filename, 'r') as zip_ref:
    zip_ref.extractall('data')

# 删除zip文件
os.remove(filename)

print("解压完成！")
print("\n数据集位置：D:\\pycharm\\PythonProject1\\ai_model\\data\\color")

# 检查
color_path = 'data/color'
if os.path.exists(color_path):
    subdirs = [d for d in os.listdir(color_path) if os.path.isdir(os.path.join(color_path, d))]
    print(f"\n找到 {len(subdirs)} 种病虫害类别：")
    for i, d in enumerate(subdirs[:10]):
        print(f"  {i+1}. {d}")
    if len(subdirs) > 10:
        print(f"  ... 还有 {len(subdirs)-10} 种")
else:
    print("错误：解压后找不到 data/color 文件夹")
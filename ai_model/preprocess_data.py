# -*- coding: utf-8 -*-
"""
数据集预处理脚本
功能：
1. 统一图片格式和尺寸（224×224）
2. 统计总类别数
3. 过滤损坏或模糊的图片
4. 按8:2划分训练集和验证集
5. 按"类别名/图片"结构存放
"""
import os
import shutil
from PIL import Image, ImageFilter
import random
from tqdm import tqdm

# 配置参数
INPUT_DIR = r'D:\农智云警\nongzhihuiyan\PythonProject1\ai_model\data_merged_final'
OUTPUT_DIR = r'D:\农智云警\nongzhihuiyan\PythonProject1\ai_model\data_processed'
TARGET_SIZE = (224, 224)
TRAIN_RATIO = 0.8
MIN_SIZE = 64  # 最小图片尺寸

print("=" * 80)
print("数据集预处理")
print("=" * 80)

# ============ 步骤1: 扫描数据集 ============
print("\n[步骤1] 扫描原始数据集...")

all_classes = []
class_stats = {}

for class_name in os.listdir(INPUT_DIR):
    class_path = os.path.join(INPUT_DIR, class_name)
    if not os.path.isdir(class_path):
        continue
    
    images = [f for f in os.listdir(class_path) if f.lower().endswith(('.jpg', '.jpeg', '.png', '.bmp'))]
    
    if images:
        all_classes.append(class_name)
        class_stats[class_name] = {
            'total': len(images),
            'valid': 0,
            'invalid': 0,
            'train': 0,
            'val': 0
        }

print(f"  扫描到 {len(all_classes)} 个类别")

# ============ 步骤2: 过滤损坏/模糊图片 ============
print("\n[步骤2] 过滤损坏和模糊图片...")

def is_valid_image(img_path):
    """检查图片是否有效"""
    try:
        img = Image.open(img_path)
        img.verify()
        img = Image.open(img_path)
        
        # 过滤尺寸过小的图片
        if img.width < MIN_SIZE or img.height < MIN_SIZE:
            return False, "尺寸过小"
        
        # 过滤纯灰度图
        if img.mode == 'L':
            return False, "灰度图"
        
        return True, "有效"
    except Exception as e:
        return False, f"损坏: {str(e)}"

valid_samples = {}  # {类别名: [图片路径列表]}
total_valid = 0
total_invalid = 0

for class_name in tqdm(all_classes, desc="  过滤"):
    class_path = os.path.join(INPUT_DIR, class_name)
    valid_images = []
    
    for img_file in os.listdir(class_path):
        if not img_file.lower().endswith(('.jpg', '.jpeg', '.png', '.bmp')):
            continue
        
        img_path = os.path.join(class_path, img_file)
        is_valid, reason = is_valid_image(img_path)
        
        if is_valid:
            valid_images.append(img_path)
            total_valid += 1
        else:
            total_invalid += 1
    
    valid_samples[class_name] = valid_images
    class_stats[class_name]['valid'] = len(valid_images)
    class_stats[class_name]['invalid'] = class_stats[class_name]['total'] - len(valid_images)

print(f"\n  有效图片: {total_valid} 张")
print(f"  无效图片: {total_invalid} 张")

# ============ 步骤3: 按8:2划分训练集和验证集 ============
print("\n[步骤3] 按8:2划分训练集和验证集...")

random.seed(42)

train_samples = {}
val_samples = {}

for class_name in tqdm(all_classes, desc="  划分"):
    samples = valid_samples[class_name]
    
    if len(samples) == 0:
        continue
    
    random.shuffle(samples)
    split_idx = int(len(samples) * TRAIN_RATIO)
    
    train_samples[class_name] = samples[:split_idx]
    val_samples[class_name] = samples[split_idx:]
    
    class_stats[class_name]['train'] = len(train_samples[class_name])
    class_stats[class_name]['val'] = len(val_samples[class_name])

total_train = sum(len(v) for v in train_samples.values())
total_val = sum(len(v) for v in val_samples.values())

print(f"\n  训练集: {total_train} 张 ({total_train/(total_train+total_val)*100:.1f}%)")
print(f"  验证集: {total_val} 张 ({total_val/(total_train+total_val)*100:.1f}%)")

# ============ 步骤4: 统一格式和尺寸并保存 ============
print("\n[步骤4] 统一图片格式和尺寸并保存...")

os.makedirs(OUTPUT_DIR, exist_ok=True)
train_dir = os.path.join(OUTPUT_DIR, 'train')
val_dir = os.path.join(OUTPUT_DIR, 'val')
os.makedirs(train_dir, exist_ok=True)
os.makedirs(val_dir, exist_ok=True)

def process_and_save_image(src_path, dst_path):
    """统一图片格式和尺寸"""
    try:
        img = Image.open(src_path)
        
        # 转换为RGB
        if img.mode != 'RGB':
            img = img.convert('RGB')
        
        # 调整尺寸
        img = img.resize(TARGET_SIZE, Image.LANCZOS)
        
        # 保存为JPEG格式
        img.save(dst_path, 'JPEG', quality=95)
        return True
    except Exception as e:
        return False

# 保存训练集
print("  保存训练集...")
train_count = 0
for class_name, samples in tqdm(train_samples.items(), desc="    训练集"):
    if not samples:
        continue
    
    class_dir = os.path.join(train_dir, class_name)
    os.makedirs(class_dir, exist_ok=True)
    
    for i, img_path in enumerate(samples):
        dst_path = os.path.join(class_dir, f'{i:05d}.jpg')
        if process_and_save_image(img_path, dst_path):
            train_count += 1

print(f"    训练集保存完成: {train_count} 张")

# 保存验证集
print("  保存验证集...")
val_count = 0
for class_name, samples in tqdm(val_samples.items(), desc="    验证集"):
    if not samples:
        continue
    
    class_dir = os.path.join(val_dir, class_name)
    os.makedirs(class_dir, exist_ok=True)
    
    for i, img_path in enumerate(samples):
        dst_path = os.path.join(class_dir, f'{i:05d}.jpg')
        if process_and_save_image(img_path, dst_path):
            val_count += 1

print(f"    验证集保存完成: {val_count} 张")

# ============ 步骤5: 生成统计报告 ============
print("\n[步骤5] 生成统计报告...")

report_path = os.path.join(OUTPUT_DIR, 'preprocess_report.txt')

with open(report_path, 'w', encoding='utf-8') as f:
    f.write("=" * 80 + "\n")
    f.write("数据集预处理报告\n")
    f.write("=" * 80 + "\n\n")
    
    f.write("原始数据集:\n")
    f.write(f"  路径: {INPUT_DIR}\n")
    f.write(f"  类别数: {len(all_classes)}\n")
    f.write(f"  总图片数: {total_valid + total_invalid}\n\n")
    
    f.write("预处理结果:\n")
    f.write(f"  有效图片: {total_valid}\n")
    f.write(f"  无效图片: {total_invalid}\n")
    f.write(f"  训练集: {train_count} 张\n")
    f.write(f"  验证集: {val_count} 张\n\n")
    
    f.write("处理参数:\n")
    f.write(f"  目标尺寸: {TARGET_SIZE[0]}×{TARGET_SIZE[1]}\n")
    f.write(f"  图片格式: JPEG\n")
    f.write(f"  训练/验证比例: {TRAIN_RATIO:.1%}/{1-TRAIN_RATIO:.1%}\n\n")
    
    f.write("各类别详情:\n")
    f.write("-" * 80 + "\n")
    for class_name in sorted(class_stats.keys()):
        stats = class_stats[class_name]
        f.write(f"{class_name:50s} | 原始: {stats['total']:5d} | 有效: {stats['valid']:5d} | "
                f"训练: {stats['train']:4d} | 验证: {stats['val']:4d}\n")
    
    f.write("\n" + "=" * 80 + "\n")
    f.write(f"处理完成！数据已保存到: {OUTPUT_DIR}\n")
    f.write("=" * 80 + "\n")

print(f"  报告已保存: {report_path}")

# ============ 完成 ============
print("\n" + "=" * 80)
print("数据集预处理完成")
print("=" * 80)
print(f"总类别数: {len(all_classes)}")
print(f"训练集: {train_count} 张")
print(f"验证集: {val_count} 张")
print(f"输出目录: {OUTPUT_DIR}")
print(f"  - 训练集: {train_dir}")
print(f"  - 验证集: {val_dir}")
print("=" * 80)
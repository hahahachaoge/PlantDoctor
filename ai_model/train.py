import torch
import torch.nn as nn
import torch.optim as optim
from torchvision import datasets, transforms, models
from torch.utils.data import DataLoader, random_split
import os
import json

print("=" * 60)
print("开始训练病虫害识别模型（CPU优化版）")
print("=" * 60)

# 1. 检查数据集
data_path = './data'
if not os.path.exists(data_path):
    print(f"错误：找不到数据集文件夹 {data_path}")
    exit()

# 2. 图片预处理（简化，减少计算量）
transform = transforms.Compose([
    transforms.Resize((224, 224)),
    transforms.RandomHorizontalFlip(),
    transforms.ToTensor(),
    transforms.Normalize(mean=[0.485, 0.456, 0.406], std=[0.229, 0.224, 0.225])
])

val_transform = transforms.Compose([
    transforms.Resize((224, 224)),
    transforms.ToTensor(),
    transforms.Normalize(mean=[0.485, 0.456, 0.406], std=[0.229, 0.224, 0.225])
])

# 3. 加载数据集
print("加载数据集...")
dataset = datasets.ImageFolder(data_path, transform=transform)
print(f"共有 {len(dataset)} 张图片")
print(f"可识别的病虫害种类: {dataset.classes}")
print(f"共 {len(dataset.classes)} 种")

# 4. 分成训练集和验证集
train_size = int(0.8 * len(dataset))
val_size = len(dataset) - train_size
train_dataset, val_dataset = random_split(dataset, [train_size, val_size])
val_dataset.dataset.transform = val_transform

# CPU优化：减小batch size
train_loader = DataLoader(train_dataset, batch_size=16, shuffle=True, num_workers=0)
val_loader = DataLoader(val_dataset, batch_size=16, shuffle=False, num_workers=0)

# 5. 加载预训练模型
print("加载ConvNeXt V2模型...")
model = models.convnext_base(pretrained=True)

# 6. 修改最后一层
num_classes = len(dataset.classes)
model.classifier[2] = nn.Linear(model.classifier[2].in_features, num_classes)

# 7. 使用CPU
device = torch.device('cpu')
model = model.to(device)
print(f"使用设备: {device} (CPU训练较慢，请耐心等待)")

# 8. 设置训练参数
criterion = nn.CrossEntropyLoss()
optimizer = optim.Adam(model.parameters(), lr=0.001)

# 9. 开始训练
print("\n开始训练...")
print("预计需要2-3小时，可以去做别的事，让它后台跑着")
num_epochs = 5  # 先跑5轮，大约1-1.5小时
best_val_acc = 0

for epoch in range(num_epochs):
    model.train()
    running_loss = 0.0
    correct = 0
    total = 0

    print(f"\n第{epoch + 1}轮训练中...")
    for batch_idx, (images, labels) in enumerate(train_loader):
        images, labels = images.to(device), labels.to(device)

        optimizer.zero_grad()
        outputs = model(images)
        loss = criterion(outputs, labels)
        loss.backward()
        optimizer.step()

        running_loss += loss.item()
        _, predicted = torch.max(outputs, 1)
        total += labels.size(0)
        correct += (predicted == labels).sum().item()

        # 每50个batch打印一次进度
        if batch_idx % 50 == 0:
            print(f"  进度: {batch_idx}/{len(train_loader)} batch, 当前准确率: {100 * correct / total:.2f}%")

    train_acc = 100 * correct / total

    # 验证
    print("验证中...")
    model.eval()
    val_correct = 0
    val_total = 0
    with torch.no_grad():
        for images, labels in val_loader:
            images, labels = images.to(device), labels.to(device)
            outputs = model(images)
            _, predicted = torch.max(outputs, 1)
            val_total += labels.size(0)
            val_correct += (predicted == labels).sum().item()

    val_acc = 100 * val_correct / val_total

    print(f"\n第{epoch + 1}轮完成 - 损失:{running_loss:.4f} 训练准确率:{train_acc:.2f}% 验证准确率:{val_acc:.2f}%")

    if val_acc > best_val_acc:
        best_val_acc = val_acc
        torch.save(model.state_dict(), 'best_model.pth')
        print(f"  -> 保存最佳模型 (验证准确率: {val_acc:.2f}%)")

# 10. 保存模型和类别
torch.save(model.state_dict(), 'pest_model.pth')
with open('classes.json', 'w', encoding='utf-8') as f:
    json.dump(dataset.classes, f, ensure_ascii=False)

print(f"\n训练完成！")
print(f"最佳验证准确率: {best_val_acc:.2f}%")
print("文件已保存：pest_model.pth 和 classes.json")
print("\n现在可以运行 python api.py 启动识别服务了")
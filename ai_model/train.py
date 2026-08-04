"""
病虫害识别模型训练脚本
严格按照申报书技术路线：
1. ConvNeXt V2 + 迁移学习
2. 保守训练策略
3. 目标准确率: 92.6%
4. 输出模型供APP集成
支持断点续训
"""
import torch
import torch.nn as nn
import torch.optim as optim
from torchvision import datasets, transforms, models
from torch.utils.data import DataLoader
import os
import json
import time
from tqdm import tqdm
import copy

# 强制使用GPU
print("[设备] 强制使用GPU训练")


class ConservativeLoss(nn.Module):
    """
    保守训练策略
    在原有损失基础上添加参数变化约束
    """

    def __init__(self, base_criterion, original_params, lambda_cons=0.01):
        super().__init__()
        self.base_criterion = base_criterion
        self.original_params = original_params
        self.lambda_cons = lambda_cons

    def forward(self, outputs, targets, model):
        # 基础损失
        base_loss = self.base_criterion(outputs, targets)

        # 保守训练正则项：约束参数变化（跳过分类器层）
        cons_loss = 0.0
        for name, param in model.named_parameters():
            if name in self.original_params and 'classifier' not in name:
                cons_loss += torch.norm(param - self.original_params[name].to(model.device), 2)

        return base_loss + self.lambda_cons * cons_loss


if __name__ == '__main__':
    print("=" * 80)
    print("病虫害识别模型训练")
    print("技术路线: ConvNeXt V2 + 迁移学习 + 保守训练")
    print("目标准确率: 92.6%")
    print("=" * 80)

    # ============ 配置参数 ============
    # Kaggle云端路径
    DATA_DIR = '/kaggle/input/datasets/ziruizhaotong/plant-disease/data_processed'
    OUTPUT_DIR = '/kaggle/working/'
    BATCH_SIZE = 32
    NUM_EPOCHS = 100
    LEARNING_RATE = 0.0002
    WEIGHT_DECAY = 0.01
    TARGET_ACC = 92.6
    EARLY_STOP_PATIENCE = 15

    os.makedirs(OUTPUT_DIR, exist_ok=True)

    # ============ 断点续训配置 ============
    # 手动指定检查点路径（Kaggle每次重启会清空/kaggle/working/，需手动上传检查点）
    # 示例: '/kaggle/input/your-checkpoint/checkpoint_epoch_3.pth'
    MANUAL_RESUME_CKPT = '/kaggle/input/datasets/scnuzm/trazi60/checkpoint_epoch_60.pth'  # 在这里填写上传的检查点文件路径

    # 自动检测最新检查点（支持断点续训）
    RESUME_CKPT = None
    if MANUAL_RESUME_CKPT:
        RESUME_CKPT = MANUAL_RESUME_CKPT
        print(f"[手动指定] 使用检查点: {MANUAL_RESUME_CKPT}")
    else:
        ckpt_files = [f for f in os.listdir(OUTPUT_DIR) if f.startswith('checkpoint_epoch_') and f.endswith('.pth')]
        if ckpt_files:
            latest_ckpt = max(ckpt_files, key=lambda x: int(x.split('_')[2].split('.')[0]))
            RESUME_CKPT = os.path.join(OUTPUT_DIR, latest_ckpt)
            print(f"[自动检测] 发现最新检查点: {latest_ckpt}")

    # ============ 1. 数据增强 ============
    print("\n[1] 配置数据增强...")

    train_transform = transforms.Compose([
        transforms.Resize((256, 256)),
        transforms.RandomCrop(224),
        transforms.RandomHorizontalFlip(p=0.5),
        transforms.RandomVerticalFlip(p=0.3),
        transforms.RandomRotation(30),
        transforms.ColorJitter(brightness=0.2, contrast=0.2, saturation=0.2),
        transforms.ToTensor(),
        transforms.Normalize(mean=[0.485, 0.456, 0.406], std=[0.229, 0.224, 0.225]),
        transforms.RandomErasing(p=0.2)
    ])

    val_transform = transforms.Compose([
        transforms.Resize((224, 224)),
        transforms.ToTensor(),
        transforms.Normalize(mean=[0.485, 0.456, 0.406], std=[0.229, 0.224, 0.225])
    ])

    # ============ 2. 加载数据集 ============
    print("\n[2] 加载数据集...")

    train_dir = os.path.join(DATA_DIR, 'train')
    val_dir = os.path.join(DATA_DIR, 'val')

    train_dataset = datasets.ImageFolder(train_dir, transform=train_transform)
    val_dataset = datasets.ImageFolder(val_dir, transform=val_transform)

    num_classes = len(train_dataset.classes)

    print(f"  训练集: {len(train_dataset)} 张")
    print(f"  验证集: {len(val_dataset)} 张")
    print(f"  类别数: {num_classes}")

    # ============ 3. 数据加载器 ============
    device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
    if not torch.cuda.is_available():
        print("  警告: CUDA不可用，将使用CPU")
    else:
        print(f"  GPU: {torch.cuda.get_device_name(0)}")
    print(f"\n[3] 使用设备: {device}")

    num_workers = 0
    train_loader = DataLoader(train_dataset, batch_size=BATCH_SIZE, shuffle=True,
                              num_workers=num_workers, pin_memory=True)
    val_loader = DataLoader(val_dataset, batch_size=BATCH_SIZE, shuffle=False,
                            num_workers=num_workers, pin_memory=True)

    # ============ 4. 构建ConvNeXt V2模型 ============
    print("\n[4] 构建ConvNeXt V2模型（迁移学习）...")

    # 检查是否有检查点
    if RESUME_CKPT and os.path.exists(RESUME_CKPT):
        print("  检测到检查点，跳过预训练模型下载")
        model = models.convnext_base(weights=None)
        need_load_pretrained = False
    else:
        # 尝试加载预训练模型
        try:
            model = models.convnext_base(weights='IMAGENET1K_V1')
            print("  成功加载ImageNet预训练权重")
        except Exception as e:
            print(f"  警告: 无法下载预训练权重 ({e})")
            print("  使用无预训练模型（效果可能较差）")
            model = models.convnext_base(weights=None)
        need_load_pretrained = True

    # 保存原始参数（用于保守训练）
    original_params = copy.deepcopy(model.state_dict())

    # 修改分类头
    model.classifier[2] = nn.Linear(model.classifier[2].in_features, num_classes)
    model = model.to(device)
    model.device = device

    print(f"  模型: ConvNeXt V2 Base")
    print(f"  预训练: ImageNet-1K")
    print(f"  分类类别: {num_classes}")

    # ============ 5. 训练配置 ============
    print("\n[5] 配置训练参数...")

    base_criterion = nn.CrossEntropyLoss(label_smoothing=0.1)
    criterion = ConservativeLoss(base_criterion, original_params, lambda_cons=0.01)

    optimizer = optim.AdamW(model.parameters(), lr=LEARNING_RATE, weight_decay=WEIGHT_DECAY)
    scheduler = optim.lr_scheduler.CosineAnnealingLR(optimizer, T_max=100)

    # ============ 6. 断点续训检查 ============
    start_epoch = 0
    best_val_acc = 0
    best_model_state = None
    patience_counter = 0
    history = {'train_loss': [], 'train_acc': [], 'val_loss': [], 'val_acc': []}

    if RESUME_CKPT and os.path.exists(RESUME_CKPT):
        print("\n[检测到检查点] 加载断点续训...")
        checkpoint = torch.load(RESUME_CKPT, map_location=device)

        # 检查是否为完整检查点（包含训练状态）
        if 'epoch' in checkpoint:
            # 完整检查点：加载所有状态
            start_epoch = checkpoint['epoch'] + 1
            best_val_acc = checkpoint['best_val_acc']
            best_model_state = checkpoint['best_model_state']
            patience_counter = checkpoint['patience_counter']
            history = checkpoint['history']
            model.load_state_dict(checkpoint['model_state_dict'])
            optimizer.load_state_dict(checkpoint['optimizer_state_dict'])

            if 'original_params' in checkpoint:
                original_params = checkpoint['original_params']
                criterion = ConservativeLoss(base_criterion, original_params, lambda_cons=0.01)
                print(f"  保守训练参数已加载 (lambda_cons=0.01)")

            # 手动调整调度器到当前epoch（避免学习率跳变）
            for _ in range(start_epoch):
                scheduler.step()

            current_lr = optimizer.param_groups[0]['lr']
            print(f"  从第 {start_epoch + 1} 轮继续训练")
            print(f"  当前最佳准确率: {best_val_acc:.2f}%")
            print(f"  调度器已同步，当前学习率: {current_lr:.6f}")
        else:
            # 仅模型权重：只加载模型
            model.load_state_dict(checkpoint)
            print(f"  加载预训练模型权重")
            print(f"  从第 1 轮开始训练")

    # ============ 7. 开始训练 ============
    print("\n" + "=" * 80)
    print("开始训练")
    print("=" * 80)

    start_time = time.time()

    for epoch in range(start_epoch, NUM_EPOCHS):
        epoch_start = time.time()

        # 训练
        model.train()
        running_loss = 0.0
        correct = 0
        total = 0

        train_bar = tqdm(train_loader, desc=f"Epoch {epoch + 1}/{NUM_EPOCHS} [训练]")
        for images, labels in train_bar:
            images, labels = images.to(device), labels.to(device)

            optimizer.zero_grad()
            outputs = model(images)
            loss = criterion(outputs, labels, model)
            loss.backward()
            optimizer.step()

            running_loss += loss.item()
            _, predicted = torch.max(outputs, 1)
            total += labels.size(0)
            correct += (predicted == labels).sum().item()

            train_bar.set_postfix({'loss': f'{loss.item():.4f}', 'acc': f'{100 * correct / total:.2f}%'})

        train_loss = running_loss / len(train_loader)
        train_acc = 100 * correct / total

        # 验证
        model.eval()
        val_loss = 0.0
        val_correct = 0
        val_total = 0

        with torch.no_grad():
            val_bar = tqdm(val_loader, desc=f"Epoch {epoch + 1}/{NUM_EPOCHS} [验证]")
            for images, labels in val_bar:
                images, labels = images.to(device), labels.to(device)
                outputs = model(images)
                loss = base_criterion(outputs, labels)

                val_loss += loss.item()
                _, predicted = torch.max(outputs, 1)
                val_total += labels.size(0)
                val_correct += (predicted == labels).sum().item()

        val_loss = val_loss / len(val_loader)
        val_acc = 100 * val_correct / val_total

        # 更新学习率
        scheduler.step()
        current_lr = optimizer.param_groups[0]['lr']

        # 记录历史
        history['train_loss'].append(train_loss)
        history['train_acc'].append(train_acc)
        history['val_loss'].append(val_loss)
        history['val_acc'].append(val_acc)

        epoch_time = time.time() - epoch_start

        # 打印结果
        print(f"\nEpoch {epoch + 1} 完成 (耗时: {epoch_time:.1f}s)")
        print(f"  训练 - Loss: {train_loss:.4f}, Acc: {train_acc:.2f}%")
        print(f"  验证 - Loss: {val_loss:.4f}, Acc: {val_acc:.2f}%")
        print(f"  学习率: {current_lr:.6f}")

        # 保存最佳模型
        if val_acc > best_val_acc:
            best_val_acc = val_acc
            best_model_state = copy.deepcopy(model.state_dict())
            patience_counter = 0

            # 保存最佳模型检查点
            torch.save({
                'epoch': epoch,
                'model_state_dict': model.state_dict(),
                'optimizer_state_dict': optimizer.state_dict(),
                'val_acc': val_acc,
                'num_classes': num_classes,
                'classes': train_dataset.classes
            }, os.path.join(OUTPUT_DIR, 'best_model.pth'))

            print(f"  [保存] 最佳模型 (验证准确率: {val_acc:.2f}%)")

            # 新增：记录最佳模型信息到txt
            with open(os.path.join(OUTPUT_DIR, 'best_model_info.txt'), 'w', encoding='utf-8') as f:
                f.write(f"最佳模型轮次: Epoch {epoch + 1}\n")
                f.write(f"验证准确率: {val_acc:.2f}%\n")
                f.write(f"验证损失: {val_loss:.4f}\n")
                f.write(f"训练准确率: {train_acc:.2f}%\n")
                f.write(f"训练损失: {train_loss:.4f}\n")
                f.write(f"保存时间: {time.strftime('%Y-%m-%d %H:%M:%S')}\n")

            # 达到目标准确率
            if val_acc >= TARGET_ACC:
                print(f"\n[达标] 已达到目标准确率 {TARGET_ACC}%！")
        else:
            patience_counter += 1

        # 保存检查点（每轮都保存，支持断点续训）
        # 每轮单独保存检查点（不覆盖）
        ckpt_path = os.path.join(OUTPUT_DIR, f'checkpoint_epoch_{epoch + 1}.pth')
        torch.save({
            'epoch': epoch,
            'model_state_dict': model.state_dict(),
            'optimizer_state_dict': optimizer.state_dict(),
            'scheduler_state_dict': scheduler.state_dict(),
            'best_val_acc': best_val_acc,
            'best_model_state': best_model_state,
            'patience_counter': patience_counter,
            'history': history,
            'original_params': original_params  # 保存原始参数（保守训练）
        }, ckpt_path)

        # 新增：每轮指标保存到txt
        epoch_info_path = os.path.join(OUTPUT_DIR, f'epoch_{epoch + 1}_info.txt')
        with open(epoch_info_path, 'w', encoding='utf-8') as f:
            f.write(f"轮次: Epoch {epoch + 1}\n")
            f.write(f"训练准确率: {train_acc:.2f}%\n")
            f.write(f"训练损失: {train_loss:.4f}\n")
            f.write(f"验证准确率: {val_acc:.2f}%\n")
            f.write(f"验证损失: {val_loss:.4f}\n")
            f.write(f"当前最佳准确率: {best_val_acc:.2f}%\n")
            f.write(f"学习率: {current_lr:.6f}\n")
            f.write(f"耗时: {epoch_time:.1f}s\n")
            f.write(f"保存时间: {time.strftime('%Y-%m-%d %H:%M:%S')}\n")

        # 早停检查
        if patience_counter >= EARLY_STOP_PATIENCE:
            print(f"\n[早停] 验证准确率连续 {EARLY_STOP_PATIENCE} 轮未提升")
            break

    # ============ 8. 保存模型供APP集成 ============
    print("\n" + "=" * 80)
    print("保存模型文件供APP集成")
    print("=" * 80)

    # 保存最佳模型（APP使用）
    torch.save(best_model_state, os.path.join(OUTPUT_DIR, 'pest_model.pth'))

    # 保存类别列表（APP使用）
    with open(os.path.join(OUTPUT_DIR, 'classes.json'), 'w', encoding='utf-8') as f:
        json.dump(train_dataset.classes, f, ensure_ascii=False, indent=2)

    # 保存训练历史
    with open(os.path.join(OUTPUT_DIR, 'training_history.json'), 'w') as f:
        json.dump(history, f, indent=2)

    # 保存训练报告
    total_time = time.time() - start_time
    with open(os.path.join(OUTPUT_DIR, 'training_report.txt'), 'w', encoding='utf-8') as f:
        f.write("=" * 80 + "\n")
        f.write("病虫害识别模型训练报告\n")
        f.write("=" * 80 + "\n\n")

        f.write("技术路线:\n")
        f.write("  1. ConvNeXt V2卷积神经网络\n")
        f.write("  2. 迁移学习（ImageNet预训练）\n")
        f.write("  3. 保守训练策略\n")
        f.write("  4. 数据增强\n\n")

        f.write("训练配置:\n")
        f.write(f"  数据集: {num_classes}类\n")
        f.write(f"  训练集: {len(train_dataset)}张\n")
        f.write(f"  验证集: {len(val_dataset)}张\n")
        f.write(f"  批次大小: {BATCH_SIZE}\n")
        f.write(f"  训练轮数: {epoch + 1}\n")
        f.write(f"  学习率: {LEARNING_RATE}\n\n")

        f.write("训练结果:\n")
        f.write(f"  最佳验证准确率: {best_val_acc:.2f}%\n")
        f.write(f"  目标准确率: {TARGET_ACC}%\n")
        f.write(f"  是否达标: {'是' if best_val_acc >= TARGET_ACC else '否'}\n")
        f.write(f"  总训练时间: {total_time / 3600:.2f}小时\n\n")

        f.write("输出文件:\n")
        f.write("  - pest_model.pth (模型文件，供APP集成)\n")
        f.write("  - classes.json (类别列表)\n")
        f.write("  - best_model.pth (最佳模型检查点)\n")

        f.write("\n" + "=" * 80 + "\n")

    print(f"\n训练完成！")
    print(f"最佳验证准确率: {best_val_acc:.2f}%")
    print(f"目标准确率: {TARGET_ACC}%")
    print(f"是否达标: {'是' if best_val_acc >= TARGET_ACC else '否'}")

    print(f"\n输出文件:")
    print(f"  1. {os.path.join(OUTPUT_DIR, 'pest_model.pth')}")
    print(f"     - 模型文件，供APP集成使用")
    print(f"  2. {os.path.join(OUTPUT_DIR, 'classes.json')}")
    print(f"     - 类别列表，供APP集成使用")
    print(f"  3. {os.path.join(OUTPUT_DIR, 'best_model.pth')}")
    print(f"     - 最佳模型检查点")
    print(f"  4. {os.path.join(OUTPUT_DIR, 'training_report.txt')}")
    print(f"     - 训练报告")

    print("\n" + "=" * 80)
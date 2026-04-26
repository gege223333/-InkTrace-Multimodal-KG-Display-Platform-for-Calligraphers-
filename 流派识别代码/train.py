# ==================================================
# 本地训练代码（ResNet50 + GPU + 5类 + 断点续训）
# ==================================================
#AI辅助生成：DeepSeek-R1 2026-4
import os
import torch
import torch.nn as nn
from torch.utils.data import Dataset, DataLoader
from torchvision import transforms, models
from PIL import Image, ImageOps
from tqdm import tqdm
import time
import shutil
import random

# ========== 1. 路径配置 ==========
base_path = r'D:\奥义 学习\计算机\其他项目\大创\数字人文\流派识别'
train_path = os.path.join(base_path, r'MCCD_Character(1)\MCCD_Character\trainset_dataset\dataset\train1')
test_path = os.path.join(base_path, r'MCCD_Character(1)\MCCD_Character\trainset_dataset\dataset\test1')
extra_images_path = r'D:\奥义 学习\计算机\其他项目\大创\数字人文\流派识别\新加测试图'
output_dir = os.path.join(base_path, 'model_output')
checkpoint_dir = os.path.join(base_path, 'checkpoints')
os.makedirs(output_dir, exist_ok=True)
os.makedirs(checkpoint_dir, exist_ok=True)

# 5类
STYLE_CLASSES = ['楷', '行', '草', '隶', '篆']
STYLE_TO_ID = {s: i for i, s in enumerate(STYLE_CLASSES)}
NUM_CLASSES = len(STYLE_CLASSES)

# ========== 2. 数据集类 ==========
class CalligraphyDataset(Dataset):
    def __init__(self, root, transform=None):
        self.samples = []
        self.transform = transform
        for style in STYLE_CLASSES:
            style_dir = os.path.join(root, style)
            if not os.path.exists(style_dir):
                print(f"  警告: {style_dir} 不存在")
                continue
            for img_name in os.listdir(style_dir):
                if img_name.lower().endswith(('.png', '.jpg', '.jpeg')):
                    self.samples.append({
                        'path': os.path.join(style_dir, img_name),
                        'label': STYLE_TO_ID[style]
                    })
        print(f"从 {root} 加载 {len(self.samples)} 张图片")
    
    def __len__(self):
        return len(self.samples)
    
    def __getitem__(self, idx):
        img = Image.open(self.samples[idx]['path']).convert('RGB')
        if self.transform:
            img = self.transform(img)
        return img, self.samples[idx]['label']

# ========== 🔥 随机反色类 ==========
class RandomInvert:
    def __call__(self, img):
        if random.random() < 0.5:   # 50% 概率反转颜色
            return ImageOps.invert(img)
        return img

# ========== 3. 主程序 ==========
if __name__ == '__main__':
    # 复制新增图片到训练集
    print("=" * 50)
    print("复制新增图片到训练集")
    print("=" * 50)

    new_images = {
        '草.png': '草',
        '楷.png': '楷',
        '楷书.png': '楷',
        '行.png': '行'
    }

    for img_name, style in new_images.items():
        src = os.path.join(extra_images_path, img_name)
        dst_dir = os.path.join(train_path, style)
        if os.path.exists(src):
            os.makedirs(dst_dir, exist_ok=True)
            dst = os.path.join(dst_dir, img_name)
            shutil.copy2(src, dst)
            print(f"  ✅ {img_name} → {style}/")
        else:
            print(f"  ⚠️ 找不到: {src}")

    # ========== 🔥 数据预处理（加入随机反色）==========
    train_transform = transforms.Compose([
        RandomInvert(),  # 🔥 关键：50%概率随机反色，让模型学会颜色不变性
        transforms.Resize((224, 224)),
        transforms.RandomHorizontalFlip(p=0.5),
        transforms.RandomRotation(10),
        transforms.ColorJitter(brightness=0.2, contrast=0.2),
        transforms.ToTensor(),
        transforms.Normalize(mean=[0.485, 0.456, 0.406], std=[0.229, 0.224, 0.225])
    ])

    test_transform = transforms.Compose([
        transforms.Resize((224, 224)),
        transforms.ToTensor(),
        transforms.Normalize(mean=[0.485, 0.456, 0.406], std=[0.229, 0.224, 0.225])
    ])

    # 加载数据
    print("\n" + "=" * 50)
    print("加载数据")
    print("=" * 50)

    train_dataset = CalligraphyDataset(train_path, train_transform)
    test_dataset = CalligraphyDataset(test_path, test_transform)

    batch_size = 16
    train_loader = DataLoader(
    train_dataset, 
    batch_size=batch_size, 
    shuffle=True, 
    num_workers=2,      # 🔥 关键：从 0 改成 2
    pin_memory=True,    # 🔥 关键：开启
    prefetch_factor=4   # 预取 4 个 batch
)
    test_loader = DataLoader(test_dataset, batch_size=batch_size, shuffle=False, num_workers=0)

    print(f"训练批次数: {len(train_loader)}")
    print(f"测试批次数: {len(test_loader)}")

    # 创建模型
    device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
    print(f"\n使用设备: {device}")

    model = models.resnet50(pretrained=True)
    model.fc = nn.Linear(2048, NUM_CLASSES)
    model = model.to(device)

    criterion = nn.CrossEntropyLoss()
    optimizer = torch.optim.Adam(model.parameters(), lr=0.001)
    scheduler = torch.optim.lr_scheduler.StepLR(optimizer, step_size=5, gamma=0.5)

    # ========== 断点续训：加载之前的检查点 ==========
    start_epoch = 1
    best_acc = 0

    # 查找最新的检查点
    checkpoint_files = [f for f in os.listdir(checkpoint_dir) if f.startswith('checkpoint_epoch_')]
    if checkpoint_files:
        # 提取轮数并找最大的
        epochs = [int(f.split('_')[-1].split('.')[0]) for f in checkpoint_files]
        latest_epoch = max(epochs)
        checkpoint_path = os.path.join(checkpoint_dir, f'checkpoint_epoch_{latest_epoch}.pth')
        
        print(f"\n发现检查点: {checkpoint_path}")
        checkpoint = torch.load(checkpoint_path, map_location=device)
        model.load_state_dict(checkpoint['model_state_dict'])
        optimizer.load_state_dict(checkpoint['optimizer_state_dict'])
        scheduler.load_state_dict(checkpoint['scheduler_state_dict'])
        start_epoch = checkpoint['epoch'] + 1
        best_acc = checkpoint.get('best_acc', 0)
        print(f"✅ 从第 {start_epoch} 轮继续训练")
        print(f"   之前最佳验证准确率: {best_acc:.2f}%")
    else:
        print("\n未发现检查点，从头开始训练")

    # 训练函数
    def train_epoch(model, loader, criterion, optimizer, epoch):
        model.train()
        correct = 0
        total = 0
        
        pbar = tqdm(loader, desc=f"Epoch {epoch} [训练]")
        for images, labels in pbar:
            images, labels = images.to(device), labels.to(device)
            optimizer.zero_grad()
            
            outputs = model(images)
            loss = criterion(outputs, labels)
            loss.backward()
            optimizer.step()
            
            _, predicted = torch.max(outputs, 1)
            total += labels.size(0)
            correct += (predicted == labels).sum().item()
            pbar.set_postfix({'acc': f'{100.*correct/total:.2f}%'})
        
        return 100. * correct / total

    def validate(model, loader):
        model.eval()
        correct = 0
        total = 0
        with torch.no_grad():
            pbar = tqdm(loader, desc="[验证]")
            for images, labels in pbar:
                images, labels = images.to(device), labels.to(device)
                outputs = model(images)
                _, predicted = torch.max(outputs, 1)
                total += labels.size(0)
                correct += (predicted == labels).sum().item()
                pbar.set_postfix({'acc': f'{100.*correct/total:.2f}%'})
        return 100. * correct / total

    # 开始训练
    num_epochs = 25  # 从20轮继续到25轮
    print("\n" + "=" * 50)
    print(f"开始训练（ResNet50, batch_size={batch_size}, 共{num_epochs}轮）")
    print(f"从第 {start_epoch} 轮开始")
    print("⚠️ 已加入随机反色增强，模型将学习颜色不变性")
    print("=" * 50)

    start_time = time.time()

    for epoch in range(start_epoch, num_epochs + 1):
        print(f"\nEpoch {epoch}/{num_epochs}")
        
        train_acc = train_epoch(model, train_loader, criterion, optimizer, epoch)
        test_acc = validate(model, test_loader)
        
        scheduler.step()
        
        print(f"训练准确率: {train_acc:.2f}% | 验证准确率: {test_acc:.2f}%")
        
        # 保存最佳模型
        if test_acc > best_acc:
            best_acc = test_acc
            best_model_path = os.path.join(output_dir, 'best_model_5classes.pth')
            torch.save(model.state_dict(), best_model_path)
            print(f"  ★ 保存最佳模型，准确率: {best_acc:.2f}%")
        
        # 每轮结束后保存检查点（用于断点续训）
        checkpoint = {
            'epoch': epoch,
            'model_state_dict': model.state_dict(),
            'optimizer_state_dict': optimizer.state_dict(),
            'scheduler_state_dict': scheduler.state_dict(),
            'best_acc': best_acc,
            'train_acc': train_acc,
            'test_acc': test_acc,
        }
        checkpoint_path = os.path.join(checkpoint_dir, f'checkpoint_epoch_{epoch}.pth')
        torch.save(checkpoint, checkpoint_path)
        print(f"  💾 已保存检查点: {checkpoint_path}")

    total_time = time.time() - start_time
    print("\n" + "=" * 50)
    print(f"训练完成！总耗时: {int(total_time//60)}分{int(total_time%60)}秒")
    print(f"最佳验证准确率: {best_acc:.2f}%")
    print(f"模型保存位置: {output_dir}\\best_model_5classes.pth")
    print("=" * 50)
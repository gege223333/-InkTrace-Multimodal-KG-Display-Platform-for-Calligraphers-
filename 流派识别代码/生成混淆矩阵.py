import torch
import torch.nn as nn
from torch.utils.data import DataLoader
from torchvision import transforms, models
from sklearn.metrics import confusion_matrix
import matplotlib.pyplot as plt
import seaborn as sns
import numpy as np
import os
from torch.utils.data import Dataset, DataLoader
import matplotlib.pyplot as plt
#AI辅助生成 DeepSeek-R1网页版 2026-4
# 设置中文字体
plt.rcParams['font.sans-serif'] = ['SimHei', 'Microsoft YaHei', 'PingFang SC', 'Heiti SC']  # 中文字体
plt.rcParams['axes.unicode_minus'] = False  # 解决负号显示问题

# ==================================================
# 1. 加载模型
# ==================================================
base_path = r'D:\奥义 学习\计算机\其他项目\大创\数字人文\流派识别'
model_path = os.path.join(base_path, r'模型+预测代码\best_model_5classes.pth')

STYLE_CLASSES = ['楷', '行', '草', '隶', '篆']
NUM_CLASSES = len(STYLE_CLASSES)

device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
print(f"使用设备: {device}")

# 创建模型
model = models.resnet50(pretrained=False)
model.fc = nn.Linear(2048, NUM_CLASSES)
model.load_state_dict(torch.load(model_path, map_location=device))
model = model.to(device)
model.eval()
print("✅ 模型加载成功")

# ==================================================
# 2. 加载测试集
# ==================================================
test_path = os.path.join(base_path, r'MCCD_Character(1)\MCCD_Character\trainset_dataset\dataset\test1')

test_transform = transforms.Compose([
    transforms.Resize((224, 224)),
    transforms.ToTensor(),
    transforms.Normalize(mean=[0.485, 0.456, 0.406], std=[0.229, 0.224, 0.225])
])

# 数据集类（和训练时一样）
class CalligraphyDataset(Dataset):
    def __init__(self, root, transform=None):
        self.samples = []
        self.transform = transform
        for style in STYLE_CLASSES:
            style_dir = os.path.join(root, style)
            if not os.path.exists(style_dir):
                continue
            for img_name in os.listdir(style_dir):
                if img_name.lower().endswith(('.png', '.jpg', '.jpeg')):
                    self.samples.append({
                        'path': os.path.join(style_dir, img_name),
                        'label': STYLE_CLASSES.index(style)
                    })
        print(f"从 {root} 加载 {len(self.samples)} 张图片")
    
    def __len__(self):
        return len(self.samples)
    
    def __getitem__(self, idx):
        from PIL import Image
        img = Image.open(self.samples[idx]['path']).convert('RGB')
        if self.transform:
            img = self.transform(img)
        return img, self.samples[idx]['label']

test_dataset = CalligraphyDataset(test_path, test_transform)
test_loader = DataLoader(test_dataset, batch_size=32, shuffle=False, num_workers=0)

# ==================================================
# 3. 预测并收集结果
# ==================================================
all_preds = []
all_labels = []

print("正在预测测试集...")
with torch.no_grad():
    for images, labels in test_loader:
        images, labels = images.to(device), labels.to(device)
        outputs = model(images)
        _, preds = torch.max(outputs, 1)
        all_preds.extend(preds.cpu().numpy())
        all_labels.extend(labels.cpu().numpy())

# ==================================================
# 4. 生成混淆矩阵
# ==================================================
cm = confusion_matrix(all_labels, all_preds)

# 归一化（百分比）
cm_percent = cm.astype('float') / cm.sum(axis=1)[:, np.newaxis] * 100

# 绘图
plt.figure(figsize=(8, 6))
sns.heatmap(cm_percent, annot=True, fmt='.1f', cmap='Blues',
            xticklabels=STYLE_CLASSES, yticklabels=STYLE_CLASSES)
plt.xlabel('预测', fontsize=12)
plt.ylabel('真实', fontsize=12)
plt.title('混淆矩阵 (百分比%)', fontsize=14)
plt.tight_layout()
plt.savefig('confusion_matrix.png', dpi=300)
plt.show()

# 打印各类别准确率
print("\n各类别识别准确率:")
for i, style in enumerate(STYLE_CLASSES):
    correct = cm[i][i]
    total = np.sum(cm[i])
    acc = correct / total * 100
    print(f"  {style}: {acc:.2f}% ({correct}/{total})")

# 整体准确率
total_correct = np.trace(cm)
total_samples = np.sum(cm)
print(f"\n整体准确率: {total_correct/total_samples*100:.2f}%")
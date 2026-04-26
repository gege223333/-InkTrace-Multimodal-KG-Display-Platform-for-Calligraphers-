import torch
import torch.nn as nn
from torchvision import transforms, models
from PIL import Image, ImageFilter, ImageOps
import numpy as np
import os
import matplotlib.pyplot as plt
#AI辅助生成 DeepSeek-R1网页版2026-04
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
# 2. 图像预处理函数（二值化 + 去噪）
# ==================================================
def preprocess_image(image_path):
    """
    读取图片，自动反转深色底 + 二值化 + 去噪
    """
    img = Image.open(image_path).convert('RGB')
    original = img.copy()

    # 步骤1：转灰度
    img_gray = img.convert('L')
    img_array = np.array(img_gray)

    # ========== 🔥 关键新增：自动检测深色底并反转 ==========
    avg_brightness = np.mean(img_array)
    if avg_brightness <127:
        print("  🔄 检测到深色底（如黑底白字），自动反转颜色")
        img_array = 255 - img_array   # 黑白反转
        img_gray = Image.fromarray(img_array)

    # 步骤2：二值化（自适应阈值）
    threshold = np.mean(img_array)
    binary_array = np.where(img_array > threshold, 255, 0).astype(np.uint8)

    # 步骤3：中值滤波去噪
    binary_img = Image.fromarray(binary_array)
    denoised_img = binary_img.filter(ImageFilter.MedianFilter(size=3))

    # 步骤4：转回 RGB
    final_img = denoised_img.convert('RGB')

    return final_img, original

# ==================================================
# 3. 预测函数
# ==================================================
def predict(image_path, show_preprocess=True):
    """
    预测书法图片的流派
    show_preprocess: 是否显示预处理前后的对比
    """
    # 预处理
    processed_img, original_img = preprocess_image(image_path)
    
    if show_preprocess:
        # 显示预处理效果
        import matplotlib.pyplot as plt
        fig, axes = plt.subplots(1, 3, figsize=(12, 4))
        
        axes[0].imshow(original_img)
        axes[0].set_title('原图')
        axes[0].axis('off')
        
        axes[1].imshow(processed_img)
        axes[1].set_title('二值化+去噪后')
        axes[1].axis('off')
        
        # 显示模型关注区域（可选）
        axes[2].axis('off')
        
        plt.tight_layout()
        plt.show()
    
    # 标准预处理（归一化等）
    transform = transforms.Compose([
        transforms.Resize((224, 224)),
        transforms.ToTensor(),
        transforms.Normalize(mean=[0.485, 0.456, 0.406], std=[0.229, 0.224, 0.225])
    ])
    
    # 转换
    img_tensor = transform(processed_img).unsqueeze(0).to(device)
    
    # 预测
    with torch.no_grad():
        outputs = model(img_tensor)
        probabilities = torch.softmax(outputs, dim=1)
        predicted_idx = torch.argmax(outputs, dim=1).item()
    
    # 结果
    predicted_style = STYLE_CLASSES[predicted_idx]
    confidence = probabilities[0][predicted_idx].item() * 100
    
    # 打印所有流派概率
    print(f"\n图片: {os.path.basename(image_path)}")
    print(f"预测流派: {predicted_style}")
    print(f"置信度: {confidence:.2f}%")
    print("\n所有流派可能性:")
    for i, style in enumerate(STYLE_CLASSES):
        prob = probabilities[0][i].item() * 100
        print(f"  {style}: {prob:.2f}%")
    
    # Top-3
    top3_probs, top3_idxs = torch.topk(probabilities[0], 3)
    print("\nTop-3 可能性:")
    for i, (idx, prob) in enumerate(zip(top3_idxs, top3_probs)):
        print(f"  {i+1}. {STYLE_CLASSES[idx.item()]}: {prob.item()*100:.2f}%")
    
    return predicted_style, confidence

# ==================================================
# 4. 批量预测
# ==================================================
def batch_predict(image_folder):
    """批量预测文件夹内的所有图片"""
    results = []
    for img_name in os.listdir(image_folder):
        if img_name.lower().endswith(('.png', '.jpg', '.jpeg')):
            img_path = os.path.join(image_folder, img_name)
            try:
                style, conf = predict(img_path, show_preprocess=False)
                results.append({'name': img_name, 'style': style, 'confidence': conf})
                print(f"  {img_name} → {style} ({conf:.2f}%)")
            except Exception as e:
                print(f"  ❌ {img_name} 预测失败: {e}")
    return results

# ==================================================
# 5. 使用示例
# ==================================================
if __name__ == '__main__':
    
    # 单张图片预测
    test_image = r'D:\奥义 学习\计算机\其他项目\大创\数字人文\流派识别\新测试集\楷1.png'
    
    if os.path.exists(test_image):
        predict(test_image, show_preprocess=True)
    else:
        print(f"图片不存在: {test_image}")
        print("请修改 test_image 路径")

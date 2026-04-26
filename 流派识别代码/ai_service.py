import torch
import torch.nn as nn
from torchvision import transforms, models
from PIL import Image, ImageFilter
import os
import numpy as np

STYLE_CLASSES = ['楷', '行', '草', '隶', '篆']

class AIService:
    def __init__(self):
        self.device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
        self.model = None
        self._load_model()

    def _load_model(self):
        model_path = os.path.join(os.path.dirname(__file__), 'models', 'best_model_5classes.pth')
        model_path = os.path.abspath(model_path)

        if not os.path.exists(model_path):
            print(f"模型文件不存在: {model_path}")
            return

        model = models.resnet50(pretrained=False)
        model.fc = nn.Linear(2048, len(STYLE_CLASSES))
        model.load_state_dict(torch.load(model_path, map_location=self.device))
        model = model.to(self.device)
        model.eval()
        self.model = model
        print(f"AI模型加载成功！设备: {self.device}")

    def preprocess_image(self, image_path):
        """
        读取图片，自动反转深色底 + 二值化 + 去噪
        返回处理后的 PIL Image
        """
        # 读取图片
        img = Image.open(image_path).convert('RGB')
        
        # 步骤1：转灰度
        img_gray = img.convert('L')
        img_array = np.array(img_gray)

        # 关键新增：自动检测深色底并反转
        avg_brightness = np.mean(img_array)
        if avg_brightness < 70:
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

        return final_img

    def predict(self, image_path):
        if self.model is None:
            return None, 0.0, {}

        # 预处理图像
        processed_img = self.preprocess_image(image_path)
        
        # 标准预处理（归一化等）
        transform = transforms.Compose([
            transforms.Resize((224, 224)),
            transforms.ToTensor(),
            transforms.Normalize(mean=[0.485, 0.456, 0.406], std=[0.229, 0.224, 0.225])
        ])
        
        # 转换
        img_tensor = transform(processed_img).unsqueeze(0).to(self.device)

        with torch.no_grad():
            outputs = self.model(img_tensor)
            probabilities = torch.softmax(outputs, dim=1)
            predicted_idx = torch.argmax(outputs, dim=1).item()

        predicted_style = STYLE_CLASSES[predicted_idx]
        confidence = probabilities[0][predicted_idx].item() * 100

        all_probs = {}
        for i, style in enumerate(STYLE_CLASSES):
            all_probs[style] = probabilities[0][i].item() * 100

        return predicted_style, confidence, all_probs

ai_service = AIService()

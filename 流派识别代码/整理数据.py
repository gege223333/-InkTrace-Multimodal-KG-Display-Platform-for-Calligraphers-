import os
import shutil
from collections import defaultdict
from tqdm import tqdm
#AI辅助生成 Deepseek -R1 网页版2026.4
TRAIN_SRC = r"D:\奥义 学习\计算机\其他项目\大创\数字人文\流派识别\MCCD_Character(1)\MCCD_Character\trainset_dataset\train"
TEST_SRC = r"D:\奥义 学习\计算机\其他项目\大创\数字人文\流派识别\MCCD_Character(1)\MCCD_Character\trainset_dataset\test"

# 目标路径（整理后的）
TRAIN_DST = r"D:\奥义 学习\计算机\其他项目\大创\数字人文\流派识别\MCCD_Character(1)\MCCD_Character\trainset_dataset\train1"
TEST_DST = r"D:\奥义 学习\计算机\其他项目\大创\数字人文\流派识别\MCCD_Character(1)\MCCD_Character\trainset_dataset\test1"

# 流派列表（从文件名中提取）
STYLES = ['六体', '其他', '印', '楷', '甲骨', '石', '简', '篆', '草', '行', '金', '隶']

# 创建目标文件夹
print("创建目标文件夹...")
for style in STYLES:
    os.makedirs(os.path.join(TRAIN_DST, style), exist_ok=True)
    os.makedirs(os.path.join(TEST_DST, style), exist_ok=True)

def count_files(src_dir):
    """统计总文件数"""
    total = 0
    for char_folder in os.listdir(src_dir):
        char_path = os.path.join(src_dir, char_folder)
        if os.path.isdir(char_path):
            for filename in os.listdir(char_path):
                if filename.endswith('.png'):
                    total += 1
    return total

def organize_files(src_dir, dst_dir, desc="整理"):
    """遍历子文件夹，按流派分类复制图片"""
    # 先统计总文件数
    total_files = count_files(src_dir)
    
    # 统计每个流派的文件数
    style_counts = defaultdict(int)
    
    with tqdm(total=total_files, desc=desc, unit="张") as pbar:
        for char_folder in os.listdir(src_dir):
            char_path = os.path.join(src_dir, char_folder)
            if not os.path.isdir(char_path):
                continue
            
            for filename in os.listdir(char_path):
                if not filename.endswith('.png'):
                    continue
                
                # 从文件名提取流派：格式是 "字-流派-作者-编号.png"
                parts = filename.replace('.png', '').split('-')
                if len(parts) >= 2:
                    style = parts[1]  # 第二个部分是流派
                    if style in STYLES:
                        src_file = os.path.join(char_path, filename)
                        dst_file = os.path.join(dst_dir, style, filename)
                        shutil.copy2(src_file, dst_file)
                        style_counts[style] += 1
                
                pbar.update(1)
                pbar.set_postfix_str(f"当前流派: {style if 'style' in locals() else '未知'}")
    
    return style_counts

print("="*50)
print("开始整理训练集...")
print("="*50)
train_counts = organize_files(TRAIN_SRC, TRAIN_DST, desc="训练集")

print("="*50)
print("开始整理测试集...")
print("="*50)
test_counts = organize_files(TEST_SRC, TEST_DST, desc="测试集")

print("="*50)
print("整理完成！新结构：")
print("="*50)
print(f"{'流派':<8} {'训练集':>10} {'测试集':>10} {'总计':>10}")
print("-"*40)
total_train = 0
total_test = 0
for style in STYLES:
    train_c = train_counts.get(style, 0)
    test_c = test_counts.get(style, 0)
    total_train += train_c
    total_test += test_c
    print(f"{style:<8} {train_c:>10} {test_c:>10} {train_c+test_c:>10}")
print("-"*40)
print(f"{'总计':<8} {total_train:>10} {total_test:>10} {total_train+total_test:>10}")
print("="*50)

# 验证文件是否复制成功
print("\n验证示例文件...")
for style in STYLES[:3]:  # 只检查前3个流派
    train_dir = os.path.join(TRAIN_DST, style)
    if os.path.exists(train_dir):
        files = os.listdir(train_dir)
        if files:
            print(f"  {style}: {files[0]}")

            
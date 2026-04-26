import fitz
import os

pdf_path = r"D:\奥义 学习\计算机\其他项目\大创\数字人文\OCR识别\玉台书画史.pdf"  
output_folder = r"D:\奥义 学习\计算机\其他项目\大创\数字人文\OCR识别\pdf_images"  

os.makedirs(output_folder, exist_ok=True)
doc = fitz.open(pdf_path)

for i, page in enumerate(doc):
    pix = page.get_pixmap(dpi=200)  
    pix.save(f"{output_folder}/page_{i+1:04d}.png")
    print(f"已转换第{i+1}页")

print(f"完成！共{len(doc)}页")
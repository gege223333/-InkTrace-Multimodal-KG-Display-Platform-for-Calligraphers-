from aip import AipOcr
import opencc


APP_ID = '7542843'
API_KEY = 'feqlshoCeqUlrnErtRoVDlqQ'
SECRET_KEY = 'VAjXvXukeZjsj2G41wpGhIs7RCyq6gSM'

# 2. 初始化客户端
client = AipOcr(APP_ID, API_KEY, SECRET_KEY)

# 3. 初始化繁简转换器
converter = opencc.OpenCC('t2s')  # t2s = 繁体转简体

def ocr_image(image_path):
    """识别单张图片，返回简体中文文本"""
    with open(image_path, 'rb') as f:
        image = f.read()
    
    # 调用高精度OCR，language_type设为CHN_ENG（支持中英文混合）
    # 百度OCR会自动检测竖排文字方向，无需额外设置[citation:1]
    result = client.basicAccurate(image, options={
        'language_type': 'CHN_ENG',  # 中英文混合
        'detect_direction': 'true'   # 自动检测文字方向
    })
    
    # 提取识别的文字
    extracted_text = ""
    if 'words_result' in result:
        for item in result['words_result']:
            extracted_text += item['words'] + "\n"
    
    # 繁转简
    simplified_text = converter.convert(extracted_text)
    return simplified_text

# 使用示例
text = ocr_image('你的古籍页面.jpg')
print(text)

# 保存结果
with open('output.txt', 'w', encoding='utf-8') as f:
    f.write(text)
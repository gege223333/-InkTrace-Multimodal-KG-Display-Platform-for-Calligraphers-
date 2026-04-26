import dashscope
from http import HTTPStatus
import sys

try:
    from config import DASHSCOPE_API_KEY, DASHSCOPE_MODEL
except ImportError:
    print("错误: 找不到config.py文件或配置不正确")
    print("请创建config.py文件，包含DASHSCOPE_API_KEY和DASHSCOPE_MODEL")
    sys.exit(1)

print(f"使用模型: {DASHSCOPE_MODEL}")
dashscope.api_key = DASHSCOPE_API_KEY

# 简单测试
response = dashscope.Generation.call(
    model=DASHSCOPE_MODEL,
    prompt="请用一句话回复'连接成功'",
    max_tokens=20
)

if response.status_code == HTTPStatus.OK:
    print(f"✓ API连接成功！")
    print(f"回复: {response.output.choices[0].message.content}")
else:
    print(f"✗ API连接失败: {response.code}")
    if response.message:
        print(f"错误信息: {response.message}")

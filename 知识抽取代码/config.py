# config.py
# 删除或注释原来的DeepSeek配置，改为阿里云DashScope配置
DASHSCOPE_API_KEY = "sk-dc88cc36272a48618bba279b040f7160"  # 替换为您的DashScope API密钥
DASHSCOPE_MODEL = "qwen-max"  # 可选：qwen-max, qwen-plus, qwen-turbo

# 处理参数
CHUNK_SIZE = 2000
MAX_TOKENS = 4000
BATCH_SIZE = 5
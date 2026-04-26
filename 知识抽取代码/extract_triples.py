import json
import re
import time
import dashscope
from dashscope import Generation

# ===================== 你的配置 =====================
dashscope.api_key = "sk-2561c82d251646628dd0caf66b6554a3"
CHUNK_SIZE = 800
WAIT_TIME = 0.6
# =====================================================

def read_md_file(file_path):
    with open(file_path, "r", encoding="utf-8") as f:
        content = f.read()
    content = re.sub(r'\n+', '\n', content).strip()
    content = re.sub(r'\t+', '', content)
    content = re.sub(r' +', ' ', content)
    return content

def split_text_to_chunks(text, chunk_size=CHUNK_SIZE):
    chunks = []
    for i in range(0, len(text), chunk_size):
        chunks.append(text[i:i+chunk_size])
    return chunks

def get_triples_from_qwen(text):
    example = '[{"subject":"王羲之","predicate":"字号","object":"逸少"},{"subject":"王羲之","predicate":"擅长","object":"行书"}]'
    prompt = f"""
请从以下文本中抽取书画人物相关的知识三元组，只输出纯JSON数组，不要任何解释、说明、文字或标点。
格式示例：
{example}

文本：
{text}
"""
    try:
        response = Generation.call(
            model="qwen-turbo",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.1,
            top_p=0.9
        )
        res = response.output.text.strip()

        # 自动清理所有非JSON内容
        res = re.sub(r'^```json|```$', '', res, flags=re.IGNORECASE).strip()
        start = res.find('[')
        end = res.rfind(']')
        if start == -1 or end == -1:
            return []
        res = res[start:end+1]
        return json.loads(res)

    except Exception as e:
        print(f"→ 本段解析失败，已跳过：{str(e)[:50]}")
        return []

def remove_duplicate_triples(triples):
    seen = set()
    final = []
    for t in triples:
        key = (t.get("subject"), t.get("predicate"), t.get("object"))
        if key not in seen:
            seen.add(key)
            final.append(t)
    return final

# ==================== 主程序 ====================
if __name__ == "__main__":
    md_file_path = r"C:\Users\25491\OneDrive\桌面\dachuang\book.md"
    json_file_path = "triples.json"

    print("📖 正在读取书籍内容...")
    content = read_md_file(md_file_path)

    print("✂️ 正在切分文本...")
    chunks = split_text_to_chunks(content)
    print(f"✅ 文本已切分：共 {len(chunks)} 段")

    all_triples = []
    print("\n🚀 开始抽取三元组...")

    for i, chunk in enumerate(chunks):
        print(f"正在处理第 {i+1}/{len(chunks)} 段")
        triples = get_triples_from_qwen(chunk)
        if triples:
            all_triples.extend(triples)
        time.sleep(WAIT_TIME)

    # 去重
    final_triples = remove_duplicate_triples(all_triples)

    # 保存
    with open(json_file_path, "w", encoding="utf-8") as f:
        json.dump(final_triples, f, ensure_ascii=False, indent=2)

    print("\n" + "="*50)
    print("🎉 全部处理完成！")
    print(f"📊 最终有效三元组：{len(final_triples)} 条")
    print(f"📁 文件已保存到：{json_file_path}")
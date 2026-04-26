import dashscope
import json
import time
from collections import Counter

# ==================== 配置 ====================
dashscope.api_key = "sk-1c1e348420124733ad316c60182ccc09"


input_file = r"D:\奥义 学习\计算机\其他项目\大创\数字人文\OCR识别\玉台书画史\玉台书画史.md"

# 输出文件
output_file = "output.json"

# 每批处理的字符数
CHUNK_SIZE = 8000

# ==================== 读取文件 ====================
def read_file(filepath):
    with open(filepath, 'r', encoding='utf-8') as f:
        return f.read()

# ==================== 分块函数 ====================
def split_text(text, chunk_size=8000):
    """按段落分块"""
    paragraphs = text.split('\n\n')
    chunks = []
    current = ""
    
    for para in paragraphs:
        if len(current) + len(para) > chunk_size:
            if current:
                chunks.append(current)
            current = para
        else:
            current += "\n\n" + para if current else para
    
    if current:
        chunks.append(current)
    
    return chunks

# ==================== 安全转换函数 ====================
def safe_to_list(value):
    """安全地将任何值转换为列表"""
    if value is None:
        return []
    if isinstance(value, list):
        # 过滤掉空字符串和None
        return [v for v in value if v and isinstance(v, str)]
    if isinstance(value, str):
        if value == "":
            return []
        # 如果包含逗号，按逗号分割
        if "," in value:
            return [v.strip() for v in value.split(",") if v.strip()]
        return [value]
    return []

def safe_to_str(value):
    """安全地将任何值转换为字符串"""
    if value is None:
        return ""
    if isinstance(value, str):
        return value
    if isinstance(value, list):
        return ", ".join(safe_to_list(value))
    return str(value)

def safe_merge_list(list1, list2):
    """安全合并两个列表"""
    l1 = safe_to_list(list1)
    l2 = safe_to_list(list2)
    # 合并并去重
    combined = list(set(l1 + l2))
    return combined

# ==================== 标准化人物数据 ====================
def normalize_person(person):
    """将人物数据标准化为统一格式"""
    normalized = {
        "name": person.get("name", ""),
        "names": safe_to_list(person.get("names", [])),
        "era": safe_to_str(person.get("era", "")),
        "titles": safe_to_list(person.get("titles", [])),
        "specialties": safe_to_list(person.get("specialties", [])),
        "evaluation": safe_to_str(person.get("evaluation", "")),
        "friends": safe_to_list(person.get("friends", [])),
        "teachers": safe_to_list(person.get("teachers", [])),
        "students": safe_to_list(person.get("students", []))
    }
    return normalized

# ==================== 抽取函数 ====================
#调用API AI辅助生成阿里云DashScope + qwen-turbo模型3.21
def extract_persons_from_chunk(text_chunk, chunk_id):
    """从单个文本块中抽取人物信息"""
    
    prompt = f"""你是中国古代书画史专家，精通文言文和人物关系。

从以下古文文本中抽取女性书画人物信息，特别关注人物之间的交游和师承关系。

文本：
{text_chunk}

请以JSONzhu格式返回，严格按照以下结构：
{{
    "persons": [
        {{
            "name": "人物姓名",
            "names": "字、号、别号",
            "era": "年代",
            "titles": "官职封号",
            "specialties": "擅长书画类型",
            "evaluation": "评价语句",
            "friends": ["交游人物"],
            "teachers": ["师承人物"],
            "students": ["学生人物"]
        }}
    ]
}}

重要提示：
1. friends、teachers、students 必须是数组格式
2. 如果没有关系，返回空数组 []
3. 只返回JSON，不要其他文字"""

    try:
        response = dashscope.Generation.call(
            model='qwen-turbo',
            prompt=prompt,
            temperature=0,
            result_format='message'
        )
        
        if response.status_code == 200:
            content = response.output.choices[0].message.content
            
            # 提取 JSON
            json_str = content.strip()
            if "```json" in json_str:
                json_str = json_str.split("```json")[1].split("```")[0]
            elif "```" in json_str:
                json_str = json_str.split("```")[1].split("```")[0]
            
            result = json.loads(json_str)
            persons = result.get("persons", [])
            
            # 标准化每个人物
            normalized_persons = [normalize_person(p) for p in persons]
            
            print(f"  块{chunk_id} 抽取到 {len(normalized_persons)} 人")
            
            # 显示第一个人的信息
            if normalized_persons:
                p = normalized_persons[0]
                print(f"    示例: {p.get('name')}")
                if p.get("friends"):
                    print(f"      交游: {', '.join(p['friends'][:3])}")
                if p.get("teachers"):
                    print(f"      师承: {', '.join(p['teachers'][:3])}")
                if p.get("students"):
                    print(f"      弟子: {', '.join(p['students'][:3])}")
            
            return normalized_persons
        else:
            print(f"  块{chunk_id} API错误: {response.message}")
            return []
            
    except json.JSONDecodeError as e:
        print(f"  块{chunk_id} JSON解析失败: {e}")
        return []
    except Exception as e:
        print(f"  块{chunk_id} 错误: {e}")
        return []

# ==================== 去重合并（安全版） ====================
def merge_persons(all_persons):
    """按姓名去重，安全合并所有字段"""
    seen = {}
    
    for p in all_persons:
        name = p.get("name", "")
        if not name:
            continue
        
        if name not in seen:
            # 首次出现，直接保存
            seen[name] = {
                "name": name,
                "names": safe_to_list(p.get("names", [])),
                "era": safe_to_str(p.get("era", "")),
                "titles": safe_to_list(p.get("titles", [])),
                "specialties": safe_to_list(p.get("specialties", [])),
                "evaluation": safe_to_str(p.get("evaluation", "")),
                "friends": safe_to_list(p.get("friends", [])),
                "teachers": safe_to_list(p.get("teachers", [])),
                "students": safe_to_list(p.get("students", []))
            }
        else:
            # 合并
            seen[name]["names"] = safe_merge_list(seen[name]["names"], p.get("names", []))
            seen[name]["titles"] = safe_merge_list(seen[name]["titles"], p.get("titles", []))
            seen[name]["specialties"] = safe_merge_list(seen[name]["specialties"], p.get("specialties", []))
            seen[name]["friends"] = safe_merge_list(seen[name]["friends"], p.get("friends", []))
            seen[name]["teachers"] = safe_merge_list(seen[name]["teachers"], p.get("teachers", []))
            seen[name]["students"] = safe_merge_list(seen[name]["students"], p.get("students", []))
            
            # 文本字段取更长的
            if p.get("era"):
                if len(p["era"]) > len(seen[name]["era"]):
                    seen[name]["era"] = p["era"]
            if p.get("evaluation"):
                if len(p["evaluation"]) > len(seen[name]["evaluation"]):
                    seen[name]["evaluation"] = p["evaluation"]
    
    # 转换列表字段为字符串（便于阅读）
    result = []
    for p in seen.values():
        result.append({
            "name": p["name"],
            "names": ", ".join(p["names"]) if p["names"] else "",
            "era": p["era"],
            "titles": ", ".join(p["titles"]) if p["titles"] else "",
            "specialties": ", ".join(p["specialties"]) if p["specialties"] else "",
            "evaluation": p["evaluation"],
            "friends": p["friends"],  # 保留列表格式，便于后续处理
            "teachers": p["teachers"],
            "students": p["students"]
        })
    
    return result

# ==================== 保存到文件 ====================
def save_to_json(data, filename):
    with open(filename, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

# ==================== 主程序 ====================
def main():
    print("=" * 70)
    print("玉台书画史 - 人物关系抽取系统（容错版）")
    print("字段: 姓名 | 名号 | 年代 | 官职 | 擅长 | 评价 | 交游 | 师承 | 弟子")
    print("=" * 70)
    
    # 读取文件
    print(f"\n正在读取文件...")
    text = read_file(input_file)
    print(f"文本长度: {len(text):,} 字符")
    
    # 分块
    chunks = split_text(text, CHUNK_SIZE)
    print(f"分为 {len(chunks)} 块")
    
    # 抽取所有人物
    all_persons = []
    for i, chunk in enumerate(chunks):
        print(f"\n处理第 {i+1}/{len(chunks)} 块...")
        try:
            persons = extract_persons_from_chunk(chunk, i+1)
            if persons:
                all_persons.extend(persons)
                print(f"  累计: {len(all_persons)} 条记录")
        except Exception as e:
            print(f"  块{i+1} 处理异常: {e}")
            continue
        
        # 避免请求过快
        if i < len(chunks) - 1:
            time.sleep(1)
    
    # 去重
    print(f"\n{'='*70}")
    print(f"原始抽取: {len(all_persons)} 条记录")
    merged = merge_persons(all_persons)
    print(f"去重后: {len(merged)} 个人物")
    
    # 保存 JSON
    save_to_json(merged, output_file)
    print(f"\n✓ JSON 保存到: {output_file}")
    
    # 统计有关系的人物
    print("\n" + "=" * 70)
    print("关系统计:")
    print("-" * 70)
    
    with_friends = [p for p in merged if p.get("friends")]
    with_teachers = [p for p in merged if p.get("teachers")]
    with_students = [p for p in merged if p.get("students")]
    
    print(f"  有交游关系: {len(with_friends)} 人")
    print(f"  有师承关系: {len(with_teachers)} 人")
    print(f"  有弟子关系: {len(with_students)} 人")
    
    # 打印详细人物列表
    print("\n" + "=" * 70)
    print("人物详细列表（前15个）:")
    print("-" * 70)
    for i, p in enumerate(merged[:15]):
        print(f"\n{i+1}. {p.get('name', '未知')}")
        if p.get("names"):
            print(f"   名号: {p['names']}")
        if p.get("era"):
            print(f"   年代: {p['era']}")
        if p.get("titles"):
            print(f"   官职: {p['titles']}")
        if p.get("specialties"):
            print(f"   擅长: {p['specialties']}")
        if p.get("evaluation"):
            eval_short = p['evaluation'][:80] + "..." if len(p['evaluation']) > 80 else p['evaluation']
            print(f"   评价: {eval_short}")
        if p.get("friends"):
            print(f"   交游: {', '.join(p['friends'][:5])}")
        if p.get("teachers"):
            print(f"   师承: {', '.join(p['teachers'][:5])}")
        if p.get("students"):
            print(f"   弟子: {', '.join(p['students'][:5])}")
    
    print("\n" + "=" * 70)
    print("完成！")

# ==================== 入口 ====================
if __name__ == "__main__":
    main()
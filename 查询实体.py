import json
from pydantic import BaseModel
from typing import Optional
from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import PydanticOutputParser

# ==================== 1. Pydantic模板 ====================
class HeroQuery(BaseModel):
    subject: Optional[str] = None   # 人物名
    predicate: Optional[str] = None # 关系/属性
    object: Optional[str] = None    # 属性值

# ==================== 2. 加载你的JSON数据 ====================
# 👇 你的文件路径
file_path = r"D:\奥义 学习\计算机\知识图谱\爬取\huangjiguang_triples.json"

with open(file_path, "r", encoding="utf-8") as f:
    triples = json.load(f)

print(f"成功加载 {len(triples)} 条三元组")
# 输出示例：成功加载 14 条三元组

# ==================== 3. Langchain提取链 ====================
parser = PydanticOutputParser(pydantic_object=HeroQuery)

prompt = ChatPromptTemplate.from_messages([
    ("system", "从用户问题中提取实体。只提取出现的信息，没出现就设为null。\n{format_instructions}"),
    ("human", "{query}")
])

llm = ChatOpenAI(model="gpt-3.5-turbo", temperature=0)
chain = prompt | llm | parser

# ==================== 4. 查询函数 ====================
def query_hero(question: str):
    # 提取实体
    extracted = chain.invoke({
        "query": question,
        "format_instructions": parser.get_format_instructions()
    })
    
    print(f"问题: {question}")
    print(f"提取: {extracted.model_dump()}")
    
    # 匹配三元组
    results = []
    for t in triples:
        if extracted.subject and t["subject"] != extracted.subject:
            continue
        if extracted.predicate and t["predicate"] != extracted.predicate:
            continue
        if extracted.object and t["object"] != extracted.object:
            continue
        results.append(t)
    
    return results

# ==================== 5. 测试 ====================
if __name__ == "__main__":
    # 测试几个问题
    test_questions = [
        "黄继光的出生地是哪里？",
        "黄继光有哪些主要成就？",
        "黄继光什么时候牺牲的？"
    ]
    
    for q in test_questions:
        result = query_hero(q)
        print(f"结果: {result}\n")
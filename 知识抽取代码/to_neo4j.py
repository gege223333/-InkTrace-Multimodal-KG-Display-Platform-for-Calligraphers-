import json

# 读取三元组
with open("triples.json", "r", encoding="utf-8") as f:
    triples = json.load(f)

# ==================== 生成 节点文件 ====================
nodes = set()
for t in triples:
    nodes.add(t["subject"])
    nodes.add(t["object"])

with open("neo4j_nodes.csv", "w", encoding="utf-8-sig") as f:
    f.write("id,name\n")  # Neo4j 标准表头
    for i, name in enumerate(nodes):
        f.write(f"{i},{name}\n")

# ==================== 生成 关系文件 ====================
with open("neo4j_rels.csv", "w", encoding="utf-8-sig") as f:
    f.write("start,end,type\n")  # Neo4j 标准表头
    for t in triples:
        s = t["subject"]
        p = t["predicate"]
        o = t["object"]
        f.write(f"{s},{o},{p}\n")

print("✅ 生成成功！")
print("📁 neo4j_nodes.csv   节点")
print("📁 neo4j_rels.csv    关系")
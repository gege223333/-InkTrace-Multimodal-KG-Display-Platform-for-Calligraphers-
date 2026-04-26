#AI辅助生成GLM-5 2026.3.25
import pandas as pd

print("=" * 60)
print("分析同学2的数据")
print("=" * 60)

# ========== 1. 读取文件 ==========
print("\n1. 读取文件...")
df_nodes = pd.read_csv('neo4j_nodes.csv')
df_rels = pd.read_csv('neo4j_rels.csv')

print(f"节点文件: {len(df_nodes)} 行")
print(f"关系文件: {len(df_rels)} 行")

# ========== 2. 查看节点文件内容 ==========
print("\n2. 节点文件内容（前10行）:")
print(df_nodes.head(10))
print(f"\n节点文件列名: {df_nodes.columns.tolist()}")

# ========== 3. 查看关系文件内容 ==========
print("\n3. 关系文件内容（前10行）:")
print(df_rels.head(10))
print(f"\n关系文件列名: {df_rels.columns.tolist()}")

# ========== 4. 统计关系类型 ==========
print("\n4. 关系类型统计:")
type_counts = df_rels['type'].value_counts()
print(type_counts)

# ========== 5. 查看一些示例 ==========
print("\n5. 关系示例:")
print("\n专长示例:")
print(df_rels[df_rels['type'] == '专长'].head(3))
print("\n评价示例:")
print(df_rels[df_rels['type'] == '评价'].head(3))
print("\n朋友示例:")
print(df_rels[df_rels['type'] == '朋友'].head(3))

# ========== 6. 查看人物节点数量 ==========
print(f"\n6. 人物节点数量: {len(df_nodes)}")

# ========== 7. 查看关系中的start和end ==========
all_starts = set(df_rels['start'].tolist())
all_ends = set(df_rels['end'].tolist())
print(f"\n7. 关系中的start（人物）: {len(all_starts)} 个")
print(f"   关系中的end（属性值）: {len(all_ends)} 个")

# ========== 8. 检查重叠 ==========
nodes_set = set(df_nodes['name'].tolist())
starts_in_nodes = len(all_starts & nodes_set)
ends_in_nodes = len(all_ends & nodes_set)
print(f"\n8. start在节点中: {starts_in_nodes}/{len(all_starts)}")
print(f"   end在节点中: {ends_in_nodes}/{len(all_ends)}")

# ========== 9. 查看哪些end不在节点中 ==========
ends_not_in_nodes = all_ends - nodes_set
print(f"\n9. end不在节点中的示例（前20个）:")
for i, name in enumerate(list(ends_not_in_nodes)[:20]):
    print(f"   {name}")
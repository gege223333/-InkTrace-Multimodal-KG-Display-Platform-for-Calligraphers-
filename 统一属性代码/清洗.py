import pandas as pd

# 读取手动处理的关系
manual_relations = pd.read_csv(
    r'd:\北语文件\大创\书法\知识抽取\relations_still_unmatched.csv',
    encoding='utf-8'
)

# 读取最终关系表
final_relations = pd.read_csv(
    r'd:\北语文件\大创\书法\知识抽取\relations_final.csv',
    encoding='utf-8'
)

# 添加手动处理的关系
final_relations = pd.concat([final_relations, manual_relations], ignore_index=True)

# 去重
final_relations = final_relations.drop_duplicates()

# 保存
final_relations.to_csv(
    r'd:\北语文件\大创\书法\知识抽取\relations_final.csv',
    index=False,
    encoding='utf-8'
)

print(f"最终关系总数: {len(final_relations)}")
print("合并完成！")
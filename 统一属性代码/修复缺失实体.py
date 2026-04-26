import pandas as pd

print("正在修复缺失的实体...")

# 读取实体表
entities_df = pd.read_csv(
    r'd:\北语文件\大创\书法\知识抽取\entities_final.csv',
    encoding='utf-8'
)

# 添加缺失的实体"真宗时"
new_entity = pd.DataFrame([{
    'id': len(entities_df),
    'name': '真宗时',
    'type': '时间'
}])

entities_df = pd.concat([entities_df, new_entity], ignore_index=True)

# 保存
entities_df.to_csv(
    r'd:\北语文件\大创\书法\知识抽取\entities_final.csv',
    index=False,
    encoding='utf-8'
)

print(f"✓ 已添加实体: 真宗时 (类型: 时间)")
print(f"✓ 实体总数: {len(entities_df)}")
print("修复完成！")

import pandas as pd

print("正在处理文件...")

# 读取原始文件
entities_df = pd.read_csv(
    r'd:\北语文件\大创\书法\知识抽取\entities_final.csv',
    encoding='utf-8'
)

print(f"原始文件: {len(entities_df)} 行")
print(f"原始列: {list(entities_df.columns)}")

# 删除 id 列
entities_df = entities_df[['name', 'type']]

print(f"删除 id 列后的列: {list(entities_df.columns)}")

# 保存为新文件
output_file = r'd:\北语文件\大创\书法\知识抽取\entities_final_no_id.csv'
entities_df.to_csv(output_file, index=False, encoding='utf-8')

print(f"\n✓ 已保存到: {output_file}")
print(f"✓ 总行数: {len(entities_df)}")
print("\n前5行预览:")
print(entities_df.head())

import pandas as pd
from collections import defaultdict

print("="*60)
print("书法知识图谱数据质量验证")
print("="*60)

print("\n【步骤1】读取数据文件...")
entities_df = pd.read_csv(
    r'd:\北语文件\大创\书法\知识抽取\entities_final.csv',
    encoding='utf-8'
)
relations_df = pd.read_csv(
    r'd:\北语文件\大创\书法\知识抽取\relations_final.csv',
    encoding='utf-8'
)

print(f"  实体总数: {len(entities_df)}")
print(f"  关系总数: {len(relations_df)}")

print("\n" + "="*60)
print("【验证1】关系类型完整性检查")
print("="*60)

valid_relation_types = ['擅长', '作品', '师承', '交游', '评价', '名号', '家人', '官职', '朝代', '籍贯']

relation_types = relations_df['type'].value_counts()
print(f"\n关系类型统计:")
for rel_type, count in relation_types.items():
    status = "✓" if rel_type in valid_relation_types else "✗"
    print(f"  {status} {rel_type}: {count} 条")

invalid_types = [t for t in relation_types.index if t not in valid_relation_types]
if invalid_types:
    print(f"\n⚠️ 发现非标准关系类型: {invalid_types}")
else:
    print(f"\n✓ 所有关系类型都在预定义的10类之内")

print("\n" + "="*60)
print("【验证2】关系-实体对应检查")
print("="*60)

entity_names = set(entities_df['name'].unique())
relation_entities = set()
relation_entities.update(relations_df['start'].unique())
relation_entities.update(relations_df['end'].unique())

missing_entities = relation_entities - entity_names

if missing_entities:
    print(f"\n⚠️ 发现 {len(missing_entities)} 个关系中的实体不在实体表中:")
    for entity in sorted(list(missing_entities))[:20]:
        print(f"  - {entity}")
    if len(missing_entities) > 20:
        print(f"  ... 还有 {len(missing_entities) - 20} 个")
else:
    print(f"\n✓ 所有关系中的实体都在实体表中")

print("\n" + "="*60)
print("【验证3】实体分类直观性评估")
print("="*60)

entity_type_samples = {}
for entity_type in entities_df['type'].unique():
    samples = entities_df[entities_df['type'] == entity_type]['name'].sample(
        min(10, len(entities_df[entities_df['type'] == entity_type]))
    ).tolist()
    entity_type_samples[entity_type] = samples

print(f"\n实体类型分布及抽样:")
for entity_type, count in entities_df['type'].value_counts().items():
    print(f"\n  {entity_type} ({count} 个):")
    samples = entity_type_samples.get(entity_type, [])
    for i, sample in enumerate(samples[:5], 1):
        print(f"    {i}. {sample}")

print("\n" + "="*60)
print("【验证结果总结】")
print("="*60)

issues = []

if invalid_types:
    issues.append(f"存在非标准关系类型: {invalid_types}")

if missing_entities:
    issues.append(f"存在 {len(missing_entities)} 个关系实体不在实体表中")

other_entities = entities_df[entities_df['type'] == '其他']
if len(other_entities) > 100:
    issues.append(f"「其他」类实体过多: {len(other_entities)} 个")

if issues:
    print(f"\n⚠️ 发现以下问题:")
    for i, issue in enumerate(issues, 1):
        print(f"  {i}. {issue}")
else:
    print(f"\n✓ 所有验证通过，数据可入库")

print("\n" + "="*60)
print("【详细统计】")
print("="*60)

print(f"\n实体类型分布:")
for entity_type, count in entities_df['type'].value_counts().items():
    percentage = (count / len(entities_df)) * 100
    print(f"  {entity_type}: {count} 个 ({percentage:.1f}%)")

print(f"\n关系类型分布:")
for rel_type, count in relation_types.items():
    percentage = (count / len(relations_df)) * 100
    print(f"  {rel_type}: {count} 条 ({percentage:.1f}%)")

print("\n" + "="*60)

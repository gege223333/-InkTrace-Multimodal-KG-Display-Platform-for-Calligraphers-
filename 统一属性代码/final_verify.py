import csv
from collections import defaultdict

base = r'd:\北语文件\大创\书法\数据清洗'

print('=' * 60)
print('最终全面验证报告')
print('=' * 60)

# 1. 验证entities_fixed.csv
print('\n【1. entities_fixed.csv 验证】')
with open(base + r'\entities_fixed.csv', 'r', encoding='utf-8-sig') as f:
    reader = csv.DictReader(f)
    types = defaultdict(int)
    names = set()
    dupes = []
    invalid_types = []
    for row in reader:
        types[row['type']] += 1
        if row['name'] in names:
            dupes.append(row['name'])
        names.add(row['name'])
        if row['type'] not in {'人', '作品', '书法类别', '领域', '评价', '名号', '官职', '时间', '地点', '其他'}:
            invalid_types.append((row['name'], row['type']))

print(f'  总实体数: {len(names)}')
print(f'  重复实体数: {len(dupes)}')
print(f'  无效类型数: {len(invalid_types)}')
if invalid_types:
    for n, t in invalid_types[:5]:
        print(f'    无效类型: {n} -> {t}')
print(f'  类型分布:')
for k, v in sorted(types.items(), key=lambda x: -x[1]):
    print(f'    {k}: {v}')

# 2. 验证relations_fixed.csv
print('\n【2. relations_fixed.csv 验证】')
valid_rel_types = {'朝代', '籍贯', '擅长', '作品', '师承', '取法', '交游', '评价', '名号', '家人', '官职'}
with open(base + r'\relations_fixed.csv', 'r', encoding='utf-8-sig') as f:
    reader = csv.DictReader(f)
    rel_types = defaultdict(int)
    count = 0
    invalid_rels = []
    for row in reader:
        rel_types[row['Type']] += 1
        count += 1
        if row['Type'] not in valid_rel_types:
            invalid_rels.append((row['Start'], row['Type'], row['End']))

print(f'  总关系数: {count}')
print(f'  无效关系类型数: {len(invalid_rels)}')
if invalid_rels:
    for s, t, e in invalid_rels[:5]:
        print(f'    无效: {s} -{t}-> {e}')
print(f'  关系类型分布:')
for k, v in sorted(rel_types.items(), key=lambda x: -x[1]):
    print(f'    {k}: {v}')

# 3. 验证entity_changelog.csv
print('\n【3. entity_changelog.csv 验证】')
with open(base + r'\entity_changelog.csv', 'r', encoding='utf-8-sig') as f:
    reader = csv.DictReader(f)
    decisions = defaultdict(int)
    total = 0
    for row in reader:
        decisions[row['处理决策']] += 1
        total += 1
print(f'  总条目数: {total}')
for k, v in sorted(decisions.items(), key=lambda x: -x[1]):
    print(f'    {k}: {v}')

# 4. 验证relation_changelog.csv
print('\n【4. relation_changelog.csv 验证】')
with open(base + r'\relation_changelog.csv', 'r', encoding='utf-8-sig') as f:
    reader = csv.DictReader(f)
    decisions = defaultdict(int)
    total = 0
    for row in reader:
        decisions[row['处理决策']] += 1
        total += 1
print(f'  总条目数: {total}')
for k, v in sorted(decisions.items(), key=lambda x: -x[1]):
    print(f'    {k}: {v}')

# 5. 交叉验证: relations_fixed中的实体是否都在entities_fixed中
print('\n【5. 交叉验证: 关系实体是否在实体表中】')
entity_names = set()
with open(base + r'\entities_fixed.csv', 'r', encoding='utf-8-sig') as f:
    reader = csv.DictReader(f)
    for row in reader:
        entity_names.add(row['name'])

missing_entities = set()
with open(base + r'\relations_fixed.csv', 'r', encoding='utf-8-sig') as f:
    reader = csv.DictReader(f)
    for row in reader:
        if row['Start'] not in entity_names:
            missing_entities.add(row['Start'])
        if row['End'] not in entity_names:
            missing_entities.add(row['End'])

print(f'  关系表中不在实体表中的实体数: {len(missing_entities)}')
if missing_entities:
    for me in list(missing_entities)[:10]:
        print(f'    缺失: {me}')

# 6. 检查关键修正案例
print('\n【6. 关键修正案例检查】')

# 蔡文姬师承钟繇 - 应被修正
with open(base + r'\relation_changelog.csv', 'r', encoding='utf-8-sig') as f:
    reader = csv.DictReader(f)
    for row in reader:
        if '蔡文姬' in row['原始Start'] and '钟繇' in row['原始End']:
            print(f'  蔡文姬-师承-钟繇: 决策={row["处理决策"]}, 依据={row["决策依据"][:80]}')

# 卫铄交游王羲之 - 应被修正
with open(base + r'\relation_changelog.csv', 'r', encoding='utf-8-sig') as f:
    reader = csv.DictReader(f)
    for row in reader:
        if '卫铄' in row['原始Start'] and '王羲之' in row['原始End']:
            print(f'  卫铄-交游-王羲之: 决策={row["处理决策"]}, 依据={row["决策依据"][:80]}')

# 谢安朝代西晋 - 应被修正
with open(base + r'\relation_changelog.csv', 'r', encoding='utf-8-sig') as f:
    reader = csv.DictReader(f)
    for row in reader:
        if '谢安' in row['原始Start'] and '西晋' in row['原始End']:
            print(f'  谢安-朝代-西晋: 决策={row["处理决策"]}, 修正后End={row["修正后End"]}')

print('\n' + '=' * 60)
print('验证完成')
print('=' * 60)

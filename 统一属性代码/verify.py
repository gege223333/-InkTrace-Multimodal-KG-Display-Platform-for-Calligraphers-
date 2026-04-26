import csv
base = r'd:\北语文件\大创\书法\数据清洗'

print('=== 检查关键实体修正 ===')
with open(base + r'\entities_fixed.csv', 'r', encoding='utf-8-sig') as f:
    reader = csv.DictReader(f)
    for row in reader:
        n = row['name']
        if n in ['爱新觉罗', '赵孟頫', '王珣', '谢安', '卫铄', '杜度', '楚珍']:
            print(f'  {n}: {row["type"]}')

print('\n=== 检查关键关系修正 ===')
with open(base + r'\relations_fixed.csv', 'r', encoding='utf-8-sig') as f:
    reader = csv.DictReader(f)
    for row in reader:
        s, t, e = row['Start'], row['Type'], row['End']
        if '爱新觉罗' in s or '赵孟頫' in s:
            print(f'  {s} -{t}-> {e}')
        if t == '取法' and '白蕉' in s:
            print(f'  {s} -{t}-> {e}')

print('\n=== 检查学习是否已全部转为取法 ===')
learn_count = 0
with open(base + r'\relations_fixed.csv', 'r', encoding='utf-8-sig') as f:
    reader = csv.DictReader(f)
    for row in reader:
        if row['Type'] == '学习':
            learn_count += 1
print(f'  剩余学习关系数: {learn_count}')

print('\n=== 检查非标准关系类型 ===')
valid_types = {'朝代', '籍贯', '擅长', '作品', '师承', '取法', '交游', '评价', '名号', '家人', '官职'}
with open(base + r'\relations_fixed.csv', 'r', encoding='utf-8-sig') as f:
    reader = csv.DictReader(f)
    for row in reader:
        if row['Type'] not in valid_types:
            print(f'  非标准: {row["Start"]} -{row["Type"]}-> {row["End"]}')

print('\n=== 检查错字修正 ===')
with open(base + r'\entity_changelog.csv', 'r', encoding='utf-8-sig') as f:
    reader = csv.DictReader(f)
    for row in reader:
        orig = row['原始name']
        fixed = row['修正后name']
        if orig != fixed:
            print(f'  {orig} -> {fixed} ({row["处理决策"]})')

print('\n=== 检查交游->取法修正 ===')
with open(base + r'\relation_changelog.csv', 'r', encoding='utf-8-sig') as f:
    reader = csv.DictReader(f)
    count = 0
    for row in reader:
        if row['处理决策'] == '建议删除' and row['原始Type'] == '交游':
            count += 1
            if count <= 5:
                print(f'  建议删除交游: {row["原始Start"]} -{row["原始Type"]}-> {row["原始End"]}')
    print(f'  总计建议删除交游关系: {count}')

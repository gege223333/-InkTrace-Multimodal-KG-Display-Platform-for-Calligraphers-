import csv

# 读取 CSV 文件
with open('rels.csv', 'r', encoding='utf-8') as f:
    reader = csv.reader(f)
    header = next(reader)
    rows = list(reader)

# 用于跟踪已处理的 (frozenset({start, end}), type)
seen = set()

# 去重后的行
# AI辅助生成
deduped_rows = []

for row in rows:
    if len(row) >= 3:
        start, typ, end = row[0], row[1], row[2]
        key = (frozenset({start, end}), typ)
        if key not in seen:
            seen.add(key)
            deduped_rows.append([start, typ, end])
    else:
        print(f"Skipping row with {len(row)} fields: {row}")

# 写回 CSV 文件
with open('rels_deduped.csv', 'w', encoding='utf-8', newline='') as f:
    writer = csv.writer(f)
    writer.writerow(header)
    writer.writerows(deduped_rows)

print("去重完成，新文件：rels_deduped.csv")
import pandas as pd
import re
#AI辅助生成GLM-5 2026.4.3
# 读取原始数据
df_relation = pd.read_csv('统一后的关系.csv')
df_entity = pd.read_csv('统一后的实体.csv')

# 创建修改记录（用于标记）
modifications = []

# ===================== 任务1：从评价中提取擅长信息 =====================
# 找出所有评价中包含“擅长”或“善”“工”等关键词的行
new_rows = []
for idx, row in df_relation.iterrows():
    new_rows.append(row)
    if row['type'] == '评价' and isinstance(row['end'], str):
        text = row['end']
        # 提取“善XX”“工XX”“擅长XX”等模式
        skills = re.findall(r'[善工擅长]于?([^，。；、]+?)(?=[，。；、]|$)', text)
        for skill in skills:
            skill = skill.strip()
            if skill and len(skill) < 20:  # 过滤过长的匹配
                new_row = row.copy()
                new_row['type'] = '领域'
                new_row['end'] = skill
                new_rows.append(new_row)
                modifications.append({
                    '原始实体': row['start'],
                    '原始类型': '评价',
                    '原始内容': row['end'],
                    '修改动作': '从评价中提取领域',
                    '提取出的领域': skill
                })

# 替换原数据
df_relation = pd.DataFrame(new_rows)

# ===================== 任务2：拆分多值领域（以逗号分隔） =====================
split_rows = []
for idx, row in df_relation.iterrows():
    if row['type'] == '领域' and isinstance(row['end'], str) and ',' in row['end']:
        # 拆分多个领域
        skills = [s.strip() for s in row['end'].split(',')]
        for skill in skills:
            new_row = row.copy()
            new_row['end'] = skill
            split_rows.append(new_row)
            modifications.append({
                '原始实体': row['start'],
                '原始类型': '领域',
                '原始内容': row['end'],
                '修改动作': '拆分多值领域',
                '拆分后': skill
            })
    else:
        split_rows.append(row)

df_final = pd.DataFrame(split_rows)

# ===================== 生成标记文件 =====================
# 1. 输出最终数据
df_final.to_csv('处理后的关系.csv', index=False, encoding='utf-8-sig')

# 2. 输出修改记录标记文件
df_mod = pd.DataFrame(modifications)
df_mod.to_csv('修改标记记录.csv', index=False, encoding='utf-8-sig')

print("处理完成！")
print(f"生成文件：处理后的关系.csv")
print(f"生成文件：修改标记记录.csv")
print(f"共修改/拆分 {len(modifications)} 处")
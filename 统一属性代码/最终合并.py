import pandas as pd
import re
from collections import defaultdict

STATS = {
    '原始标准关系数': 0,
    '原始无法归类关系数': 0,
    '成功映射关系数': 0,
    '仍无法归类关系数': 0,
    '最终关系数': 0,
    '最终实体数': 0,
    '关系类型分布': defaultdict(int),
    '实体类型分布': defaultdict(int),
    '孤立实体数': 0
}

def clean_name(name):
    if pd.isna(name) or name == 'nan':
        return None
    name = re.sub(r'[\[\]（）()\s]', '', str(name))
    name = name.strip()
    return name if name else None

def infer_entity_type_from_relation(entity_name, all_relations):
    as_subject = [r for r in all_relations if r['start'] == entity_name]
    as_object = [r for r in all_relations if r['end'] == entity_name]
    
    for rel in as_subject:
        rel_type = rel['type']
        if rel_type == '擅长':
            return '人'
        elif rel_type == '作品':
            return '人'
        elif rel_type == '师承':
            return '人'
        elif rel_type == '交游':
            return '人'
        elif rel_type == '评价':
            return '人'
        elif rel_type == '名号':
            return '人'
        elif rel_type == '官职':
            return '人'
        elif rel_type == '朝代':
            return '人'
        elif rel_type == '籍贯':
            return '人'
        elif rel_type == '家人':
            return '人'
    
    for rel in as_object:
        rel_type = rel['type']
        if rel_type == '擅长':
            if '书' in entity_name or '篆' in entity_name or '隶' in entity_name:
                return '书法类别'
            return '领域'
        elif rel_type == '作品':
            return '作品'
        elif rel_type == '师承':
            return '人'
        elif rel_type == '交游':
            return '人'
        elif rel_type == '评价':
            return '评价'
        elif rel_type == '名号':
            return '名号'
        elif rel_type == '官职':
            return '官职'
        elif rel_type == '朝代':
            return '时间'
        elif rel_type == '籍贯':
            return '地点'
        elif rel_type == '家人':
            return '人'
    
    return None

def infer_entity_type_from_name(name):
    famous_persons = [
        '张旭', '怀素', '董源', '项容', '文同', '文璧', '周臣', '吴道子',
        '颜真卿', '柳公权', '欧阳询', '赵孟頫', '米芾', '苏轼', '黄庭坚',
        '蔡襄', '王铎', '傅山', '董其昌', '文徵明', '祝允明', '唐寅',
        '徐渭', '倪瓒', '黄公望', '王蒙', '吴镇', '沈周', '仇英',
        '李斯', '帝喾', '帝尧', '夏禹', '务光', '史籀', '胡毋敬',
        '程邈', '王次仲', '萧何', '杨雄', '司马长卿', '史游',
        '杜度', '崔瑗', '谷永', '傅介子', '刘向', '章帝', '刘炽',
        '安帝', '刘祜', '崔寔', '蔡邕', '曹操', '曹丕', '曹植',
        '韦诞', '邯郸淳', '卫凯', '钟会', '皇象', '胡昭', '卫瓘',
        '卫恒', '王导', '王廙', '王洽', '王珣', '王献之', '王羲之'
    ]
    if name in famous_persons:
        return '人'
    
    if re.match(r'^字.{1,4}$', name) or re.match(r'^号.{1,4}$', name):
        return '名号'
    if re.match(r'^.{1,4}氏$', name):
        return '名号'
    
    official_keywords = ['官', '将军', '监', '令', '丞', '太守', '刺史', '丞相', 
                        '御史', '侍郎', '大夫', '尚书', '司马', '侯', '史官']
    if any(kw in name for kw in official_keywords):
        return '官职'
    
    location_patterns = [r'.*人$', r'.*县$', r'.*市$', r'.*省$', r'.*郡$', r'.*州$']
    for pattern in location_patterns:
        if re.match(pattern, name):
            return '地点'
    
    script_keywords = ['书', '篆', '隶', '楷', '行', '草']
    if any(kw in name for kw in script_keywords) and len(name) <= 4:
        return '书法类别'
    
    if re.match(r'^《.*》$', name):
        return '作品'
    
    time_patterns = [r'^.*朝$', r'^.*代$', r'^上古$', r'^秦$', r'^汉$', r'^晋$', 
                     r'^唐$', r'^宋$', r'^元$', r'^明$', r'^清$']
    for pattern in time_patterns:
        if re.match(pattern, name):
            return '时间'
    
    return None

def try_map_unmatched_relation(start, original_predicate, end):
    if not end or end == 'nan':
        return None
    
    predicate_lower = original_predicate.lower()
    
    if any(kw in predicate_lower for kw in ['师', '宗', '学', '从']):
        return '师承'
    
    if any(kw in predicate_lower for kw in ['友', '交', '游', '同门']):
        return '交游'
    
    if any(kw in predicate_lower for kw in ['父', '母', '子', '女', '兄', '弟', '妻', '夫', '祖', '孙', '家人']):
        return '家人'
    
    if any(kw in predicate_lower for kw in ['擅长', '善', '工', '能', '精']):
        return '擅长'
    
    if any(kw in predicate_lower for kw in ['著', '作', '撰', '书']):
        return '作品'
    
    if any(kw in predicate_lower for kw in ['字', '号', '名', '谥', '封']):
        return '名号'
    
    if any(kw in predicate_lower for kw in ['官', '任', '职']):
        return '官职'
    
    if any(kw in predicate_lower for kw in ['朝', '代', '时']):
        return '朝代'
    
    if any(kw in predicate_lower for kw in ['籍', '贯', '居', '地']):
        return '籍贯'
    
    if any(kw in predicate_lower for kw in ['评', '论', '赞', '谓']):
        return '评价'
    
    if predicate_lower == '是':
        if re.match(r'^.*人$', end):
            return '籍贯'
        if re.match(r'^.*朝$', end) or re.match(r'^.*代$', end):
            return '朝代'
        if any(kw in end for kw in ['官', '职', '郎', '将']):
            return '官职'
    
    return None

def main():
    print("="*60)
    print("书法知识图谱最终合并处理")
    print("="*60)
    
    print("\n【步骤1】读取输入文件...")
    relations_standard = pd.read_csv(
        r'd:\北语文件\大创\书法\知识抽取\relations_standard.csv',
        encoding='utf-8'
    )
    relations_unmatched = pd.read_csv(
        r'd:\北语文件\大创\书法\知识抽取\relations_unmatched.csv',
        encoding='utf-8'
    )
    
    STATS['原始标准关系数'] = len(relations_standard)
    STATS['原始无法归类关系数'] = len(relations_unmatched)
    
    print(f"  标准化关系: {STATS['原始标准关系数']} 条")
    print(f"  无法归类关系: {STATS['原始无法归类关系数']} 条")
    
    print("\n【步骤2】处理无法归类关系...")
    corrected_relations = []
    still_unmatched = []
    
    for _, row in relations_unmatched.iterrows():
        start = clean_name(row['start'])
        original_predicate = str(row['original_predicate'])
        end = clean_name(row['end'])
        
        if not start or not end:
            continue
        
        mapped_type = try_map_unmatched_relation(start, original_predicate, end)
        
        if mapped_type:
            corrected_relations.append({
                'start': start,
                'type': mapped_type,
                'end': end
            })
            STATS['成功映射关系数'] += 1
        else:
            still_unmatched.append({
                'start': start,
                'original_predicate': original_predicate,
                'end': end
            })
            STATS['仍无法归类关系数'] += 1
    
    print(f"  成功映射: {STATS['成功映射关系数']} 条")
    print(f"  仍无法归类: {STATS['仍无法归类关系数']} 条")
    
    print("\n【步骤3】合并所有关系表...")
    all_relations = []
    
    for _, row in relations_standard.iterrows():
        all_relations.append({
            'start': clean_name(row['start']),
            'type': row['type'],
            'end': clean_name(row['end'])
        })
    
    all_relations.extend(corrected_relations)
    
    relations_df = pd.DataFrame(all_relations)
    relations_df = relations_df.dropna()
    relations_df = relations_df.drop_duplicates()
    relations_df = relations_df.reset_index(drop=True)
    
    STATS['最终关系数'] = len(relations_df)
    
    for rel_type in relations_df['type'].unique():
        count = len(relations_df[relations_df['type'] == rel_type])
        STATS['关系类型分布'][rel_type] = count
    
    print(f"  合并后关系总数: {STATS['最终关系数']} 条")
    print(f"  去重后保留: {STATS['最终关系数']} 条")
    
    print("\n【步骤4】提取并处理实体...")
    print("  正在从关系中提取实体...")
    all_entities = set()
    all_entities.update(relations_df['start'].unique())
    all_entities.update(relations_df['end'].unique())
    all_entities.discard(None)
    
    print(f"  提取到 {len(all_entities)} 个唯一实体")
    print("  正在推断实体类型...")
    
    entity_list = []
    relations_records = relations_df.to_dict('records')
    
    for i, entity_name in enumerate(all_entities):
        if i % 100 == 0:
            print(f"    处理进度: {i}/{len(all_entities)}")
        
        entity_type = infer_entity_type_from_relation(entity_name, relations_records)
        if not entity_type:
            entity_type = infer_entity_type_from_name(entity_name)
        if not entity_type:
            entity_type = '其他'
        
        entity_list.append({
            'name': entity_name,
            'type': entity_type
        })
        STATS['实体类型分布'][entity_type] += 1
    
    print(f"  实体类型推断完成")
    
    entities_df = pd.DataFrame(entity_list)
    entities_df = entities_df.sort_values('name').reset_index(drop=True)
    entities_df['id'] = range(len(entities_df))
    entities_df = entities_df[['id', 'name', 'type']]
    
    STATS['最终实体数'] = len(entities_df)
    
    print(f"  实体总数: {STATS['最终实体数']} 个")
    
    print("\n【步骤5】校验数据完整性...")
    entity_names = set(entities_df['name'])
    
    missing_entities = []
    for _, row in relations_df.iterrows():
        if row['start'] not in entity_names:
            missing_entities.append(row['start'])
        if row['end'] not in entity_names:
            missing_entities.append(row['end'])
    
    if missing_entities:
        print(f"  警告: 发现 {len(set(missing_entities))} 个关系中的实体不在实体表中")
    else:
        print(f"  ✓ 所有关系中的实体都在实体表中")
    
    relation_entities = set()
    relation_entities.update(relations_df['start'].unique())
    relation_entities.update(relations_df['end'].unique())
    
    isolated_entities = entity_names - relation_entities
    STATS['孤立实体数'] = len(isolated_entities)
    
    if isolated_entities:
        print(f"  警告: 发现 {STATS['孤立实体数']} 个孤立实体（未出现在任何关系中）")
    else:
        print(f"  ✓ 无孤立实体")
    
    print("\n【步骤6】输出最终文件...")
    entities_df.to_csv(
        r'd:\北语文件\大创\书法\知识抽取\entities_final.csv',
        index=False,
        encoding='utf-8'
    )
    
    relations_df.to_csv(
        r'd:\北语文件\大创\书法\知识抽取\relations_final.csv',
        index=False,
        encoding='utf-8'
    )
    
    if still_unmatched:
        still_unmatched_df = pd.DataFrame(still_unmatched)
        still_unmatched_df.to_csv(
            r'd:\北语文件\大创\书法\知识抽取\relations_still_unmatched.csv',
            index=False,
            encoding='utf-8'
        )
    
    print("\n" + "="*60)
    print("【最终统计报告】")
    print("="*60)
    
    print(f"\n【关系统计】")
    print(f"  原始标准关系: {STATS['原始标准关系数']} 条")
    print(f"  原始无法归类: {STATS['原始无法归类关系数']} 条")
    print(f"  成功映射: {STATS['成功映射关系数']} 条")
    print(f"  仍无法归类: {STATS['仍无法归类关系数']} 条")
    print(f"  最终关系总数: {STATS['最终关系数']} 条")
    
    print(f"\n【关系类型分布】")
    for rel_type, count in sorted(STATS['关系类型分布'].items(), key=lambda x: -x[1]):
        percentage = (count / STATS['最终关系数']) * 100
        print(f"  {rel_type}: {count} 条 ({percentage:.1f}%)")
    
    print(f"\n【实体统计】")
    print(f"  最终实体总数: {STATS['最终实体数']} 个")
    print(f"  孤立实体: {STATS['孤立实体数']} 个")
    
    print(f"\n【实体类型分布】")
    for entity_type, count in sorted(STATS['实体类型分布'].items(), key=lambda x: -x[1]):
        percentage = (count / STATS['最终实体数']) * 100
        print(f"  {entity_type}: {count} 个 ({percentage:.1f}%)")
    
    print("\n" + "="*60)
    print("输出文件:")
    print(f"  最终实体表: d:\\北语文件\\大创\\书法\\知识抽取\\entities_final.csv")
    print(f"  最终关系表: d:\\北语文件\\大创\\书法\\知识抽取\\relations_final.csv")
    if still_unmatched:
        print(f"  仍无法归类: d:\\北语文件\\大创\\书法\\知识抽取\\relations_still_unmatched.csv")
    print("="*60)

if __name__ == "__main__":
    main()

import csv
import re
import os
from collections import defaultdict

BASE_DIR = r'd:\北语文件\大创\书法\数据清洗'

def read_csv(filepath):
    rows = []
    with open(filepath, 'r', encoding='utf-8-sig') as f:
        reader = csv.DictReader(f)
        fieldnames = reader.fieldnames
        for row in reader:
            rows.append(row)
    return fieldnames, rows

def write_csv(filepath, fieldnames, rows):
    with open(filepath, 'w', encoding='utf-8-sig', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)

_, nodes_raw = read_csv(os.path.join(BASE_DIR, 'nodes(1).csv'))
_, rels_raw = read_csv(os.path.join(BASE_DIR, 'rels(1).csv'))
_, content_errors = read_csv(os.path.join(BASE_DIR, 'content_errors_to_review_v3.csv'))
_, type_errors = read_csv(os.path.join(BASE_DIR, 'nodes_type_errors_to_review.csv'))

print(f"原始实体数: {len(nodes_raw)}")
print(f"原始关系数: {len(rels_raw)}")
print(f"关系层疑似错误数: {len(content_errors)}")
print(f"实体类型预审错误数: {len(type_errors)}")

# ============================================================
# 步骤1: 从关系表收集实体及角色信息
# ============================================================
entity_roles = defaultdict(lambda: {'as_start': defaultdict(int), 'as_end': defaultdict(int)})

for rel in rels_raw:
    s, t, e = rel['start'].strip(), rel['type'].strip(), rel['end'].strip()
    entity_roles[s]['as_start'][t] += 1
    entity_roles[e]['as_end'][t] += 1

rels_entities = set()
for rel in rels_raw:
    rels_entities.add(rel['start'].strip())
    rels_entities.add(rel['end'].strip())

nodes_entities = {n['name'].strip() for n in nodes_raw}
only_in_rels = rels_entities - nodes_entities
print(f"仅在关系表中出现的实体数: {len(only_in_rels)}")

# ============================================================
# 步骤2: 加载预审错误清单
# ============================================================
type_error_map = {}
for te in type_errors:
    name = te['name'].strip()
    type_error_map[name] = {
        'original_type': te.get('type', '').strip(),
        'suggested_type': te.get('建议的类别', '').strip(),
        'problem': te.get('可能的问题', '').strip()
    }

content_error_set = set()
content_error_map = defaultdict(list)
for ce in content_errors:
    s = ce.get('start', '').strip()
    t = ce.get('type', '').strip()
    e = ce.get('end', '').strip()
    prob = ce.get('可能的问题', '').strip()
    key = (s, t, e)
    content_error_set.add(key)
    content_error_map[(s, t)].append({'end': e, 'problem': prob})

# ============================================================
# 步骤3: 实体名称清洗与去重
# ============================================================
name_corrections = {}

typo_fixes = {
    '爱新党罗': '爱新觉罗',
    '赵孟烦': '赵孟頫',
    '赵孟俯': '赵孟頫',
    '米黻': '米芾',
    '卫凯': '卫觊',
    '吴大激': '吴大澂',
    '王遽常': '王蘧常',
    '顾磷': '顾璘',
}

for wrong, correct in typo_fixes.items():
    name_corrections[wrong] = correct

variant_names = {}
same_person_groups = [
    {'南朝梁', '南朝·梁'},
    {'三国·吴', '三国吴'},
    {'三国·魏', '三国魏'},
    {'三国·蜀', '三国蜀'},
    {'五代·前蜀', '前蜀'},
    {'五代·南唐', '南唐'},
    {'五代·后周', '后周'},
    {'五代·后唐', '后唐'},
    {'五代·后蜀', '后蜀'},
    {'五代·吴越', '吴越'},
    {'五代·梁', '后梁'},
]

standard_time_names = {
    '南朝梁': '南朝·梁',
    '三国吴': '三国·吴',
    '三国魏': '三国·魏',
    '三国蜀': '三国·蜀',
}

for variant, standard in standard_time_names.items():
    name_corrections[variant] = standard

duplicate_person_fixes = {
    '钱钱': '钱(辛弃疾妾)',
    '田田': '田(辛弃疾妾)',
    '艳艳': '艳(宋代女画家)',
    '回回': '回回(元代)',
}

for wrong, correct in duplicate_person_fixes.items():
    name_corrections[wrong] = correct

# ============================================================
# 步骤4: 实体类型推断与修正
# ============================================================
VALID_TYPES = {'人', '作品', '书法类别', '领域', '评价', '名号', '官职', '时间', '地点', '其他'}
VALID_REL_TYPES = {'朝代', '籍贯', '擅长', '作品', '师承', '取法', '交游', '评价', '名号', '家人', '官职'}

CALLIGRAPHY_TYPES = {'篆书', '隶书', '楷书', '行书', '草书', '章草', '飞白', '篆', '隶', '楷', '行', '草',
                     '籀', '八分', '真', '正', '小篆', '大篆', '行草', '行楷', '正书', '真书', '今草',
                     '狂草', '小楷', '大字', '小字', '行书', '草隶', '科斗篆籀', '正隶飞白',
                     '行草章草颠草', '六体', '四体', '二王', '魏碑', '北碑'}

def is_calligraphy_type(name):
    for ct in CALLIGRAPHY_TYPES:
        if ct in name and len(name) <= len(ct) + 2:
            return True
    if name in CALLIGRAPHY_TYPES:
        return True
    return False

def infer_entity_type(name, original_type, roles, type_error_info):
    if name in standard_time_names.values() or name in standard_time_names:
        return '时间', '关系角色推断:作为朝代尾实体'

    if roles['as_end'].get('朝代', 0) > 0:
        return '时间', '关系角色推断:作为朝代尾实体'

    if roles['as_end'].get('籍贯', 0) > 0:
        return '地点', '关系角色推断:作为籍贯尾实体'

    if roles['as_end'].get('作品', 0) > 0:
        return '作品', '关系角色推断:作为作品尾实体'

    if roles['as_end'].get('名号', 0) > 0:
        return '名号', '关系角色推断:作为名号尾实体'

    if roles['as_end'].get('官职', 0) > 0:
        return '官职', '关系角色推断:作为官职尾实体'

    if roles['as_end'].get('评价', 0) > 0:
        return '评价', '关系角色推断:作为评价尾实体'

    if roles['as_end'].get('擅长', 0) > 0:
        if is_calligraphy_type(name):
            return '书法类别', '关系角色推断:作为擅长尾实体且名称含书体名'
        if name in CALLIGRAPHY_TYPES:
            return '书法类别', '关系角色推断:作为擅长尾实体且为已知书体'
        domain_keywords = ['画', '诗', '文', '山水', '花鸟', '人物', '佛像', '墨竹', '兰',
                          '篆刻', '琴', '乐府', '词', '丹青', '绘事', '写真', '传神', '临摹',
                          '指画', '没骨', '写生', '写意', '花卉', '翎毛', '竹石', '仕女',
                          '鬼神', '道释', '佛像', '鞍马', '楼观', '阁楼', '牛马', '虫禽',
                          '鸟兽', '台阁', '着色', '佛像人物', '佛道', '神仙', '古文', '辞章',
                          '音律', '经学', '词章', '词翰', '翰墨', '笔札', '书法', '绘画',
                          '书画', '诗文', '正书', '行书', '草书', '楷书', '隶书', '篆书',
                          '章草', '飞白', '小楷', '行草', '行楷', '大字', '小字', '八分',
                          '飞白书', '籀书', '草隶', '拓古', '刻竹', '紫砂', '墨菊', '墨竹',
                          '枯木', '石菖蒲', '道释人物', '番马', '鱼水', '虎', '马', '龙水',
                          '水石', '松树', '折枝', '草木', '花', '鸟', '犬', '猫', '鹤',
                          '观音', '大士', '罗汉', '天王', '鬼神', '肖像', '肖像画']
        for kw in domain_keywords:
            if kw in name:
                return '领域', f'关系角色推断:作为擅长尾实体且含领域关键词"{kw}"'
        return '领域', '关系角色推断:作为擅长尾实体(默认领域)'

    if (roles['as_start'].get('师承', 0) > 0 or roles['as_start'].get('取法', 0) > 0 or
        roles['as_end'].get('师承', 0) > 0 or roles['as_end'].get('取法', 0) > 0 or
        roles['as_start'].get('交游', 0) > 0 or roles['as_end'].get('交游', 0) > 0 or
        roles['as_start'].get('家人', 0) > 0 or roles['as_end'].get('家人', 0) > 0):
        return '人', '关系角色推断:作为师承/取法/交游/家人的头或尾实体'

    if roles['as_start'].get('朝代', 0) > 0:
        return '人', '关系角色推断:作为朝代头实体(人物所属朝代)'

    if roles['as_start'].get('籍贯', 0) > 0:
        return '人', '关系角色推断:作为籍贯头实体(人物籍贯)'

    if roles['as_start'].get('擅长', 0) > 0:
        return '人', '关系角色推断:作为擅长头实体(人物擅长)'

    if roles['as_start'].get('作品', 0) > 0:
        return '人', '关系角色推断:作为作品头实体(人物创作作品)'

    if roles['as_start'].get('评价', 0) > 0:
        return '人', '关系角色推断:作为评价头实体(人物被评价)'

    if roles['as_start'].get('名号', 0) > 0:
        return '人', '关系角色推断:作为名号头实体(人物有名号)'

    if roles['as_start'].get('官职', 0) > 0:
        return '人', '关系角色推断:作为官职头实体(人物任官职)'

    if type_error_info:
        suggested = type_error_info.get('suggested_type', '')
        if suggested in VALID_TYPES:
            return suggested, f'参考实体预审错误清单建议: {type_error_info.get("problem", "")}'

    if '《' in name or '》' in name or '帖' in name or '碑' in name or '序' in name or '论' in name or '集' in name or '谱' in name or '图' in name or '记' in name or '赋' in name or '卷' in name or '歌' in name:
        if original_type != '作品':
            return '作品', '名称语义辅助:含作品特征词'

    place_suffixes = ['人', '县', '郡', '州', '里', '省', '城', '镇', '村', '山', '水', '江', '河', '湖', '海']
    if any(name.endswith(s) for s in place_suffixes) and '今' in name:
        return '地点', '名称语义辅助:含地名特征(今...)'

    if any(s in name for s in ['将军', '监', '令', '公', '侯', '尚书', '侍郎', '大夫', '刺史', '太守',
                                '都督', '司马', '长史', '参军', '主簿', '学士', '宰相', '丞相',
                                '巡抚', '总督', '知府', '知州', '知县', '进士', '举人']):
        if original_type not in ('官职', '人'):
            return '官职', '名称语义辅助:含官职词'

    dynasty_keywords = ['朝', '代', '年', '纪', '元', '晋', '唐', '宋', '明', '清', '汉', '魏',
                       '秦', '周', '隋', '五代', '南北朝', '南宋', '北宋', '东晋', '西晋',
                       '东汉', '西汉', '三国', '民国', '现代', '古代']
    if any(kw in name for kw in dynasty_keywords) and len(name) <= 6:
        if re.match(r'^[\d～\-]+$', name) or re.match(r'^\d{2,4}[～\-]\d{2,4}', name):
            return '时间', '名称语义辅助:含时间特征(数字年份)'

    return original_type if original_type in VALID_TYPES else '其他', '保留原始类型或兜底'

# ============================================================
# 构建完整实体清单
# ============================================================
all_entity_names = set()
entity_original_types = {}

for n in nodes_raw:
    name = n['name'].strip()
    otype = n['type'].strip()
    corrected_name = name_corrections.get(name, name)
    all_entity_names.add(corrected_name)
    if corrected_name not in entity_original_types:
        entity_original_types[corrected_name] = otype
    else:
        if otype in VALID_TYPES and entity_original_types[corrected_name] not in VALID_TYPES:
            entity_original_types[corrected_name] = otype

for name in only_in_rels:
    corrected_name = name_corrections.get(name, name)
    all_entity_names.add(corrected_name)
    if corrected_name not in entity_original_types:
        entity_original_types[corrected_name] = '(无)'

# ============================================================
# 推断实体类型
# ============================================================
entity_fixed_types = {}
entity_type_evidence = {}

for name in all_entity_names:
    original_type = entity_original_types.get(name, '其他')
    roles = entity_roles.get(name, {'as_start': defaultdict(int), 'as_end': defaultdict(int)})

    corrected_for_lookup = name
    for orig, corr in name_corrections.items():
        if name == corr:
            corrected_for_lookup = orig
            break

    type_err_info = type_error_map.get(name) or type_error_map.get(corrected_for_lookup)

    fixed_type, evidence = infer_entity_type(name, original_type, roles, type_err_info)
    entity_fixed_types[name] = fixed_type
    entity_type_evidence[name] = evidence

# ============================================================
# 特定实体类型修正（基于联网验证）
# ============================================================
specific_type_fixes = {
    '《圣教序》': ('作品', '联网验证:圣教序是碑刻作品，非人物'),
    '《孙叔敖碑》': ('作品', '联网验证:碑刻作品，非人物'),
    '《晋书》': ('作品', '联网验证:史书作品，非书法类别'),
    '《卓歇图》': ('作品', '联网验证:画作，非领域'),
    '《兰亭》': ('作品', '联网验证:兰亭序是书法作品'),
    '王珣': ('人', '联网验证:王珣(350-401)东晋书法家'),
    '谢安': ('人', '联网验证:谢安(320-385)东晋政治家'),
    '卫铄': ('人', '联网验证:卫铄(272-349)即卫夫人，东晋女书法家'),
    '杜度': ('人', '联网验证:杜度即杜操，东汉书法家'),
    '楚珍': ('人', '联网验证:楚珍为宋代女书法家'),
    '爱新觉罗': ('人', '联网验证:爱新觉罗为清代皇族姓氏'),
    '赵孟頫': ('人', '联网验证:赵孟頫(1254-1322)元代书法家'),
    '亦能诗': ('领域', '参考预审清单:可能是擅长/领域'),
    '善真草书': ('领域', '参考预审清单:可能是擅长/领域'),
    '善属文,尤工书': ('领域', '参考预审清单:可能是擅长/领域'),
    '善鉴古器物书画': ('领域', '参考预审清单:可能是擅长/领域'),
    '善正书': ('领域', '参考预审清单:可能是擅长/领域'),
    '工书画': ('领域', '参考预审清单:可能是擅长/领域'),
    '善才寺碑': ('作品', '参考预审清单:碑刻作品'),
    '南唐吏部尚书': ('官职', '参考预审清单:包含尚书'),
    '赠兵部尚书': ('官职', '参考预审清单:包含尚书'),
    '邢尚书': ('官职', '参考预审清单:包含尚书'),
    '楷书朱柏庐先生治家格言屏': ('作品', '参考预审清单:书法作品'),
    '项圣谟王维诗意图册题跋': ('作品', '参考预审清单:题跋作品'),
    '题王石谷画': ('作品', '参考预审清单:题画作品'),
    '临王羲之帖': ('作品', '参考预审清单:临帖作品'),
    '自古帝王图': ('作品', '参考预审清单:画作作品'),
    '王志': ('人', '参考预审清单:应为人物'),
}

for name, (fixed_type, evidence) in specific_type_fixes.items():
    if name in entity_fixed_types:
        entity_fixed_types[name] = fixed_type
        entity_type_evidence[name] = evidence

# ============================================================
# 步骤5: 生成修正后实体表
# ============================================================
entities_fixed = []
for name in sorted(all_entity_names):
    entities_fixed.append({
        'name': name,
        'type': entity_fixed_types[name]
    })

write_csv(os.path.join(BASE_DIR, 'entities_fixed.csv'), ['name', 'type'], entities_fixed)
print(f"修正后实体数: {len(entities_fixed)}")

# ============================================================
# 步骤6: 实体变更日志
# ============================================================
entity_changelog = []

for n in nodes_raw:
    orig_name = n['name'].strip()
    orig_type = n['type'].strip()
    corrected_name = name_corrections.get(orig_name, orig_name)

    if orig_name in name_corrections:
        decision = '修正'
        if orig_name in duplicate_person_fixes.values():
            decision = '合并'
        elif orig_name in typo_fixes:
            decision = '修正'
    elif corrected_name in entity_fixed_types and entity_fixed_types[corrected_name] != orig_type:
        decision = '修正'
    else:
        decision = '保留'

    fixed_type = entity_fixed_types.get(corrected_name, orig_type)
    evidence = entity_type_evidence.get(corrected_name, '')

    entity_changelog.append({
        '原始name': orig_name,
        '原始type': orig_type,
        '处理决策': decision,
        '修正后name': corrected_name,
        '修正后type': fixed_type,
        '决策依据': evidence,
        '验证来源': '联网搜索' if '联网' in evidence else '规则推断'
    })

for name in only_in_rels:
    corrected_name = name_corrections.get(name, name)
    if corrected_name not in {n['name'].strip() for n in nodes_raw} and corrected_name not in {c['修正后name'] for c in entity_changelog}:
        fixed_type = entity_fixed_types.get(corrected_name, '其他')
        evidence = entity_type_evidence.get(corrected_name, '')
        entity_changelog.append({
            '原始name': name,
            '原始type': '(无)',
            '处理决策': '修正',
            '修正后name': corrected_name,
            '修正后type': fixed_type,
            '决策依据': '该实体由关系表提取，原实体表中不存在; ' + evidence,
            '验证来源': '联网搜索' if '联网' in evidence else '规则推断'
        })

write_csv(os.path.join(BASE_DIR, 'entity_changelog.csv'),
          ['原始name', '原始type', '处理决策', '修正后name', '修正后type', '决策依据', '验证来源'],
          entity_changelog)
print(f"实体变更日志条数: {len(entity_changelog)}")

# ============================================================
# 步骤7: 关系表修复
# ============================================================

# 7.0 构建名称映射表
name_mapping = {}
for cl in entity_changelog:
    orig = cl['原始name']
    fixed = cl['修正后name']
    if orig != fixed:
        name_mapping[orig] = fixed

# 7.1 关系类型标准化: "学习" -> "取法"
def standardize_rel_type(rel_type):
    if rel_type == '学习':
        return '取法'
    if rel_type == '其它':
        return '取法'
    return rel_type

# 7.3 多值拆分
def split_multi_value(end_value):
    if '、' in end_value or (',' in end_value and '，' not in end_value and '《' not in end_value):
        parts = re.split('[、,]', end_value)
        result = []
        for p in parts:
            p = p.strip()
            if p:
                result.append(p)
        if len(result) > 1:
            return result
    return [end_value]

# 7.2 时代逻辑校验 - 关键人物朝代映射
person_dynasty = {
    '王羲之': '东晋', '王献之': '东晋', '颜真卿': '唐代', '柳公权': '唐代',
    '欧阳询': '唐代', '褚遂良': '唐代', '虞世南': '唐代', '张旭': '唐代',
    '怀素': '唐代', '钟繇': '三国·魏', '蔡邕': '东汉', '蔡文姬': '东汉',
    '苏轼': '北宋', '黄庭坚': '北宋', '米芾': '北宋', '蔡襄': '北宋',
    '赵孟頫': '元代', '董其昌': '明代', '文徵明': '明代', '祝允明': '明代',
    '王铎': '清代', '刘墉': '清代', '翁方纲': '清代', '铁保': '清代',
    '何绍基': '清代', '邓石如': '清代', '吴昌硕': '清代', '康有为': '清代',
    '包世臣': '清代', '沈曾植': '清代', '齐白石': '现代', '启功': '现代',
    '谢安': '东晋', '卫铄': '东晋', '杜度': '东汉', '皇象': '三国·吴',
    '索靖': '西晋', '卫瓘': '西晋', '卫觊': '三国·魏', '卫恒': '西晋',
    '张芝': '东汉', '韦诞': '三国·魏', '蔡松年': '金代', '王庭筠': '金代',
    '宋克': '明代', '白蕉': '现代', '李世民': '唐代', '李邕': '唐代',
    '陆深': '明代', '梅调鼎': '清代', '高士奇': '清代', '宋荦': '清代',
    '孙承泽': '清代', '孙过庭': '唐代', '方以智': '清代', '丰子恺': '现代',
    '郭沫若': '现代', '丁佛言': '现代', '乔曾勣': '现代', '章士钊': '现代',
    '谢稚柳': '现代', '萧蜕': '现代', '张伯英': '现代', '谭延闿': '现代',
    '赵熙': '现代', '金城': '现代', '倪瓒': '元代', '钱选': '元代',
    '管夫人': '元代', '冒襄': '清代', '沈荃': '清代', '祁豸佳': '清代',
    '普荷': '清代', '翁方纲': '清代', '周於礼': '清代', '朱稻孙': '清代',
    '王鸿绪': '清代', '杨宾': '清代', '刘墉': '清代', '蒋士铨': '清代',
    '张孝祥': '宋代', '商挺': '元代', '杨凝式': '五代', '陈希祖': '清代',
    '桂馥': '清代', '黄葆戊': '现代', '沈曾植': '清代', '马一浮': '现代',
    '弘一': '现代', '沙孟海': '现代', '徐悲鸿': '现代', '萧娴': '现代',
    '饶介': '元代', '陈洪绶': '明代', '徐渭': '明代', '金农': '清代',
    '吴宽': '明代', '李流芳': '明代', '沈周': '明代', '文从简': '明代',
    '查慎行': '清代', '玄烨': '清代', '王艺孙': '清代', '龚璠': '清代',
    '林散之': '现代', '王铎': '清代', '曾纪泽': '清代', '吴大澂': '清代',
    '李东阳': '明代', '蔡京': '宋代', '蔡襄': '宋代', '曾国藩': '清代',
    '华岛': '清代', '仇氏': '明代', '郑贵妃': '明代', '厉鹗': '清代',
    '周淑祜': '明代', '周淑禧': '明代', '朱彝尊': '清代', '查慎行': '清代',
    '王妃': '明代', '绿华': '前蜀', '琼华': '前蜀', '刘婉容': '南宋',
    '汤漱玉': '清代', '汪远孙': '清代', '汪选楼': '清代', '梁端': '清代',
    '胡敬': '清代', '陈扶雅': '清代', '张翼': '东晋', '马治': '明代',
    '张昶': '东汉', '贝义渊': '南朝·梁', '杜琼': '明代',
    '程邈': '秦代', '李斯': '秦代', '梁鹄': '东汉',
    '贺知章': '唐代', '黄公望': '元代', '司马师': '三国·魏',
    '司马昭': '三国·魏', '仁宗': '搁置', '神宗': '搁置',
    '文宗': '搁置', '英宗': '搁置', '宣宗': '搁置',
    '孝宗': '搁置', '武帝': '搁置',
    '蔡有邻': '唐代', '蔡羽': '明代', '陈鉴': '明代',
    '程钜夫': '元代', '姚枢': '元代', '姚燧': '元代',
    '耶律楚材': '元代', '虞集': '元代', '张謇': '清代',
    '赵秉文': '金代', '赵伯啸': '宋代', '赵佶': '北宋',
    '赵孟坚': '宋代', '朱元璋': '明代', '泰不华': '元代',
    '徐铉': '宋代', '徐霖': '明代', '薛稷': '唐代',
    '张羽': '元代', '宋克': '明代', '苏庠': '搁置',
    '陶弘景': '南朝·梁', '萧衍': '南朝·梁', '萧绎': '南朝·梁',
    '辛亥': '搁置', '卞赛': '明代', '李夫人': '搁置',
    '王孟仁': '搁置', '王僧虔': '南朝·齐',
}

dynasty_order = {
    '秦代': 1, '秦': 1, '西汉': 2, '东汉': 3, '汉朝': 3,
    '三国·魏': 4, '三国·吴': 4, '三国·蜀': 4, '三国魏': 4, '三国吴': 4,
    '西晋': 5, '东晋': 6, '晋': 5.5,
    '南朝·宋': 7, '南朝·齐': 7, '南朝·梁': 7, '南朝·陈': 7, '南朝陈': 7,
    '隋': 8, '唐代': 9, '唐': 9, '五代': 10, '北宋': 11, '宋': 11,
    '南宋': 12, '金代': 11.5, '金': 11.5, '元代': 13, '元': 13,
    '明代': 14, '明': 14, '清代': 15, '清': 15,
    '现代': 16, '民国': 15.5, '前蜀': 10, '后唐': 10,
}

def get_dynasty_order(dynasty):
    if dynasty in dynasty_order:
        return dynasty_order[dynasty]
    return 0

def check_temporal_logic(start_person, end_person, rel_type):
    start_dynasty = person_dynasty.get(start_person)
    end_dynasty = person_dynasty.get(end_person)

    if not start_dynasty or not end_dynasty:
        return None, '无法获取可信朝代信息'

    if start_dynasty == '搁置' or end_dynasty == '搁置':
        return None, '朝代信息存在歧义，搁置'

    start_order = get_dynasty_order(start_dynasty)
    end_order = get_dynasty_order(end_dynasty)

    if rel_type == '师承':
        if start_order <= end_order and start_dynasty == end_dynasty:
            return None, '同朝代师承关系需进一步验证'
        if start_order < end_order:
            return '方向错误', f'学生{start_person}({start_dynasty})年代不晚于老师{end_person}({end_dynasty})'

    if rel_type == '取法':
        if start_order < end_order:
            return '方向错误', f'后来者{start_person}({start_dynasty})年代不晚于前辈{end_person}({end_dynasty})'

    if rel_type == '交游':
        if abs(start_order - end_order) > 1:
            same_period = (start_dynasty == end_dynasty)
            if not same_period:
                return '时代无交集', f'{start_person}({start_dynasty})与{end_person}({end_dynasty})年代无交集'

    return None, ''

# ============================================================
# 处理关系表
# ============================================================
relation_changelog = []
fixed_relations = []

for rel in rels_raw:
    orig_start = rel['start'].strip()
    orig_type = rel['type'].strip()
    orig_end = rel['end'].strip()

    fixed_start = name_mapping.get(orig_start, orig_start)
    fixed_end_raw = name_mapping.get(orig_end, orig_end)
    fixed_type = standardize_rel_type(orig_type)

    ends = split_multi_value(fixed_end_raw)

    content_error_matched = False
    content_error_note = ''
    for ce in content_errors:
        ce_s = ce.get('start', '').strip()
        ce_t = ce.get('type', '').strip()
        ce_e = ce.get('end', '').strip()
        if (ce_s == orig_start or ce_s == fixed_start) and ce_t == orig_type and (ce_e == orig_end or ce_e == fixed_end_raw):
            content_error_matched = True
            content_error_note = ce.get('可能的问题', '').strip()
            break
    if not content_error_matched:
        for ce in content_errors:
            ce_s = ce.get('start', '').strip()
            ce_t = ce.get('type', '').strip()
            ce_e = ce.get('end', '').strip()
            mapped_ce_s = name_mapping.get(ce_s, ce_s)
            mapped_ce_e = name_mapping.get(ce_e, ce_e)
            if (mapped_ce_s == fixed_start) and ce_t == fixed_type and (mapped_ce_e == fixed_end_raw or mapped_ce_e in ends):
                content_error_matched = True
                content_error_note = ce.get('可能的问题', '').strip()
                break

    decision = '保留'
    decision_evidence = ''
    verification_source = ''

    if orig_start in name_corrections or orig_end in name_corrections:
        decision = '修正'
        decision_evidence = f'实体名称修正: {orig_start}→{fixed_start}, {orig_end}→{fixed_end_raw}'
        verification_source = '联网搜索验证'

    if orig_type == '学习':
        if decision == '保留':
            decision = '修正'
        decision_evidence += '; 关系类型标准化: 学习→取法'

    if len(ends) > 1:
        decision = '拆分'
        decision_evidence += f'; 多值拆分: {fixed_end_raw}→{", ".join(ends)}'

    if content_error_matched:
        if '朝代不一致' in content_error_note:
            if fixed_type == '朝代':
                correct_dynasty = person_dynasty.get(fixed_start)
                if correct_dynasty and correct_dynasty != '搁置':
                    decision = '修正'
                    decision_evidence += f'; 参考content_errors_to_review_v3: 朝代不一致，{fixed_start}正确朝代为{correct_dynasty}'
                    verification_source = '联网搜索验证'
                    ends = [correct_dynasty]
                elif fixed_end_raw in person_dynasty:
                    alt_dynasty = person_dynasty[fixed_end_raw]
                    if alt_dynasty and alt_dynasty != '搁置':
                        decision = '修正'
                        decision_evidence += f'; 参考content_errors_to_review_v3: 朝代不一致，保留标准朝代{alt_dynasty}'
                        verification_source = '联网搜索验证'
                        ends = [alt_dynasty]
                    else:
                        decision = '搁置'
                        decision_evidence += f'; 参考content_errors_to_review_v3: 朝代不一致且无法确定正确朝代'
                else:
                    non_standard = [e for e in ends if e not in dynasty_order and not re.match(r'^\d', e)]
                    standard = [e for e in ends if e in dynasty_order]
                    if standard:
                        ends = standard[:1]
                        decision = '修正'
                        decision_evidence += f'; 参考content_errors_to_review_v3: 朝代不一致，保留标准朝代名称'
                    else:
                        decision = '搁置'
                        decision_evidence += f'; 参考content_errors_to_review_v3: 朝代不一致，全部为非标准朝代名称'

        elif '名字可能有误' in content_error_note:
            if '重复字符' in content_error_note:
                if orig_start in duplicate_person_fixes or orig_end in duplicate_person_fixes:
                    if decision == '保留':
                        decision = '修正'
                    decision_evidence += f'; 参考content_errors_to_review_v3: 重复字符名称已修正'

        elif '交游关系可能不合理' in content_error_note:
            temporal_issue, temp_evidence = check_temporal_logic(fixed_start, fixed_end_raw, '交游')
            if temporal_issue:
                decision = '建议删除'
                decision_evidence += f'; 参考content_errors_to_review_v3: {content_error_note}; {temp_evidence}'
                verification_source = '联网搜索验证'
            else:
                decision_evidence += f'; 参考content_errors_to_review_v3: {content_error_note}; 经核查，该问题不成立(时代有交集或无法确认)'

        elif '师承关系可能不合理' in content_error_note:
            temporal_issue, temp_evidence = check_temporal_logic(fixed_start, fixed_end_raw, '师承')
            if temporal_issue == '方向错误':
                decision = '修正'
                fixed_start, fixed_end_raw = fixed_end_raw, fixed_start
                ends = [fixed_end_raw]
                decision_evidence += f'; 参考content_errors_to_review_v3: {content_error_note}; 师承方向修正: {temp_evidence}'
                verification_source = '联网搜索验证'
            elif temporal_issue:
                decision = '搁置'
                decision_evidence += f'; 参考content_errors_to_review_v3: {content_error_note}; {temp_evidence}'
                verification_source = '联网搜索验证'

        elif '取法内容过短' in content_error_note:
            decision = '搁置'
            decision_evidence += f'; 参考content_errors_to_review_v3: {content_error_note}'

        elif '名号包含引号' in content_error_note:
            cleaned = fixed_end_raw.strip('"').strip('"').strip('"')
            if cleaned != fixed_end_raw:
                if decision == '保留':
                    decision = '修正'
                ends = [cleaned]
                decision_evidence += f'; 参考content_errors_to_review_v3: 清理名号中的引号'

        elif '名号过短' in content_error_note:
            if len(fixed_end_raw) <= 1:
                decision = '搁置'
                decision_evidence += f'; 参考content_errors_to_review_v3: 名号过短(单字)，可能为名而非号'

        elif '评价内容过短' in content_error_note:
            if len(fixed_end_raw) <= 1:
                decision = '搁置'
                decision_evidence += f'; 参考content_errors_to_review_v3: 评价内容过短(单字)'

        elif '评价内容包含问号' in content_error_note:
            decision = '建议删除'
            decision_evidence += f'; 参考content_errors_to_review_v3: 评价内容包含问号，可能不是评价'

        elif '籍贯错误' in content_error_note:
            decision = '建议删除'
            decision_evidence += f'; 参考content_errors_to_review_v3: {content_error_note}'
            verification_source = '规则推断'

        elif '官职错误' in content_error_note:
            decision = '建议删除'
            decision_evidence += f'; 参考content_errors_to_review_v3: {content_error_note}'

        elif '作品名称过短' in content_error_note:
            if len(fixed_end_raw) <= 1:
                decision = '建议删除'
                decision_evidence += f'; 参考content_errors_to_review_v3: 作品名称过短(单字)'

        elif '作品名称不明确' in content_error_note:
            decision = '建议删除'
            decision_evidence += f'; 参考content_errors_to_review_v3: 作品名称不明确'

        elif '擅长内容包含标点' in content_error_note:
            decision = '搁置'
            decision_evidence += f'; 参考content_errors_to_review_v3: {content_error_note}'

        elif '擅长内容过短' in content_error_note:
            if len(fixed_end_raw) <= 1:
                decision = '搁置'
                decision_evidence += f'; 参考content_errors_to_review_v3: 擅长内容过短(单字)'

        elif '家人关系过短' in content_error_note:
            decision = '搁置'
            decision_evidence += f'; 参考content_errors_to_review_v3: {content_error_note}'

        else:
            decision_evidence += f'; 参考content_errors_to_review_v3: {content_error_note}'

    # 7.4 籍贯有效性校验
    if fixed_type == '籍贯':
        end_type = entity_fixed_types.get(fixed_end_raw, '')
        if end_type and end_type not in ('地点',):
            if decision == '保留':
                decision = '建议删除'
            decision_evidence += f'; 籍贯尾实体类型为{end_type}，非地点类型'

    # 时代逻辑校验(师承/取法/交游)
    if fixed_type in ('师承', '取法', '交游') and not content_error_matched:
        temporal_issue, temp_evidence = check_temporal_logic(fixed_start, fixed_end_raw, fixed_type)
        if temporal_issue == '方向错误':
            if decision == '保留':
                decision = '修正'
            fixed_start, fixed_end_raw = fixed_end_raw, fixed_start
            ends = [fixed_end_raw]
            decision_evidence += f'; 时代逻辑校验: {temp_evidence}'
            verification_source = '联网搜索验证'
        elif temporal_issue == '时代无交集':
            if decision == '保留':
                decision = '建议删除'
            decision_evidence += f'; 时代逻辑校验: {temp_evidence}'
            verification_source = '联网搜索验证'

    # 记录变更日志
    for end_val in ends:
        changelog_entry = {
            '原始Start': orig_start,
            '原始Type': orig_type,
            '原始End': orig_end,
            '处理决策': decision if len(ends) == 1 else ('拆分新增' if end_val != ends[0] else '拆分'),
            '修正后Start': fixed_start,
            '修正后Type': fixed_type,
            '修正后End': end_val,
            '决策依据': decision_evidence.strip('; '),
            '验证来源': verification_source or '规则推断'
        }
        relation_changelog.append(changelog_entry)

        if decision in ('保留', '修正', '拆分', '拆分新增'):
            is_dup = any(r['Start'] == fixed_start and r['Type'] == fixed_type and r['End'] == end_val
                        for r in fixed_relations)
            if not is_dup:
                fixed_relations.append({
                    'Start': fixed_start,
                    'Type': fixed_type,
                    'End': end_val
                })

# ============================================================
# 步骤8: 关系变更日志
# ============================================================
write_csv(os.path.join(BASE_DIR, 'relation_changelog.csv'),
          ['原始Start', '原始Type', '原始End', '处理决策', '修正后Start', '修正后Type', '修正后End', '决策依据', '验证来源'],
          relation_changelog)
print(f"关系变更日志条数: {len(relation_changelog)}")

# ============================================================
# 步骤9: 生成修正后关系表
# ============================================================
write_csv(os.path.join(BASE_DIR, 'relations_fixed.csv'),
          ['Start', 'Type', 'End'],
          fixed_relations)
print(f"修正后关系数: {len(fixed_relations)}")

# ============================================================
# 统计信息
# ============================================================
print("\n===== 处理统计 =====")
print(f"原始实体数: {len(nodes_raw)}")
print(f"修正后实体数: {len(entities_fixed)}")
print(f"原始关系数: {len(rels_raw)}")
print(f"修正后关系数: {len(fixed_relations)}")

entity_decisions = defaultdict(int)
for cl in entity_changelog:
    entity_decisions[cl['处理决策']] += 1
print(f"\n实体处理决策统计:")
for k, v in sorted(entity_decisions.items()):
    print(f"  {k}: {v}")

rel_decisions = defaultdict(int)
for cl in relation_changelog:
    rel_decisions[cl['处理决策']] += 1
print(f"\n关系处理决策统计:")
for k, v in sorted(rel_decisions.items()):
    print(f"  {k}: {v}")

type_dist = defaultdict(int)
for e in entities_fixed:
    type_dist[e['type']] += 1
print(f"\n修正后实体类型分布:")
for k, v in sorted(type_dist.items(), key=lambda x: -x[1]):
    print(f"  {k}: {v}")

rel_type_dist = defaultdict(int)
for r in fixed_relations:
    rel_type_dist[r['Type']] += 1
print(f"\n修正后关系类型分布:")
for k, v in sorted(rel_type_dist.items(), key=lambda x: -x[1]):
    print(f"  {k}: {v}")

print("\n===== 处理完成 =====")

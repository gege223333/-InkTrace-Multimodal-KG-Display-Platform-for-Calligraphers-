﻿# kg_builder.py
import re
import json
import os
import time
from typing import List, Dict, Any
import pandas as pd
import spacy
from tqdm import tqdm
import dashscope
from http import HTTPStatus

# ai辅助生成
class CalligraphyKGBuilder:
    def __init__(self, api_key: str = None):
        """初始化构建器"""
        print("初始化知识图谱构建器...")
        
        # 加载中文NLP模型
        try:
            self.nlp = spacy.load("zh_core_web_sm")
            print("✓ 成功加载spacy中文模型")
        except:
            print("✗ 无法加载spacy中文模型，将使用基础分词")
            self.nlp = None
        
        # 设置DashScope API
        if api_key:
            dashscope.api_key = api_key
            self.use_api = True
            self.model_name = "qwen-max"
            print(f"✓ 已配置DashScope API，使用模型: {self.model_name}")
        else:
            self.use_api = False
            print("⚠ 未配置API，将使用规则提取")
        
        # 存储结果
        self.all_entities = {}
        self.all_relations = []
        self.all_events = []
        
        # 统计信息
        self.stats = {
            "total_chunks": 0,
            "processed_chunks": 0,
            "api_calls": 0,
            "failed_chunks": 0,
            "total_entities": 0,
            "total_relations": 0
        }
        
        # 实体映射字典
        self.entity_map = {}  # 实体名称 -> 实体ID
        self.entity_id_counter = 1
        
        # 创建输出目录
        os.makedirs("output", exist_ok=True)
        os.makedirs("temp", exist_ok=True)
    
    def load_and_split_file(self, file_path: str) -> List[Dict]:
        """加载并智能分割文件"""
        print(f"加载文件: {file_path}")
        
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        print(f"文件大小: {len(content):,} 字符")
        
        # 按章节分割
        chapters = self._split_by_chapters(content)
        print(f"分割为 {len(chapters)} 个章节")
        
        # 对每个章节进一步分块
        all_chunks = []
        for i, chapter in enumerate(chapters):
            chunks = self._split_chapter_into_chunks(chapter, i+1)
            all_chunks.extend(chunks)
        
        self.stats["total_chunks"] = len(all_chunks)
        print(f"总共 {len(all_chunks)} 个处理块")
        
        return all_chunks
    
    def _split_by_chapters(self, content: str) -> List[Dict]:
        """按章节分割内容"""
        chapter_pattern = r'(^|\n)(#{1,3}\s+[^\n]+)(\n|$)'
        
        chapters = []
        last_end = 0
        
        for match in re.finditer(chapter_pattern, content, re.MULTILINE):
            if match.start() > last_end:
                chapter_content = content[last_end:match.start()]
                if chapter_content.strip():
                    chapters.append({
                        "title": "前言" if len(chapters) == 0 else chapters[-1]["title"],
                        "content": chapter_content.strip()
                    })
            
            title = match.group(2).strip()
            last_end = match.end()
        
        if last_end < len(content):
            chapter_content = content[last_end:]
            if chapter_content.strip():
                chapters.append({
                    "title": title if 'title' in locals() else "附录",
                    "content": chapter_content.strip()
                })
        
        return chapters
    
    def _split_chapter_into_chunks(self, chapter: Dict, chapter_num: int) -> List[Dict]:
        """将章节分割为处理块"""
        chunks = []
        content = chapter["content"]
        
        if len(content) <= 2000:  # CHUNK_SIZE
            chunks.append({
                "chapter": chapter_num,
                "title": chapter["title"],
                "content": content,
                "chunk_num": 1,
                "total_chunks": 1
            })
            return chunks
        
        paragraphs = re.split(r'\n\n+', content)
        current_chunk = []
        current_length = 0
        
        for para in paragraphs:
            para = para.strip()
            if not para:
                continue
                
            para_length = len(para)
            
            if para_length > 2000:  # CHUNK_SIZE
                if current_chunk:
                    chunks.append({
                        "chapter": chapter_num,
                        "title": chapter["title"],
                        "content": "\n\n".join(current_chunk),
                        "chunk_num": len(chunks) + 1,
                        "total_chunks": 0
                    })
                    current_chunk = []
                    current_length = 0
                
                sentences = re.split(r'[。！？；]', para)
                temp_sentences = []
                temp_length = 0
                
                for sent in sentences:
                    sent = sent.strip()
                    if not sent:
                        continue
                        
                    sent_length = len(sent) + 1
                    
                    if temp_length + sent_length > 2000 and temp_sentences:  # CHUNK_SIZE
                        chunks.append({
                            "chapter": chapter_num,
                            "title": chapter["title"],
                            "content": "。".join(temp_sentences) + "。",
                            "chunk_num": len(chunks) + 1,
                            "total_chunks": 0
                        })
                        temp_sentences = []
                        temp_length = 0
                    
                    temp_sentences.append(sent)
                    temp_length += sent_length
                
                if temp_sentences:
                    chunks.append({
                        "chapter": chapter_num,
                        "title": chapter["title"],
                        "content": "。".join(temp_sentences) + "。",
                        "chunk_num": len(chunks) + 1,
                        "total_chunks": 0
                    })
            
            elif current_length + para_length <= 2000:  # CHUNK_SIZE
                current_chunk.append(para)
                current_length += para_length
            else:
                chunks.append({
                    "chapter": chapter_num,
                    "title": chapter["title"],
                    "content": "\n\n".join(current_chunk),
                    "chunk_num": len(chunks) + 1,
                    "total_chunks": 0
                })
                current_chunk = [para]
                current_length = para_length
        
        if current_chunk:
            chunks.append({
                "chapter": chapter_num,
                "title": chapter["title"],
                "content": "\n\n".join(current_chunk),
                "chunk_num": len(chunks) + 1,
                "total_chunks": 0
            })
        
        for chunk in chunks:
            chunk["total_chunks"] = len(chunks)
        
        return chunks
    
    def extract_with_llm(self, chunk: Dict, max_retries: int = 3) -> Dict:
        """使用DashScope Qwen API提取信息"""
        if not self.use_api:
            return self._fallback_extraction(chunk["content"])
        
        prompt = self._create_extraction_prompt(chunk)
        
        for attempt in range(max_retries):
            try:
                response = dashscope.Generation.call(
                    model=self.model_name,
                    prompt=prompt,
                    seed=123,
                    result_format='message',
                    max_tokens=2000,
                    temperature=0.1
                )
                
                self.stats["api_calls"] += 1
                
                if response.status_code == HTTPStatus.OK:
                    result_text = response.output.choices[0].message.content
                    
                    try:
                        json_text = result_text.strip()
                        
                        if "```json" in json_text:
                            json_text = json_text.split("```json")[1].split("```")[0]
                        elif "```" in json_text:
                            json_text = json_text.split("```")[1].split("```")[0]
                        
                        result = json.loads(json_text)
                        
                        if self._validate_extraction_result(result):
                            return result
                        else:
                            print(f"第{attempt+1}次尝试：返回结果格式不正确")
                            
                    except json.JSONDecodeError as e:
                        print(f"第{attempt+1}次尝试：JSON解析失败: {e}")
                        
                else:
                    print(f"第{attempt+1}次尝试：API调用失败，状态码: {response.status_code}")
                    
            except Exception as e:
                print(f"第{attempt+1}次尝试失败: {str(e)}")
                if attempt < max_retries - 1:
                    time.sleep(2 ** attempt)
                continue
        
        print(f"块 {chunk['chapter']}-{chunk['chunk_num']} 提取失败，使用备用方法")
        return self._fallback_extraction(chunk["content"])
    
    def _create_extraction_prompt(self, chunk: Dict) -> str:
     """创建提取提示词 - 专门针对中国古代书画家传记"""
     return f"""你是一个专业的知识抽取助手，专门从中国古代书法家/画家的传记文献中抽取三元组知识。

请仔细阅读以下文本，从中提取所有能形成关系的事实：

文本来自第{chunk['chapter']}章：{chunk['title']}
这是该章的第{chunk['chunk_num']}/{chunk['total_chunks']}部分

文本内容：
{chunk['content']}

请从文本中提取所有关于中国古代书法家/画家的三元组知识。关系类型包括但不限于：
1. 师承：如"张芝初师崔瑗" → (张芝, 师承, 崔瑗)
2. 擅长：如"李斯作小篆" → (李斯, 擅长, 小篆)
3. 籍贯：如"李斯，楚上蔡人" → (李斯, 籍贯, 楚上蔡)
4. 官职：如"李斯，始皇丞相" → (李斯, 官职, 丞相)
5. 评价：如"评斯书者，以谓骨气风云" → (李斯, 评价, 骨气风云)
6. 著作：如"著《仓颉篇》" → (李斯, 著作, 仓颉篇)
7. 朝代：如"秦" → (李斯, 朝代, 秦)
8. 同门：如"与某某同师某" → (A, 同门, B)
9. 交游：如"与某某友善" → (A, 交游, B)
10. 创制：如"作隶书" → (程邈, 创制, 隶书)
11. 风格：如"善草书" → (张芝, 风格, 草书)
12. 事件：如"因罪下狱" → (程邈, 事件, 下狱)
13. 称号：如"人称草圣" → (张芝, 称号, 草圣)
14. 受学于：如"受学于刘德升" → (钟繇, 受学于, 刘德升)
15. 师法：如"师法曹喜、蔡邕" → (梁鹄, 师法, 曹喜)

提取要求：
1. 只提取明确提到的关系，不要推测或编造
2. 主语必须是具体的书法家或画家
3. 宾语可以是人物、书体、地点、著作、评价等
4. 如果同一关系有多个对象，拆分为多个三元组
5. 保留原文的表达方式

输出格式必须是严格的JSON，包含一个"triples"数组，每个元素有"subject"、"predicate"、"object"三个字段：

{{
  "triples": [
    {{"subject": "张芝", "predicate": "师承", "object": "崔瑗"}},
    {{"subject": "李斯", "predicate": "擅长", "object": "小篆"}}
  ]
}}

如果文本中没有关于书画家的明确关系，输出空数组。

示例：
文本："李斯，楚上蔡人，始皇丞相。作小篆，著《仓颉篇》。"
应返回：
{{
  "triples": [
    {{"subject": "李斯", "predicate": "籍贯", "object": "楚上蔡"}},
    {{"subject": "李斯", "predicate": "官职", "object": "丞相"}},
    {{"subject": "李斯", "predicate": "朝代", "object": "秦"}},
    {{"subject": "李斯", "predicate": "擅长", "object": "小篆"}},
    {{"subject": "李斯", "predicate": "著作", "object": "《仓颉篇》"}}
  ]
}}

现在请处理上述文本：
"""
    
    def _fallback_extraction(self, text: str) -> Dict:
        """备用规则提取方法"""
        entities = []
        relations = []
        
        # 提取人物
        person_patterns = [
            r'([^\s，。]{2,5}氏)',
            r'([^\s，。]{2,4}[帝王皇祖圣])',
            r'([^\s，。]{2,4}臣)',
            r'([^\s，。]{2,4}史)'
        ]
        
        for pattern in person_patterns:
            for match in re.finditer(pattern, text):
                name = match.group(1)
                if name not in [e["name"] for e in entities if e["type"] == "PERSON"]:
                    entities.append({
                        "name": name,
                        "type": "PERSON",
                        "description": "",
                        "aliases": []
                    })
        
        # 提取书体
        script_patterns = [
            r'([^\s，。]{2,6}书)',
            r'([^\s，。]{2,4}文)',
            r'([^\s，。]{2,4}字)',
            r'([^\s，。]{2,4}篆)',
            r'([^\s，。]{2,4}隶)',
            r'([^\s，。]{2,4}楷)',
            r'([^\s，。]{2,4}草)',
            r'([^\s，。]{2,4}行)'
        ]
        
        for pattern in script_patterns:
            for match in re.finditer(pattern, text):
                name = match.group(1)
                if name not in [e["name"] for e in entities if e["type"] == "SCRIPT_STYLE"]:
                    entities.append({
                        "name": name,
                        "type": "SCRIPT_STYLE",
                        "description": "",
                        "aliases": []
                    })
        
        # 提取创造关系
        creation_patterns = [
            (r'([^\s，。]{2,5})作([^\s，。]{2,6}书)', '创造'),
            (r'([^\s，。]{2,5})造([^\s，。]{2,6}书)', '创造'),
            (r'([^\s，。]{2,5})创([^\s，。]{2,6}书)', '创造'),
            (r'([^\s，。]{2,5})制([^\s，。]{2,6}书)', '创造')
        ]
        
        for pattern, rel_type in creation_patterns:
            for match in re.finditer(pattern, text):
                subject = match.group(1)
                obj = match.group(2)
                relations.append({
                    "subject": subject,
                    "predicate": rel_type,
                    "object": obj,
                    "evidence": match.group(0)
                })
        
        return {
            "entities": entities,
            "relations": relations,
            "events": []
        }
    
    def _validate_extraction_result(self, result: Dict) -> bool:
        """验证提取结果格式"""
        if not isinstance(result, dict):
            return False
        
        required_keys = ["entities", "relations", "events"]
        if not all(key in result for key in required_keys):
            return False
        
        if not (isinstance(result["entities"], list) and 
                isinstance(result["relations"], list) and 
                isinstance(result["events"], list)):
            return False
        
        return True
    
    def _register_entity(self, entity: Dict) -> str:
        """注册实体，返回实体ID"""
        name = entity["name"]
        entity_type = entity.get("type", "OTHER")
        
        entity_key = f"{entity_type}:{name}"
        
        if entity_key not in self.entity_map:
            entity_id = f"E{self.entity_id_counter:06d}"
            self.entity_map[entity_key] = entity_id
            self.entity_id_counter += 1
            
            self.all_entities[entity_id] = {
                "id": entity_id,
                "name": name,
                "type": entity_type,
                "description": entity.get("description", ""),
                "aliases": entity.get("aliases", []),
                "sources": []
            }
        
        return self.entity_map[entity_key]
    
    def process_chunk(self, chunk: Dict) -> bool:
        """处理单个块"""
        try:
            result = self.extract_with_llm(chunk)
            
            for entity in result.get("entities", []):
                entity_id = self._register_entity(entity)
                self.all_entities[entity_id]["sources"].append({
                    "chapter": chunk["chapter"],
                    "chunk": chunk["chunk_num"],
                    "title": chunk["title"]
                })
            
            for rel in result.get("relations", []):
                subj_id = None
                for entity_key, eid in self.entity_map.items():
                    if entity_key.endswith(f":{rel['subject']}"):
                        subj_id = eid
                        break
                
                obj_id = None
                for entity_key, eid in self.entity_map.items():
                    if entity_key.endswith(f":{rel['object']}"):
                        obj_id = eid
                        break
                
                if subj_id and obj_id:
                    self.all_relations.append({
                        "id": f"R{len(self.all_relations):06d}",
                        "subject_id": subj_id,
                        "subject_name": rel["subject"],
                        "predicate": rel["predicate"],
                        "object_id": obj_id,
                        "object_name": rel["object"],
                        "evidence": rel.get("evidence", ""),
                        "source": {
                            "chapter": chunk["chapter"],
                            "chunk": chunk["chunk_num"],
                            "title": chunk["title"]
                        }
                    })
            
            for event in result.get("events", []):
                self.all_events.append({
                    "id": f"EV{len(self.all_events):06d}",
                    **event,
                    "source": {
                        "chapter": chunk["chapter"],
                        "chunk": chunk["chunk_num"],
                        "title": chunk["title"]
                    }
                })
            
            self.stats["processed_chunks"] += 1
            return True
            
        except Exception as e:
            print(f"处理块 {chunk['chapter']}-{chunk['chunk_num']} 时出错: {str(e)}")
            self.stats["failed_chunks"] += 1
            return False
    
    def process_file(self, file_path: str, max_chunks: int = None) -> Dict:
        """处理整个文件"""
        print(f"\n开始处理文件: {file_path}")
        
        try:
            chunks = self.load_and_split_file(file_path)
            
            if max_chunks:
                chunks = chunks[:max_chunks]
                print(f"只处理前 {max_chunks} 个块（测试模式）")
            
            print("\n开始提取信息...")
            for i, chunk in enumerate(chunks):
                try:
                    if (i + 1) % 10 == 0:
                        print(f"已处理 {i+1}/{len(chunks)} 个块，"
                              f"提取到 {len(self.all_entities)} 个实体，"
                              f"{len(self.all_relations)} 个关系")
                    
                    success = self.process_chunk(chunk)
                    
                    if (i + 1) % 10 == 0 and success:
                        self.save_intermediate_results()
                    
                    # 增强API调用控制
                    if self.use_api:
                        if (i + 1) % 5 == 0:  # 每5个块休息一下
                            time.sleep(2)
                        if (i + 1) % 50 == 0:  # 每50个块长休息
                            print("休息10秒避免API限制...")
                            time.sleep(10)
                    
                    # 内存管理：每100个块清理一次
                    if (i + 1) % 100 == 0:
                        import gc
                        gc.collect()
                        print("已执行内存清理")
                        
                except Exception as e:
                    print(f"处理块 {i+1} 时出现严重错误: {str(e)}")
                    print("跳过此块，继续处理下一个...")
                    self.stats["failed_chunks"] += 1
                    continue
            
            final_results = self.save_results()
            self.print_statistics()
            
            return final_results
            
        except Exception as e:
            print(f"处理文件时出现严重错误: {str(e)}")
            # 尝试保存已处理的结果
            try:
                self.save_intermediate_results()
                print("已保存当前进度")
            except:
                print("无法保存进度")
            raise
    
    def save_intermediate_results(self):
        """保存中间结果"""
        temp_data = {
            "entities": self.all_entities,
            "relations": self.all_relations,
            "events": self.all_events,
            "stats": self.stats,
            "entity_map": self.entity_map
        }
        
        timestamp = time.strftime("%Y%m%d_%H%M%S")
        temp_file = f"temp/checkpoint_{timestamp}.json"
        
        with open(temp_file, 'w', encoding='utf-8') as f:
            json.dump(temp_data, f, ensure_ascii=False, indent=2)
        
        print(f"✓ 已保存检查点到: {temp_file}")
    
    def save_results(self) -> Dict:
        """保存最终结果"""
        print("\n保存结果...")
        
        results = {
            "metadata": {
                "generated_at": time.strftime("%Y-%m-%d %H:%M:%S"),
                "total_chunks": self.stats["total_chunks"],
                "processed_chunks": self.stats["processed_chunks"],
                "api_calls": self.stats["api_calls"],
                "total_entities": len(self.all_entities),
                "total_relations": len(self.all_relations),
                "total_events": len(self.all_events)
            },
            "entities": self.all_entities,
            "relations": self.all_relations,
            "events": self.all_events
        }
        
        json_file = "output/knowledge_graph.json"
        with open(json_file, 'w', encoding='utf-8') as f:
            json.dump(results, f, ensure_ascii=False, indent=2)
        print(f"✓ 已保存完整数据到: {json_file}")
        
        self.save_as_csv()
        
        return results
    
    def save_as_csv(self):
        """保存为CSV文件"""
        # 实体CSV
        entities_data = []
        for eid, entity in self.all_entities.items():
            entities_data.append({
                "id": eid,
                "name": entity["name"],
                "type": entity["type"],
                "description": entity["description"],
                "aliases": "; ".join(entity["aliases"]),
                "source_count": len(entity["sources"])
            })
        
        if entities_data:
            df_entities = pd.DataFrame(entities_data)
            df_entities.to_csv("output/entities.csv", index=False, encoding='utf-8-sig')
            print(f"✓ 已保存实体数据: {len(df_entities)} 行")
        
        # 关系CSV
        if self.all_relations:
            relations_data = []
            for rel in self.all_relations:
                relations_data.append({
                    "id": rel["id"],
                    "subject_id": rel["subject_id"],
                    "subject_name": rel["subject_name"],
                    "predicate": rel["predicate"],
                    "object_id": rel["object_id"],
                    "object_name": rel["object_name"],
                    "evidence": rel["evidence"][:100] if rel["evidence"] else "",
                    "source": f"{rel['source']['chapter']}-{rel['source']['chunk']}"
                })
            
            df_relations = pd.DataFrame(relations_data)
            df_relations.to_csv("output/relations.csv", index=False, encoding='utf-8-sig')
            print(f"✓ 已保存关系数据: {len(df_relations)} 行")
        
        # 事件CSV
        if self.all_events:
            events_data = []
            for event in self.all_events:
                events_data.append({
                    "id": event["id"],
                    "name": event.get("name", ""),
                    "participants": "; ".join(event.get("participants", [])),
                    "time": event.get("time", ""),
                    "location": event.get("location", ""),
                    "description": event.get("description", "")[:200],
                    "source": f"{event['source']['chapter']}-{event['source']['chunk']}"
                })
            
            df_events = pd.DataFrame(events_data)
            df_events.to_csv("output/events.csv", index=False, encoding='utf-8-sig')
            print(f"✓ 已保存事件数据: {len(df_events)} 行")
    
    def print_statistics(self):
        """打印统计信息"""
        print("\n" + "="*50)
        print("处理统计")
        print("="*50)
        print(f"总块数: {self.stats['total_chunks']}")
        print(f"成功处理: {self.stats['processed_chunks']}")
        print(f"失败块数: {self.stats['failed_chunks']}")
        print(f"API调用次数: {self.stats['api_calls']}")
        print(f"提取实体数: {len(self.all_entities)}")
        print(f"提取关系数: {len(self.all_relations)}")
        print(f"提取事件数: {len(self.all_events)}")
        print("\n实体类型分布:")
        
        type_counts = {}
        for entity in self.all_entities.values():
            etype = entity["type"]
            type_counts[etype] = type_counts.get(etype, 0) + 1
        
        for etype, count in sorted(type_counts.items(), key=lambda x: x[1], reverse=True):
            print(f"  {etype}: {count}")
        
        print("\n关系类型分布:")
        predicate_counts = {}
        for rel in self.all_relations:
            pred = rel["predicate"]
            predicate_counts[pred] = predicate_counts.get(pred, 0) + 1
        
        for pred, count in sorted(predicate_counts.items(), key=lambda x: x[1], reverse=True):
            print(f"  {pred}: {count}")
        print("="*50)

def main():
    """主函数"""
    import argparse
    
    parser = argparse.ArgumentParser(description="书法史知识图谱构建工具")
    parser.add_argument("--file", type=str, default="calligraphy_history.md", 
                       help="输入MD文件路径")
    parser.add_argument("--test", type=int, default=0, 
                       help="测试模式，只处理前N个块")
    parser.add_argument("--no-api", action="store_true", 
                       help="不使用API，仅用规则提取")
    
    args = parser.parse_args()
    
    # 获取API密钥
    try:
        from config import DASHSCOPE_API_KEY
        api_key = None if args.no_api else DASHSCOPE_API_KEY
    except ImportError:
        api_key = None
        if not args.no_api:
            print("警告: 无法从config.py导入DASHSCOPE_API_KEY")
            print("将使用规则提取模式")
            args.no_api = True
    
    if not api_key and not args.no_api:
        print("错误: 未设置API密钥！")
        print("请编辑 config.py 文件，设置 DASHSCOPE_API_KEY")
        print("或使用 --no-api 参数仅使用规则提取")
        return
    
    # 检查文件是否存在
    if not os.path.exists(args.file):
        print(f"错误: 文件 {args.file} 不存在！")
        print("请确保您的MD文件在当前目录，并命名为 calligraphy_history.md")
        return
    
    # 创建构建器
    builder = CalligraphyKGBuilder(api_key=api_key)
    
    # 处理文件
    max_chunks = args.test if args.test > 0 else None
    builder.process_file(args.file, max_chunks)
    
    print("\n处理完成！结果保存在 output/ 目录中")

if __name__ == "__main__":
    main()
# kg_builder_batch.py
import re
import json
import os
import time
from typing import List, Dict, Any
import pandas as pd
from tqdm import tqdm
import dashscope
from http import HTTPStatus
from config import DASHSCOPE_API_KEY

print("=== 知识图谱构建器 - 批处理优化版 ===")
print("带进度条、自动重试、分批保存")

class BatchKGBuilder:
    def __init__(self, api_key: str = DASHSCOPE_API_KEY, batch_size: int = 20):
        """初始化构建器"""
        print("初始化批处理构建器...")
        
        # 设置DashScope API
        dashscope.api_key = api_key
        self.use_api = True
        self.model_name = "qwen-max"
        
        # 批处理设置
        self.batch_size = batch_size
        self.current_batch = 1
        
        # 存储结果
        self.all_entities = {}
        self.all_relations = []
        self.all_events = []
        
        # 统计信息
        self.stats = {
            "total_chunks": 0,
            "processed_chunks": 0,
            "success_chunks": 0,
            "failed_chunks": 0,
            "api_calls": 0,
            "json_parse_errors": 0,
            "api_errors": 0
        }
        
        # 实体映射
        self.entity_map = {}
        self.entity_id_counter = 1
        
        # 创建输出目录
        os.makedirs("batch_output", exist_ok=True)
        os.makedirs("batch_output/batches", exist_ok=True)
        os.makedirs("batch_output/checkpoints", exist_ok=True)
        
        print(f"批大小: {batch_size} 个块")
        print(f"输出目录: batch_output/")
    
    def extract_json_safely(self, text: str, max_attempts: int = 5) -> Dict:
        """安全提取JSON，多种方法尝试"""
        if not text.strip():
            return {"triples": []}
        
        attempts = [
            # 方法1: 直接解析
            lambda t: json.loads(t),
            
            # 方法2: 提取```json块
            lambda t: json.loads(t.split("```json")[1].split("```")[0]),
            
            # 方法3: 提取```块
            lambda t: json.loads(t.split("```")[1].split("```")[0]),
            
            # 方法4: 查找第一个{和最后一个}
            lambda t: json.loads(t[t.find("{"):t.rfind("}")+1]),
            
            # 方法5: 正则提取
            lambda t: json.loads(re.search(r'\{.*\}', t, re.DOTALL).group()),
        ]
        
        for attempt_func in attempts:
            try:
                return attempt_func(text)
            except:
                continue
        
        # 如果所有方法都失败，尝试清理文本
        try:
            # 去除可能的非JSON字符
            lines = text.strip().split('\n')
            json_lines = []
            in_json = False
            
            for line in lines:
                line = line.strip()
                if line.startswith('{') or line.startswith('['):
                    in_json = True
                if in_json:
                    json_lines.append(line)
                if line.endswith('}') or line.endswith(']'):
                    in_json = False
            
            json_text = '\n'.join(json_lines)
            if json_text:
                return json.loads(json_text)
        except:
            pass
        
        return {"triples": []}
    
    def extract_with_llm_safe(self, chunk: Dict, max_retries: int = 3) -> Dict:
        """安全提取信息，带重试和错误处理"""
        if not self.use_api:
            return self._fallback_extraction(chunk["content"])
        
        # 创建更严格的提示词
        prompt = f"""请从以下文本中提取中国古代书画家信息，只输出JSON格式，不要任何其他文字。

文本（第{chunk['chunk_num']}部分）：
{chunk['content'][:800]}

请提取以下关系：
- 师承：A师从B
- 擅长：A擅长B
- 籍贯：A是B人
- 官职：A任B
- 评价：A被评价为B
- 著作：A著B
- 朝代：A是B朝人
- 同门：A与B同师
- 交游：A与B友善

如果没有信息，输出：{{"triples": []}}

必须输出纯JSON，格式：
{{"triples": [{{"subject": "", "predicate": "", "object": ""}}]}}"""
        
        for attempt in range(max_retries):
            try:
                response = dashscope.Generation.call(
                    model=self.model_name,
                    prompt=prompt,
                    seed=123 + attempt,  # 不同重试使用不同种子
                    result_format='message',
                    max_tokens=1000,
                    temperature=0.1
                )
                
                self.stats["api_calls"] += 1
                
                if response.status_code == HTTPStatus.OK:
                    result_text = response.output.choices[0].message.content
                    
                    # 安全提取JSON
                    result = self.extract_json_safely(result_text)
                    
                    # 验证格式
                    if "triples" in result and isinstance(result["triples"], list):
                        return result
                    else:
                        print(f"  块{chunk['chunk_num']}-重试{attempt+1}: 格式不正确")
                        self.stats["json_parse_errors"] += 1
                        
                else:
                    print(f"  块{chunk['chunk_num']}-重试{attempt+1}: API失败 {response.code}")
                    self.stats["api_errors"] += 1
                    
            except Exception as e:
                print(f"  块{chunk['chunk_num']}-重试{attempt+1}: 异常 {str(e)[:50]}")
            
            # 重试前等待
            if attempt < max_retries - 1:
                wait_time = 2 ** attempt
                print(f"  等待{wait_time}秒后重试...")
                time.sleep(wait_time)
        
        # 所有重试都失败
        self.stats["failed_chunks"] += 1
        return {"triples": []}
    
    def process_batch(self, chunks: List[Dict], batch_num: int) -> bool:
        """处理一个批次"""
        print(f"\n处理批次 {batch_num} ({len(chunks)} 个块)...")
        
        batch_entities = {}
        batch_relations = []
        batch_events = []
        
        # 使用进度条
        for chunk in tqdm(chunks, desc=f"批次{batch_num}"):
            try:
                result = self.extract_with_llm_safe(chunk)
                self.stats["processed_chunks"] += 1
                
                if result.get("triples"):
                    self.stats["success_chunks"] += 1
                    
                    # 处理实体
                    for triple in result["triples"]:
                        # 注册主语实体
                        subj = triple["subject"]
                        if subj and subj not in self.entity_map:
                            entity_id = f"E{self.entity_id_counter:06d}"
                            self.entity_map[subj] = entity_id
                            self.entity_id_counter += 1
                            
                            batch_entities[entity_id] = {
                            "id": entity_id,
                            "name": subj,
                            "type": "PERSON",
                            "sources": [{
                                "chunk": chunk["chunk_num"],
                                "title": chunk["title"]
                            }]
                        }
                        
                        # 注册宾语实体
                        obj = triple["object"]
                        if obj and obj not in self.entity_map:
                            # 判断宾语类型
                            obj_type = "OTHER"
                            if any(marker in obj for marker in ["书", "篆", "隶", "楷", "草", "行"]):
                                obj_type = "SCRIPT_STYLE"
                            elif "《" in obj and "》" in obj:
                                obj_type = "WORK"
                            elif any(dynasty in obj for dynasty in ["秦", "汉", "唐", "宋", "元", "明", "清"]):
                                obj_type = "TIME"
                            
                            entity_id = f"E{self.entity_id_counter:06d}"
                            self.entity_map[obj] = entity_id
                            self.entity_id_counter += 1
                            
                            batch_entities[entity_id] = {
                                "id": entity_id,
                                "name": obj,
                                "type": obj_type,
                                "sources": []
                            }
                        
                        # 添加关系
                        batch_relations.append({
                            "id": f"R{len(self.all_relations) + len(batch_relations):06d}",
                            "subject": subj,
                            "subject_id": self.entity_map.get(subj),
                            "predicate": triple["predicate"],
                            "object": obj,
                            "object_id": self.entity_map.get(obj),
                            "source": {
                                "chunk": chunk["chunk_num"],
                                "title": chunk["title"]
                            }
                        })
                
            except Exception as e:
                print(f"处理块 {chunk['chunk_num']} 时出错: {str(e)[:50]}")
                self.stats["failed_chunks"] += 1
        
        # 合并结果
        self.all_entities.update(batch_entities)
        self.all_relations.extend(batch_relations)
        self.all_events.extend(batch_events)
        
        # 保存批次结果
        self.save_batch_results(batch_num, batch_entities, batch_relations)
        
        return len(batch_entities) > 0 or len(batch_relations) > 0
    
    def save_batch_results(self, batch_num: int, entities: Dict, relations: List):
        """保存批次结果"""
        batch_file = f"batch_output/batches/batch_{batch_num:03d}.json"
        
        batch_data = {
            "batch": batch_num,
            "entities": entities,
            "relations": relations,
            "stats": {
                "entities_count": len(entities),
                "relations_count": len(relations)
            }
        }
        
        with open(batch_file, 'w', encoding='utf-8') as f:
            json.dump(batch_data, f, ensure_ascii=False, indent=2)
        
        print(f"  批次{batch_num}结果已保存: {batch_file}")
        
        # 保存检查点
        self.save_checkpoint()
    
    def save_checkpoint(self):
        """保存检查点"""
        checkpoint_file = f"batch_output/checkpoints/checkpoint_{self.current_batch:03d}.json"
        
        checkpoint_data = {
            "current_batch": self.current_batch,
            "stats": self.stats,
            "total_entities": len(self.all_entities),
            "total_relations": len(self.all_relations)
        }
        
        with open(checkpoint_file, 'w', encoding='utf-8') as f:
            json.dump(checkpoint_data, f, ensure_ascii=False, indent=2)
    
    def process_file(self, file_path: str, start_batch: int = 1, max_batches: int = None):
        """处理文件（分批）"""
        print(f"处理文件: {file_path}")
        
        # 加载文件
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # 简单分块（每1500字符一个块）
        chunk_size = 1500
        chunks = []
        
        for i in range(0, len(content), chunk_size):
            chunks.append({
                "chunk_num": len(chunks) + 1,
                "content": content[i:i+chunk_size],
                "title": f"第{len(chunks) + 1}块"
            })
        
        self.stats["total_chunks"] = len(chunks)
        print(f"文件大小: {len(content):,} 字符")
        print(f"分割为: {len(chunks)} 个块")
        print(f"批大小: {self.batch_size} 个块/批")
        print(f"总批次数: {len(chunks) // self.batch_size + 1}")
        
        # 分批
        all_batches = [chunks[i:i+self.batch_size] for i in range(0, len(chunks), self.batch_size)]
        
        if max_batches:
            all_batches = all_batches[:max_batches]
        
        print(f"将处理 {len(all_batches)} 个批次")
        
        # 从指定批次开始
        if start_batch > 1:
            print(f"从批次 {start_batch} 开始")
            all_batches = all_batches[start_batch-1:]
        
        # 处理每个批次
        for batch_num, batch_chunks in enumerate(all_batches, start_batch):
            self.current_batch = batch_num
            print(f"\n{'='*60}")
            print(f"开始处理批次 {batch_num}/{len(all_batches) + start_batch - 1}")
            
            success = self.process_batch(batch_chunks, batch_num)
            
            if success:
                print(f"批次 {batch_num} 处理成功")
            else:
                print(f"批次 {batch_num} 处理失败或无数据")
            
            # 批次间暂停
            if batch_num < len(all_batches) + start_batch - 1:
                print("批次间暂停5秒...")
                time.sleep(5)
        
        # 保存最终结果
        self.save_final_results()
        
        # 打印统计
        self.print_statistics()
    
    def save_final_results(self):
        """保存最终结果"""
        print(f"\n保存最终结果...")
        
        # 合并所有批次
        all_batch_files = sorted([f for f in os.listdir("batch_output/batches") if f.endswith('.json')])
        
        merged_entities = {}
        merged_relations = []
        
        for batch_file in all_batch_files:
            batch_path = f"batch_output/batches/{batch_file}"
            with open(batch_path, 'r', encoding='utf-8') as f:
                batch_data = json.load(f)
            
            merged_entities.update(batch_data.get("entities", {}))
            merged_relations.extend(batch_data.get("relations", []))
        
        # 保存为JSON
        final_json = {
            "metadata": {
                "generated_at": time.strftime("%Y-%m-%d %H:%M:%S"),
                "total_batches": self.current_batch,
                "total_entities": len(merged_entities),
                "total_relations": len(merged_relations)
            },
            "entities": merged_entities,
            "relations": merged_relations
        }
        
        with open("batch_output/final_knowledge_graph.json", 'w', encoding='utf-8') as f:
            json.dump(final_json, f, ensure_ascii=False, indent=2)
        
        # 保存为CSV
        if merged_entities:
            entities_list = []
            for eid, entity in merged_entities.items():
                entities_list.append({
                    "id": eid,
                    "name": entity["name"],
                    "type": entity["type"],
                    "source_count": len(entity.get("sources", []))
                })
            
            df_entities = pd.DataFrame(entities_list)
            df_entities.to_csv("batch_output/entities.csv", index=False, encoding='utf-8-sig')
        
        if merged_relations:
            relations_list = []
            for rel in merged_relations:
                relations_list.append({
                    "id": rel["id"],
                    "subject": rel["subject"],
                    "predicate": rel["predicate"],
                    "object": rel["object"]
                })
            
            df_relations = pd.DataFrame(relations_list)
            df_relations.to_csv("batch_output/relations.csv", index=False, encoding='utf-8-sig')
        
        print(f"最终结果已保存到 batch_output/")
    
    def print_statistics(self):
        """打印统计信息"""
        print(f"\n{'='*60}")
        print("处理统计")
        print(f"{'='*60}")
        print(f"总块数: {self.stats['total_chunks']}")
        print(f"已处理: {self.stats['processed_chunks']}")
        print(f"成功块数: {self.stats['success_chunks']}")
        print(f"失败块数: {self.stats['failed_chunks']}")
        print(f"API调用次数: {self.stats['api_calls']}")
        print(f"JSON解析错误: {self.stats['json_parse_errors']}")
        print(f"API错误: {self.stats['api_errors']}")
        print(f"总实体数: {len(self.all_entities)}")
        print(f"总关系数: {len(self.all_relations)}")
        print(f"{'='*60}")

def main():
    """主函数"""
    import argparse
    
    parser = argparse.ArgumentParser(description="知识图谱构建器 - 批处理版")
    parser.add_argument("--file", type=str, default="calligraphy_history.md", 
                       help="输入MD文件路径")
    parser.add_argument("--batch-size", type=int, default=20, 
                       help="每批处理块数")
    parser.add_argument("--start-batch", type=int, default=1, 
                       help="起始批次（用于恢复）")
    parser.add_argument("--max-batches", type=int, default=None, 
                       help="最大批次数（用于测试）")
    parser.add_argument("--test", action="store_true", 
                       help="测试模式（只处理1批）")
    
    args = parser.parse_args()
    
    if not os.path.exists(args.file):
        print(f"错误: 文件 {args.file} 不存在！")
        return
    
    if args.test:
        args.max_batches = 1
        print("测试模式：只处理1批")
    
    # 创建构建器
    builder = BatchKGBuilder(
        api_key=DASHSCOPE_API_KEY,
        batch_size=args.batch_size
    )
    
    # 处理文件
    builder.process_file(
        file_path=args.file,
        start_batch=args.start_batch,
        max_batches=args.max_batches
    )

if __name__ == "__main__":
    main()

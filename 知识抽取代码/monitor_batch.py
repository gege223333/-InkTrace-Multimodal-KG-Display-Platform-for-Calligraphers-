# monitor_batch.py
import os
import json
import time
from datetime import datetime

def monitor_batch():
    """监控批处理进度"""
    print("批处理进度监控")
    print("按Ctrl+C停止监控")
    
    try:
        while True:
            os.system('cls' if os.name == 'nt' else 'clear')
            print(f"监控时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
            print("="*60)
            
            # 检查输出目录
            if os.path.exists("batch_output"):
                # 检查批次文件
                batch_dir = "batch_output/batches"
                if os.path.exists(batch_dir):
                    batch_files = [f for f in os.listdir(batch_dir) if f.endswith('.json')]
                    print(f"已完成批次: {len(batch_files)}")
                    
                    if batch_files:
                        # 显示最新批次
                        latest = sorted(batch_files)[-1]
                        with open(f"{batch_dir}/{latest}", 'r', encoding='utf-8') as f:
                            batch_data = json.load(f)
                        print(f"最新批次: {batch_data.get('batch', '?')}")
                        print(f"实体数: {batch_data.get('stats', {}).get('entities_count', 0)}")
                        print(f"关系数: {batch_data.get('stats', {}).get('relations_count', 0)}")
                
                # 检查检查点
                checkpoint_dir = "batch_output/checkpoints"
                if os.path.exists(checkpoint_dir):
                    checkpoints = [f for f in os.listdir(checkpoint_dir) if f.endswith('.json')]
                    if checkpoints:
                        latest_checkpoint = sorted(checkpoints)[-1]
                        with open(f"{checkpoint_dir}/{latest_checkpoint}", 'r', encoding='utf-8') as f:
                            cp_data = json.load(f)
                        print(f"\n检查点信息:")
                        print(f"当前批次: {cp_data.get('current_batch', '?')}")
                        print(f"总实体: {cp_data.get('total_entities', 0)}")
                        print(f"总关系: {cp_data.get('total_relations', 0)}")
            
            print("\n" + "="*60)
            print("监控中... (每30秒刷新)")
            time.sleep(30)
            
    except KeyboardInterrupt:
        print("\n监控已停止")

if __name__ == "__main__":
    monitor_batch()

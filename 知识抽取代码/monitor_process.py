# monitor_process.py
import os
import time
import subprocess
from datetime import datetime

print("开始完整处理，时间:", datetime.now().strftime("%Y-%m-%d %H:%M:%S"))

# 运行主程序
process = subprocess.Popen(["python", "kg_builder.py"], 
                          stdout=subprocess.PIPE, 
                          stderr=subprocess.PIPE,
                          universal_newlines=True)

# 监控进度
try:
    while True:
        output = process.stdout.readline()
        if output:
            print(output.strip())
        
        # 检查是否结束
        if process.poll() is not None:
            break
            
        # 每10秒检查一次输出目录
        time.sleep(10)
        if os.path.exists("output"):
            files = os.listdir("output")
            if files:
                print(f"进度: output目录中有 {len(files)} 个文件")
                
except KeyboardInterrupt:
    print("检测到中断信号，终止处理...")
    process.terminate()

print("处理结束，时间:", datetime.now().strftime("%Y-%m-%d %H:%M:%S"))

print("检查已安装的包...")
import subprocess
import sys
result = subprocess.run([sys.executable, "-m", "pip", "list"], capture_output=True, text=True)
packages = result.stdout# 检查关键包
required = ["spacy", "dashscope", "pandas", "tqdm", "regex"]
installed = []

for package in required:
    if package in packages.lower():
        installed.append(package)
        print(f"✓ {package} 已安装")
    else:
        print(f"✗ {package} 未安装")

print(f"\n已安装 {len(installed)}/{len(required)} 个必要包")
if len(installed) < len(required):
    print("\n请运行: pip install spacy dashscope pandas tqdm regex")

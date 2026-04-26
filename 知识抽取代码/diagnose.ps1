Write-Host "=== Python环境诊断 ===" -ForegroundColor Yellow

# 1. 检查当前目录
$currentDir = Get-Location
Write-Host "当前目录: $currentDir"

# 2. 检查虚拟环境Python
$venvPython = "venv\Scripts\python.exe"
if (Test-Path $venvPython) {
    Write-Host "✓ 虚拟环境Python存在: $venvPython" -ForegroundColor Green
    
    # 获取版本
    $version = & $venvPython --version
    Write-Host "  版本: $version"
} else {
    Write-Host "✗ 虚拟环境Python不存在" -ForegroundColor Red
}

# 3. 检查python命令
Write-Host "`n检查python命令:" -ForegroundColor Cyan
$pythonCmd = Get-Command python -ErrorAction SilentlyContinue
if ($pythonCmd) {
    Write-Host "  python命令路径: $($pythonCmd.Source)" -ForegroundColor Cyan
    
    # 检查是否指向虚拟环境
    if ($pythonCmd.Source -like "*\calligraphy_knowledge_graph\venv\*") {
        Write-Host "  ✓ python命令指向虚拟环境" -ForegroundColor Green
    } else {
        Write-Host "  ✗ python命令指向: $($pythonCmd.Source)" -ForegroundColor Red
        Write-Host "  这可能是Windows应用商店的Python" -ForegroundColor Yellow
    }
} else {
    Write-Host "  ✗ 未找到python命令" -ForegroundColor Red
}

# 4. 检查kg_builder.py
Write-Host "`n检查kg_builder.py:" -ForegroundColor Cyan
if (Test-Path "kg_builder.py") {
    $size = (Get-Item "kg_builder.py").Length
    Write-Host "  ✓ kg_builder.py存在 ($size 字节)" -ForegroundColor Green
} else {
    Write-Host "  ✗ kg_builder.py不存在" -ForegroundColor Red
    Write-Host "  当前目录中的.py文件:" -ForegroundColor Yellow
    Get-ChildItem *.py | ForEach-Object { Write-Host "    - $($_.Name)" }
}

# 5. 建议
Write-Host "`n建议:" -ForegroundColor Yellow
if (Test-Path $venvPython) {
    Write-Host "  使用完整路径运行: .\venv\Scripts\python.exe kg_builder.py --test 5" -ForegroundColor Green
} else {
    Write-Host "  虚拟环境可能已损坏，请重新创建" -ForegroundColor Red
}

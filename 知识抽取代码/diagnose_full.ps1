Write-Host "=== 诊断知识图谱构建器 ===" -ForegroundColor Yellow

# 1. 检查Python
Write-Host "`n1. 检查Python环境..." -ForegroundColor Cyan
python --version
python -c "import sys; print(f'Python路径: {sys.executable}')"

# 2. 检查必要的包
Write-Host "`n2. 检查Python包..." -ForegroundColor Cyan
$packages = @("spacy", "dashscope", "pandas", "tqdm", "regex")
foreach ($pkg in $packages) {
    python -c "
try:
    import $pkg
    print('  ✓ ' + '$pkg' + ' 已安装')
except:
    print('  ✗ ' + '$pkg' + ' 未安装')
"
}

# 3. 检查文件
Write-Host "`n3. 检查文件..." -ForegroundColor Cyan
$requiredFiles = @("kg_builder.py", "config.py", "calligraphy_history.md")
foreach ($file in $requiredFiles) {
    if (Test-Path $file) {
        $size = (Get-Item $file).Length
        if ($size -gt 0) {
            Write-Host "  ✓ $file 存在 ($size 字节)" -ForegroundColor Green
        } else {
            Write-Host "  ✗ $file 存在但为空" -ForegroundColor Red
        }
    } else {
        Write-Host "  ✗ $file 不存在" -ForegroundColor Red
    }
}

# 4. 检查config.py内容
Write-Host "`n4. 检查config.py..." -ForegroundColor Cyan
if (Test-Path "config.py") {
    Get-Content config.py -TotalCount 10
}

# 5. 运行简单测试
Write-Host "`n5. 运行简单测试..." -ForegroundColor Cyan
python -c "
print('开始测试...')
try:
    from kg_builder import CalligraphyKGBuilder
    print('  ✓ 可以导入CalligraphyKGBuilder')
    
    builder = CalligraphyKGBuilder(api_key='sk-dc88cc36272a48618bba279b040f7160')
    print('  ✓ 可以创建构建器实例')
    
    # 检查dashscope
    import dashscope
    dashscope.api_key = 'sk-dc88cc36272a48618bba279b040f7160'
    print('  ✓ dashscope配置成功')
    
    print('测试通过！')
    
except Exception as e:
    print(f'  ✗ 测试失败: {e}')
    import traceback
    traceback.print_exc()
"

Write-Host "`n诊断完成！" -ForegroundColor Yellow

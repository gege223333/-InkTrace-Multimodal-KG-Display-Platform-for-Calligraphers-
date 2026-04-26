// frontend/components/search.js

export const initSearch = (onSearch, onUpload) => {
    // 1. 获取DOM
    const searchBtn = document.getElementById('search-btn');
    const searchInput = document.getElementById('search-input');
    const uploadBtn = document.getElementById('upload-btn');
    const fileInput = document.getElementById('file-input');
    const typeBtns = document.querySelectorAll('.search-type-btn');

    // 严谨检查
    if (!searchBtn || !searchInput || !uploadBtn || !fileInput || typeBtns.length === 0) {
        console.error("搜索组件元素获取失败，请检查HTML");
        return;
    }

    let currentType = 'calligrapher'; // 默认搜书法家

    // 2. 搜索类型切换逻辑
    typeBtns.forEach(btn => {
        btn.addEventListener('click', () => {
            // 移除旧active，添加新active
            typeBtns.forEach(b => b.classList.remove('active'));
            btn.classList.add('active');
            
            currentType = btn.dataset.type;
            
            // 3. 动态占位符切换 (实现你想要的功能)
            searchInput.placeholder = currentType === 'calligrapher' ? '输入书法家姓名...' : '输入汉字或作品名称...';
            console.log("搜索模式切换为:", currentType);
        });
    });

    // 4. 搜索触发函数
    const doSearch = () => {
        const val = searchInput.value.trim();
        if (val) {
            onSearch({ keyword: val, type: currentType });
        } else {
            alert('请输入搜索关键词');
        }
    };

    searchBtn.addEventListener('click', doSearch);
    searchInput.addEventListener('keypress', (e) => e.key === 'Enter' && doSearch());

    // 5. 图片上传触发
    uploadBtn.addEventListener('click', () => fileInput.click());
    fileInput.addEventListener('change', (e) => {
        const file = e.target.files[0];
        if (file) {
            if (!file.type.startsWith('image/')) {
                alert('请上传图片文件');
                return;
            }
            onUpload(file); // 调用 main.js 的回调
        }
    });

    console.log("搜索组件 JS 逻辑初始化完成。");
};
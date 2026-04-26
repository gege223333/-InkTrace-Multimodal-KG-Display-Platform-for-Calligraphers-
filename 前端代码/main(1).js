// 修复后的完整main.js代码
// 核心逻辑控制中心
// 整合了：ECharts初始化、数据加载、搜索过滤、AI上传识别、面板交互

// 全局变量存储图谱实例
let chart = null;
let fullNodes = [];
let fullLinks = [];
// 存储原始数据
let originalData = null;
let completeData = null; // 保存完整的数据集
// 当前选中的节点ID
let selectedNodeId = null;
// 节点点击历史记录
let nodeHistory = [];



// 当前分页信息
let currentPage = 1;
const pageSize = 100;
let totalPages = 0;

// 搜索状态标志
let isSearchMode = false;
// 汉字搜索状态标志
let isCharacterSearchMode = false;
// 面板互斥锁，防止多个面板同时显示
let panelLock = false;
// 当前激活的面板类型
let activePanel = null; // 'character' | 'painter' | null

// 完全独立的系统标志
let characterSystemActive = false;  // 汉字系统专用
let nodeSystemActive = false;        // 节点系统专用

// 性能优化：缓存机制
const cache = {
    colorMap: new Map(), // 缓存颜色计算结果
    nodeMap: new Map(), // 缓存节点数据
    linkMap: new Map() // 缓存连接数据
};

// 搜索记忆框 - sessionStorage，关闭浏览器清空，刷新不清空
function getSearchMemory(mode) {
    return JSON.parse(sessionStorage.getItem(`search_memory_${mode}`) || '[]');
}

function addToMemory(mode, query) {
    if (!query) return;
    let arr = getSearchMemory(mode);
    arr = arr.filter(item => item !== query);
    arr.unshift(query);
    if (arr.length > 3) arr = arr.slice(0, 3);
    sessionStorage.setItem(`search_memory_${mode}`, JSON.stringify(arr));
}

function renderHistoryBox(boxId, mode, inputId, onSearch) {
    const box = document.getElementById(boxId);
    const arr = getSearchMemory(mode);
    if (!box) return;
    box.innerHTML = '';
    if (arr.length === 0) {
        box.classList.remove('visible');
        return;
    }
    arr.forEach(item => {
        const div = document.createElement('div');
        div.className = 'history-item';
        div.textContent = item;
        div.addEventListener('click', () => {
            const input = document.getElementById(inputId);
            if (input) input.value = item;
            if (onSearch) onSearch(item);
            box.classList.remove('visible');
        });
        box.appendChild(div);
    });
    // 主应用记忆框：动态定位对齐搜索框
    if (boxId === 'app-search-history') {
        const input = document.getElementById(inputId);
        if (input) {
            const rect = input.getBoundingClientRect();
            box.style.position = 'fixed';
            box.style.top = (rect.bottom + 4) + 'px';
            box.style.left = rect.left + 'px';
            box.style.width = rect.width + 'px';
        }
    }
    box.classList.add('visible');
}

// 1. 页面加载完成后启动
document.addEventListener('DOMContentLoaded', function() {
    const cover = document.getElementById('cover');
    const enterBtn = document.getElementById('enter-btn');
    const landingPage = document.getElementById('landing-page');
    const app = document.getElementById('app');
    const landingSearchInput = document.getElementById('landing-search-input');
    const landingSearchBtn = document.getElementById('landing-search-btn');
    const landingTabs = document.querySelectorAll('.landing-tab');
    const landingUpload = document.getElementById('landing-upload');

    let landingSearchMode = 'calligrapher';

    // 处理封面进入按钮
    if (enterBtn && cover && landingPage) {
        enterBtn.addEventListener('click', function() {
            cover.style.opacity = '0';
            setTimeout(() => {
                cover.style.display = 'none';
                landingPage.style.display = 'flex';
            }, 800);
        });
    } else {
        // 如果没有封面，直接显示落地页
        if (landingPage) {
            landingPage.style.display = 'flex';
        }
    }

    // 首页标签切换
    const landingContent = document.querySelector('.landing-content');
    const landingHistoryBox = document.getElementById('landing-search-history');
    landingTabs.forEach(tab => {
        tab.addEventListener('click', () => {
            landingTabs.forEach(t => t.classList.remove('active'));
            tab.classList.add('active');
            landingSearchMode = tab.dataset.type;

            if (landingContent) {
                landingContent.setAttribute('data-mode', landingSearchMode);
            }

            if (landingSearchMode === 'calligrapher') {
                landingSearchInput.placeholder = '输入书画家姓名...';
                landingSearchInput.style.display = '';
                landingSearchBtn.style.display = '';
                landingSearchInput.value = '';
                renderHistoryBox('landing-search-history', 'calligrapher', 'landing-search-input');
            } else if (landingSearchMode === 'character') {
                landingSearchInput.placeholder = '输入汉字...';
                landingSearchInput.style.display = '';
                landingSearchBtn.style.display = '';
                landingSearchInput.value = '';
                renderHistoryBox('landing-search-history', 'character', 'landing-search-input');
            } else if (landingSearchMode === 'upload') {
                landingSearchInput.value = '';
                if (landingHistoryBox) landingHistoryBox.classList.remove('visible');
                landingUpload.click();
            }
        });
    });

    // 首页输入框聚焦时显示记忆框
    if (landingSearchInput) {
        landingSearchInput.addEventListener('focus', () => {
            renderHistoryBox('landing-search-history', landingSearchMode, 'landing-search-input');
        });
        landingSearchInput.addEventListener('blur', () => {
            setTimeout(() => {
                if (landingHistoryBox) landingHistoryBox.classList.remove('visible');
            }, 200);
        });
    }

    // 点击页面其他地方关闭记忆框
    document.addEventListener('click', (e) => {
        if (landingHistoryBox && !landingHistoryBox.contains(e.target) && e.target !== landingSearchInput) {
            landingHistoryBox.classList.remove('visible');
        }
    });

    // 从首页进入主应用的过渡函数
    function transitionToApp(callback) {
        if (landingPage) {
            landingPage.classList.add('fade-out');
            setTimeout(() => {
                landingPage.style.display = 'none';
            }, 500);
        }
        if (app) {
            app.style.display = 'block';
            initChart();
            loadGraphData();
            initInteractions();
        }
        // 添加历史记录，使浏览器返回按钮可以返回落地页
        history.pushState({ page: 'app' }, '', '#app');
        if (callback) callback();
    }

    // 浏览器返回按钮事件
    window.addEventListener('popstate', function(e) {
        if (app && app.style.display !== 'none') {
            // 返回到落地页
            app.style.display = 'none';
            if (landingPage) {
                landingPage.style.display = 'flex';
                landingPage.classList.remove('fade-out');
            }
            // 关闭所有面板
            closeAllPanels();
        }
    });

    // 首页搜索逻辑
    function handleLandingSearch() {
        const val = landingSearchInput.value.trim();
        if (!val) {
            alert('请输入搜索内容');
            return;
        }

        // 保存到搜索记忆框
        addToMemory(landingSearchMode, val);
        if (landingHistoryBox) landingHistoryBox.classList.remove('visible');

        // 同步首页搜索模式到主应用搜索类型按钮
        const appSearchTypeBtns = document.querySelectorAll('.search-type-btn');
        appSearchTypeBtns.forEach(btn => {
            btn.classList.remove('active');
            if (btn.dataset.type === landingSearchMode) {
                btn.classList.add('active');
            }
        });

        const appSearchInput = document.getElementById('search-input');
        if (appSearchInput) {
            appSearchInput.value = val;
            appSearchInput.placeholder = landingSearchMode === 'calligrapher' ? '输入书画家姓名...' : '输入汉字...';
        }

        if (landingSearchMode === 'calligrapher') {
            transitionToApp(() => {
                currentPage = 1;
                originalData = null;
                isSearchMode = true;
                loadGraphData(val);
            });
        } else if (landingSearchMode === 'character') {
            transitionToApp(() => {
                handleCharacterSearch(val);
            });
        }
    }

    // 保存首页搜索历史
    function saveLandingHistory(mode, query) {
        const history = JSON.parse(localStorage.getItem(`landing_history_${mode}`) || '[]');
        const filtered = history.filter(item => item !== query);
        filtered.unshift(query);
        localStorage.setItem(`landing_history_${mode}`, JSON.stringify(filtered.slice(0, 5)));
    }

    if (landingSearchBtn) {
        landingSearchBtn.addEventListener('click', function() {
            if (landingSearchMode === 'upload') {
                // 单字流派识别模式：触发文件上传
                landingUpload.click();
            } else {
                // 书画家或汉字模式：执行搜索
                handleLandingSearch();
            }
        });
    }
    if (landingSearchInput) {
        landingSearchInput.addEventListener('keypress', (e) => {
            if (e.key === 'Enter') handleLandingSearch();
        });
    }

    // 首页上传逻辑
    if (landingUpload) {
        landingUpload.addEventListener('change', async function(e) {
            const file = e.target.files[0];
            if (!file) return;

            transitionToApp();

            const formData = new FormData();
            formData.append('image', file);

            try {
                const response = await fetch('/api/ai/classify', {
                    method: 'POST',
                    body: formData
                });
                const result = await response.json();

                if (result.error) {
                    alert(result.error);
                    return;
                }

                if (result.style) {
                    closeAllPanels();
                    const aiPanel = document.getElementById('ai-panel');
                    if (aiPanel) {
                        aiPanel.classList.remove('hidden');
                        // 直接进入全屏状态
                        aiPanel.classList.add('fullscreen');
                        // 隐藏页码控件
                        hidePaginationControls();
                        setGraphContainerVisible(true);
                    }

                    const aiName = document.getElementById('ai-name');
                    const aiAllProbs = document.getElementById('ai-all-probs');
                    const aiDesc = document.getElementById('ai-desc');
                    const aiImg = document.getElementById('ai-img');
                    
                    if (aiName) aiName.innerText = "AI 识别详情";
                    if (aiImg) aiImg.src = URL.createObjectURL(file);
                    
                    // 构建AI识别结果内容
                    let aiContent = '';
                    aiContent += `<p><strong>检测到该作品流派为：</strong><span style="background: #fff7ed; color: #c2410c; padding: 4px 8px; border-radius: 4px; font-size: 12px; border: 1px solid #fdba74; font-weight: bold;">${result.style}</span></p>`;
                    aiContent += `<p><strong>置信度：</strong><span style="background: #f3f4f6; color: #374151; padding: 4px 8px; border-radius: 4px; font-size: 12px; font-weight: bold;">${result.confidence}%</span></p>`;
                    
                    if (aiDesc) {
                        aiDesc.innerHTML = aiContent;
                    }
                    
                    // 显示流派可能性
                    if (aiAllProbs) {
                        const styleOrder = ['楷', '行', '草', '隶', '篆'];
                        let probHtml = '<strong>所有流派可能性：</strong><ul>';
                        for (const style of styleOrder) {
                            if (result.all_probabilities[style] !== undefined) {
                                probHtml += '<li>' + style + ': ' + result.all_probabilities[style].toFixed(2) + '%</li>';
                            }
                        }
                        probHtml += '</ul>';
                        aiAllProbs.innerHTML = probHtml;
                        aiAllProbs.style.display = 'block';
                    }
                    
                    panelLock = true;
                    activePanel = 'ai';
                }
            } catch (error) {
                console.error("上传识别过程出错:", error);
                alert("识别过程出错，请重试");
            }
        });
    }

    // 确保页面加载时不显示单个节点
    originalData = null;
});

// 2. 初始化 ECharts
function initChart() {
    const chartDom = document.getElementById('graph-container');
    if (!chartDom) return;
    
    chart = echarts.init(chartDom);
    
    const option = {
        tooltip: {
            formatter: params => params.dataType === 'node' ? 
                `${params.data.name}<br/>${params.data.type || ''}` : ''
        },
        series: [{
            type: 'graph',
            layout: 'force',
            force: {
                repulsion: 300,
                gravity: 0.05,
                edgeLength: 120
            },
            data: [],
            links: [],
            roam: true,
            draggable: true,
            label: {
                show: true,
                position: 'right',
                color: '#333'
            },
            lineStyle: {
                color: '#ddd',
                curveness: 0.2
            },
            emphasis: {
                focus: 'adjacency',
                lineStyle: { width: 5 }
            }
        }]
    };
    
    chart.setOption(option);

    // 点击节点显示关系 - 节点系统专用
    chart.on('click', function(params) {
        if (params.dataType === 'node') {
            // 如果汉字独立系统激活，绝对不显示书画家面板
            if (characterSystemActive || isCharacterSearchMode) {
                console.log('汉字系统激活，阻止节点面板显示');
                return;
            }
            
            // 保存原始数据
            if (!originalData) {
                originalData = { nodes: [...fullNodes], links: [...fullLinks] };
            }
            
            console.log('点击节点:', params.data.name);
            
            // 保存当前节点到历史记录
            if (selectedNodeId) {
                nodeHistory.push(selectedNodeId);
                // 限制历史记录长度为10
                if (nodeHistory.length > 10) {
                    nodeHistory.shift();
                }
                // 显示返回按钮
                showBackButton();
            }
            
            // 更新选中的节点ID
            selectedNodeId = params.data.id;
            
            // 调用API获取该节点的关系数据
            fetch(`/api/graph/node/relations?node_id=${params.data.id}`)
                .then(response => response.json())
                .then(data => {
                    console.log('获取节点关系数据:', data);
                    // 更新图表显示该节点的关系
                    updateChart(data);
                    // 显示书画家面板
                    showPainterPanel(params.data);
                })
                .catch(error => {
                    console.error('获取节点关系失败:', error);
                    // 显示书画家面板
                    showPainterPanel(params.data);
                });
        }
    });
    
    // 初始化完成后自动缩放到适合视图
    setTimeout(() => {
        // 缩放到超级小的比例，以便看到更多节点
        chart.dispatchAction({
            type: 'zoomTo',
            zoom: 0.00001,
            animation: { duration: 500, easing: 'cubicOut' }
        });
    }, 1000);
}

// 3. 加载数据
async function loadGraphData(query = '', page = 1) {
    try {
        // 首先加载完整的数据集（如果还没有加载）
        if (!completeData) {
            const fullDataResponse = await fetch('/api/graph/data');
            if (fullDataResponse.ok) {
                const fullData = await fullDataResponse.json();
                completeData = { ...fullData };
                console.log('加载了完整的数据集:', completeData);
            }
        }
        
        // 从后端API加载数据
        let apiUrl = '/api/graph/data';
        if (query) {
            // 搜索时不使用分页
            apiUrl = `/api/graph/search?q=${encodeURIComponent(query)}`;
        } else {
            // 使用分页API
            apiUrl = `/api/graph/data/page?page=${page}&size=${pageSize}`;
        }
        
        const response = await fetch(apiUrl);
        if (!response.ok) {
            throw new Error(`API请求失败: ${response.status} ${response.statusText}`);
        }
        
        const data = await response.json();
        
        if (query) {
            // 搜索结果
            originalData = { nodes: [...data.nodes], links: [...data.links] };
            fullNodes = [...data.nodes];
            fullLinks = [...data.links];
            
            // 如果搜索结果有节点，自动选中第一个节点并显示相关信息
            if (data.nodes.length > 0) {
                const firstNode = data.nodes[0];
                selectedNodeId = firstNode.id;
                
                // 保存原始数据
                if (!originalData) {
                    originalData = { nodes: [...fullNodes], links: [...fullLinks] };
                }
                
                // 调用API获取该节点的关系数据
                fetch(`/api/graph/node/relations?node_id=${firstNode.id}`)
                    .then(response => response.json())
                    .then(relationData => {
                        console.log('获取节点关系数据:', relationData);
                        // 更新图表显示该节点的关系
                        updateChart(relationData);
                        // 显示书画家面板
                        showPainterPanel(firstNode);
                    })
                    .catch(error => {
                        console.error('获取节点关系失败:', error);
                        // 显示书画家面板
                        showPainterPanel(firstNode);
                    });
            } else {
                updateChart(data);
            }
        } else {
            // 分页数据
            fullNodes = data.nodes;
            fullLinks = data.links;
            totalPages = data.total_pages;
            currentPage = data.current_page;
            
            // 保存完整的数据集（如果还没有加载）
            if (!completeData) {
                completeData = { ...data };
            }
            
            updateChart(data);
            
            // 更新分页控件
            updatePaginationControls();
        }

    } catch (error) {
            console.error('加载数据失败:', error);
            // 显示详细的错误信息
            alert(`加载数据失败: ${error.message}\n请检查后端服务是否运行`);
        }
}

// 更新分页控件
function updatePaginationControls() {
    // 在搜索模式下隐藏页码
    if (isSearchMode) {
        hidePaginationControls();
        return;
    }
    
    // 在页面上添加分页控件，如果没有的话
    let paginationContainer = document.getElementById('pagination-controls');
    if (!paginationContainer) {
        paginationContainer = document.createElement('div');
        paginationContainer.id = 'pagination-controls';
        paginationContainer.style.cssText = `
            position: fixed;
            bottom: 20px;
            left: 50%;
            transform: translateX(-50%);
            z-index: 1000;
            background: rgba(255, 255, 255, 0.4);
            padding: 10px 15px;
            border-radius: 5px;
            box-shadow: 0 2px 10px rgba(0,0,0,0.1);
            display: flex;
            align-items: center;
            gap: 8px;
        `;
        document.body.appendChild(paginationContainer);
    }
    
    // 构建分页HTML
    let paginationHTML = `
        <span style="margin-right: 10px; font-family: 'Palatino Linotype', 'Book Antiqua', Palatino, serif; color: #8d322c;">第 ${currentPage} 页，共 ${totalPages} 页</span>
        <button onclick="loadGraphData('', 1)" ${currentPage === 1 ? 'disabled' : ''} style="padding: 4px 8px; font-size: 12px; font-family: 'Palatino Linotype', 'Book Antiqua', Palatino, serif; color: #8d322c; background-color: rgba(204, 186, 170, 0.3); border-width: 1px; border-style: solid; border-color: #8d322c;">首页</button>
        <button onclick="loadGraphData('', Math.max(1, currentPage - 1))" ${currentPage === 1 ? 'disabled' : ''} style="padding: 4px 8px; font-size: 12px; font-family: 'Palatino Linotype', 'Book Antiqua', Palatino, serif; color: #8d322c; background-color: #f0eae5; border-width: 1px; border-style: solid; border-color: #8d322c;">上页</button>
        <button onclick="loadGraphData('', Math.min(totalPages, currentPage + 1))" ${currentPage === totalPages ? 'disabled' : ''} style="padding: 4px 8px; font-size: 12px; font-family: 'Palatino Linotype', 'Book Antiqua', Palatino, serif; color: #8d322c; border-width: 1px; border-style: solid; border-color: #8d322c;">下页</button>
        <button onclick="loadGraphData('', totalPages)" ${currentPage === totalPages ? 'disabled' : ''} style="padding: 4px 8px; font-size: 12px; color: #8d322c; border-width: 1px; border-style: solid; border-color: #8d322c;">末页</button>
        <input type="number" id="page-input" min="1" max="${totalPages}" value="${currentPage}" style="width: 50px; height: 24px; font-size: 12px; text-align: center; font-family: 'Palatino Linotype', 'Book Antiqua', Palatino, serif; color: #8d322c; border-width: 1px; border-style: solid; border-color: #8d322c;" />
        <button onclick="goToPage()" style="padding: 4px 8px; font-size: 12px; border-width: 1px; border-style: solid; border-color: #8d322c; color: #8d322c; font-family: 'Palatino Linotype', 'Book Antiqua', Palatino, serif;">跳转</button>
    `;
    
    paginationContainer.innerHTML = paginationHTML;
}

// 跳转到指定页面
function goToPage() {
    const pageInput = document.getElementById('page-input');
    const pageNum = parseInt(pageInput.value);
    
    if (pageNum >= 1 && pageNum <= totalPages) {
        loadGraphData('', pageNum);
    } else {
        alert(`请输入1到${totalPages}之间的页码`);
    }
}

// 根据节点类型获取颜色
function getColorByType(type) {
    // 人物节点使用特殊颜色
    if (type === '人物' || type === '书画家' || type === '人') {
        return '#8d322c'; // 红褐色，代表人物
    }
    // 其他类型节点使用不同颜色
    switch (type) {
        case '作品':
            return '#4a6b8a'; // 蓝色，代表作品
        case '流派':
            return '#2d5016'; // 绿色，代表流派
        case '朝代':
            return '#8b4513'; // 棕色，代表朝代
        default:
            return '#666666'; // 灰色，代表其他
    }
}

// 4. 更新图表渲染（优化：使用缓存提高性能）
function updateChart(data) {
    // 不限制节点数量，显示所有节点
    let renderNodes = data.nodes;
    let renderLinks = data.links;
    
    // 映射节点属性（使用缓存）
    const nodes = renderNodes.map(node => {
        const nodeKey = `node_${node.id}`;
        
        // 计算节点大小
        let nodeSize = node.size || node.symbolSize || 70;
        // 计算节点颜色
        let nodeColor = getColorByType(node.type);
        
        // 如果是选中的节点，放大成最高档的1.5倍大小，并改为更深的橙色
        if (node.id === selectedNodeId) {
            nodeSize = 90 * 1.5; // 最高档是90，1.5倍就是135
            nodeColor = '#d35400'; // 更深的橙色
        }
        
        // 检查缓存是否存在，并且缓存的大小和颜色与当前计算的一致
        if (cache.nodeMap.has(nodeKey)) {
            const cachedNode = cache.nodeMap.get(nodeKey);
            if (cachedNode.symbolSize === nodeSize && cachedNode.itemStyle.color === nodeColor) {
                return cachedNode;
            }
        }
        
        const nodeWithProps = {
            ...node,
            symbolSize: nodeSize,
            itemStyle: { 
                color: nodeColor,
                borderColor: '#fff',
                borderWidth: 2
            },
            label: {
                show: true,
                position: 'inside',
                formatter: function(params) {
                    const name = params.data.name;
                    return name.length > 8 ? name.substring(0, 8) + '...' : name;
                },
                fontSize: 12,
                color: '#000',
                fontWeight: 'bold',
                backgroundColor: 'rgba(255,255,255,0.7)',
                borderRadius: 3,
                padding: [2, 4]
            }
        };
        
        cache.nodeMap.set(nodeKey, nodeWithProps);
        return nodeWithProps;
    });
    
    // 映射关系属性（使用缓存）
    const links = renderLinks.map(link => {
        const linkKey = `link_${link.source}_${link.target}_${link.value}`;
        if (cache.linkMap.has(linkKey)) {
            return cache.linkMap.get(linkKey);
        }
        
        const linkWithProps = {
            source: link.source,
            target: link.target,
            value: link.value,
            lineStyle: { 
                width: 2,
                opacity: 0.7,
                color: '#D3CAB6'
            },
            emphasis: { focus: 'adjacency' },
            label: { 
                show: true,
                formatter: '{c}',
                fontSize: 10,
                position: 'middle',
                backgroundColor: 'rgba(255,255,255,0.8)',
                borderRadius: 2,
                padding: [1, 3]
            },
            emphasis: {
                lineStyle: {
                    width: 3,
                    color: '#AA3723'
                }
            }
        };
        
        cache.linkMap.set(linkKey, linkWithProps);
        return linkWithProps;
    });

    // 配置图表选项
    const option = {
        animation: false,
        series: [{
            type: 'graph',
            layout: 'force',
            data: nodes,
            links: links,
            roam: true,
            draggable: true,
            focusNodeAdjacency: true,
            force: {
                repulsion: 2000,
                gravity: 0.05,
                edgeLength: 150,
                layoutAnimation: false
            },
            label: {
                show: true,
                position: 'inside',
                fontSize: 16
            },
            lineStyle: {
                color: '#D3CAB6',
                width: 2,
                curveness: 0
            },
            emphasis: {
                lineStyle: {
                    width: 3
                }
            },
            progressive: 0,
            progressiveThreshold: 3000
        }]
    };

    try {
        chart.clear();
        chart.setOption(option, true);
        
        // 延迟执行缩放以确保图表完全渲染
        setTimeout(() => {
            chart.dispatchAction({
                type: 'zoomTo',
                zoom: 0.00001,
                animation: { duration: 500, easing: 'cubicOut' }
            });
        }, 500);
    } catch (e) {
        console.error('图表渲染错误:', e);
    }
}



// 6.5 汉字搜索功能 - 全局函数，供首页和主应用共用
async function handleCharacterSearch(char) {
    if (!char) {
        alert('请输入要搜索的汉字');
        return;
    }
    
    console.log('开始汉字搜索:', char);
    
    closeAllPanels();
    
    isCharacterSearchMode = true;
    
    try {
        console.log('发送汉字搜索请求:', `/api/character/search?char=${encodeURIComponent(char)}`);
        const response = await fetch(`/api/character/search?char=${encodeURIComponent(char)}`);
        
        if (!response.ok) {
            throw new Error(`API请求失败: ${response.status} ${response.statusText}`);
        }
        
        const data = await response.json();
        console.log('汉字搜索响应:', data);
        
        if (data.error) {
            alert(data.error);
            isCharacterSearchMode = false;
            return;
        }
        
        showCharacterPanel(char, data.images);
    } catch (error) {
        console.error('汉字搜索失败:', error);
        alert('汉字搜索失败，请检查后端服务');
        isCharacterSearchMode = false;
    }
}

// 6.// 显示返回按钮
function showBackButton() {
    // 检查是否已经存在返回按钮容器
    let backButtonContainer = document.getElementById('back-button-container');
    if (!backButtonContainer) {
        // 创建返回按钮容器
        backButtonContainer = document.createElement('div');
        backButtonContainer.id = 'back-button-container';
        backButtonContainer.style.cssText = `
            position: fixed;
            top: 20%;
            right: 80px;
            transform: translateY(-50%);
            display: flex;
            flex-direction: column;
            align-items: center;
            z-index: 1;
        `;
        
        // 创建返回按钮
        const backButton = document.createElement('div');
        backButton.id = 'back-button';
        backButton.style.cssText = `
            width: 60px;
            height: 60px;
            background-color: #8d322c;
            color: white;
            border-radius: 50%;
            display: flex;
            align-items: center;
            justify-content: center;
            cursor: pointer;
            box-shadow: 0 2px 10px rgba(0,0,0,0.2);
            font-size: 18px;
            font-weight: bold;
            margin-bottom: 8px;
            z-index: 1;
        `;
        backButton.textContent = '←';
        backButton.title = '返回到上一个节点';
        
        // 创建标签
        const backButtonLabel = document.createElement('div');
        backButtonLabel.id = 'back-button-label';
        backButtonLabel.style.cssText = `
            font-size: 12px;
            color: #000000;
            text-align: center;
            font-family: 'Palatino Linotype', 'Book Antiqua', Palatino, serif;
            background-color: white;
            padding: 4px 8px;
            border-radius: 4px;
            box-shadow: 0 1px 3px rgba(0,0,0,0.2);
            z-index: 1;
        `;
        backButtonLabel.textContent = '返回上个节点';
        
        // 添加到容器
        backButtonContainer.appendChild(backButton);
        backButtonContainer.appendChild(backButtonLabel);
        document.body.appendChild(backButtonContainer);
        
        // 添加点击事件
        backButton.addEventListener('click', function() {
            if (nodeHistory.length > 0) {
                // 从历史记录中获取上一个节点ID
                const prevNodeId = nodeHistory.pop();
                // 如果历史记录为空，隐藏返回按钮
                if (nodeHistory.length === 0) {
                    backButtonContainer.style.display = 'none';
                }
                // 调用API获取上一个节点的关系数据
                fetch(`/api/graph/node/relations?node_id=${prevNodeId}`)
                    .then(response => response.json())
                    .then(data => {
                        console.log('获取上一个节点关系数据:', data);
                        // 更新选中的节点ID
                        selectedNodeId = prevNodeId;
                        // 更新图表显示该节点的关系
                        updateChart(data);
                        // 查找该节点的数据
                        const prevNode = data.nodes.find(node => node.id === prevNodeId);
                        if (prevNode) {
                            // 显示书画家面板
                            showPainterPanel(prevNode);
                        }
                    })
                    .catch(error => {
                        console.error('获取上一个节点关系失败:', error);
                    });
            }
        });
    } else {
        // 如果已经存在，显示它
        backButtonContainer.style.display = 'flex';
    }
}

// 绑定交互事件
function initInteractions() {
    // 搜索类型切换功能
    const searchTypeBtns = document.querySelectorAll('.search-type-btn');
    const searchInput = document.getElementById('search-input');
    const searchGroup = document.querySelector('.search-group');
    const appHistoryBox = document.getElementById('app-search-history');
    let currentSearchMode = 'calligrapher';
    
    if (searchTypeBtns.length > 0) {
        searchTypeBtns.forEach(btn => {
            btn.addEventListener('click', () => {
                searchTypeBtns.forEach(b => b.classList.remove('active'));
                btn.classList.add('active');
                
                currentSearchMode = btn.dataset.type;
                
                if (searchGroup) {
                    searchGroup.setAttribute('data-mode', currentSearchMode);
                }
                
                if (currentSearchMode === 'calligrapher') {
                    searchInput.placeholder = '输入书画家姓名...';
                    document.querySelector('.search-input-group').style.display = '';
                    searchInput.value = '';
                    renderHistoryBox('app-search-history', 'calligrapher', 'search-input');
                } else if (currentSearchMode === 'character') {
                    searchInput.placeholder = '输入汉字...';
                    document.querySelector('.search-input-group').style.display = '';
                    searchInput.value = '';
                    renderHistoryBox('app-search-history', 'character', 'search-input');
                } else if (currentSearchMode === 'upload') {
                    searchInput.value = '';
                    if (appHistoryBox) appHistoryBox.classList.remove('visible');
                    document.getElementById('ai-upload').click();
                }
            });
        });
    }

    // 主应用输入框聚焦时显示记忆框
    if (searchInput) {
        searchInput.addEventListener('focus', () => {
            renderHistoryBox('app-search-history', currentSearchMode, 'search-input');
        });
        searchInput.addEventListener('blur', () => {
            setTimeout(() => {
                if (appHistoryBox) appHistoryBox.classList.remove('visible');
            }, 200);
        });
    }

    // 搜索功能
    const searchBtn = document.getElementById('search-btn');
    
    const handleSearch = () => {
        // 单字流派识别模式：触发文件上传
        if (currentSearchMode === 'upload') {
            const aiUpload = document.getElementById('ai-upload');
            if (aiUpload) {
                aiUpload.click();
            }
            return;
        }
        
        const val = searchInput.value.trim();
        if (!val) {
            alert('请输入搜索内容');
            return;
        }
        
        currentPage = 1;
        originalData = null;
        isSearchMode = !!val;
        
        addToMemory(currentSearchMode, val);
        if (appHistoryBox) appHistoryBox.classList.remove('visible');
        
        if (currentSearchMode === 'calligrapher') {
            // 重置汉字搜索模式
            isCharacterSearchMode = false;
            characterSystemActive = false;
            loadGraphData(val);
        } else {
            handleCharacterSearch(val);
        }
    };

    if (searchBtn && searchInput) {
        searchBtn.addEventListener('click', handleSearch);
        searchInput.addEventListener('keypress', (e) => e.key === 'Enter' && handleSearch());
    }

    searchInput.value = '';



    // 上传按钮点击事件
    const uploadBtn = document.getElementById('upload-btn');
    const aiUpload = document.getElementById('ai-upload');
    
    if (uploadBtn && aiUpload) {
        uploadBtn.addEventListener('click', (e) => {
            e.stopPropagation();
            e.preventDefault();
            console.log('点击上传按钮，切换到单字流派识别模式并触发文件选择');
            
            // 先切换到单字流派识别模式
            const uploadTypeBtn = document.querySelector('.search-type-btn[data-type="upload"]');
            if (uploadTypeBtn) {
                uploadTypeBtn.click();
            } else {
                // 如果找不到按钮，直接触发文件上传
                aiUpload.click();
            }
        });
    } else {
        console.error('上传按钮或文件输入框未找到');
        if (!uploadBtn) console.error('未找到上传按钮: upload-btn');
        if (!aiUpload) console.error('未找到文件输入框: ai-upload');
    }
    
    // 标题点击返回落地页
    const logoTitle = document.querySelector('.logo h1');
    if (logoTitle) {
        logoTitle.style.cursor = 'pointer';
        logoTitle.title = '返回首页';
        logoTitle.addEventListener('click', () => {
            console.log('点击标题，返回落地页');
            
            // 关闭所有面板
            closeAllPanels();
            
            // 隐藏主应用
            const app = document.getElementById('app');
            if (app) {
                app.style.display = 'none';
            }
            
            // 显示落地页
            const landingPage = document.getElementById('landing-page');
            if (landingPage) {
                landingPage.style.display = 'flex';
                landingPage.classList.remove('fade-out');
            }
            
            // 重置状态
            isSearchMode = false;
            isCharacterSearchMode = false;
            characterSystemActive = false;
            nodeSystemActive = false;
            
            console.log('已返回落地页');
        });
    }

    // 关闭书画家面板
    const closePanelBtn = document.getElementById('close-panel');
    if (closePanelBtn) {
        closePanelBtn.addEventListener('click', (e) => {
            e.stopPropagation();
            e.preventDefault();
            
            // 保存当前状态
            const wasSearchMode = isSearchMode;
            
            // 关闭面板
            closePainterPanel();
            
            // 恢复到搜索结果状态或原始状态
            if (originalData) {
                try {
                    updateChart(originalData);
                    // 保持搜索模式状态
                    isSearchMode = wasSearchMode;
                } catch (error) {
                    console.error('更新图表失败:', error);
                    // 如果更新失败，使用空数据避免卡死
                    updateChart({ nodes: [], links: [] });
                }
            } else {
                // 如果没有原始数据，使用空数据
                updateChart({ nodes: [], links: [] });
            }
        });
    }

    // 关闭汉字面板（顶部关闭按钮）- 禁用
    const closeCharacterPanelBtn = document.getElementById('close-character-panel');
    if (closeCharacterPanelBtn) {
        closeCharacterPanelBtn.style.display = 'none';
    }

    // 关闭汉字面板（底部关闭按钮）- 禁用
    const bottomCloseCharacterPanelBtn = document.getElementById('bottom-close-character-panel');
    if (bottomCloseCharacterPanelBtn) {
        bottomCloseCharacterPanelBtn.style.display = 'none';
    }

    // 键盘ESC键关闭支持 - 禁用汉字面板关闭
    document.addEventListener('keydown', (e) => {
        if (e.key === 'Escape') {
            // 只关闭其他面板，不关闭汉字面板
            closePainterPanel();
            closeSearchResults();
        }
    });

    // 点击面板外部关闭 - 禁用汉字面板关闭
    const characterPanel = document.getElementById('character-panel');
    if (characterPanel) {
        characterPanel.addEventListener('click', (e) => {
            // 不关闭汉字面板
        });
    }

    // 点击书画家面板外部关闭
    const infoPanel = document.getElementById('info-panel');
    if (infoPanel) {
        infoPanel.addEventListener('click', (e) => {
            if (e.target === e.currentTarget) {
                closePainterPanel();
            }
        });
    }

    // AI 上传识别核心逻辑
    const aiInput = document.getElementById('ai-upload');
    if (aiInput) {
        aiInput.addEventListener('change', async function(e) {
            const file = e.target.files[0];
            if (!file) return;

            console.log('开始AI识别，文件:', file.name);
            
            const formData = new FormData();
            formData.append('image', file);

            try {
                const response = await fetch('/api/ai/classify', {
                    method: 'POST',
                    body: formData
                });

                const result = await response.json();
                console.log('AI识别结果:', result);

                if (result.error) {
                    alert(result.error);
                    return;
                }

                if (result.style) {
                    // 强制关闭所有面板
                    closeAllPanels();
                    
                    // 显示AI识别面板
                    const aiPanel = document.getElementById('ai-panel');
                    if (!aiPanel) {
                        console.error('ai-panel元素未找到');
                        return;
                    }
                    
                    aiPanel.classList.remove('hidden');
                    // 直接进入全屏状态
                    aiPanel.classList.add('fullscreen');
                    // 隐藏页码控件
                    hidePaginationControls();
                    setGraphContainerVisible(true);
                    
                    // 设置AI识别结果
                    const aiName = document.getElementById('ai-name');
                    const aiAllProbs = document.getElementById('ai-all-probs');
                    const aiDesc = document.getElementById('ai-desc');
                    const aiImg = document.getElementById('ai-img');
                    
                    if (aiName) aiName.innerText = "AI 识别详情";
                    if (aiImg) aiImg.src = URL.createObjectURL(file);
                    
                    // 构建AI识别结果内容
                    let aiContent = '';
                    aiContent += `<p><strong>检测到该作品流派为：</strong><span style="background: #fff7ed; color: #c2410c; padding: 4px 8px; border-radius: 4px; font-size: 12px; border: 1px solid #fdba74; font-weight: bold;">${result.style}</span></p>`;
                    aiContent += `<p><strong>置信度：</strong><span style="background: #f3f4f6; color: #374151; padding: 4px 8px; border-radius: 4px; font-size: 12px; font-weight: bold;">${result.confidence}%</span></p>`;
                    
                    if (aiDesc) {
                        aiDesc.innerHTML = aiContent;
                    }
                    
                    // 显示流派可能性
                    if (aiAllProbs) {
                        const styleOrder = ['楷', '行', '草', '隶', '篆'];
                        let probHtml = '<strong>所有流派可能性：</strong><ul>';
                        for (const style of styleOrder) {
                            if (result.all_probabilities[style] !== undefined) {
                                probHtml += '<li>' + style + ': ' + result.all_probabilities[style].toFixed(2) + '%</li>';
                            }
                        }
                        probHtml += '</ul>';
                        aiAllProbs.innerHTML = probHtml;
                        aiAllProbs.style.display = 'block';
                    }
                    
                    // 设置面板锁和激活状态
                    panelLock = true;
                    activePanel = 'ai';
                }
            } catch (error) {
                console.error("上传识别过程出错:", error);
                alert("识别过程出错，请重试");
            }
        });
    } else {
        console.error('AI上传输入框未找到: ai-upload');
    }
    
    // 关闭AI面板功能 - 通过ESC键或其他方式触发
    // 移除了关闭按钮和全屏按钮，AI面板默认以全屏状态显示
}

// 控制知识图谱区域显示（单字检索时隐藏底图）
function setGraphContainerVisible(visible) {
    const graphContainer = document.getElementById('graph-container');
    if (!graphContainer) return;
    graphContainer.style.opacity = visible ? '1' : '0';
    graphContainer.style.pointerEvents = visible ? 'auto' : 'none';
}

// 7. 显示书画家面板函数 - 节点系统专用
function showPainterPanel(data) {
    // 如果汉字独立系统激活，绝对不显示书画家面板
    if (characterSystemActive || isCharacterSearchMode) {
        console.log('汉字系统激活，拒绝显示书画家面板');
        return;
    }
    
    console.log('显示书画家面板:', data.name);
    
    // 强制关闭所有其他面板
    closeAllPanels();
    setGraphContainerVisible(true);
    
    // 检查DOM元素是否存在
    const panel = document.getElementById('info-panel');
    if (!panel) {
        console.error('书画家面板元素未找到: info-panel');
        return;
    }
    
    panel.classList.remove('hidden');
    
    // 根据实体类型显示不同内容
    const nodeType = data.type || data.nodeType || '';
    const isPerson = nodeType === '人物' || nodeType === '书画家' || nodeType === '人';
    
    // 检查各个DOM元素是否存在
    const pName = document.getElementById('p-name');
    const pDynasty = document.getElementById('p-dynasty');
    const pStyle = document.getElementById('p-style');
    const pConfidence = document.getElementById('p-confidence');
    const pAllProbs = document.getElementById('p-all-probs');
    const pDesc = document.getElementById('p-desc');
    const pImg = document.getElementById('p-img');
    
    if (pName) {
        pName.innerText = data.name || '未知';
    }
    
    if (pDesc) {
        // 构建统一的信息内容
        let infoContent = '';
        
        // 添加朝代信息
        if (isPerson && (data.dynasty || data.time)) {
            infoContent += `<p><strong>朝代：</strong><span style="background: #f3f4f6; color: #374151; padding: 4px 8px; border-radius: 4px; font-size: 12px; font-weight: bold;">${data.dynasty || data.time}</span></p>`;
        }
        
        // 添加流派信息
        if (data.style) {
            infoContent += `<p><strong>流派：</strong><span style="background: #fff7ed; color: #c2410c; padding: 4px 8px; border-radius: 4px; font-size: 12px; border: 1px solid #fdba74; font-weight: bold;">${data.style}</span></p>`;
        }
        
        // 添加描述信息
        let description = data.description || '暂无详细介绍。';
        // 移除可能包含的朝代和类型信息，使用更全面的正则表达式
        description = description.replace(/类型[：:].*?(\n|$)/g, '');
        description = description.replace(/朝代[：:].*?(\n|$)/g, '');
        description = description.replace(/时期[：:].*?(\n|$)/g, '');
        description = description.replace(/时代[：:].*?(\n|$)/g, '');
        description = description.trim();
        
        if (description) {
            infoContent += `<div style="margin-top: 15px;">${description}</div>`;
        }
        
        pDesc.innerHTML = infoContent || '暂无详细介绍。';
        
        // 检查是否是AI识别结果（AI识别结果的名称通常是"AI 识别详情"）
        const isAIResult = data.name === "AI 识别详情";
        
        // 只有非AI识别结果才加载版权声明
        if (!isAIResult) {
            // 尝试加载对应文件夹中的版权声明
            let nodeName = data.name || '';
            // 去掉节点名称中的书名号
            nodeName = nodeName.replace(/《|》/g, '');
            
            // 尝试从人物文件夹加载版权声明
            const personCopyrightPath = `/assets/人物/图片版权说明.txt`;
            // 尝试从作品图片文件夹加载版权声明
            const workCopyrightPath = `/assets/作品图片/图片版权声明.txt`;
            
            // 函数：加载并显示版权声明
            function loadCopyright(path, folderName) {
                fetch(path)
                    .then(response => {
                        if (!response.ok) {
                            throw new Error('版权声明文件不存在');
                        }
                        return response.text();
                    })
                    .then(text => {
                        // 查找与当前节点相关的版权信息
                        const lines = text.split('\n');
                        let copyrightText = '';
                        let found = false;
                        
                        // 调试：打印当前节点名称和版权文件内容
                        console.log('当前节点名称:', nodeName);
                        console.log('版权文件内容:', text);
                        
                        // 尝试多种匹配方式
                        // 1. 精确匹配节点名称（包含书名号）
                        const nodeNameWithQuotes = `《${nodeName}》`;
                        for (let i = 0; i < lines.length; i++) {
                            const line = lines[i].trim();
                            if (line.includes(nodeName) || line.includes(nodeNameWithQuotes)) {
                                // 找到相关版权信息，收集后续几行
                                copyrightText += line + '\n';
                                for (let j = i + 1; j < Math.min(i + 5, lines.length); j++) {
                                    const nextLine = lines[j].trim();
                                    if (nextLine && !nextLine.startsWith('《')) {
                                        copyrightText += nextLine + '\n';
                                    } else if (nextLine.startsWith('《')) {
                                        break;
                                    }
                                }
                                found = true;
                                break;
                            }
                        }
                        
                        // 2. 如果没有找到，尝试别名匹配
                        if (!found) {
                            const aliasMap = {
                                '颜真卿': ['颜鲁公'],
                                '米芾': ['米襄阳'],
                                '柳公权': ['柳公权'],
                                '汉书': ['前汉书', '汉书']
                            };
                            
                            const aliases = aliasMap[nodeName] || [];
                            for (const alias of aliases) {
                                for (let i = 0; i < lines.length; i++) {
                                    const line = lines[i].trim();
                                    if (line.includes(alias)) {
                                        // 找到相关版权信息，收集后续几行
                                        copyrightText += line + '\n';
                                        for (let j = i + 1; j < Math.min(i + 5, lines.length); j++) {
                                            const nextLine = lines[j].trim();
                                            if (nextLine && !nextLine.startsWith('《')) {
                                                copyrightText += nextLine + '\n';
                                            } else if (nextLine.startsWith('《')) {
                                                break;
                                            }
                                        }
                                        found = true;
                                        break;
                                    }
                                }
                                if (found) break;
                            }
                        }
                        
                        // 3. 如果还是没有找到，尝试更宽松的匹配（去除书名号、括号等）
                        if (!found) {
                            const simplifiedNodeName = nodeName.replace(/《|》|（|）|·|・/g, '');
                            for (let i = 0; i < lines.length; i++) {
                                const line = lines[i].trim();
                                const simplifiedLine = line.replace(/《|》|（|）|·|・/g, '');
                                if (simplifiedLine.includes(simplifiedNodeName)) {
                                    // 找到相关版权信息，收集后续几行
                                    copyrightText += line + '\n';
                                    for (let j = i + 1; j < Math.min(i + 5, lines.length); j++) {
                                        const nextLine = lines[j].trim();
                                        if (nextLine && !nextLine.startsWith('《')) {
                                            copyrightText += nextLine + '\n';
                                        } else if (nextLine.startsWith('《')) {
                                            break;
                                        }
                                    }
                                    found = true;
                                    break;
                                }
                            }
                        }
                        
                        // 4. 最后尝试关键词匹配（包含任意关键词）
                        if (!found) {
                            const keywords = nodeName.split(/\s+|、|，|。/);
                            for (const keyword of keywords) {
                                if (keyword.length < 2) continue;
                                for (let i = 0; i < lines.length; i++) {
                                    const line = lines[i].trim();
                                    if (line.includes(keyword)) {
                                        // 找到相关版权信息，收集后续几行
                                        copyrightText += line + '\n';
                                        for (let j = i + 1; j < Math.min(i + 5, lines.length); j++) {
                                            const nextLine = lines[j].trim();
                                            if (nextLine && !nextLine.startsWith('《')) {
                                                copyrightText += nextLine + '\n';
                                            } else if (nextLine.startsWith('《')) {
                                                break;
                                            }
                                        }
                                        found = true;
                                        break;
                                    }
                                }
                                if (found) break;
                            }
                        }
                        
                        // 调试：打印最终找到的版权信息
                        console.log('找到的版权信息:', copyrightText);
                        
                        // 显示版权声明
                        showCopyrightInfo(copyrightText || `未找到相应图片，此处使用占位图`);
                    })
                    .catch(error => {
                        console.log(`无法加载${folderName}版权声明:`, error);
                        // 如果从人物文件夹加载失败，尝试从作品图片文件夹加载
                        if (folderName === '人物') {
                            loadCopyright(workCopyrightPath, '作品图片');
                        } else {
                            // 如果都加载失败，显示默认版权信息
                            showCopyrightInfo('未找到相应图片，此处使用占位图');
                        }
                    });
            }
            
            // 函数：显示版权信息
            function showCopyrightInfo(copyrightText) {
                // 清除现有的版权信息（如果有）
                const existingCopyright = pDesc.nextElementSibling;
                if (existingCopyright && existingCopyright.style.fontSize === '12px') {
                    existingCopyright.remove();
                }
                
                // 添加版权声明
                const copyrightInfo = document.createElement('div');
                copyrightInfo.style.cssText = `
                    margin-top: 15px;
                    padding: 10px;
                    background-color: #f5f5f5;
                    border-radius: 5px;
                    font-size: 12px;
                    color: #666;
                    max-height: 200px;
                    overflow-y: auto;
                `;
                copyrightInfo.innerHTML = `
                    <p><strong>图片版权声明：</strong></p>
                    <pre style="white-space: pre-wrap; margin: 0;">${copyrightText}</pre>
                `;
                
                // 添加版权声明
                pDesc.parentNode.insertBefore(copyrightInfo, pDesc.nextSibling);
            }
            
            // 开始加载版权声明
            // 先判断是人物还是作品
            const isPerson = ['颜真卿', '米芾', '柳公权', '王羲之', '文徵明', '虞世南', '钟繇', '孙思邈', '班固'].includes(nodeName);
            if (isPerson) {
                loadCopyright(personCopyrightPath, '人物');
            } else {
                loadCopyright(workCopyrightPath, '作品图片');
            }
        } else {
            // 清除现有的版权信息（如果有）
            const existingCopyright = pDesc.nextElementSibling;
            if (existingCopyright && existingCopyright.style.fontSize === '12px') {
                existingCopyright.remove();
            }
        }
    }
    
    // 隐藏置信度和流派可能性（AI识别专用）
    if (pConfidence && pConfidence.parentElement) {
        pConfidence.parentElement.style.display = 'none';
    }
    if (pAllProbs) {
        pAllProbs.style.display = 'none';
    }
    
    if (pImg) {
        // 尝试从assets/人物目录加载对应节点的图片
        let nodeName = data.name || '';
        // 去掉节点名称中的书名号
        nodeName = nodeName.replace(/《|》/g, '');
        console.log('尝试加载节点图片:', nodeName);
        
        // 尝试加载图片的路径
        const imagePath = `/assets/人物/${nodeName}.png`;
        console.log('尝试加载人物图片路径:', imagePath);
        
        // 创建图片对象进行预加载，检查图片是否存在
        const img = new Image();
        img.onload = function() {
            console.log('人物图片加载成功:', imagePath);
            pImg.src = imagePath;
        };
        img.onerror = function() {
            console.log('人物图片加载失败，尝试加载作品图片:', nodeName);
            // 如果图片不存在，尝试从assets/作品图片目录加载，使用jpg格式
            const workImagePath = `/assets/作品图片/${nodeName}.jpg`;
            console.log('尝试加载作品图片路径:', workImagePath);
            const workImg = new Image();
            workImg.onload = function() {
                console.log('作品图片加载成功:', workImagePath);
                pImg.src = workImagePath;
            };
            workImg.onerror = function() {
                console.log('作品图片加载失败，使用默认图片:', nodeName);
                // 如果图片不存在，使用默认图片，并添加时间戳避免缓存
                const timestamp = new Date().getTime();
                // 使用指定的占位图路径
                const defaultImagePath = `/assets/OIP-C.jpg?${timestamp}`;
                console.log('使用默认图片:', defaultImagePath);
                pImg.src = data.image_url || defaultImagePath;
            };
            workImg.src = workImagePath;
        };
        img.src = imagePath;
    }
    
    // 激活节点独立系统
    nodeSystemActive = true;
    
    // 设置面板锁和激活状态
    panelLock = true;
    activePanel = 'painter';
    console.log('书画家面板已显示，面板锁激活');
}

// 8. 显示汉字面板函数 - 完全独立系统
function showCharacterPanel(character, images) {
    // 如果节点独立系统激活，绝对不显示汉字面板
    if (nodeSystemActive) {
        console.log('节点系统激活，拒绝显示汉字面板');
        return;
    }
    
    console.log('显示汉字面板:', character);
    
    // 强制关闭所有其他面板
    closeAllPanels();
    
    // 隐藏返回按钮
    const backButtonContainer = document.getElementById('back-button-container');
    if (backButtonContainer) {
        backButtonContainer.style.display = 'none';
    }
    
    const panel = document.getElementById('character-panel');
    
    // 退出全屏状态（如果之前是全屏）
    if (panel) {
        // 单字检索结果默认使用与AI识别一致的主视图
        panel.classList.add('fullscreen');
        panel.classList.remove('hidden');
        setGraphContainerVisible(false);
        
        // 显示汉字
        const cCharacter = document.getElementById('c-character');
        if (cCharacter) {
            cCharacter.innerText = character;
        }
        
        // 清空图片容器
        const imagesContainer = document.getElementById('c-images');
        if (imagesContainer) {
            imagesContainer.innerHTML = '';
            
            // 显示书法作品图片
            if (images && images.length > 0) {
                images.forEach(img => {
                    const imgElement = document.createElement('div');
                    imgElement.className = 'character-image-item';
                    imgElement.innerHTML = `
                        <img src="${img.path}" alt="${img.filename}" />
                        <div class="image-info">
                            <p><strong>字体：</strong>${img.font}</p>
                            <p><strong>朝代：</strong>${img.dynasty}</p>
                            <p><strong>书法家：</strong>${img.calligrapher}</p>
                        </div>
                    `;
                    imagesContainer.appendChild(imgElement);
                });
            } else {
                imagesContainer.innerHTML = '<p>暂无该汉字的书法作品</p>';
            }
        }
        
        // 面板显示后自动聚焦，支持ESC键关闭
        panel.focus();
        
        // 主视图模式隐藏分页控件，避免遮挡结果内容
        hidePaginationControls();
        
        // 设置面板锁和激活状态
        panelLock = true;
        activePanel = 'character';
        
        // 激活汉字独立系统
        characterSystemActive = true;
        
        console.log('汉字面板已显示，面板锁激活');
    }
}

// 9. 关闭汉字面板函数 - 汉字系统专用
function closeCharacterPanel() {
    console.log('关闭汉字面板');
    const panel = document.getElementById('character-panel');
    
    // 检查面板是否已经隐藏
    if (!panel || panel.classList.contains('hidden')) {
        console.log('汉字面板已经隐藏或不存在');
        return;
    }
    
    // 强制退出全屏状态
    panel.classList.remove('fullscreen');
    
    // 隐藏面板
    panel.classList.add('hidden');
    
    // 清除面板内容
    const cCharacter = document.getElementById('c-character');
    const cImages = document.getElementById('c-images');
    
    if (cCharacter) cCharacter.innerText = '';
    if (cImages) cImages.innerHTML = '';
    
    // 退出汉字搜索模式
    isCharacterSearchMode = false;
    
    // 停用汉字独立系统
    characterSystemActive = false;
    
    // 退出全屏时显示页码显示
    showPaginationControls();
    
    // 释放面板锁和激活状态
    panelLock = false;
    activePanel = null;
    
    // 显示返回按钮（如果有历史记录）
    const backButtonContainer = document.getElementById('back-button-container');
    if (backButtonContainer && nodeHistory.length > 0) {
        backButtonContainer.style.display = 'flex';
    }
    
    console.log('汉字面板已关闭，面板锁释放');
}

// 10. 关闭书画家面板函数
function closePainterPanel() {
    const panel = document.getElementById('info-panel');
    
    // 检查面板是否已经隐藏
    if (!panel || panel.classList.contains('hidden')) {
        console.log('书画家面板已经隐藏或不存在');
        return;
    }
    
    panel.classList.add('hidden');
    
    // 清除AI识别结果
    const pName = document.getElementById('p-name');
    const pStyle = document.getElementById('p-style');
    const pDynasty = document.getElementById('p-dynasty');
    const pConfidence = document.getElementById('p-confidence');
    const pDesc = document.getElementById('p-desc');
    const pAllProbs = document.getElementById('p-all-probs');
    const pImg = document.getElementById('p-img');
    
    if (pName) pName.innerText = '姓名加载中...';
    if (pStyle) pStyle.innerText = '-';
    if (pDynasty) pDynasty.innerText = '-';
    if (pConfidence) pConfidence.innerText = '-';
    if (pDesc) pDesc.innerText = '';
    if (pAllProbs) pAllProbs.innerHTML = '';
    if (pImg) pImg.src = '';
    
    // 隐藏面板
    panel.classList.add('hidden');
    
    // 释放面板锁和激活状态
    panelLock = false;
    activePanel = null;
    nodeSystemActive = false;
    
    console.log('书画家面板已关闭，面板锁释放');
}

// 11. 关闭所有面板函数
function closeAllPanels() {
    console.log('关闭所有面板');
    
    // 获取三个面板元素
    const characterPanel = document.getElementById('character-panel');
    const painterPanel = document.getElementById('info-panel');
    const aiPanel = document.getElementById('ai-panel');
    
    // 强制隐藏三个面板
    if (characterPanel && !characterPanel.classList.contains('hidden')) {
        characterPanel.classList.add('hidden');
    }
    
    if (painterPanel && !painterPanel.classList.contains('hidden')) {
        painterPanel.classList.add('hidden');
    }
    
    if (aiPanel && !aiPanel.classList.contains('hidden')) {
        aiPanel.classList.add('hidden');
    }
    setGraphContainerVisible(true);
    
    // 重置所有状态变量
    panelLock = false;
    activePanel = null;
    isCharacterSearchMode = false;
    characterSystemActive = false;
    nodeSystemActive = false;
    
    console.log('所有面板已强制关闭，状态已重置');
}

// 12. 关闭AI面板函数
function closeAiPanel() {
    const panel = document.getElementById('ai-panel');
    if (panel) {
        // 强制退出全屏状态
        panel.classList.remove('fullscreen');
        
        // 隐藏面板
        panel.classList.add('hidden');
        
        // 退出全屏时显示页码显示
        showPaginationControls();
        
        // 释放面板锁和激活状态
        panelLock = false;
        activePanel = null;
        
        console.log('AI面板已关闭，面板锁释放');
    }
}

// 12. 隐藏页码显示函数
function hidePaginationControls() {
    const paginationContainer = document.getElementById('pagination-controls');
    if (paginationContainer) {
        paginationContainer.style.display = 'none';
    }
}

// 13. 显示页码显示函数
function showPaginationControls() {
    const paginationContainer = document.getElementById('pagination-controls');
    if (paginationContainer) {
        paginationContainer.style.display = 'flex';
    }
}

// 14. 工具函数：根据类型分配颜色
// 优化：使用缓存避免重复计算
function getColorByType(type) {
    // 先检查缓存
    if (cache.colorMap.has(type)) {
        return cache.colorMap.get(type);
    }
    
    // 人物节点使用主色调
    if (type === '人物' || type === '书画家' || type === '人') {
        const color = '#8d322c'; // 红褐色，代表人物
        cache.colorMap.set(type, color);
        return color;
    }
    
    // 其他类型节点使用协调的颜色方案
    const colors = {
        '作品': '#4a6b8a', // 深蓝色，代表作品
        '朝代': '#8b4513', // 棕色，代表朝代
        '时间': '#D3CAB6', // 浅米色，代表时间
        '评价': '#D4A573', // 浅棕色，代表评价
        '官职': '#D4A573', // 浅棕色，代表官职
        '籍贯': '#D3CAB6', // 浅米色，代表籍贯
        '名号': '#D3CAB6', // 浅米色，代表名号
        '家人': '#D4A573', // 浅棕色，代表家人
        '擅长': '#D4A573', // 浅棕色，代表擅长
        '师承': '#D4A573', // 浅棕色，代表师承
        '影响': '#D3CAB6', // 浅米色，代表影响
        '同时代': '#D3CAB6', // 浅米色，代表同时代
        '书法': '#D4A573', // 浅棕色，代表书法
        '流派': '#4a6b8a', // 深蓝色，代表流派
        '风格': '#4a6b8a'  // 深蓝色，代表风格
    };
    
    const color = colors[type] || '#D3CAB6'; // 浅米色，代表其他
    // 缓存结果
    cache.colorMap.set(type, color);
    return color;
}

// 高亮显示与选中节点相关的节点
function highlightRelatedNodes(selectedNode) {
    // 始终使用完整数据集来查找相关节点
    // 这样即使在搜索后点击节点，也能显示该节点的所有相关关系
    const allNodes = completeData ? completeData.nodes : (originalData ? originalData.nodes : fullNodes);
    const allLinks = completeData ? completeData.links : (originalData ? originalData.links : fullLinks);
    
    if (!allNodes || allNodes.length === 0) {
        return;
    }
    
    // 找到与选中节点相关的所有节点和关系
    const relatedNodeIds = new Set();
    relatedNodeIds.add(selectedNode.id);
    
    // 查找所有与选中节点直接相连的关系
    const relatedLinks = allLinks.filter(link => {
        if (link.source === selectedNode.id || link.target === selectedNode.id) {
            relatedNodeIds.add(link.source);
            relatedNodeIds.add(link.target);
            return true;
        }
        return false;
    });
    
    // 获取相关节点
    const relatedNodes = allNodes.filter(node => relatedNodeIds.has(node.id));
    
    // 如果没有找到相关节点，说明这是一个孤立节点
    if (relatedNodes.length === 0) {
        relatedNodeIds.clear();
        relatedNodeIds.add(selectedNode.id);
    }
    
    // 优化：只处理相关的节点和关系，而不是整个数据集
    const nodesWithEmphasis = relatedNodes.map(node => {
        if (node.id === selectedNode.id) {
            // 对选中节点进行特殊标记
            return {
                ...node,
                symbolSize: 100,
                itemStyle: { 
                    color: '#AA3723',
                    borderColor: '#000',
                    borderWidth: 3,
                    shadowBlur: 15,
                    shadowColor: '#333'
                },
                label: {
                    show: true,
                    position: 'inside',
                    fontSize: 14,
                    fontWeight: 'bold',
                    color: '#000',
                    backgroundColor: 'rgba(255,255,255,0.8)',
                    borderRadius: 3,
                    padding: [2, 4]
                },
                x: 680,
                y: 380,
                fixed: true
            };
        } else {
            // 对相关节点进行轻微突出
            return {
                ...node,
                symbolSize: 70,
                itemStyle: { 
                    color: getColorByType(node.type),
                    borderColor: '#fff',
                    borderWidth: 2,
                    opacity: 0.9
                },
                label: {
                    show: true,
                    position: 'inside',
                    fontSize: 12,
                    color: '#000',
                    opacity: 0.9
                }
            };
        }
    });
    
    // 优化：只处理相关的关系
    const linksWithEmphasis = relatedLinks.map(link => {
        // 突出显示与选中节点相关的连接
            return {
                ...link,
                lineStyle: {
                    ...link.lineStyle,
                    width: 2,
                    color: '#AA3723',
                    opacity: 1
                },
            label: {
                show: true,
                formatter: '{c}',
                fontSize: 10,
                position: 'middle',
                backgroundColor: 'rgba(255,255,255,0.8)',
                borderRadius: 2,
                padding: [1, 3]
            },
            emphasis: {
                ...link.emphasis,
                lineStyle: {
                    width: 3,
                    color: '#AA3723'
                }
            }
        };
    });

    // 更新图表显示
    const option = {
        animation: false,
        series: [{
            type: 'graph',
            layout: 'force',
            data: nodesWithEmphasis,
            links: linksWithEmphasis,
            roam: true,
            draggable: true,
            focusNodeAdjacency: true,
            force: {
                repulsion: 800,
                gravity: 0.1,
                edgeLength: 100,
                layoutAnimation: false
            },
            label: {
                show: true,
                position: 'inside',
                fontSize: 12
            },
            lineStyle: {
                color: '#999',
                width: 1,
                curveness: 0
            },
            emphasis: {
                lineStyle: {
                    width: 2
                }
            }
        }]
    };
    
    chart.setOption(option, true);
    
    // 将选中节点移动到画面中央
    setTimeout(() => {
        const nodeIndex = nodesWithEmphasis.findIndex(n => n.id === selectedNode.id);
        
        if (nodeIndex !== -1) {
            chart.dispatchAction({
                type: 'focusNodeAdjacency',
                dataIndex: nodeIndex
            });
            
            chart.dispatchAction({
                type: 'zoomTo',
                zoom: 0.5,
                animation: {
                    duration: 300,
                    easing: 'cubicOut'
                }
            });
        }
    }, 100);
}

// 恢复显示所有节点
function showAllNodes() {
    if (originalData) {
        updateChart(originalData);
    }
}
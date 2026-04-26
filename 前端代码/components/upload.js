import eventBus from '../core/eventBus.js';
// 注意：确保 graph.js 确实导出了 renderGraph 函数
import { renderGraph } from '../core/graph.js'; 

export const initUpload = () => {
    const fileInput = document.getElementById('ai-upload');
    if (!fileInput) return;

    fileInput.addEventListener('change', async (event) => {
        const file = event.target.files[0];
        if (!file) return;

        // 构造 FormData
        const formData = new FormData();
        formData.append('image', file);

        try {
            // 发送识别请求
            const response = await fetch('/api/ai/classify', {
                method: 'POST',
                body: formData
            });

            const result = await response.json();

            if (result.style) {
                // 1. 更新面板文字（不刷新页面）
                document.getElementById('info-panel').classList.remove('hidden');
                document.getElementById('p-name').innerText = "AI 识别详情";
                document.getElementById('p-style').innerText = result.style;
                document.getElementById('p-desc').innerText = "检测到该作品流派为：" + result.style;

                // 2. 重新获取图谱数据（带上流派参数）
                // 确保这里的 URL 拼接没有语法错误
                const graphResponse = await fetch('/api/graph/data?style=' + encodeURIComponent(result.style));
                const newData = await graphResponse.json();

                // 3. 调用渲染函数更新图谱
                renderGraph(newData);
            }
        } catch (error) {
            console.error("上传识别过程出错:", error);
        }
    }); // 这里的括号和分号必须对应 addEventListener 的开始
};
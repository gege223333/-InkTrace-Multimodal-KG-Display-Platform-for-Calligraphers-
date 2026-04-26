import { API_BASE_URL } from '../config.js';

export const graphApi = {
    // 获取初始图谱
    async fetchInitialData() {
        const res = await fetch(`${API_BASE_URL}/api/graph/data`);
        return await res.json();
    },
    
    // 按名称搜索
    async searchPainter(keyword) {
        const res = await fetch(`${API_BASE_URL}/api/graph/search?q=${keyword}`);
        return await res.json();
    },
    
    // 搜索汉字
    async searchCharacter(char) {
        const res = await fetch(`${API_BASE_URL}/api/character/search?char=${char}`);
        return await res.json();
    }
};
let myChart = null;

export const initGraph = (id) => {
    const container = document.getElementById(id);
    if (!container) return;
    myChart = echarts.init(container);
};

export const renderGraph = (data) => {
    if (!myChart) return;
    const option = {
        title: { text: '书画关联图谱', bottom: 10, left: 'center' },
        series: [{
            type: 'graph',
            layout: 'force',
            data: data.nodes,
            links: data.links,
            roam: true,
            label: { show: true },
            force: { repulsion: 1000 }
        }]
    };
    myChart.setOption(option);
};
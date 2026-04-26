from flask import Flask, jsonify, send_from_directory, request
from flask_cors import CORS
import os
import tempfile
from services.graph_service import GraphService
from ai_service import ai_service

# 自动定位前端文件夹 (绝对路径)
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
FRONTEND_DIR = os.path.abspath(os.path.join(BASE_DIR, '..', 'frontend'))

# 定位汉字数据集路径（使用后端static/assets目录）
CHARACTER_DATASET_PATH = os.path.abspath(os.path.join(BASE_DIR, 'static', 'assets', 'characters'))

app = Flask(__name__, static_folder=FRONTEND_DIR, static_url_path='')
CORS(app)



# 添加静态文件路由，用于访问后端的static目录
@app.route('/static/<path:path>')
def static_file(path):
    return send_from_directory('static', path)

# 初始化GraphService
graph_service = GraphService()

@app.route('/')
def index():
    # 从frontend目录提供index.html文件
    return send_from_directory('../frontend', 'index.html')

@app.route('/api/graph/data')
def get_graph_data():
    """获取全量图谱数据"""
    data = graph_service.get_all_painters()
    return jsonify(data)

@app.route('/api/graph/search')
def search_painter():
    """搜索书画家"""
    query = request.args.get('q', '').strip()
    data = graph_service.search_by_name(query)
    return jsonify(data)

@app.route('/api/graph/node/relations')
def get_node_relations():
    """获取指定节点的所有关系和相关节点"""
    node_id = request.args.get('node_id', '').strip()
    data = graph_service.get_node_relations(node_id)
    return jsonify(data)

@app.route('/api/graph/data/page')
def get_graph_data_page():
    """分页获取图谱数据"""
    page = int(request.args.get('page', 1))
    page_size = int(request.args.get('size', 100))
    
    # 获取所有数据
    all_data = graph_service.get_all_painters()
    
    # 计算起始和结束索引
    start_idx = (page - 1) * page_size
    end_idx = start_idx + page_size
    
    # 获取当前页的节点
    paginated_nodes = all_data['nodes'][start_idx:end_idx]
    
    # 获取与当前页节点相关的所有关系
    node_ids = {node['id'] for node in paginated_nodes}
    
    # 收集与当前页节点相关的所有节点ID
    related_node_ids = set()
    related_links = []
    
    for link in all_data['links']:
        if link['source'] in node_ids or link['target'] in node_ids:
            related_links.append(link)
            related_node_ids.add(link['source'])
            related_node_ids.add(link['target'])
    
    # 获取所有相关节点
    all_related_nodes = [node for node in all_data['nodes'] if node['id'] in related_node_ids]
    
    result = {
        'nodes': all_related_nodes,
        'links': related_links,
        'total_nodes': len(all_data['nodes']),
        'total_pages': (len(all_data['nodes']) + page_size - 1) // page_size,  # 向上取整
        'current_page': page,
        'page_size': page_size
    }
    
    return jsonify(result)

@app.route('/api/character/search')
def search_character():
    """根据汉字查询书法家作品"""
    char = request.args.get('char', '').strip()
    if not char:
        return jsonify({"error": "请输入汉字"})
    
    # 构建汉字文件夹路径
    char_folder = os.path.join(CHARACTER_DATASET_PATH, char)
    if not os.path.exists(char_folder):
        return jsonify({"error": "未找到该汉字的书法作品"})
    
    # 获取该汉字的所有书法作品
    character_images = []
    for filename in os.listdir(char_folder):
        if filename.endswith('.png'):
            # 解析文件名获取信息
            parts = filename.split('-')
            if len(parts) >= 4:
                character_images.append({
                    "filename": filename,
                    "character": parts[0],
                    "font": parts[1],
                    "dynasty": parts[2],
                    "calligrapher": parts[3],
                    "path": f"/assets/characters/{char}/{filename}"
                })
    
    return jsonify({"images": character_images})

@app.route('/api/ai/classify', methods=['POST'])
def classify_calligraphy():
    if 'image' not in request.files:
        return jsonify({"error": "没有上传图片"}), 400

    file = request.files['image']
    if file.filename == '':
        return jsonify({"error": "文件名为空"}), 400

    suffix = os.path.splitext(file.filename)[1]
    with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
        file.save(tmp.name)
        tmp_path = tmp.name

    try:
        result = ai_service.predict(tmp_path)
        if result[0] is None:
            return jsonify({"error": "模型未加载"}), 500
        
        style, confidence, all_probs = result
        return jsonify({
            "style": style,
            "confidence": round(confidence, 2),
            "all_probabilities": {k: round(v, 2) for k, v in all_probs.items()}
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500
    finally:
        if os.path.exists(tmp_path):
            os.remove(tmp_path)

if __name__ == "__main__":
    print("启动书画家知识图谱服务...")
    print(f" 前端文件夹路径: {FRONTEND_DIR}")
    print(f" 汉字数据集路径: {CHARACTER_DATASET_PATH}")
    print("服务将在 http://localhost:5000 运行")
    print(" 可用 API 端点:")
    print("   - GET /              - 前端页面")
    print("   - GET /api/graph/data - 获取图谱数据") 
    print("   - GET /api/graph/search?q=关键词 - 搜索书画家")
    print("   - GET /api/graph/node/relations?node_id=节点ID - 获取节点关系")
    print("   - GET /api/character/search?char=汉字 - 搜索汉字书法作品")
    print("   - GET /api/graph/data/page?page=页码&size=每页数量 - 分页获取图谱数据")
    print(" 按 Ctrl+C 停止服务")
    print("=" * 50)
    
    app.run(debug=True, host='0.0.0.0', port=5000)
from flask import Blueprint, jsonify, request
import os
from security import security_check, csrf_protect
from service.pdf_service import analyze_pdf_page

# 创建pdf蓝图
pdf_bp = Blueprint('pdf_bp', __name__)

@pdf_bp.route('/api/pdf/analyze', methods=['POST'])
@security_check
@csrf_protect
def analyze_pdf():
    """分析PDF文件的指定页面"""
    if 'file' not in request.files:
        return jsonify({'error': 'No PDF file provided'}), 400
    
    file = request.files['file']
    if file.filename == '':
        return jsonify({'error': 'No file selected'}), 400
    
    # 获取页码参数并验证
    try:
        page_num = int(request.form.get('page_num', 1))
        if page_num <= 0:
            return jsonify({'error': 'Page number must be a positive integer'}), 400
    except (ValueError, TypeError):
        return jsonify({'error': 'Invalid page number'}), 400
    
    # 保存上传的文件
    upload_dir = 'uploads'
    if not os.path.exists(upload_dir):
        os.makedirs(upload_dir)
    
    # 使用安全的文件名
    from werkzeug.utils import secure_filename
    filename = secure_filename(file.filename)
    
    # 再次验证文件扩展名
    if not filename.lower().endswith('.pdf'):
        return jsonify({'error': 'File is not a PDF'}), 400
    
    file_path = os.path.join(upload_dir, filename)
    file.save(file_path)
    
    try:
        result = analyze_pdf_page(file_path, page_num)
        
        return jsonify({
            'message': f'PDF page {page_num} analyzed successfully',
            'analysis': result
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500
    finally:
        # 清理上传的文件（可选，根据需要保留或删除）
        # os.remove(file_path)
        pass
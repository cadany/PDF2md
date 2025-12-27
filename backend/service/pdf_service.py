import fitz  # PyMuPDF
import os


def analyze_pdf_page(pdf_path, page_num):
    """分析PDF文件的指定页面"""
    doc = fitz.open(pdf_path)
    
    # 检查页码是否有效
    if page_num < 1 or page_num > len(doc):
        raise ValueError(f'Page number must be between 1 and {len(doc)}')
    
    page = doc[page_num - 1]  # 页码转换为索引（从0开始）
    
    # 方法1：检查是否有图片
    images = page.get_images()
    
    # 方法2：检查文字层
    text = page.get_text()
    
    # 方法3：检查文字位置（如果是OCR生成，文字位置可能很奇怪）
    words = page.get_text("words")  # 获取每个词的位置
    
    # 方法4：渲染页面并保存
    pix = page.get_pixmap()
    filename = pdf_path.split('/')[-1].replace('.pdf', '')
    output_filename = f"{filename}_page_{page_num}_rendered.png"
    upload_dir = 'uploads'
    output_path = os.path.join(upload_dir, output_filename)
    pix.save(output_path)
    
    # 分析结果
    result = {
        "has_images": len(images) > 0,
        "has_text": bool(text.strip()),
        "text_quality": "OCR-like" if "  " in text else "Native",
        "page_number": page_num,
        "total_pages": len(doc),
        "word_count": len(words),
        "rendered_image_path": output_path
    }
    
    # 确保文档被关闭
    doc.close()
    
    return result


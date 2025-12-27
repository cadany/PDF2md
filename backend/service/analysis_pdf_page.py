import fitz  # PyMuPDF
import json

def analyze_pdf_page(pdf_path="投标文件样本.pdf", page_num=4):
    doc = fitz.open(pdf_path)
    page = doc[page_num - 1]  # 页码转换为索引（从0开始）

    print(f"页面 {page_num} 总页数: {len(doc)}")
    
    # 方法1：检查是否有图片
    images = page.get_images()
    print(f"页面中的图片数量: {len(images)}")
    
    # 方法2：检查文字层是否为空
    text = page.get_text()
    print(f"文字层内容预览:\n{text[:500]}\n")
    
    # 方法3：检查文字位置（如果是OCR生成，文字位置可能很奇怪）
    words = page.get_text("words")  # 获取每个词的位置
    for word in words[:10]:  # 看前10个词
        print(f"词: '{word[4]}', 位置: ({word[0]}, {word[1]})")
    
    # 方法4：渲染页面并查看
    pix = page.get_pixmap()
    filename = pdf_path.split('/')[-1].replace('.pdf', '')
    pix.save(f"{filename}_page_{page_num}_rendered.png")
    print("已保存页面渲染图，可以查看是否为图片")
    
    return {
        "has_images": len(images) > 0,
        "has_text": bool(text.strip()),
        "text_quality": "OCR-like" if "  " in text else "Native"
    }

if __name__ == "__main__":
    # 测试函数
    import sys
    if len(sys.argv) != 3:
        print("Usage: python analyze_pdf_page.py <pdf_path> <page_num>")
        sys.exit(1)
    
    pdf_path = sys.argv[1]
    page_num = int(sys.argv[2])
    
    try:
        result = analyze_pdf_page(pdf_path, page_num)
        print("PDF Analysis Result:")
        print(json.dumps(result, indent=2, ensure_ascii=False))
    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)
#!/usr/bin/env python3
"""
测试 analyze_pdf_page 函数的脚本
"""

import os
import sys
import json

# 添加 backend 目录到 Python 路径
sys.path.append(os.path.join(os.path.dirname(__file__), 'backend'))

from service.pdf_service import analyze_pdf_page

def test_analyze_pdf_page():
    """测试 analyze_pdf_page 函数"""
    print("PDF分析函数测试")
    print("=" * 50)
    
    # 获取当前目录下的PDF文件
    current_dir = os.getcwd()
    pdf_files = [f for f in os.listdir(current_dir) if f.lower().endswith('.pdf')]
    
    if not pdf_files:
        print("在当前目录中没有找到PDF文件")
        print("请将PDF文件放在当前目录中，然后重新运行测试")
        return
    
    print(f"找到PDF文件: {pdf_files}")
    
    for pdf_file in pdf_files:
        pdf_path = os.path.join(current_dir, pdf_file)
        print(f"\n正在分析文件: {pdf_file}")
        
        # 获取PDF总页数
        import fitz
        try:
            doc = fitz.open(pdf_path)
            total_pages = len(doc)
            doc.close()
            print(f"PDF总页数: {total_pages}")
            
            # 测试第一页
            if total_pages >= 1:
                print(f"正在分析第1页...")
                try:
                    result = analyze_pdf_page(pdf_path, 1)
                    print("分析结果:")
                    print(json.dumps(result, indent=2, ensure_ascii=False))
                except Exception as e:
                    print(f"分析第1页时出错: {e}")
            
            # 如果有多页，也测试最后一页
            if total_pages > 1:
                print(f"\n正在分析最后一页 (第{total_pages}页)...")
                try:
                    result = analyze_pdf_page(pdf_path, total_pages)
                    print("分析结果:")
                    print(json.dumps(result, indent=2, ensure_ascii=False))
                except Exception as e:
                    print(f"分析最后一页时出错: {e}")
                    
        except Exception as e:
            print(f"打开PDF文件时出错: {e}")

def test_with_sample():
    """使用示例参数测试（如果当前目录没有PDF文件）"""
    print("\n" + "=" * 50)
    print("使用示例参数测试（请替换为实际的PDF文件路径）")
    print("示例命令: analyze_pdf_page('/path/to/your/file.pdf', 1)")
    
    print("\n如果要测试，请使用以下方式:")
    print("方法1: 将PDF文件放在当前目录，然后运行此脚本")
    print("方法2: 在终端中直接运行:")
    print("  python backend/service/pdf_service.py '/path/to/your/file.pdf' 1")
    print("方法3: 在Python中直接调用:")
    print("  from backend.service.pdf_service import analyze_pdf_page")
    print("  result = analyze_pdf_page('/path/to/your/file.pdf', 1)")
    print("  print(result)")

if __name__ == "__main__":
    test_analyze_pdf_page()
    test_with_sample()
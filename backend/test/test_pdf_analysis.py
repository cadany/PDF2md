import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), '.'))

from service.analysis_pdf_page import analyze_pdf_page

# 示例用法
if __name__ == "__main__":
    # 使用默认参数（保持向后兼容性）
    result1 = analyze_pdf_page()
    print("使用默认参数的结果:", result1)
    
    print("\n" + "="*50 + "\n")
    
    # 使用自定义参数
    # result2 = analyze_pdf_page("path/to/your/pdf.pdf", 1)  # 替换为实际PDF路径
    # print("使用自定义参数的结果:", result2)
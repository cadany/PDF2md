import os
import sys
import cv2
import numpy as np
from PIL import Image
import io

# 添加项目根目录到Python路径
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

from service.pdf_to_text_converter import PDFToTextConverter, ProcessingConfig

def test_pdf_with_ocr():
    """测试带OCR功能的PDF转换"""
    print("开始测试PDF转换中的OCR功能...")
    
    # 创建转换器实例
    config = ProcessingConfig(
        ocr_enabled=True, 
        ocr_service_type="local",
        include_images=True,
        include_tables=True,
        preserve_formatting=True
    )
    converter = PDFToTextConverter(config)
    
    # 查找测试PDF文件
    test_pdfs = [
        "/Users/cadany/Desktop/code/labs/BiddingChecker/backend/test.pdf",
        "/Users/cadany/Desktop/code/labs/BiddingChecker/backend/fj-23p.pdf",
        "/Users/cadany/Desktop/code/labs/BiddingChecker/backend/example.pdf"
    ]
    
    for pdf_path in test_pdfs:
        if os.path.exists(pdf_path):
            print(f"发现测试PDF文件: {pdf_path}")
            try:
                print(f"开始转换PDF: {pdf_path}")
                output_path = converter.convert_pdf_to_text(
                    pdf_path=pdf_path,
                    start_page=1,
                    end_page=2  # 只处理前两页以加快测试速度
                )
                print(f"PDF转换完成，输出文件: {output_path}")
                
                # 读取并显示部分输出内容
                with open(output_path, 'r', encoding='utf-8') as f:
                    content = f.read(2000)  # 读取前2000个字符
                    print(f"\n输出内容预览:\n{content}")
                
                break
            except Exception as e:
                print(f"处理PDF {pdf_path} 时出错: {e}")
                import traceback
                traceback.print_exc()
        else:
            print(f"未找到PDF文件: {pdf_path}")
    
    if not any(os.path.exists(pdf) for pdf in test_pdfs):
        print(f"未找到任何测试PDF文件。请确保以下文件之一存在:")
        for pdf in test_pdfs:
            print(f"  - {pdf}")

def test_ocr_with_real_image():
    """使用真实图像测试OCR功能"""
    print("\n开始测试真实图像的OCR功能...")
    
    # 创建一个更清晰的测试图像
    img = np.zeros((150, 300, 3), dtype=np.uint8)
    img.fill(255)  # 白色背景
    
    # 添加中文和英文文字
    cv2.putText(img, '测试文字', (50, 70), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 0, 0), 2)
    cv2.putText(img, 'Test Text', (50, 120), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 0, 0), 2)
    
    # 保存图像
    test_image_path = "/Users/cadany/Desktop/code/labs/BiddingChecker/backend/test_real_image.png"
    cv2.imwrite(test_image_path, img)
    print(f"创建测试图像: {test_image_path}")
    
    # 测试OCR
    config = ProcessingConfig(ocr_enabled=True, ocr_service_type="local")
    converter = PDFToTextConverter(config)
    
    test_image = Image.open(test_image_path)
    print(f"测试图像尺寸: {test_image.size}")
    
    ocr_result = converter._local_ocr(test_image)
    print(f"真实图像OCR结果: '{ocr_result}'")
    
    # 测试不同尺寸的处理
    print("\n测试不同尺寸图像的OCR:")
    
    # 小图像
    small_img = test_image.resize((75, 150))
    small_result = converter._local_ocr(small_img)
    print(f"小图像OCR结果: '{small_result}' (尺寸: {small_img.size})")
    
    # 中等图像
    medium_img = test_image.resize((225, 450))
    medium_result = converter._local_ocr(medium_img)
    print(f"中等图像OCR结果: '{medium_result}' (尺寸: {medium_img.size})")
    
    # 大图像
    large_img = test_image.resize((450, 900))
    large_result = converter._local_ocr(large_img)
    print(f"大图像OCR结果: '{large_result}' (尺寸: {large_img.size})")

if __name__ == "__main__":
    test_ocr_with_real_image()
    test_pdf_with_ocr()
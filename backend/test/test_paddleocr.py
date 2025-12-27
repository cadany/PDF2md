import os
import sys
import cv2
import numpy as np
from PIL import Image
import io

# 添加项目根目录到Python路径
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

from service.pdf_to_text_converter import PDFToTextConverter, ProcessingConfig

def test_ocr_functionality():
    """测试PaddleOCR功能"""
    print("开始测试PaddleOCR功能...")
    
    # 创建转换器实例
    config = ProcessingConfig(ocr_enabled=True, ocr_service_type="local")
    converter = PDFToTextConverter(config)
    
    # 创建一个简单的测试图像，包含一些文字
    # 这里我们使用一个实际的图像文件进行测试
    test_image_path = "/Users/cadany/Desktop/code/labs/BiddingChecker/backend/test_image.png"
    
    # 如果测试图像不存在，创建一个
    if not os.path.exists(test_image_path):
        print("创建测试图像...")
        # 创建一个带有文字的简单图像
        img = np.zeros((200, 400, 3), dtype=np.uint8)
        img.fill(255)  # 白色背景
        
        # 添加一些文字
        cv2.putText(img, '测试文字 Test Text', (50, 100), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 0, 0), 2)
        
        # 保存图像
        cv2.imwrite(test_image_path, img)
        print(f"测试图像已创建: {test_image_path}")
    
    # 测试OCR功能
    try:
        # 加载测试图像
        test_image = Image.open(test_image_path)
        print(f"测试图像尺寸: {test_image.size}")
        
        # 执行OCR
        ocr_result = converter._local_ocr(test_image)
        print(f"OCR结果: {ocr_result}")
        
        # 测试不同尺寸的图像
        print("\n测试不同尺寸的图像处理:")
        
        # 小图像测试
        small_img = test_image.resize((50, 25))
        print(f"小图像尺寸: {small_img.size}")
        small_result = converter._local_ocr(small_img)
        print(f"小图像OCR结果: {small_result}")
        
        # 中等图像测试
        medium_img = test_image.resize((150, 75))
        print(f"中等图像尺寸: {medium_img.size}")
        medium_result = converter._local_ocr(medium_img)
        print(f"中等图像OCR结果: {medium_result}")
        
        # 大图像测试
        large_img = test_image.resize((400, 200))
        print(f"大图像尺寸: {large_img.size}")
        large_result = converter._local_ocr(large_img)
        print(f"大图像OCR结果: {large_result}")
        
        print("\nPaddleOCR功能测试完成")
        
    except Exception as e:
        print(f"OCR测试过程中出现错误: {e}")
        import traceback
        traceback.print_exc()

def test_pdf_conversion():
    """测试PDF转换功能"""
    # 检查是否存在PDF测试文件
    test_pdf_path = "/Users/cadany/Desktop/code/labs/BiddingChecker/backend/test.pdf"
    
    if os.path.exists(test_pdf_path):
        print(f"\n开始测试PDF转换: {test_pdf_path}")
        
        config = ProcessingConfig(ocr_enabled=True, ocr_service_type="local")
        converter = PDFToTextConverter(config)
        
        try:
            output_path = converter.convert_pdf_to_text(
                pdf_path=test_pdf_path,
                start_page=1,
                end_page=2
            )
            print(f"PDF转换完成，输出文件: {output_path}")
        except Exception as e:
            print(f"PDF转换过程中出现错误: {e}")
            import traceback
            traceback.print_exc()
    else:
        print(f"\n未找到测试PDF文件: {test_pdf_path}")

if __name__ == "__main__":
    test_ocr_functionality()
    test_pdf_conversion()
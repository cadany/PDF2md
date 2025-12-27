import cv2
import numpy as np
import pytesseract
from PIL import Image
import io

def test_basic_ocr(image_path):
    """测试基础OCR功能"""
    image = Image.open(image_path)
    open_cv_image = cv2.cvtColor(np.array(image), cv2.COLOR_RGB2BGR)
    gray = cv2.cvtColor(open_cv_image, cv2.COLOR_BGR2GRAY)
    
    # 基础OCR
    basic_text = pytesseract.image_to_string(gray, lang='chi_sim+eng')
    print("基础OCR结果:")
    print(basic_text[:200])
    print()
    
    # 使用原始方法
    _, thresh = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
    denoised = cv2.medianBlur(thresh, 3)
    kernel = np.ones((1, 1), np.uint8)
    processed = cv2.dilate(denoised, kernel, iterations=1)
    processed = cv2.erode(processed, kernel, iterations=1)
    
    original_method_text = pytesseract.image_to_string(processed, lang='chi_sim+eng')
    print("原始方法结果:")
    print(original_method_text[:200])
    print()
    
    # 使用优化方法
    height, width = open_cv_image.shape[:2]
    if height < 100 or width < 100:
        open_cv_image = cv2.resize(open_cv_image, None, fx=3, fy=3, interpolation=cv2.INTER_CUBIC)
    
    gray = cv2.cvtColor(open_cv_image, cv2.COLOR_BGR2GRAY)
    blurred = cv2.GaussianBlur(gray, (3, 3), 0)
    adaptive_thresh = cv2.adaptiveThreshold(blurred, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY, 11, 2)
    kernel = np.ones((2, 2), np.uint8)
    processed = cv2.morphologyEx(adaptive_thresh, cv2.MORPH_CLOSE, kernel)
    denoised = cv2.medianBlur(processed, 3)
    
    # 尝试多种配置
    ocr_configs = [
        r'--oem 3 --psm 6',
        r'--oem 3 --psm 4',
        r'--oem 3 --psm 3',
        r'--oem 3 --psm 13',
    ]
    
    languages = ['chi_sim+eng', 'chi_sim', 'eng']
    
    best_text = ""
    best_confidence = 0
    
    for config in ocr_configs:
        for lang in languages:
            try:
                text = pytesseract.image_to_string(denoised, config=config, lang=lang)
                if text.strip() and len(text.strip()) > len(best_text):
                    try:
                        data = pytesseract.image_to_data(denoised, config=config, lang=lang, output_type=pytesseract.Output.DICT)
                        confidences = [int(conf) for conf in data['conf'] if int(conf) > 0]
                        avg_confidence = sum(confidences) / len(confidences) if confidences else 0
                        
                        if avg_confidence > best_confidence:
                            best_confidence = avg_confidence
                            best_text = text
                    except:
                        if len(text.strip()) > len(best_text):
                            best_text = text
            except:
                continue
    
    print("优化方法结果:")
    print(best_text[:200])
    print(f"最佳置信度: {best_confidence}")

if __name__ == "__main__":
    print("测试OCR改进方法")
    # Note: This would require an actual image file to test
    # test_basic_ocr("path_to_test_image.png")
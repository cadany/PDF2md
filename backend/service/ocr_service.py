import logging
from typing import Optional
from dataclasses import dataclass

try:
    from paddleocr import PaddleOCR , benchmark
    import cv2
    import numpy as np
    from PIL import Image
    OCR_AVAILABLE = True
except ImportError:
    OCR_AVAILABLE = False


@dataclass
class ProcessingConfig:
    ocr_service_type: str = "local"  # "local" 或 "cloud"

class OCRService:
    def __init__(self, config: Optional[ProcessingConfig] = None):
        self.config = config or ProcessingConfig()
        self.logger = logging.getLogger(f"service.{self.__class__.__name__}")
        # 使用uvicorn的日志配置，不添加自定义处理器
        
        # 检查OCR库是否可用
        if not OCR_AVAILABLE:
            self.logger.info("OCR库不可用。请安装paddleocr、opencv-python和Pillow以获得OCR功能。")
        
        # 初始化OCR引擎（如果可用）
        self.ocr = None
        if OCR_AVAILABLE and self.config.ocr_service_type == "local":
            try:
                self.logger.info("初始化PaddleOCR...")
                self.ocr = PaddleOCR(lang='ch',
                    # device="gpu",
                    # enable_hpi=True,
                    # cpu_threads=8,
                    use_doc_orientation_classify=False, # 指定不使用文档方向分类模型
                    use_doc_unwarping=False, # 指定不使用文本图像矫正模型
                    use_textline_orientation=False # 指定不使用文本行方向分类模型    
                    ) 
                self.logger.info("PaddleOCR初始化成功!")
            except Exception as e:
                self.logger.error(f"初始化PaddleOCR失败: {e}")
    


    def perform_ocr(self, image: Image.Image) -> str:
        """使用配置的服务对图像执行OCR"""
        if self.config.ocr_service_type == "local":
            return self._local_ocr(image)
        elif self.config.ocr_service_type == "cloud":
            return self._cloud_ocr(image)
        else:
            raise ValueError(f"未知OCR服务类型: {self.config.ocr_service_type}")
     
    def _local_ocr(self, image: Image.Image) -> str:
        """使用PaddleOCR执行本地OCR"""
        img_array = self._preprocess_image(image)

        # 使用PaddleOCR进行文字识别
        self.logger.info("开始OCR识别...")
        result = self.ocr.predict(img_array)
        self.logger.debug(f"OCR识别结果: {result}")

        extracted_text = []
        # 提取识别结果中的文本
        if result and len(result) > 0 and 'rec_texts' in result[0]:
            texts = result[0]['rec_texts']
            self.logger.debug(f"OCR识别文本: {texts}")
            for text in texts:
                if text and len(text) > 0:
                    extracted_text.append(text)
        
        final_text = "\n".join(extracted_text)
        return final_text.strip()

    def _cloud_ocr(self, image: Image.Image) -> str:
        """使用云OCR服务执行OCR"""
        raise NotImplementedError("云OCR服务未实现")

    def _preprocess_image(self, image: Image.Image) -> np.ndarray:
        """对图像进行预处理以提高OCR准确性"""
        # 将PIL图像转换为numpy数组
        img_array = np.array(image)
        
        # 处理不同图像格式
        if len(img_array.shape) == 3:
            if img_array.shape[2] == 4:  # RGBA格式
                # 将RGBA转换为RGB（移除alpha通道）
                img_array_rgb = cv2.cvtColor(img_array, cv2.COLOR_RGBA2RGB)
            elif img_array.shape[2] == 3:  # RGB格式
                img_array_rgb = img_array
            else:
                # 其他格式，转换为RGB
                img_array_rgb = cv2.cvtColor(img_array, cv2.COLOR_BGR2RGB)
        else:
            # 灰度图，转换为RGB
            img_array_rgb = cv2.cvtColor(img_array, cv2.COLOR_GRAY2RGB)
        
        # 转换为BGR供OpenCV使用
        img_array_bgr = cv2.cvtColor(img_array_rgb, cv2.COLOR_RGB2BGR)
        
        # 对于低质量图像进行适度增强，高质量图像则最小化处理
        height, width = img_array_bgr.shape[:2]

        # 当图片尺寸大于1200时，进行缩小处理，避免OCR识别失败或时间超时或“segmentation fault”
        if max(height, width) > 1200:  
            # 图像尺寸太大，可能需要缩小
            scale = 1200 / max(height, width)
            new_width = int(width * scale)
            new_height = int(height * scale)
            img_array_bgr = cv2.resize(img_array_bgr, (new_width, new_height), interpolation=cv2.INTER_CUBIC)
            
        # 检查图像大小，只在确实很小时才放大，避免改变文本顺序
        # 提高阈值以避免对正常大小的图像进行不必要的处理
        if height < 100 or width < 100:
            # 放大图像以提高OCR准确性
            img_array_bgr = cv2.resize(img_array_bgr, None, fx=3, fy=3, interpolation=cv2.INTER_CUBIC)
        elif height < 200 or width < 200:
            # 中等大小的图像适度放大
            img_array_bgr = cv2.resize(img_array_bgr, None, fx=2, fy=2, interpolation=cv2.INTER_CUBIC)
        
        # 将处理后的图像转换回RGB格式供PaddleOCR使用
        img_array_rgb = cv2.cvtColor(img_array_bgr, cv2.COLOR_BGR2RGB)
        
        return img_array_rgb
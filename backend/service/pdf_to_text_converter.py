"""
PDF转文本转换器，具有OCR功能
该模块将复杂的PDF文档转换为文本，同时保留格式
并使用OCR从图像中提取文本。
输出格式针对LLM处理进行了优化。
"""

import fitz  # PyMuPDF - 用于PDF处理的库
import os
import json
import logging
import io
import numpy as np
from typing import Optional, Dict, Any, List
from dataclasses import dataclass
from pathlib import Path

# 初始化OCR可用性标志
OCR_AVAILABLE = False
PADDLE_OCR_MODULE = None

try:
    import paddleocr
    PADDLE_OCR_MODULE = paddleocr
    from PIL import Image
    import cv2
    import numpy as np
    OCR_AVAILABLE = True
except ImportError:
    print("OCR库不可用。请安装paddleocr、opencv-python和Pillow以获得OCR功能。")
    # 即使OCR不可用，也要确保cv2和Image可用
    import cv2
    from PIL import Image


@dataclass
class ProcessingConfig:
    """PDF处理配置"""
    ocr_enabled: bool = True
    ocr_service_type: str = "local"  # "local" 或 "cloud"
    cloud_ocr_endpoint: Optional[str] = None
    cloud_ocr_api_key: Optional[str] = None
    preserve_formatting: bool = True
    include_images: bool = True
    include_tables: bool = True
    output_format: str = "text"  # "text", "json", "markdown"


class PDFToTextConverter:
    """
    一个全面的PDF转文本转换器，保留复杂格式
    并使用OCR从图像中提取文本。
    输出格式针对LLM处理进行了优化。
    """
    
    def __init__(self, config: Optional[ProcessingConfig] = None):
        self.config = config or ProcessingConfig()
        self.logger = self._setup_logger()
        # 初始化PaddleOCR
        if OCR_AVAILABLE:
            try:
                self.ocr = PADDLE_OCR_MODULE.PaddleOCR(use_angle_cls=True, lang='ch')
            except Exception as e:
                self.logger.error(f"初始化PaddleOCR失败: {e}")
                # 注意：不要在这里重新赋值OCR_AVAILABLE，因为它会导致UnboundLocalError
        
    def _setup_logger(self) -> logging.Logger:
        """设置转换器的日志"""
        logger = logging.getLogger(__name__)
        logger.setLevel(logging.INFO)
        
        if not logger.handlers:
            handler = logging.StreamHandler()
            formatter = logging.Formatter(
                '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
            )
            handler.setFormatter(formatter)
            logger.addHandler(handler)
        
        return logger
    
    def convert_pdf_to_text(
        self, 
        pdf_path: str, 
        start_page: Optional[int] = None, 
        end_page: Optional[int] = None,
        output_path: Optional[str] = None
    ) -> str:
        """
        转换PDF为文本，保留格式并支持OCR
        
        Args:
            pdf_path: 输入PDF文件的路径
            start_page: 起始页码（从1开始），默认为1
            end_page: 结束页码（从1开始），默认为最后一页
            output_path: 保存输出文本文件的路径
            
        Returns:
            输出文本文件的路径
        """
        if not os.path.exists(pdf_path):
            raise FileNotFoundError(f"未找到PDF文件: {pdf_path}")
        
        doc = None
        try:
            doc = fitz.open(pdf_path)
            total_pages = len(doc)
            
            # 设置默认页面范围
            if start_page is None:
                start_page = 1
            if end_page is None:
                end_page = total_pages
            
            # 验证页面范围
            if start_page < 1 or start_page > total_pages:
                raise ValueError(f"起始页码必须在1到{total_pages}之间")
            if end_page < start_page or end_page > total_pages:
                raise ValueError(f"结束页码必须在{start_page}到{total_pages}之间")
            
            self.logger.info(f"开始PDF转换: {pdf_path}")
            self.logger.info(f"处理页面 {start_page} 到 {end_page} 共 {total_pages} 页")
            
            # 处理每一页
            output_text = ""
            total_pages_to_process = end_page - start_page + 1
            
            for page_idx, page_num in enumerate(range(start_page, end_page + 1)):
                try:
                    progress = (page_idx + 1) / total_pages_to_process * 100
                    self.logger.info(f"正在处理页面 {page_num}/{end_page} ({progress:.1f}%)")
                    
                    page_content = self._process_page(doc, page_num - 1)  # PyMuPDF使用0索引
                    output_text += page_content
                    
                    # 添加页面分隔符（更简洁，更适合LLM处理）
                    if page_num < end_page:
                        output_text += f"\n\n--- 页面 {page_num} 结束 ---\n\n"  # 简洁的页面分隔符
                        
                except Exception as e:
                    self.logger.error(f"处理页面 {page_num} 时出错: {e}")
                    # 向输出添加错误信息但继续处理
                    output_text += f"\n错误: 未能处理页面 {page_num} - {str(e)}\n"
                    continue
            
            # 将输出写入文件
            if output_path is None:
                base_name = Path(pdf_path).stem
                output_path = f"{base_name}_converted.txt"
            
            with open(output_path, 'w', encoding='utf-8') as f:
                f.write(output_text)
            
            self.logger.info(f"转换完成。输出保存到: {output_path}")
            return output_path
            
        except Exception as e:
            self.logger.error(f"PDF转换过程中出错: {e}")
            raise
        finally:
            if doc:
                doc.close()
    
    def _process_page(self, doc: fitz.Document, page_index: int) -> str:
        """
        处理PDF文档的单页
        
        Args:
            doc: PyMuPDF文档对象
            page_index: 要处理的页面索引
            
        Returns:
            页面的文本内容
        """
        page = doc[page_index]
        
        # 获取页面块（文本、图像、表格）
        blocks = page.get_text("dict")["blocks"]
        
        # 按Y坐标排序块，以确保正确的文档顺序
        sorted_blocks = sorted(blocks, key=lambda block: block['bbox'][1])  # 按Y1坐标排序
        
        # 处理所有块，包括文本、图像和表格
        processed_content = self._process_sorted_blocks(page, sorted_blocks, page_index)
        
        return processed_content
    
    def _process_sorted_blocks(self, page: fitz.Page, sorted_blocks: List[Dict], page_index: int) -> str:
        """处理按顺序排列的块，确保OCR文本和表格插入到正确位置"""
        # 创建一个包含所有元素的列表（文本块、图像块和表格），按Y坐标排序
        all_elements = []
        
        # 添加文本块
        for block in sorted_blocks:
            if "lines" in block:  # 文本块
                for line in block["lines"]:
                    line_text = ""
                    for span in line["spans"]:
                        line_text += span["text"]
                    
                    # 添加保留格式的行
                    bbox = line["bbox"]
                    x0, y0, x1, y1 = bbox
                    
                    # 根据位置确定对齐方式（但不使用标记，而是通过自然缩进来表示）
                    page_width = page.rect.width
                    left_margin = x0
                    right_margin = page_width - x1
                    center_margin = abs(left_margin - right_margin)
                    
                    if center_margin < 30:  # 居中文本
                        # 通过缩进实现居中效果，更适合LLM处理
                        formatted_text = f"    {line_text}\n"  # 添加缩进以表示居中
                    elif right_margin < 30:  # 右对齐
                        # 通过缩进实现右对齐效果，更适合LLM处理
                        formatted_text = f"        {line_text}\n"  # 添加更多缩进以表示右对齐
                    else:  # 左对齐
                        formatted_text = f"{line_text}\n"
                    
                    # 将文本块作为元素添加到列表中
                    all_elements.append({
                        'type': 'text',
                        'y_position': y0,  # 使用Y坐标作为排序位置
                        'content': formatted_text
                    })
        
        # 添加表格块
        if self.config.include_tables:
            try:
                tables = page.find_tables()
                for table in tables:
                    # 提取表格数据
                    table_data = table.extract()
                    # 获取表格边界框坐标
                    table_bbox = table.bbox
                    # 格式化表格为markdown
                    markdown_table = self._format_table_as_markdown(table_data)
                    # 添加表格到元素列表
                    all_elements.append({
                        'type': 'table',
                        'y_position': table_bbox[1],  # 使用表格的Y坐标 (top coordinate)
                        'content': f"\n{markdown_table}\n"
                    })
            except Exception as e:
                self.logger.warning(f"处理页面 {page_index + 1} 上的表格时出错: {e}")
        
        # 添加图像块（带OCR处理）
        if self.config.ocr_enabled and OCR_AVAILABLE:
            image_list = page.get_images()
            if image_list:
                for img_index, img in enumerate(image_list):
                    xref = img[0]  # 图像的xref
                    try:
                        # 获取图像对象
                        pix = fitz.Pixmap(page.parent, xref)
                        if pix.n < 5:  # 灰度或RGB
                            # 获取图像在页面上的位置
                            img_rects = page.get_image_rects(xref)
                            
                            if img_rects:
                                for rect_idx, rect in enumerate(img_rects):
                                    # 执行OCR
                                    img_data = pix.tobytes("png")
                                    pil_img = Image.open(io.BytesIO(img_data))
                                    
                                    ocr_text = self._perform_ocr(pil_img)
                                    
                                    # 将图像块作为元素添加到列表中，按Y坐标排序
                                    if ocr_text.strip():
                                        # 添加OCR文本到图像位置
                                        image_content = f"\n[图像OCR文本 - 位置: 第{page_index + 1}页, 坐标({rect.x0:.2f}, {rect.y0:.2f}) - ({rect.x1:.2f}, {rect.y1:.2f})]\n{ocr_text}\n"
                                    else:
                                        # 即使OCR没有识别出文本，也记录图像位置信息
                                        image_content = f"\n[图像 - 位置: 第{page_index + 1}页, 坐标({rect.x0:.2f}, {rect.y0:.2f}) - ({rect.x1:.2f}, {rect.y1:.2f})]\n"
                                    
                                    # 使用图像的Y坐标作为排序位置
                                    all_elements.append({
                                        'type': 'image',
                                        'y_position': rect.y0,  # 使用图像的Y坐标
                                        'content': image_content
                                    })
                            else:
                                # 如果没有位置信息，使用简化的格式并将其添加到末尾
                                all_elements.append({
                                    'type': 'image',
                                    'y_position': float('inf'),  # 将无位置信息的图像放到最后
                                    'content': f"\n[页面 {page_index + 1} 上的图像 {img_index + 1}]\n"
                                })
                        pix = None  # 释放内存
                    except Exception as e:
                        self.logger.warning(f"处理页面 {page_index + 1} 上的图像 {xref} 时出错: {e}")
        
        # 按Y坐标位置排序所有元素
        sorted_elements = sorted(all_elements, key=lambda el: el['y_position'])
        
        # 按顺序生成内容
        content = []
        for element in sorted_elements:
            content.append(element['content'])
        
        return "".join(content)
    
    def _process_image_at_position(self, page: fitz.Page, xref: int, page_index: int) -> str:
        """在特定位置处理图像并使用OCR提取文本"""
        if not self.config.ocr_enabled or not OCR_AVAILABLE:
            return ""
        
        try:
            # 获取图像对象
            pix = fitz.Pixmap(page.parent, xref)
            
            # 转换为图像并执行OCR
            if pix.n < 5:  # 灰度或RGB
                img_data = pix.tobytes("png")
                pil_img = Image.open(io.BytesIO(img_data))
                
                # 执行OCR
                ocr_text = self._perform_ocr(pil_img)
                
                if ocr_text.strip():
                    # 获取图像在页面上的位置
                    img_rects = page.get_image_rects(xref)
                    
                    if img_rects:
                        content = []
                        for rect in img_rects:
                            # 添加OCR文本到图像位置
                            content.append(f"\n[图像OCR文本 - 坐标: ({rect.x0:.2f}, {rect.y0:.2f}) - ({rect.x1:.2f}, {rect.y1:.2f})]\n")
                            content.append(ocr_text)
                            content.append("\n")
                        return "".join(content)
                    else:
                        # 如果没有位置信息，使用简化的格式
                        return f"\n[OCR文本: {ocr_text}]\n"
            
            pix = None  # 释放内存
            
        except Exception as e:
            self.logger.warning(f"处理页面 {page_index + 1} 上的图像 {xref} 时出错: {e}")
        
        return ""
    

    
    def _perform_ocr(self, image: Image.Image) -> str:
        """使用配置的服务对图像执行OCR"""
        if self.config.ocr_service_type == "local":
            return self._local_ocr(image)
        elif self.config.ocr_service_type == "cloud":
            return self._cloud_ocr(image)
        else:
            raise ValueError(f"未知OCR服务类型: {self.config.ocr_service_type}")
    
    def _local_ocr(self, image: Image.Image) -> str:
        """使用PaddleOCR执行本地OCR"""
        try:
            # 将PIL图像转换为numpy数组以供PaddleOCR使用
            img_array = np.array(image)
            
            # 对于低质量图像进行适度增强，高质量图像则最小化处理
            height, width = img_array.shape[:2]
            
            # 检查图像大小，如果太小则放大以提高OCR准确性
            if height < 100 or width < 100:
                # 放大图像以提高OCR准确性
                img_array = cv2.resize(img_array, None, fx=3, fy=3, interpolation=cv2.INTER_CUBIC)
            elif height < 200 or width < 200:
                # 中等大小的图像适度放大
                img_array = cv2.resize(img_array, None, fx=2, fy=2, interpolation=cv2.INTER_CUBIC)
            
            # 使用PaddleOCR进行文字识别
            if hasattr(self, 'ocr') and self.ocr:
                result = self.ocr.ocr(img_array, cls=True)
                
                # 提取识别结果中的文本
                extracted_text = []
                if result and result[0]:  # 检查是否有检测结果
                    for item in result[0]:
                        if len(item) > 1 and len(item[1]) > 0:
                            text = item[1][0]  # 提取文本部分
                            confidence = item[1][1]  # 提取置信度
                            
                            # 只保留置信度较高的文本
                            if confidence > 0.5:  # 置信度阈值
                                extracted_text.append(text)
                
                final_text = " ".join(extracted_text)
                return final_text.strip()
            else:
                self.logger.error("PaddleOCR实例不可用")
                return ""
                
        except Exception as e:
            self.logger.error(f"本地OCR失败: {e}")
            return ""
    
    def _cloud_ocr(self, image: Image.Image) -> str:
        """使用API执行云OCR（占位符实现）"""
        try:
            if not self.config.cloud_ocr_endpoint or not self.config.cloud_ocr_api_key:
                self.logger.warning("未提供云OCR端点或API密钥，回退到本地OCR")
                return self._local_ocr(image)
            
            # 将图像转换为base64以进行API请求
            import base64
            import requests
            
            # 将图像保存为字节
            img_byte_arr = io.BytesIO()
            image.save(img_byte_arr, format='PNG')
            img_byte_arr = img_byte_arr.getvalue()
            img_base64 = base64.b64encode(img_byte_arr).decode('utf-8')
            
            # 准备请求数据（这是一个通用示例 - 根据您的云服务进行调整）
            headers = {
                'Authorization': f'Bearer {self.config.cloud_ocr_api_key}',
                'Content-Type': 'application/json'
            }
            
            data = {
                'image': img_base64,
                'language': 'zh-Hans'  # 根据您的需要进行调整
            }
            
            # 发起API请求
            response = requests.post(self.config.cloud_ocr_endpoint, json=data, headers=headers)
            
            if response.status_code == 200:
                result = response.json()
                # 从响应中提取文本（格式取决于特定API）
                # 这是一个通用示例 - 根据您的云服务响应格式进行调整
                if 'text' in result:
                    return result['text']
                elif 'result' in result:
                    return result['result']
                else:
                    self.logger.warning(f"意外的云OCR响应格式: {result}")
                    return self._local_ocr(image)
            else:
                self.logger.error(f"云OCR API请求失败，状态码 {response.status_code}: {response.text}")
                return self._local_ocr(image)
                
        except Exception as e:
            self.logger.error(f"云OCR失败: {e}，回退到本地OCR")
            return self._local_ocr(image)
    
    def _process_tables(self, page: fitz.Page) -> str:
        """处理页面中的表格"""
        content = []
        
        # 尝试使用PyMuPDF的表格功能提取表格
        try:
            tables = page.find_tables()
            
            for i, table in enumerate(tables):
                try:
                    table_data = table.extract()
                    if table_data:
                        content.append(f"\n表格 {i + 1}:\n")  # 更简洁的表格标记
                        
                        # 以更好的对齐方式将表格格式化为文本
                        # 查找每列的最大宽度
                        col_widths = []
                        for row in table_data:
                            if row:
                                for j, cell in enumerate(row):
                                    cell_str = str(cell or "")
                                    if j >= len(col_widths):
                                        col_widths.append(len(cell_str))
                                    else:
                                        col_widths[j] = max(col_widths[j], len(cell_str))
                        
                        # 使用适当的间距格式化每行
                        for row in table_data:
                            if row:  # 跳过空行
                                formatted_cells = []
                                for j, cell in enumerate(row):
                                    cell_str = str(cell or "")
                                    if j < len(col_widths):
                                        formatted_cells.append(cell_str.ljust(col_widths[j]))
                                    else:
                                        formatted_cells.append(cell_str)
                                content.append(" | ".join(formatted_cells) + "\n")
                        
                        content.append("\n")  # 简单换行而不是特殊标记
                except Exception as e:
                    self.logger.warning(f"处理表格 {i + 1} 时出错: {e}")
        except Exception as e:
            self.logger.warning(f"页面上未找到表格或查找表格时出错: {e}")
        
        return "".join(content)
    
    def _format_table_as_markdown(self, table_data: List[List[str]]) -> str:
        """将表格数据格式化为markdown格式"""
        if not table_data or not any(row for row in table_data):
            return ""
        
        # 过滤掉完全为空的行
        filtered_table_data = [row for row in table_data if any(cell and str(cell).strip() for cell in row)]
        
        if not filtered_table_data:
            return ""
        
        # 找出每列的最大宽度
        col_widths = []
        for row in filtered_table_data:
            for j, cell in enumerate(row):
                cell_str = str(cell or "")
                if j >= len(col_widths):
                    col_widths.append(len(cell_str))
                else:
                    col_widths[j] = max(col_widths[j], len(cell_str))
        
        # 构建markdown表格
        markdown_lines = []
        
        for i, row in enumerate(filtered_table_data):
            # 格式化单元格内容
            formatted_cells = []
            for j, cell in enumerate(row):
                cell_str = str(cell or "")
                if j < len(col_widths):
                    formatted_cells.append(cell_str.ljust(col_widths[j]))
                else:
                    formatted_cells.append(cell_str)
            
            # 添加行
            markdown_lines.append("| " + " | ".join(formatted_cells) + " |")
            
            # 在表头后添加分隔行
            if i == 0:
                separator_cells = []
                for width in col_widths:
                    separator_cells.append("-" * width)
                markdown_lines.append("| " + " | ".join(separator_cells) + " |")
        
        return "\n".join(markdown_lines)


def convert_pdf_to_text(
    pdf_path: str,
    start_page: Optional[int] = None,
    end_page: Optional[int] = None,
    output_path: Optional[str] = None,
    config: Optional[ProcessingConfig] = None
) -> str:
    """
    主函数，用于转换PDF为文本并保留复杂格式
    
    Args:
        pdf_path: 输入PDF文件的路径
        start_page: 起始页码（从1开始），默认为1
        end_page: 结束页码（从1开始），默认为最后一页
        output_path: 保存输出文本文件的路径
        config: 处理配置
        
    Returns:
        输出文本文件的路径
    """
    converter = PDFToTextConverter(config)
    return converter.convert_pdf_to_text(pdf_path, start_page, end_page, output_path)


# 用于测试目的
if __name__ == "__main__":
    import sys
    
    if len(sys.argv) < 2:
        print("用法: python pdf_to_text_converter.py <pdf_path> [output_path] [start_page] [end_page]")
        print("示例: python pdf_to_text_converter.py document.pdf output.txt 1 10")
        sys.exit(1)
    
    pdf_path = sys.argv[1]
    output_path = sys.argv[2] if len(sys.argv) > 2 else None
    start_page = int(sys.argv[3]) if len(sys.argv) > 3 and sys.argv[3].isdigit() else None
    end_page = int(sys.argv[4]) if len(sys.argv) > 4 and sys.argv[4].isdigit() else None
    print(f"输入PDF: {pdf_path}")
    print(f"起始页码: {start_page}")
    print(f"结束页码: {end_page}")
    print(f"输出路径: {output_path}")
    
    try:
        result_path = convert_pdf_to_text(pdf_path, start_page, end_page, output_path)
        print(f"PDF转换成功完成。输出保存到: {result_path}")
    except Exception as e:
        print(f"PDF转换过程中出错: {e}")
        sys.exit(1)
"""
PDF转Markdown转换器 V2
基于PyMuPDF和pdfplumber，专门处理大文件和高稳定性需求
"""

import fitz
import pdfplumber
import os
import sys
import time
import logging
from typing import Optional, Dict, List, Tuple, Any
from dataclasses import dataclass
from pathlib import Path
from PIL import Image
import io

# 添加项目根目录到Python路径
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# 修复OCR服务导入
from service.ocr_service import OCRService

@dataclass
class ConversionConfig:
    """转换配置"""
    # 表格处理配置
    table_detection_enabled: bool = True
    table_min_columns: int = 2
    
    # 文本处理配置
    preserve_formatting: bool = True
    extract_images: bool = True  # 启用图片处理
    
    # 性能配置
    chunk_size: int = 10  # 每批处理的页面数
    progress_update_interval: int = 10  # 进度更新间隔（页面数）
    
    # 进度回调配置
    progress_callback: Optional[callable] = None  # 进度回调函数
    

class PDFConverterV2:
    """
    PDF转Markdown转换器 V2
    专门处理大文件和高稳定性需求
    """
    
    def __init__(self, config: Optional[ConversionConfig] = None):
        self.config = config or ConversionConfig()
        self.processing_stats = {
            'total_pages': 0,
            'processed_pages': 0,
            'tables_found': 0,
            'errors': [],
            'start_time': None,
            'end_time': None
        }
        self.ocr_service = OCRService()
        self.logger = logging.getLogger(f"service.{self.__class__.__name__}")
        # 使用uvicorn的日志配置，不添加自定义处理器
        self.logger.info("PDFConverterV2初始化完成")
    
    def convert_pdf(
        self,
        pdf_path: str,
        output_path: Optional[str] = None,
        start_page: int = 1,
        end_page: Optional[int] = None,
        progress_callback: Optional[callable] = None
    ) -> Dict[str, Any]:
        """
        转换PDF文件为Markdown格式
        
        Args:
            pdf_path: 输入PDF文件路径
            output_path: 输出文件路径，如果为None则自动生成
            start_page: 起始页码（从1开始）
            end_page: 结束页码（从1开始），如果为None则处理到最后一页
            
        Returns:
            转换结果统计信息
        """
        self.processing_stats['start_time'] = time.time()
        
        # 验证输入参数
        self._validate_inputs(pdf_path, start_page, end_page)
        
        # 生成输出路径
        if output_path is None:
            output_path = self._generate_output_path(pdf_path)
        
        self.logger.info(f"开始转换PDF: {pdf_path}")
        self.logger.info(f"输出路径: {output_path}")
        self.logger.info(f"页面范围: {start_page}-{end_page or '末尾'}")
        
        try:
            # 打开PDF文件
            with fitz.open(pdf_path) as doc:
                total_pages = len(doc)
                self.processing_stats['total_pages'] = total_pages
                
                # 调整结束页码
                if end_page is None or end_page > total_pages:
                    end_page = total_pages
                
                actual_start = max(1, start_page)
                actual_end = min(total_pages, end_page)
                
                self.logger.info(f"实际处理页面: {actual_start}-{actual_end} (共{total_pages}页)")

                # 分批次处理页面
                markdown_content = self._process_pages_in_batches(doc, actual_start, actual_end, progress_callback)
                
                # 保存结果
                self._save_output(markdown_content, output_path)
                
                # 更新统计信息
                self.processing_stats['end_time'] = time.time()
                processing_time = self.processing_stats['end_time'] - self.processing_stats['start_time']
                
                self.logger.info(f"转换完成! 处理了{self.processing_stats['processed_pages']}页，"
                               f"发现{self.processing_stats['tables_found']}个表格，"
                               f"耗时{processing_time:.2f}秒")
                
                return {
                    'success': True,
                    'output_path': output_path,
                    'processing_time': processing_time,
                    'pages_processed': self.processing_stats['processed_pages'],
                    'tables_found': self.processing_stats['tables_found'],
                    'errors': self.processing_stats['errors']
                }
                
        except Exception as e:
            self.logger.error(f"转换过程中发生错误: {e}")
            self.processing_stats['errors'].append(str(e))
            return {
                'success': False,
                'error': str(e),
                'errors': self.processing_stats['errors']
            }
    
    def _validate_inputs(self, pdf_path: str, start_page: int, end_page: Optional[int]):
        """验证输入参数"""
        if not os.path.exists(pdf_path):
            raise FileNotFoundError(f"PDF文件不存在: {pdf_path}")
        
        if not pdf_path.lower().endswith('.pdf'):
            raise ValueError("输入文件必须是PDF格式")
        
        if start_page < 1:
            raise ValueError("起始页码必须大于等于1")
        
        if end_page is not None and end_page < start_page:
            raise ValueError("结束页码必须大于等于起始页码")
    
    def _generate_output_path(self, pdf_path: str) -> str:
        """生成输出文件路径"""
        pdf_path_obj = Path(pdf_path)
        pdf_name = pdf_path_obj.stem
        timestamp = int(time.time())
        # 保持与原文件相同的目录路径
        output_filename = f"{pdf_name}_converted_{timestamp}.md"
        return str(pdf_path_obj.parent / output_filename)
    
    def _process_pages_in_batches(
        self, 
        doc: fitz.Document, 
        start_page: int, 
        end_page: int,
        progress_callback: Optional[callable] = None
    ) -> str:
        """分批次处理页面"""
        markdown_parts = []
        
        # 分批次处理
        chunk_size = self.config.chunk_size
        for batch_start in range(start_page - 1, end_page, chunk_size):
            batch_end = min(batch_start + chunk_size, end_page)
            
            self.logger.info(f"处理页面批次: {batch_start + 1}-{batch_end}")
            
            batch_content = self._process_page_batch(doc, batch_start, batch_end)
            markdown_parts.append(batch_content)
            
            # 更新进度
            processed = min(batch_end - start_page + 1, self.processing_stats['total_pages'])
            progress = (processed / (end_page - start_page + 1)) * 100
            self.logger.info(f"处理进度: {progress:.1f}% ({processed}/{end_page - start_page + 1}页)")
            
            # 调用进度回调函数
            if progress_callback:
                try:
                    progress_callback(int(progress))
                except Exception as e:
                    self.logger.warning(f"进度回调调用失败: {e}")
        
        return '\n'.join(markdown_parts)
    
    def _process_page_batch(
        self, 
        doc: fitz.Document, 
        start_idx: int, 
        end_idx: int
    ) -> str:
        """处理一批页面"""
        batch_content = []
        
        for page_num in range(start_idx, end_idx):
            try:
                page_content = self._process_single_page(doc, page_num)
                batch_content.append(page_content)
                self.processing_stats['processed_pages'] += 1
                
                # 定期更新进度
                if self.processing_stats['processed_pages'] % self.config.progress_update_interval == 0:
                    self.logger.info(f"已处理 {self.processing_stats['processed_pages']} 页")
                    
            except Exception as e:
                error_msg = f"处理第{page_num + 1}页时发生错误: {e}"
                self.logger.error(error_msg)
                self.processing_stats['errors'].append(error_msg)
                
                # 添加错误标记到输出
                batch_content.append(f"\n<!-- 第{page_num + 1}页处理错误: {e} -->\n")
        
        return '\n'.join(batch_content)
    
    def _process_single_page(self, doc: fitz.Document, page_idx: int) -> str:
        """处理单个页面，保留表格和图片的原始位置"""
        page_num = page_idx + 1
        
        # 添加页面标题
        page_content = [f"\n## 第 {page_num} 页\n"]
        
        # 提取文本并插入占位符
        text_with_placeholders = self._extract_text_with_table_placeholders(doc, page_idx)
        
        # 提取表格和图片内容
        tables_dict = self._extract_tables_with_positions(doc, page_idx)
        images_dict = self._extract_images_with_positions(doc, page_idx)
        
        # 替换占位符
        final_content = self._replace_placeholders_with_tables(text_with_placeholders, tables_dict)
        final_content = self._replace_placeholders_with_images(final_content, images_dict)
        
        page_content.append(final_content)
        
        return '\n'.join(page_content)
    

    
    def _extract_table_safely(self, table) -> List[List[str]]:
        """安全地提取表格数据"""
        try:
            extracted_table = table.extract()
            return [[str(cell).strip() if cell else "" for cell in row] for row in extracted_table]
        except Exception as e:
            self.logger.warning(f"提取表格数据时发生错误: {e}")
            return []
    
    def _is_valid_table(self, table_data: List[List[str]]) -> bool:
        """检查表格数据是否有效"""
        if not table_data or len(table_data) < 2:
            return False
        
        max_columns = max(len(row) for row in table_data)
        has_content = any(cell.strip() for row in table_data for cell in row)
        
        return max_columns >= self.config.table_min_columns and has_content
    
    def _convert_table_to_markdown(self, table_data: List[List[str]]) -> str:
        """将表格数据转换为Markdown格式"""
        if not table_data or len(table_data) < 2:
            return ""
        
        cleaned_table = self._clean_table_data(table_data)
        headers = cleaned_table[0]
        
        markdown_lines = [
            f"| {' | '.join(headers)} |",
            f"| {' | '.join(['---'] * len(headers))} |"
        ]
        
        for row in cleaned_table[1:]:
            adjusted_row = row + [""] * (len(headers) - len(row))
            markdown_lines.append(f"| {' | '.join(adjusted_row[:len(headers)])} |")
        
        return '\n'.join(markdown_lines)
    
    def _clean_table_data(self, table_data: List[List[str]]) -> List[List[str]]:
        """清理和预处理表格数据"""
        return [[
            ' '.join(str(cell or '').strip().replace('\n', '<br>').split())
            for cell in row
        ] for row in table_data]
    
    def _bbox_overlap(self, bbox1, bbox2) -> bool:
        """检查两个边界框是否重叠"""
        x1_min, y1_min, x1_max, y1_max = bbox1
        x2_min, y2_min, x2_max, y2_max = bbox2
        return not (x1_max < x2_min or x1_min > x2_max or y1_max < y2_min or y1_min > y2_max)
    
    def _bbox_overlap_ratio(self, bbox1, bbox2) -> float:
        """计算两个边界框的重叠比例"""
        x1_min, y1_min, x1_max, y1_max = bbox1
        x2_min, y2_min, x2_max, y2_max = bbox2
        
        # 计算重叠区域
        overlap_x_min = max(x1_min, x2_min)
        overlap_y_min = max(y1_min, y2_min)
        overlap_x_max = min(x1_max, x2_max)
        overlap_y_max = min(y1_max, y2_max)
        
        if overlap_x_max < overlap_x_min or overlap_y_max < overlap_y_min:
            return 0.0
        
        overlap_area = (overlap_x_max - overlap_x_min) * (overlap_y_max - overlap_y_min)
        bbox1_area = (x1_max - x1_min) * (y1_max - y1_min)
        
        return overlap_area / bbox1_area if bbox1_area > 0 else 0.0
    
    def _extract_text_with_table_placeholders(self, doc: fitz.Document, page_idx: int) -> str:
        """使用PyMuPDF提取文本，在表格和图片位置插入占位符"""
        try:
            page = doc[page_idx]
            
            # 检测表格和图片位置
            table_positions = self._detect_table_positions(doc, page_idx)
            image_positions = self._detect_image_positions(doc, page_idx)
            
            # 提取并排序文本块
            text_blocks = page.get_text("dict")["blocks"]
            sorted_blocks = sorted(text_blocks, key=lambda b: b["bbox"][1])
            
            # 合并所有元素
            all_elements = []
            processed_table_indices = set()
            
            for block in sorted_blocks:
                if "lines" in block:  # 文本块
                    block_bbox = block["bbox"]
                    
                    # 检查是否在表格区域内
                    table_idx, overlap_ratio = self._find_table_overlap(block_bbox, table_positions)
                    
                    if table_idx >= 0 and overlap_ratio > 0.7:
                        # 添加表格占位符
                        if table_idx not in processed_table_indices:
                            placeholder = f"<!-- TABLE_PLACEHOLDER_{table_idx} -->"
                            all_elements.append(('table', table_idx, table_positions[table_idx][0][1], placeholder))
                            processed_table_indices.add(table_idx)
                        continue
                    else:
                        # 正常文本块
                        block_text = self._format_text_block(block)
                        if block_text.strip():
                            all_elements.append(('text', -1, block_bbox[1], block_text))
            
            # 添加图片占位符
            if image_positions and self.config.extract_images:
                for img_idx, (img_bbox, _) in enumerate(image_positions):
                    placeholder = f"<!-- IMAGE_PLACEHOLDER_{img_idx} -->"
                    all_elements.append(('image', img_idx, img_bbox[1], placeholder))
            
            # 按Y坐标排序并生成内容
            all_elements.sort(key=lambda x: x[2])
            formatted_content = []
            
            for element_type, _, _, content in all_elements:
                if element_type == 'table':
                    formatted_content.extend(["", content, ""])
                else:
                    formatted_content.append(content)
            
            return '\n'.join(formatted_content)
            
        except Exception as e:
            self.logger.warning(f"使用PyMuPDF提取第{page_idx + 1}页文本时发生错误: {e}")
            return f"<!-- 文本提取错误: {e} -->"
    
    def _find_table_overlap(self, block_bbox, table_positions) -> Tuple[int, float]:
        """查找文本块与表格的重叠情况"""
        table_idx = -1
        max_overlap_ratio = 0.0
        
        for i, (table_bbox, _) in enumerate(table_positions):
            if self._bbox_overlap(block_bbox, table_bbox):
                overlap_ratio = self._bbox_overlap_ratio(block_bbox, table_bbox)
                if overlap_ratio > max_overlap_ratio:
                    max_overlap_ratio = overlap_ratio
                    table_idx = i
        
        return table_idx, max_overlap_ratio
    
    def _extract_tables_with_positions(self, doc: fitz.Document, page_idx: int) -> Dict[int, str]:
        """提取表格内容并记录位置信息"""
        tables_dict = {}
        
        try:
            with pdfplumber.open(doc.name) as pdf:
                tables = pdf.pages[page_idx].find_tables()
                
                for i, table in enumerate(tables):
                    extracted_table = self._extract_table_safely(table)
                    
                    if extracted_table and len(extracted_table) > 1 and self._is_valid_table(extracted_table):
                        markdown_table = self._convert_table_to_markdown(extracted_table)
                        tables_dict[i] = f"**表格:**\n\n{markdown_table}\n"
                        
        except Exception as e:
            self.logger.warning(f"表格提取失败: {e}")
        
        return tables_dict
    
    def _replace_placeholders_with_tables(self, text_with_placeholders: str, tables_dict: Dict[int, str]) -> str:
        """用实际的表格内容替换占位符"""
        if not text_with_placeholders or not tables_dict:
            return text_with_placeholders
        
        result = text_with_placeholders
        for table_idx, table_content in sorted(tables_dict.items()):
            placeholder = f"<!-- TABLE_PLACEHOLDER_{table_idx} -->"
            result = result.replace(placeholder, table_content)
        
        return result
    
    def _detect_table_positions(self, doc: fitz.Document, page_idx: int) -> List[Tuple[Tuple[float, float, float, float], int]]:
        """检测表格位置和索引"""
        table_positions = []
        
        try:
            # 使用pdfplumber检测表格
            with pdfplumber.open(doc.name) as pdf:
                page_pdfplumber = pdf.pages[page_idx]
                tables = page_pdfplumber.find_tables()
                
                for i, table in enumerate(tables):
                    bbox = table.bbox
                    # 使用原始边界框
                    table_positions.append((bbox, i))
                    
        except Exception as e:
            self.logger.warning(f"表格位置检测失败: {e}")
        
        # 按Y坐标排序表格
        table_positions.sort(key=lambda x: x[0][1])
        
        return table_positions

    def _extract_images_with_positions(self, doc: fitz.Document, page_idx: int) -> Dict[int, str]:
        """提取图片内容并记录位置信息"""
        if not self.config.extract_images:
            return {}
            
        try:
            page = doc[page_idx]
            image_list = page.get_images()
            
            if not image_list:
                return {}
            
            images_dict = {}
            for img_index, img_info in enumerate(image_list):
                try:
                    image_markdown = f"\n**[第{page_idx + 1}页, 图片{img_index + 1}]**\n"
                    self.logger.info(f"\n图片 :{image_markdown}\n")
                    ##OCR图片内容
                    pix = fitz.Pixmap(page.parent, img_info[0])
                    if pix.n < 5:
                        img_data = pix.tobytes("png")
                        pil_img = Image.open(io.BytesIO(img_data))
                        # pil_img.save(f"../files/imgs/temp_img_{page_idx+1}_{img_index+1}.png")
                        ocr_text = self.ocr_service.perform_ocr(pil_img)
                        self.logger.info(f"OCR 结果: \n{ocr_text}")
                        image_markdown += f"```OCR 内容 [第{page_idx + 1}页, 图片{img_index + 1}]: \n{ocr_text} \n```\n"

                    images_dict[img_index] = image_markdown
                except Exception as img_error:
                    self.logger.warning(f"处理图片 {img_index} 时发生错误: {img_error}")
                    images_dict[img_index] = f"``` 图片 {img_index} 处理失败: {img_error} \n```\n"
                    
            return images_dict
        except Exception as e:
            self.logger.warning(f"图片提取失败: {e}")
            return {}

    def _detect_image_positions(self, doc: fitz.Document, page_idx: int) -> List[Tuple[Tuple[float, float, float, float], int]]:
        """检测图片位置和索引"""
        if not self.config.extract_images:
            return []
            
        try:
            page = doc[page_idx]
            image_list = page.get_images()
            
            if not image_list:
                return []
            
            image_positions = []
            for img_index, img_info in enumerate(image_list):
                img_rects = page.get_image_rects(img_info[0])
                
                if img_rects:
                    rect = img_rects[0]
                    img_bbox = (rect.x0, rect.y0, rect.x1, rect.y1)
                else:
                    page_rect = page.rect
                    img_height = min(100, page_rect.height * 0.1)
                    img_spacing = 20
                    
                    img_y_start = page_rect.height - (img_index + 1) * (img_height + img_spacing)
                    img_y_end = img_y_start + img_height
                    img_x_start = page_rect.width * 0.1
                    img_x_end = page_rect.width * 0.9
                    
                    img_bbox = (img_x_start, img_y_start, img_x_end, img_y_end)
                
                image_positions.append((img_bbox, img_index))
                    
        except Exception as e:
            self.logger.warning(f"表格位置检测失败: {e}")
            return []
        
        image_positions.sort(key=lambda x: x[0][1])
        return image_positions

    def _replace_placeholders_with_images(self, text_with_placeholders: str, images_dict: Dict[int, str]) -> str:
        """用实际的图片内容替换占位符"""
        if not text_with_placeholders or not images_dict:
            return text_with_placeholders
        
        result = text_with_placeholders
        for img_idx, img_content in images_dict.items():
            result = result.replace(f"<!-- IMAGE_PLACEHOLDER_{img_idx} -->", img_content)
        
        return result
    
    def _format_text_block(self, block: Dict) -> str:
        """格式化文本块，保留空格和换行结构"""
        if not self.config.preserve_formatting:
            # 简单提取文本
            return block.get("text", "").strip()
        
        formatted_lines = []
        
        # 按Y轴坐标分组，合并同一行的文本
        lines_by_y = {}
        
        for line in block["lines"]:
            if not line.get("spans"):
                continue
                
            # 获取行的Y轴坐标（使用第一个span的bbox）
            if line["spans"] and "bbox" in line["spans"][0]:
                y_coord = line["spans"][0]["bbox"][1]  # 使用Y1坐标
                
                # 四舍五入到最近的整数，处理微小差异
                y_key = round(y_coord)
                
                if y_key not in lines_by_y:
                    lines_by_y[y_key] = []
                
                lines_by_y[y_key].extend(line["spans"])
        
        # 按Y坐标排序（从大到小，PDF坐标系Y轴向上递增）
        sorted_y_keys = sorted(lines_by_y.keys(), reverse=True)
        
        for y_key in sorted_y_keys:
            spans = lines_by_y[y_key]
            line_spans = []
            
            # 按X坐标排序（从左到右）
            sorted_spans = sorted(spans, key=lambda s: s.get("bbox", [0, 0, 0, 0])[0] if "bbox" in s else 0)
            
            for span in sorted_spans:
                text = span["text"]
                if text and text.strip():
                    cleaned_text = ' '.join(text.split())
                    
                    font_size = span.get("size", 0)
                    font_flags = span.get("flags", 0)
                    is_title = font_size > 14 or (font_flags & 2)
                    
                    line_spans.append(f"**{cleaned_text}**" if is_title else cleaned_text)
            
            if line_spans:
                # 将同一行的span用空格连接，保留原始空格结构
                line_content = " ".join(line_spans)
                formatted_lines.append(line_content)
        
        if not formatted_lines:
            return ""
        
        # 将不同行用换行符连接，保留换行结构
        block_content = '\n'.join(formatted_lines)
        
        # 如果有bbox信息，检查是否为段落分隔
        if "bbox" in block:
            block_height = block["bbox"][3] - block["bbox"][1]
            # 如果是较大的文本块，可能是一个段落，添加空行分隔
            if block_height > 20:  # 假设高度大于20像素可能是段落分隔
                return f"\n{block_content}\n"
        
        return block_content
    
    def _merge_text_blocks(self, text_blocks: List[str]) -> str:
        """智能合并文本块，处理段落结构"""
        if not text_blocks:
            return ""
        
        merged_content = []
        
        for i, block in enumerate(text_blocks):
            block = block.strip()
            if not block:
                continue
                
            if block.startswith('\n') and merged_content and not merged_content[-1].endswith('\n'):
                merged_content[-1] += '\n'
                
            merged_content.append(block)
            
            if i < len(text_blocks) - 1:
                next_block = text_blocks[i + 1].strip()
                if next_block and not next_block.startswith('\n'):
                    merged_content.append(" ")
        
        result = ''.join(merged_content)
        result = '\n'.join(line.strip() for line in result.splitlines() if line.strip())
        
        return result

    def _save_output(self, content: str, output_path: str):
        """保存输出文件"""
        try:
            # 确保输出目录存在
            output_dir = Path(output_path).parent
            output_dir.mkdir(parents=True, exist_ok=True)
            
            with open(output_path, 'w', encoding='utf-8') as f:
                f.write(content)
            
            self.logger.info(f"结果已保存到: {output_path}")
            
        except Exception as e:
            raise Exception(f"保存输出文件失败: {e}")


def convert_pdf_file(
    pdf_path: str,
    output_path: Optional[str] = None,
    start_page: int = 1,
    end_page: Optional[int] = None,
    config: Optional[ConversionConfig] = None
) -> Dict[str, Any]:
    """
    便捷函数：转换PDF文件
    
    Args:
        pdf_path: 输入PDF文件路径
        output_path: 输出文件路径
        start_page: 起始页码
        end_page: 结束页码
        config: 转换配置
        
    Returns:
        转换结果
    """
    converter = PDFConverterV2(config)
    return converter.convert_pdf(pdf_path, output_path, start_page, end_page)


def main():
    """命令行入口函数"""
    import argparse
    import sys
    
    parser = argparse.ArgumentParser(
        description='PDF转Markdown转换器 V2',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
            使用示例:
            python pdf_converter_v2.py input.pdf
            python pdf_converter_v2.py input.pdf -o output.md
            python pdf_converter_v2.py input.pdf -s 1 -e 10 -o output.md
            python pdf_converter_v2.py input.pdf --chunk-size 25 --progress-interval 5
                    """
                )
    
    # 必需参数
    parser.add_argument('pdf_path', help='输入PDF文件路径')
    
    # 可选参数
    parser.add_argument('-o', '--output', dest='output_path', 
                       help='输出Markdown文件路径（默认自动生成）')
    parser.add_argument('-s', '--start-page', dest='start_page', type=int, default=1,
                       help='起始页码（默认: 1）')
    parser.add_argument('-e', '--end-page', dest='end_page', type=int,
                       help='结束页码（默认: 最后一页）')
    
    # 配置参数
    parser.add_argument('--chunk-size', type=int, default=50,
                       help='批次处理大小（默认: 50）')
    parser.add_argument('--progress-interval', type=int, default=10,
                       help='进度更新间隔（默认: 10）')
    parser.add_argument('--no-tables', action='store_true',
                       help='禁用表格检测')
    parser.add_argument('--no-formatting', action='store_true',
                       help='禁用格式保留')
    parser.add_argument('--table-min-columns', type=int, default=2,
                       help='表格最小列数（默认: 2）')
    
    args = parser.parse_args()
    
    # 创建配置
    config = ConversionConfig(
        table_detection_enabled=not args.no_tables,
        preserve_formatting=not args.no_formatting,
        chunk_size=args.chunk_size,
        progress_update_interval=args.progress_interval,
        table_min_columns=args.table_min_columns
    )
    
    # 执行转换
    try:
        result = convert_pdf_file(
            pdf_path=args.pdf_path,
            output_path=args.output_path,
            start_page=args.start_page,
            end_page=args.end_page,
            config=config
        )
        
        if result['success']:
            self.logger.info(f"✅ 转换成功!")
            self.logger.info(f"   输出文件: {result['output_path']}")
            self.logger.info(f"   处理页面: {result['pages_processed']}")
            self.logger.info(f"   发现表格: {result['tables_found']}")
            self.logger.info(f"   处理时间: {result['processing_time']:.2f}秒")
            self.logger.info(f"   详细信息: {result.get('details', '无')}")
            sys.exit(0)
        else:
            self.logger.error(f"❌ 转换失败: {result.get('error', '未知错误')}")
            if result.get('errors'):
                self.logger.error("详细错误:")
                for error in result['errors']:
                    self.logger.error(f"  - {error}")
            sys.exit(1)
            
    except Exception as e:
        self.logger.error(f"❌ 程序执行错误: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
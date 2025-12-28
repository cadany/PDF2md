"""
PDF转Markdown转换器 V2
基于PyMuPDF和pdfplumber，专门处理大文件和高稳定性需求
"""

import fitz  # PyMuPDF
import pdfplumber
import os
import logging
import re
import time
from typing import Optional, Dict, List, Tuple, Any
from dataclasses import dataclass
from pathlib import Path
import json


@dataclass
class ConversionConfig:
    """转换配置"""
    # 表格处理配置
    table_detection_enabled: bool = True
    table_extraction_method: str = "pdfplumber"  # "pdfplumber" 或 "pymupdf"
    table_min_columns: int = 2
    
    # 文本处理配置
    preserve_formatting: bool = True
    extract_images: bool = False  # 暂时不处理图片
    
    # 性能配置
    chunk_size: int = 50  # 每批处理的页面数
    progress_update_interval: int = 10  # 进度更新间隔（页面数）
    
    # 输出配置
    output_format: str = "markdown"  # "markdown" 或 "text"
    

class PDFConverterV2:
    """
    PDF转Markdown转换器 V2
    专门处理大文件和高稳定性需求
    """
    
    def __init__(self, config: Optional[ConversionConfig] = None):
        self.config = config or ConversionConfig()
        self.logger = self._setup_logger()
        self.processing_stats = {
            'total_pages': 0,
            'processed_pages': 0,
            'tables_found': 0,
            'errors': [],
            'start_time': None,
            'end_time': None
        }
    
    def _setup_logger(self) -> logging.Logger:
        """设置详细的日志系统"""
        logger = logging.getLogger(f"PDFConverterV2_{id(self)}")
        logger.setLevel(logging.INFO)
        
        if not logger.handlers:
            # 控制台处理器
            console_handler = logging.StreamHandler()
            console_formatter = logging.Formatter(
                '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
            )
            console_handler.setFormatter(console_formatter)
            logger.addHandler(console_handler)
            
            # 文件处理器
            log_file = Path("logs") / f"pdf_converter_{int(time.time())}.log"
            log_file.parent.mkdir(exist_ok=True)
            
            file_handler = logging.FileHandler(log_file, encoding='utf-8')
            file_formatter = logging.Formatter(
                '%(asctime)s - %(name)s - %(levelname)s - [%(filename)s:%(lineno)d] - %(message)s'
            )
            file_handler.setFormatter(file_formatter)
            logger.addHandler(file_handler)
        
        return logger
    
    def convert_pdf(
        self,
        pdf_path: str,
        output_path: Optional[str] = None,
        start_page: int = 1,
        end_page: Optional[int] = None
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
                markdown_content = self._process_pages_in_batches(doc, actual_start, actual_end)
                
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
        pdf_name = Path(pdf_path).stem
        timestamp = int(time.time())
        return f"{pdf_name}_converted_{timestamp}.md"
    
    def _process_pages_in_batches(
        self, 
        doc: fitz.Document, 
        start_page: int, 
        end_page: int
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
        """处理单个页面，保留表格的原始位置"""
        page_num = page_idx + 1
        
        # 添加页面标题
        page_content = [f"\n## 第 {page_num} 页\n"]
        
        # 第一步：使用PyMuPDF提取文本，在表格位置插入占位符
        text_with_placeholders = self._extract_text_with_table_placeholders(doc, page_idx)
        
        # 第二步：使用pdfplumber提取表格内容
        tables_dict = self._extract_tables_with_positions(doc, page_idx)
        
        # 第三步：用实际的表格内容替换占位符
        final_content = self._replace_placeholders_with_tables(text_with_placeholders, tables_dict)
        
        page_content.append(final_content)
        
        return '\n'.join(page_content)
    
    def _extract_tables_with_pdfplumber(self, doc: fitz.Document, page_idx: int) -> str:
        """使用pdfplumber提取表格"""
        if not self.config.table_detection_enabled:
            return ""
        
        try:
            # 将PyMuPDF页面转换为pdfplumber可处理的格式
            pdf_path = doc.name
            
            with pdfplumber.open(pdf_path) as pdf:
                if page_idx < len(pdf.pages):
                    page = pdf.pages[page_idx]
                    tables = page.find_tables()
                    
                    if tables:
                        table_content = []
                        
                        for i, table in enumerate(tables):
                            # 使用更健壮的表格提取方法
                            extracted_table = self._extract_table_safely(table)
                            
                            if (extracted_table and 
                                len(extracted_table) > 1 and 
                                self._is_valid_table(extracted_table)):
                                
                                markdown_table = self._convert_table_to_markdown(extracted_table)
                                table_content.append(f"**表格 {i + 1}:**\n\n{markdown_table}\n")
                                self.processing_stats['tables_found'] += 1
                        
                        if table_content:
                            return '\n'.join(table_content)
                        
        except Exception as e:
            self.logger.warning(f"使用pdfplumber处理第{page_idx + 1}页表格时发生错误: {e}")
        
        return ""
    
    def _extract_table_safely(self, table) -> List[List[str]]:
        """安全地提取表格数据，处理各种异常情况"""
        try:
            extracted_table = table.extract()
            
            # 确保所有单元格都是字符串
            cleaned_table = []
            for row in extracted_table:
                cleaned_row = []
                for cell in row:
                    if cell is None:
                        cleaned_row.append("")
                    else:
                        cleaned_row.append(str(cell).strip())
                cleaned_table.append(cleaned_row)
            
            return cleaned_table
            
        except Exception as e:
            self.logger.warning(f"提取表格数据时发生错误: {e}")
            return []
    
    def _is_valid_table(self, table_data: List[List[str]]) -> bool:
        """检查表格数据是否有效"""
        if not table_data or len(table_data) < 2:
            return False
        
        # 检查是否有足够的列
        max_columns = max(len(row) for row in table_data)
        if max_columns < self.config.table_min_columns:
            return False
        
        # 检查表格是否有实际内容（不只是空行）
        has_content = False
        for row in table_data:
            for cell in row:
                if cell and cell.strip():
                    has_content = True
                    break
            if has_content:
                break
        
        return has_content
    
    def _convert_table_to_markdown(self, table_data: List[List[str]]) -> str:
        """将表格数据转换为Markdown格式"""
        if not table_data or len(table_data) < 2:
            return ""
        
        markdown_lines = []
        
        # 清理和预处理表格数据
        cleaned_table = self._clean_table_data(table_data)
        
        # 表头
        headers = cleaned_table[0]
        markdown_lines.append("| " + " | ".join(headers) + " |")
        
        # 分隔线
        separator = "| " + " | ".join(["---"] * len(headers)) + " |"
        markdown_lines.append(separator)
        
        # 数据行
        for row in cleaned_table[1:]:
            if len(row) == len(headers):
                markdown_lines.append("| " + " | ".join(row) + " |")
            else:
                # 处理列数不匹配的情况
                adjusted_row = row + [""] * (len(headers) - len(row))
                markdown_lines.append("| " + " | ".join(adjusted_row[:len(headers)]) + " |")
        
        return '\n'.join(markdown_lines)
    
    def _clean_table_data(self, table_data: List[List[str]]) -> List[List[str]]:
        """清理和预处理表格数据"""
        cleaned_table = []
        
        for row in table_data:
            cleaned_row = []
            for cell in row:
                if cell is None:
                    cleaned_row.append("")
                else:
                    # 处理换行文本：将换行符替换为空格或HTML换行
                    cell_text = str(cell).strip()
                    
                    # 如果文本中有换行符，使用HTML换行标签
                    if '\n' in cell_text:
                        # 对于表格中的换行，使用HTML换行标签
                        cell_text = cell_text.replace('\n', '<br>')
                    
                    # 清理多余的空格
                    cell_text = ' '.join(cell_text.split())
                    
                    cleaned_row.append(cell_text)
            
            cleaned_table.append(cleaned_row)
        
        return cleaned_table
    
    def _remove_table_areas_from_text(self, doc: fitz.Document, page_idx: int, text_content: str) -> str:
        """从文本内容中移除表格区域的内容，避免重复"""
        if not text_content:
            return text_content
        
        try:
            # 使用pdfplumber检测表格区域
            with pdfplumber.open(doc.name) as pdf:
                page_pdfplumber = pdf.pages[page_idx]
                tables = page_pdfplumber.find_tables()
                
                if not tables:
                    return text_content
                
                # 获取表格的边界框
                table_bboxes = []
                for table in tables:
                    bbox = table.bbox
                    # 扩大边界框以确保完全捕获表格内容
                    expanded_bbox = (
                        max(0, bbox[0] - 20),
                        max(0, bbox[1] - 20),
                        min(page_pdfplumber.width, bbox[2] + 20),
                        min(page_pdfplumber.height, bbox[3] + 20)
                    )
                    table_bboxes.append(expanded_bbox)
                
                # 使用PyMuPDF提取文本块，并过滤掉表格区域的内容
                page = doc[page_idx]
                text_blocks = page.get_text("dict")["blocks"]
                
                filtered_text = []
                
                for block in text_blocks:
                    if "lines" in block:  # 文本块
                        # 检查文本块是否在表格区域内
                        block_bbox = (block["bbox"][0], block["bbox"][1], block["bbox"][2], block["bbox"][3])
                        
                        is_in_table_area = False
                        for table_bbox in table_bboxes:
                            if self._bbox_overlap(block_bbox, table_bbox):
                                is_in_table_area = True
                                break
                        
                        if not is_in_table_area:
                            block_text = self._format_text_block(block)
                            if block_text.strip():
                                filtered_text.append(block_text)
                
                return '\n'.join(filtered_text)
                
        except Exception as e:
            self.logger.warning(f"表格区域移除失败，使用原始文本: {e}")
            return text_content
    
    def _bbox_overlap(self, bbox1, bbox2) -> bool:
        """检查两个边界框是否重叠"""
        x1_min, y1_min, x1_max, y1_max = bbox1
        x2_min, y2_min, x2_max, y2_max = bbox2
        
        # 检查是否有重叠
        return not (x1_max < x2_min or x1_min > x2_max or y1_max < y2_min or y1_min > y2_max)
    
    def _bbox_contained(self, bbox1, bbox2) -> bool:
        """检查bbox1是否完全包含在bbox2内"""
        x1_min, y1_min, x1_max, y1_max = bbox1
        x2_min, y2_min, x2_max, y2_max = bbox2
        
        return (x1_min >= x2_min and x1_max <= x2_max and 
                y1_min >= y2_min and y1_max <= y2_max)
    
    def _bbox_overlap_ratio(self, bbox1, bbox2) -> float:
        """计算两个边界框的重叠比例"""
        x1_min, y1_min, x1_max, y1_max = bbox1
        x2_min, y2_min, x2_max, y2_max = bbox2
        
        # 计算重叠区域
        overlap_x_min = max(x1_min, x2_min)
        overlap_y_min = max(y1_min, y2_min)
        overlap_x_max = min(x1_max, x2_max)
        overlap_y_max = min(y1_max, y2_max)
        
        if overlap_x_max <= overlap_x_min or overlap_y_max <= overlap_y_min:
            return 0.0
        
        # 计算重叠面积
        overlap_area = (overlap_x_max - overlap_x_min) * (overlap_y_max - overlap_y_min)
        bbox1_area = (x1_max - x1_min) * (y1_max - y1_min)
        
        if bbox1_area == 0:
            return 0.0
        
        return overlap_area / bbox1_area
    
    def _extract_clean_table_text(self, tables_content: str) -> List[str]:
        """从表格内容中提取清理后的文本行"""
        clean_lines = []
        
        # 提取表格中的所有文本内容
        lines = tables_content.split('\n')
        
        for line in lines:
            # 跳过表格格式行和标题行
            if line.startswith('|') and '---' not in line and '**表格' not in line:
                # 提取单元格内容
                cells = [cell.strip() for cell in line.split('|') if cell.strip()]
                if cells:
                    # 将单元格内容合并为一行文本
                    row_text = ' '.join(cells)
                    # 移除HTML标签和清理文本
                    clean_text = row_text.replace('<br>', ' ').strip()
                    # 标准化文本（去除多余空格）
                    normalized_text = ' '.join(clean_text.split())
                    if normalized_text:
                        clean_lines.append(normalized_text)
        
        return clean_lines
    
    def _is_mostly_table_content(self, line: str, table_text_set: set) -> bool:
        """检查一行是否主要是表格内容"""
        if not line:
            return False
        
        # 检查这一行是否与表格内容高度匹配
        words = line.split()
        if not words:
            return False
        
        # 计算与表格内容的匹配度
        match_count = 0
        for word in words:
            for table_text in table_text_set:
                if word in table_text:
                    match_count += 1
                    break
        
        # 如果超过一半的词汇匹配表格内容，认为是表格行
        return match_count >= len(words) * 0.5
    
    def _extract_text_with_table_placeholders(self, doc: fitz.Document, page_idx: int) -> str:
        """使用PyMuPDF提取文本，在表格位置插入占位符"""
        try:
            page = doc[page_idx]
            
            # 检测表格区域和位置
            table_positions = self._detect_table_positions(doc, page_idx)
            
            # 提取所有文本块，按Y坐标排序
            text_blocks = page.get_text("dict")["blocks"]
            
            # 按Y坐标排序文本块
            sorted_blocks = sorted(text_blocks, key=lambda b: b["bbox"][1])
            
            formatted_content = []
            
            # 记录已处理的表格索引，避免重复插入占位符
            processed_table_indices = set()
            
            # 处理每个文本块，在表格位置插入占位符
            for block in sorted_blocks:
                if "lines" in block:  # 文本块
                    block_bbox = (block["bbox"][0], block["bbox"][1], block["bbox"][2], block["bbox"][3])
                    
                    # 检查当前块是否在表格区域内
                    table_idx = -1
                    overlap_ratio = 0.0
                    for i, (table_bbox, _) in enumerate(table_positions):
                        if self._bbox_overlap(block_bbox, table_bbox):
                            # 计算重叠比例
                            current_ratio = self._bbox_overlap_ratio(block_bbox, table_bbox)
                            if current_ratio > overlap_ratio:
                                overlap_ratio = current_ratio
                                table_idx = i
                    
                    if table_idx >= 0 and overlap_ratio > 0.7:
                        # 只有在文本块大部分在表格区域内时才跳过
                        # 在表格位置插入占位符（只插入一次）
                        if table_idx not in processed_table_indices:
                            placeholder = f"<!-- TABLE_PLACEHOLDER_{table_idx} -->"
                            # 在占位符前后添加空行，确保表格与正文有适当间距
                            formatted_content.append("")
                            formatted_content.append(placeholder)
                            formatted_content.append("")
                            processed_table_indices.add(table_idx)
                        # 跳过表格区域内的文本块
                        continue
                    else:
                        # 正常文本块或轻微重叠的文本块
                        block_text = self._format_text_block(block)
                        if block_text.strip():
                            formatted_content.append(block_text)
            
            return '\n'.join(formatted_content)
            
        except Exception as e:
            self.logger.warning(f"使用PyMuPDF提取第{page_idx + 1}页文本时发生错误: {e}")
            return f"<!-- 文本提取错误: {e} -->"
    
    def _extract_single_table(self, table) -> str:
        """提取单个表格内容"""
        try:
            # 安全地提取表格数据
            extracted_table = self._extract_table_safely(table)
            
            if extracted_table and len(extracted_table) > 1 and self._is_valid_table(extracted_table):
                # 转换为Markdown格式
                markdown_table = self._convert_table_to_markdown(extracted_table)
                return markdown_table
            
        except Exception as e:
            self.logger.warning(f"提取单个表格时发生错误: {e}")
        
        return ""
    
    def _extract_tables_with_positions(self, doc: fitz.Document, page_idx: int) -> Dict[int, str]:
        """提取表格内容并记录位置信息"""
        tables_dict = {}
        
        try:
            # 使用pdfplumber提取表格
            with pdfplumber.open(doc.name) as pdf:
                page_pdfplumber = pdf.pages[page_idx]
                tables = page_pdfplumber.find_tables()
                
                for i, table in enumerate(tables):
                    # 提取表格内容
                    table_content = self._extract_single_table(table)
                    
                    if table_content:
                        # 记录表格位置和内容
                        tables_dict[i] = table_content
                        
        except Exception as e:
            self.logger.warning(f"表格提取失败: {e}")
        
        return tables_dict
    
    def _replace_placeholders_with_tables(self, text_with_placeholders: str, tables_dict: Dict[int, str]) -> str:
        """用实际的表格内容替换占位符"""
        if not text_with_placeholders or not tables_dict:
            return text_with_placeholders
        
        result = text_with_placeholders
        
        # 按表格索引顺序替换占位符
        for table_idx, table_content in sorted(tables_dict.items()):
            placeholder = f"<!-- TABLE_PLACEHOLDER_{table_idx} -->"
            if placeholder in result:
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
                    # 精确的边界框，避免包含表格外的文字
                    expanded_bbox = (
                        max(0, bbox[0] - 2),   # 减少横向扩展
                        max(0, bbox[1] - 2),   # 减少纵向扩展
                        min(page_pdfplumber.width, bbox[2] + 2),
                        min(page_pdfplumber.height, bbox[3] + 2)
                    )
                    table_positions.append((expanded_bbox, i))
                    
        except Exception as e:
            self.logger.warning(f"表格位置检测失败: {e}")
        
        # 按Y坐标排序表格
        table_positions.sort(key=lambda x: x[0][1])
        
        return table_positions
    
    def _detect_table_areas(self, doc: fitz.Document, page_idx: int) -> List[Tuple[float, float, float, float]]:
        """检测页面中的表格区域"""
        table_bboxes = []
        
        try:
            # 使用pdfplumber检测表格
            with pdfplumber.open(doc.name) as pdf:
                page_pdfplumber = pdf.pages[page_idx]
                tables = page_pdfplumber.find_tables()
                
                for table in tables:
                    bbox = table.bbox
                    # 扩大边界框以确保完全捕获表格内容
                    expanded_bbox = (
                        max(0, bbox[0] - 30),
                        max(0, bbox[1] - 30),
                        min(page_pdfplumber.width, bbox[2] + 30),
                        min(page_pdfplumber.height, bbox[3] + 30)
                    )
                    table_bboxes.append(expanded_bbox)
                    
        except Exception as e:
            self.logger.warning(f"表格区域检测失败: {e}")
        
        return table_bboxes
    
    def _format_text_block(self, block: Dict) -> str:
        """格式化文本块"""
        if not self.config.preserve_formatting:
            # 简单提取文本
            return block.get("text", "").strip()
        
        block_text = []
        
        for line in block["lines"]:
            line_text = []
            
            for span in line["spans"]:
                text = span["text"].strip()
                if text:
                    # 简单的格式判断（可根据字体大小、粗细等扩展）
                    font_size = span.get("size", 0)
                    
                    if font_size > 14:  # 可能是标题
                        line_text.append(f"**{text}**")
                    else:
                        line_text.append(text)
            
            if line_text:
                # 将同一行的span用空格连接
                line_content = " ".join(line_text)
                block_text.append(line_content)
        
        # 将整个文本块的内容用换行符连接
        return '\n'.join(block_text)
    
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
    
    def get_processing_stats(self) -> Dict[str, Any]:
        """获取处理统计信息"""
        return self.processing_stats.copy()
    
    def reset_stats(self):
        """重置统计信息"""
        self.processing_stats = {
            'total_pages': 0,
            'processed_pages': 0,
            'tables_found': 0,
            'errors': [],
            'start_time': None,
            'end_time': None
        }


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
            print(f"✅ 转换成功!")
            print(f"   输出文件: {result['output_path']}")
            print(f"   处理页面: {result['pages_processed']}")
            print(f"   发现表格: {result['tables_found']}")
            print(f"   处理时间: {result['processing_time']:.2f}秒")
            sys.exit(0)
        else:
            print(f"❌ 转换失败: {result.get('error', '未知错误')}")
            if result.get('errors'):
                print("详细错误:")
                for error in result['errors']:
                    print(f"  - {error}")
            sys.exit(1)
            
    except Exception as e:
        print(f"❌ 程序执行错误: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
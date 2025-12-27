"""
PDF转Markdown转换器，专门处理复杂表格和图片占位符
该模块将PDF文档转换为Markdown格式，特别优化表格处理
和图片占位符标记，以支持后续处理。
"""

import fitz  # PyMuPDF - 用于PDF处理的库
import os
import logging
import re
from typing import Optional, Dict, Any, List
from dataclasses import dataclass
from pathlib import Path

# 初始化OCR可用性标志
OCR_AVAILABLE = False
PADDLE_OCR_MODULE = None

try:
    import paddleocr

    PADDLE_OCR_MODULE = paddleocr
    OCR_AVAILABLE = True
except ImportError:
    print("OCR库不可用。请安装paddleocr、opencv-python和Pillow以获得OCR功能。")


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
    output_format: str = "markdown"  # "markdown", "text", "json"


class PDFToMarkdownConverter:
    """
    PDF转Markdown转换器，特别优化表格处理和图片占位符
    """

    def __init__(self, config: Optional[ProcessingConfig] = None):
        self.config = config or ProcessingConfig()
        self.logger = self._setup_logger()
        # 初始化PaddleOCR
        if OCR_AVAILABLE:
            try:
                self.ocr = PADDLE_OCR_MODULE.PaddleOCR(use_angle_cls=True, lang="ch")
            except Exception as e:
                self.logger.error(f"初始化PaddleOCR失败: {e}")

    def _setup_logger(self) -> logging.Logger:
        """设置转换器的日志"""
        logger = logging.getLogger(__name__)
        logger.setLevel(logging.INFO)

        if not logger.handlers:
            handler = logging.StreamHandler()
            formatter = logging.Formatter(
                "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
            )
            handler.setFormatter(formatter)
            logger.addHandler(handler)

        return logger

    def convert_pdf_to_markdown(
        self,
        pdf_path: str,
        start_page: Optional[int] = None,
        end_page: Optional[int] = None,
        output_path: Optional[str] = None,
    ) -> str:
        """
        转换PDF为Markdown格式，特别优化表格和图片处理

        Args:
            pdf_path: 输入PDF文件的路径
            start_page: 起始页码（从1开始），默认为1
            end_page: 结束页码（从1开始），默认为最后一页
            output_path: 保存输出Markdown文件的路径

        Returns:
            输出Markdown文件的路径
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

            self.logger.info(f"开始PDF到Markdown转换: {pdf_path}")
            self.logger.info(f"处理页面 {start_page} 到 {end_page} 共 {total_pages} 页")

            # 处理每一页
            output_markdown = ""
            total_pages_to_process = end_page - start_page + 1

            for page_idx, page_num in enumerate(range(start_page, end_page + 1)):
                try:
                    progress = (page_idx + 1) / total_pages_to_process * 100
                    self.logger.info(
                        f"正在处理页面 {page_num}/{end_page} ({progress:.1f}%)"
                    )

                    page_content = self._process_page_as_markdown(
                        doc, page_num - 1
                    )  # PyMuPDF使用0索引
                    output_markdown += page_content

                    # 添加页面分隔符
                    if page_num < end_page:
                        output_markdown += f"\n\n--- Page {page_num} ---\n\n"

                except Exception as e:
                    self.logger.error(f"处理页面 {page_num} 时出错: {e}")
                    # 向输出添加错误信息但继续处理
                    output_markdown += (
                        f"\n<!-- 错误: 未能处理页面 {page_num} - {str(e)} -->\n"
                    )
                    continue

            # 将输出写入文件
            if output_path is None:
                base_name = Path(pdf_path).stem
                output_path = f"{base_name}_converted.md"

            with open(output_path, "w", encoding="utf-8") as f:
                f.write(output_markdown)

            self.logger.info(f"转换完成。输出保存到: {output_path}")
            return output_path

        except Exception as e:
            self.logger.error(f"PDF转换过程中出错: {e}")
            raise
        finally:
            if doc:
                doc.close()

    def _process_page_as_markdown(self, doc: fitz.Document, page_index: int) -> str:
        """
        处理PDF文档的单页，输出Markdown格式
        """
        page = doc[page_index]

        # 获取页面块（文本、图像、表格）
        blocks = page.get_text("dict")["blocks"]

        # 按Y坐标排序块，以确保正确的文档顺序
        sorted_blocks = sorted(
            blocks, key=lambda block: block["bbox"][1]
        )  # 按Y1坐标排序

        # 处理所有块，包括文本、图像和表格
        processed_content = self._process_sorted_blocks_as_markdown(
            page, sorted_blocks, page_index
        )

        return processed_content

    def _process_sorted_blocks_as_markdown(
        self, page: fitz.Page, sorted_blocks: List[Dict], page_index: int
    ) -> str:
        """处理按顺序排列的块，输出Markdown格式，确保表格和图片插入到正确位置"""
        # 获取页面上的表格
        page_tables = []
        if self.config.include_tables:
            try:
                tables = page.find_tables()
                for table in tables:
                    # 提取表格数据
                    table_data = table.extract()
                    # 获取表格边界框坐标
                    table_bbox = table.bbox
                    # 格式化表格为markdown（处理复杂表格）
                    markdown_table = self._format_complex_table_as_markdown(table_data)
                    page_tables.append(
                        {
                            "type": "table",
                            "bbox": table_bbox,
                            "y_position": table_bbox[
                                1
                            ],  # 使用表格的Y坐标 (top coordinate)
                            "content": f"{markdown_table}\n\n",  # 表格后添加额外换行以确保与正文分离
                        }
                    )
            except Exception as e:
                self.logger.warning(f"处理页面 {page_index + 1} 上的表格时出错: {e}")

        # 创建一个包含所有元素的列表（文本块、图像块和表格），按Y坐标排序
        all_elements = []

        # 获取页面上的图片
        page_images = []
        if self.config.include_images:
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
                                    # 创建图片占位符标记
                                    image_placeholder = f'![Image_{page_index + 1}_{img_index + 1}_{rect_idx + 1}](image-placeholder-{page_index + 1}-{img_index + 1}-{rect_idx + 1}.png "图片位置: 第{page_index + 1}页, 坐标({rect.x0:.2f}, {rect.y0:.2f}) - ({rect.x1:.2f}, {rect.y1:.2f})")'

                                    page_images.append(
                                        {
                                            "type": "image",
                                            "bbox": rect,
                                            "y_position": rect.y0,  # 使用图像的Y坐标
                                            "content": f"{image_placeholder}\n",
                                        }
                                    )
                            else:
                                # 如果没有位置信息，使用简化的占位符
                                page_images.append(
                                    {
                                        "type": "image",
                                        "bbox": None,
                                        "y_position": float(
                                            "inf"
                                        ),  # 将无位置信息的图像放到最后
                                        "content": f"![Image_{page_index + 1}_{img_index + 1}](image-placeholder-{page_index + 1}-{img_index + 1}.png)\n",
                                    }
                                )
                        pix = None  # 释放内存
                    except Exception as e:
                        self.logger.warning(
                            f"处理页面 {page_index + 1} 上的图像 {xref} 时出错: {e}"
                        )

        # 处理文本块，同时检测是否与表格或图像重叠
        for block in sorted_blocks:
            if "lines" in block:  # 文本块
                # 检查文本块是否与表格有显著重叠（使用重叠比例阈值）
                block_bbox = fitz.Rect(block["bbox"])
                has_significant_overlap_with_table = any(
                    self._calculate_overlap_ratio(block_bbox, fitz.Rect(table["bbox"]))
                    > 0.7  # 70% 阈值 - 更严格的表格重叠检测
                    for table in page_tables
                )

                # 检查文本块是否与图像重叠（图像使用简单重叠检测）
                is_overlapping_with_image = any(
                    (
                        self._check_overlap(block_bbox, fitz.Rect(img["bbox"]))
                        if img["bbox"]
                        else False
                    )
                    for img in page_images
                )

                # 检查文本块是否在表格下方（但不重叠），这可能是表格说明文字
                is_below_table = False
                if not has_significant_overlap_with_table and page_tables:
                    for table in page_tables:
                        table_bbox = fitz.Rect(table["bbox"])
                        # 如果文本块在表格下方一定距离内，且不与表格重叠
                        if (
                            block_bbox.y0 >= table_bbox.y1  # 文本块顶部在表格底部下方
                            and block_bbox.y0 - table_bbox.y1
                            < 100  # 增加距离阈值以更好地处理表格后内容
                        ):  # 且距离不超过100像素
                            is_below_table = True
                            break

                # 如果文本块不与表格或图像重叠，则添加文本
                # 如果文本在表格下方，也应添加（如表格标题或说明）
                if (
                    not has_significant_overlap_with_table
                    and not is_overlapping_with_image
                ):
                    # 收集整个文本块的内容
                    block_text_lines = []
                    y_positions = []
                    
                    for line in block["lines"]:
                        line_text = ""
                        for span in line["spans"]:
                            line_text += span["text"]

                        # 跳过空行
                        if not line_text.strip():
                            continue

                        # 添加保留格式的行
                        bbox = line["bbox"]
                        x0, y0, x1, y1 = bbox
                        
                        # 记录Y坐标位置用于后续排序
                        y_positions.append(y0)

                        # 处理文本内容：保留空格但避免不必要的换行
                        # 移除行首行尾空格，但保留中间有意义的空格
                        processed_line_text = line_text.rstrip()  # 只移除行尾空白

                        # 跳过空行
                        if not processed_line_text:
                            continue

                        block_text_lines.append(processed_line_text)

                    # 将整个文本块的内容合并为一段
                    if block_text_lines:
                        # 计算平均Y位置用于排序
                        avg_y_position = sum(y_positions) / len(y_positions) if y_positions else 0
                        
                        # 合并文本块中的所有行
                        combined_text = " ".join(block_text_lines)
                        
                        # 根据位置确定对齐方式（使用第一个有效行的位置）
                        if y_positions:
                            page_width = page.rect.width
                            left_margin = x0  # 使用最后一行的值
                            right_margin = page_width - x1
                            center_margin = abs(left_margin - right_margin)

                            if center_margin < 30:  # 居中文本
                                formatted_text = (
                                    f"{combined_text}\n"  # 居中文本，单换行
                                )
                            elif right_margin < 30:  # 右对齐
                                formatted_text = (
                                    f"{combined_text}\n"  # 右对齐，单换行
                                )
                            else:  # 左对齐
                                formatted_text = f"{combined_text}\n"
                        else:
                            formatted_text = f"{combined_text}\n"

                        # 将文本块作为元素添加到列表中
                        all_elements.append(
                            {
                                "type": "text",
                                "y_position": avg_y_position,  # 使用平均Y坐标作为排序位置
                                "content": formatted_text,
                            }
                        )

        # 添加所有元素（包括文本、表格和图像）
        all_elements.extend(page_tables)
        all_elements.extend(page_images)

        # 按Y坐标位置排序所有元素
        sorted_elements = sorted(all_elements, key=lambda el: el["y_position"])

        # 按顺序生成内容，合并相邻的文本元素
        content = []
        prev_element_type = None
        prev_y_position = None
        
        for element in sorted_elements:
            # 检查是否是相邻的文本元素，可以合并
            if (element["type"] == "text" and 
                prev_element_type == "text" and 
                prev_y_position is not None and
                abs(element["y_position"] - prev_y_position) < 5):  # 在同一行或非常接近的行
                
                # 合并到上一个文本元素（替换最后一个元素）
                if content and content[-1].endswith('\n'):
                    # 如果上一个元素以换行符结尾，保持换行
                    content.append(element["content"])
                else:
                    # 否则，在元素之间添加空格
                    content[-1] = content[-1].rstrip('\n') + ' ' + element["content"]
            else:
                content.append(element["content"])
            
            prev_element_type = element["type"]
            prev_y_position = element["y_position"]

        # 合并内容并规范化多余的换行符
        full_content = "".join(content)
        # 将连续的2个或更多换行符替换为最多2个换行符（保留段落间距）
        normalized_content = re.sub(r"\n{3,}", "\n\n", full_content)
        return normalized_content

    def _format_complex_table_as_markdown(self, table_data: List[List[str]]) -> str:
        """将复杂表格数据格式化为markdown格式，处理多行、列合并、行合并的情况"""
        if not table_data or not any(row for row in table_data):
            return ""

        # 处理复杂表格（多行、合并单元格等）
        # 首先过滤掉完全为空的行
        filtered_table_data = []
        for row in table_data:
            # 过滤掉只包含空白字符或特定格式字符的行
            non_empty_cells = [
                cell
                for cell in row
                if cell
                and str(cell).strip()
                and str(cell).strip() not in ["小写：", "大写：", "小写", "大写"]
            ]
            if non_empty_cells:
                filtered_table_data.append(
                    row
                )  # 保留原始行，但会在后续处理中过滤单元格

        if not filtered_table_data:
            return ""

        # 检查是否是合并单元格的复杂表格
        # 对于合并单元格，我们需要特殊处理
        processed_table_data = self._process_merged_cells(filtered_table_data)

        # 过滤掉空行，但保留结构
        processed_table_data = [
            row
            for row in processed_table_data
            if any(cell and str(cell).strip() for cell in row)
        ]

        if not processed_table_data:
            return ""

        # 找出每列的最大宽度
        col_widths = []
        for row in processed_table_data:
            for j, cell in enumerate(row):
                # 在计算列宽时，需要先处理单元格内容中的换行符
                cell_str = str(cell or "").replace("\n", " ").replace("\r", " ").strip()
                # 过滤掉特定的格式字符
                if cell_str in ["小写：", "大写：", "小写", "大写"]:
                    cell_str = ""
                if j >= len(col_widths):
                    col_widths.append(len(cell_str))
                else:
                    col_widths[j] = max(col_widths[j], len(cell_str))

        # 构建markdown表格
        markdown_lines = []

        for i, row in enumerate(processed_table_data):
            # 格式化单元格内容
            formatted_cells = []
            for j, cell in enumerate(row):
                # 处理单元格内容中的换行符，将其替换为空格
                cell_str = str(cell or "").replace("\n", " ").replace("\r", " ").strip()
                # 过滤掉特定的格式字符
                if cell_str in ["小写：", "大写：", "小写", "大写"]:
                    cell_str = ""
                if j < len(col_widths) and col_widths[j] > 0:
                    formatted_cells.append(cell_str.ljust(col_widths[j]))
                else:
                    formatted_cells.append(cell_str)

                # 确保空字符串在格式化时也被正确处理
                if cell_str == "":
                    formatted_cells[-1] = (
                        "".ljust(col_widths[j])
                        if j < len(col_widths) and col_widths[j] > 0
                        else ""
                    )

            # 只有当行中至少有一个非空单元格时才添加行
            if any(formatted_cell.strip() for formatted_cell in formatted_cells):
                # 添加行
                markdown_lines.append("| " + " | ".join(formatted_cells) + " |")

                # 在表头后添加分隔行
                if (
                    i == 0
                    and len([cell for cell in formatted_cells if cell.strip()]) > 0
                ):
                    separator_cells = []
                    for width in col_widths:
                        if width > 0:
                            separator_cells.append("-" * width)
                    if separator_cells:
                        markdown_lines.append("| " + " | ".join(separator_cells) + " |")

        return "\n".join(markdown_lines)

    def _process_merged_cells(self, table_data: List[List[str]]) -> List[List[str]]:
        """处理合并单元格的表格数据"""
        if not table_data:
            return table_data

        # 处理空值和合并单元格的占位符
        processed_data = []
        for row in table_data:
            processed_row = []
            for cell in row:
                if cell is None:
                    processed_row.append("")
                else:
                    # 清理单元格内容，处理可能的换行符和回车符
                    cell_str = str(cell).replace("\n", " ").replace("\r", " ").strip()
                    processed_row.append(cell_str)
            processed_data.append(processed_row)

        return processed_data

    def _check_overlap(self, rect1: fitz.Rect, rect2: fitz.Rect) -> bool:
        """检查两个矩形是否重叠"""
        if rect1 is None or rect2 is None:
            return False
        # 检查矩形是否重叠
        return not (
            rect1.x1 < rect2.x0
            or rect1.x0 > rect2.x1
            or rect1.y1 < rect2.y0
            or rect1.y0 > rect2.y1
        )

    def _calculate_overlap_ratio(self, rect1: fitz.Rect, rect2: fitz.Rect) -> float:
        """计算两个矩形的重叠面积占rect1面积的比例"""
        if rect1 is None or rect2 is None:
            return 0.0

        # 检查是否重叠
        if not self._check_overlap(rect1, rect2):
            return 0.0

        # 计算重叠区域
        overlap_x0 = max(rect1.x0, rect2.x0)
        overlap_y0 = max(rect1.y0, rect2.y0)
        overlap_x1 = min(rect1.x1, rect2.x1)
        overlap_y1 = min(rect1.y1, rect2.y1)

        # 计算重叠面积
        overlap_area = max(0, overlap_x1 - overlap_x0) * max(0, overlap_y1 - overlap_y0)

        # 计算rect1的面积
        rect1_area = (rect1.x1 - rect1.x0) * (rect1.y1 - rect1.y0)

        if rect1_area == 0:
            return 0.0

        # 返回重叠比例
        return overlap_area / rect1_area


def convert_pdf_to_markdown(
    pdf_path: str,
    start_page: Optional[int] = None,
    end_page: Optional[int] = None,
    output_path: Optional[str] = None,
    config: Optional[ProcessingConfig] = None,
) -> str:
    """
    主函数，用于转换PDF为Markdown格式

    Args:
        pdf_path: 输入PDF文件的路径
        start_page: 起始页码（从1开始），默认为1
        end_page: 结束页码（从1开始），默认为最后一页
        output_path: 保存输出Markdown文件的路径
        config: 处理配置

    Returns:
        输出Markdown文件的路径
    """
    # 确保页码参数是整数类型（处理可能的字符串输入）
    if start_page is not None and isinstance(start_page, str):
        start_page = int(start_page)
    if end_page is not None and isinstance(end_page, str):
        end_page = int(end_page)

    converter = PDFToMarkdownConverter(config)
    return converter.convert_pdf_to_markdown(
        pdf_path, start_page, end_page, output_path
    )


# 用于测试目的
if __name__ == "__main__":
    import sys

    if len(sys.argv) < 2:
        print(
            "用法: python pdf_to_md_converter.py <pdf_path> [output_path] [start_page] [end_page]"
        )
        print("示例: python pdf_to_md_converter.py document.pdf output.md 1 10")
        sys.exit(1)

    pdf_path = sys.argv[1]
    output_path = sys.argv[2] if len(sys.argv) > 2 else None
    start_page = int(sys.argv[3]) if len(sys.argv) > 3 else None
    end_page = int(sys.argv[4]) if len(sys.argv) > 4 else None

    try:
        result_path = convert_pdf_to_markdown(
            pdf_path, start_page, end_page, output_path
        )
        print(f"PDF到Markdown转换成功完成。输出保存到: {result_path}")
    except Exception as e:
        print(f"PDF转换过程中出错: {e}")
        sys.exit(1)

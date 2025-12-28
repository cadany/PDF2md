"""
PDF转换器V2测试用例
"""

import os
import sys
import tempfile
import unittest
from pathlib import Path

# 添加backend目录到Python路径
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from service.pdf_converter_v2 import PDFConverterV2, ConversionConfig, convert_pdf_file


class TestPDFConverterV2(unittest.TestCase):
    """PDF转换器V2测试类"""
    
    def setUp(self):
        """测试前准备"""
        self.converter = PDFConverterV2()
        self.test_files_dir = Path("../files")  # 假设测试文件在files目录
        
    def test_config_initialization(self):
        """测试配置初始化"""
        config = ConversionConfig(
            table_detection_enabled=True,
            chunk_size=25,
            progress_update_interval=5
        )
        
        converter = PDFConverterV2(config)
        self.assertEqual(converter.config.chunk_size, 25)
        self.assertEqual(converter.config.progress_update_interval, 5)
    
    def test_input_validation(self):
        """测试输入验证"""
        # 测试不存在的文件
        with self.assertRaises(FileNotFoundError):
            self.converter.convert_pdf("nonexistent.pdf")
        
        # 测试非PDF文件
        with tempfile.NamedTemporaryFile(suffix='.txt', delete=False) as f:
            f.write(b"test content")
            temp_path = f.name
        
        try:
            with self.assertRaises(ValueError):
                self.converter.convert_pdf(temp_path)
        finally:
            os.unlink(temp_path)
        
        # 测试无效的页码
        with self.assertRaises(ValueError):
            self.converter.convert_pdf("test.pdf", start_page=0)
        
        with self.assertRaises(ValueError):
            self.converter.convert_pdf("test.pdf", start_page=2, end_page=1)
    
    def test_output_path_generation(self):
        """测试输出路径生成"""
        # 测试自动生成输出路径
        pdf_path = "/path/to/test_document.pdf"
        output_path = self.converter._generate_output_path(pdf_path)
        
        self.assertTrue(output_path.startswith("test_document_converted_"))
        self.assertTrue(output_path.endswith(".md"))
    
    def test_table_conversion(self):
        """测试表格转换功能"""
        # 模拟表格数据
        table_data = [
            ["Header1", "Header2", "Header3"],
            ["Data1", "Data2", "Data3"],
            ["Data4", "Data5", "Data6"]
        ]
        
        markdown_table = self.converter._convert_table_to_markdown(table_data)
        
        # 验证Markdown表格格式
        self.assertIn("Header1 | Header2 | Header3", markdown_table)
        self.assertIn("--- | --- | ---", markdown_table)
        self.assertIn("Data1 | Data2 | Data3", markdown_table)
    
    def test_text_formatting(self):
        """测试文本格式化"""
        # 模拟文本块数据
        text_block = {
            "lines": [
                {
                    "spans": [
                        {"text": "这是普通文本", "size": 12},
                        {"text": "这是大号文本", "size": 16}
                    ]
                }
            ]
        }
        
        formatted_text = self.converter._format_text_block(text_block)
        self.assertIsInstance(formatted_text, str)
    
    def test_error_handling(self):
        """测试错误处理"""
        # 测试无效PDF文件
        with tempfile.NamedTemporaryFile(suffix='.pdf', delete=False) as f:
            f.write(b"invalid pdf content")
            invalid_pdf_path = f.name
        
        try:
            result = self.converter.convert_pdf(invalid_pdf_path)
            self.assertFalse(result['success'])
            self.assertIn('error', result)
        finally:
            os.unlink(invalid_pdf_path)
    
    def test_statistics_tracking(self):
        """测试统计信息跟踪"""
        # 重置统计信息
        self.converter.reset_stats()
        
        stats = self.converter.get_processing_stats()
        self.assertEqual(stats['processed_pages'], 0)
        self.assertEqual(stats['tables_found'], 0)
        self.assertEqual(len(stats['errors']), 0)
    
    def test_convenience_function(self):
        """测试便捷函数"""
        # 测试便捷函数调用
        result = convert_pdf_file("test.pdf", start_page=1, end_page=5)
        
        # 由于文件不存在，应该返回失败结果
        self.assertFalse(result['success'])


class TestPDFConverterV2Integration(unittest.TestCase):
    """集成测试（需要实际PDF文件）"""
    
    def setUp(self):
        """测试前准备"""
        self.converter = PDFConverterV2()
        self.test_pdf_path = self._find_test_pdf()
    
    def _find_test_pdf(self):
        """查找测试PDF文件"""
        # 在当前目录和父目录中查找PDF文件
        possible_paths = [
            "../files/fj-6p.pdf",  # 根据之前的代码，这个文件存在
            "test.pdf",
            "sample.pdf"
        ]
        
        for path in possible_paths:
            if os.path.exists(path):
                return path
        
        return None
    
    def test_basic_conversion(self):
        """测试基本转换功能"""
        if not self.test_pdf_path:
            self.skipTest("未找到测试PDF文件")
        
        # 创建临时输出文件
        with tempfile.NamedTemporaryFile(suffix='.md', delete=False) as f:
            output_path = f.name
        
        try:
            # 转换前几页
            result = self.converter.convert_pdf(
                self.test_pdf_path,
                output_path=output_path,
                start_page=1,
                end_page=3
            )
            
            # 验证转换结果
            self.assertTrue(result['success'])
            self.assertTrue(os.path.exists(output_path))
            self.assertGreater(result['pages_processed'], 0)
            
            # 验证输出文件内容
            with open(output_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            self.assertIn("PDF转换结果", content)
            self.assertIn("第 1 页", content)
            
        finally:
            if os.path.exists(output_path):
                os.unlink(output_path)
    
    def test_partial_conversion(self):
        """测试部分页面转换"""
        if not self.test_pdf_path:
            self.skipTest("未找到测试PDF文件")
        
        with tempfile.NamedTemporaryFile(suffix='.md', delete=False) as f:
            output_path = f.name
        
        try:
            # 只转换第2页
            result = self.converter.convert_pdf(
                self.test_pdf_path,
                output_path=output_path,
                start_page=2,
                end_page=2
            )
            
            self.assertTrue(result['success'])
            self.assertEqual(result['pages_processed'], 1)
            
            with open(output_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            self.assertIn("第 2 页", content)
            
        finally:
            if os.path.exists(output_path):
                os.unlink(output_path)
    
    def test_large_file_handling(self):
        """测试大文件处理（分批次）"""
        if not self.test_pdf_path:
            self.skipTest("未找到测试PDF文件")
        
        # 使用小批次大小测试分批次处理
        config = ConversionConfig(chunk_size=1)
        converter = PDFConverterV2(config)
        
        with tempfile.NamedTemporaryFile(suffix='.md', delete=False) as f:
            output_path = f.name
        
        try:
            result = converter.convert_pdf(
                self.test_pdf_path,
                output_path=output_path,
                start_page=1,
                end_page=2
            )
            
            self.assertTrue(result['success'])
            self.assertEqual(result['pages_processed'], 2)
            
        finally:
            if os.path.exists(output_path):
                os.unlink(output_path)


def run_tests():
    """运行测试"""
    # 创建测试套件
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()
    
    # 添加单元测试
    suite.addTests(loader.loadTestsFromTestCase(TestPDFConverterV2))
    
    # 添加集成测试（如果有测试文件）
    if os.path.exists("../files/fj-6p.pdf") or os.path.exists("test.pdf"):
        suite.addTests(loader.loadTestsFromTestCase(TestPDFConverterV2Integration))
    
    # 运行测试
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    
    return result.wasSuccessful()


if __name__ == "__main__":
    # 运行测试
    success = run_tests()
    
    if success:
        print("\n✅ 所有测试通过!")
    else:
        print("\n❌ 部分测试失败!")
    
    sys.exit(0 if success else 1)
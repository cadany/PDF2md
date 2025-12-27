#!/usr/bin/env python3
"""
Test script for PDF to text converter
"""

import os
import sys
from pathlib import Path

# Add the service directory to the path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'service'))

from service.pdf_to_text_converter import convert_pdf_to_text, ProcessingConfig

def test_pdf_converter():
    """Test the PDF converter functionality"""
    print("Testing PDF to Text Converter")
    print("=" * 50)
    
    # Look for PDF files in the current directory
    current_dir = Path.cwd()
    pdf_files = list(current_dir.glob("*.pdf"))
    
    if not pdf_files:
        print("No PDF files found in the current directory.")
        print("Please place a PDF file in the current directory to test the converter.")
        return
    
    print(f"Found PDF files: {[f.name for f in pdf_files]}")
    
    # Test with the first PDF file found
    pdf_path = str(pdf_files[0])
    print(f"\nTesting with: {pdf_path}")
    
    try:
        # Create a config with OCR enabled
        config = ProcessingConfig(
            ocr_enabled=True,
            ocr_service_type="local",  # Use local OCR
            preserve_formatting=True,
            include_images=True,
            include_tables=True
        )
        
        # Test conversion of first 3 pages (or fewer if the document is shorter)
        import fitz  # PyMuPDF
        doc = fitz.open(pdf_path)
        total_pages = len(doc)
        doc.close()
        
        end_page = min(3, total_pages)  # Process first 3 pages or all pages if less than 3
        
        print(f"Converting pages 1 to {end_page} of {total_pages}")
        
        # Convert the PDF
        output_path = convert_pdf_to_text(
            pdf_path=pdf_path,
            start_page=1,
            end_page=end_page,
            config=config
        )
        
        print(f"Conversion successful! Output saved to: {output_path}")
        
        # Display first 500 characters of output
        with open(output_path, 'r', encoding='utf-8') as f:
            content = f.read()
            print(f"\nFirst 500 characters of output:")
            print("-" * 30)
            print(content[:500])
            print("-" * 30)
            print(f"Total output length: {len(content)} characters")
        
    except Exception as e:
        print(f"Error during conversion: {e}")
        import traceback
        traceback.print_exc()

def test_with_sample_config():
    """Test with different configurations"""
    print("\n" + "=" * 50)
    print("Testing with different configurations")
    
    # Example of how to use different configurations
    configs = [
        ProcessingConfig(ocr_enabled=True, preserve_formatting=True, include_images=True, include_tables=True),
        ProcessingConfig(ocr_enabled=False, preserve_formatting=False, include_images=False, include_tables=False),
    ]
    
    for i, config in enumerate(configs):
        print(f"\nConfiguration {i+1}: OCR={config.ocr_enabled}, Formatting={config.preserve_formatting}")

if __name__ == "__main__":
    test_pdf_converter()
    test_with_sample_config()
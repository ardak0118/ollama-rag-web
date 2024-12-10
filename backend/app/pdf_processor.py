import pdfplumber
import os
from typing import Dict, Any
import logging
from fastapi import UploadFile

logger = logging.getLogger(__name__)

class PDFProcessor:
    def __init__(self):
        self.upload_dir = os.path.join(os.path.dirname(__file__), "uploads")
        os.makedirs(self.upload_dir, exist_ok=True)

    def extract_text_from_pdf(self, file_path: str) -> str:
        """从 PDF 文件中提取文本"""
        try:
            text_content = []
            with pdfplumber.open(file_path) as pdf:
                for page in pdf.pages:
                    text = page.extract_text()
                    if text:
                        text_content.append(text)
            return "\n\n".join(text_content)
        except Exception as e:
            logger.error(f"Error extracting text from PDF: {str(e)}")
            raise

    async def save_pdf(self, file: UploadFile) -> Dict[str, Any]:
        """保存上传的 PDF 文件"""
        try:
            # 创建临时文件
            temp_file_path = os.path.join(self.upload_dir, file.filename)
            
            # 保存上传的文件
            content = await file.read()
            with open(temp_file_path, "wb") as buffer:
                buffer.write(content)
            
            # 提取文本内容
            text_content = self.extract_text_from_pdf(temp_file_path)
            
            return {
                "filename": file.filename,
                "path": temp_file_path,
                "content": text_content
            }
        except Exception as e:
            logger.error(f"Error saving PDF: {str(e)}")
            raise

    def get_pdf_content(self, file_path: str) -> str:
        """获取 PDF 文件内容"""
        try:
            return self.extract_text_from_pdf(file_path)
        except Exception as e:
            logger.error(f"Error getting PDF content: {str(e)}")
            raise

pdf_processor = PDFProcessor() 
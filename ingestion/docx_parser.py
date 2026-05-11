"""
Module: docx_parser
Mo ta: Xu ly tai lieu DOCX/PDF sang Markdown cho AI RAG.
Tham chieu: docs/DOCS-main/skill_docx_to_md_parser.md
"""

import re
from pathlib import Path
from markitdown import MarkItDown
from app.logger import get_logger

logger = get_logger(__name__)

class DocumentParser:
    """Class ho tro parse DOCX/PDF sang Markdown."""
    
    def __init__(self):
        self.md_converter = MarkItDown()

    def convert_to_md(self, file_path: str) -> str:
        """Chuyen doi DOCX/PDF sang Markdown."""
        try:
            logger.info(f"Bat dau convert file: {file_path}")
            result = self.md_converter.convert(file_path)
            return result.text_content if hasattr(result, 'text_content') else getattr(result, 'markdown', str(result))
        except Exception as e:
            logger.error(f"Loi khi convert file {file_path}: {e}")
            raise

    def get_structure_map(self, content: str) -> list[dict]:
        """Quet cau truc Headings."""
        # Regex tim Heading tu L1 den L3
        md_pattern = r"(?m)^(#{1,3})\s+(.+)$"
        # Tim Title in dam (thuong o L1 khi Word duoc chuyen sang MD)
        bold_pattern = r"(?m)^\s*\*\*(.*?)\*\*\s*$"
        
        headings = []
        
        # Quet in dam (L1)
        for m in re.finditer(bold_pattern, content):
            line = content.count('\n', 0, m.start()) + 1
            headings.append({
                "level": 1, 
                "title": m.group(1).strip(), 
                "line": line, 
                "pos": m.start()
            })
        
        # Quet chuan Heading Markdown (L2, L3...)
        for m in re.finditer(md_pattern, content):
            level = len(m.group(1)) + 1 # +1 vi thuong bold da la L1
            headings.append({
                "level": level, 
                "title": m.group(2).strip(), 
                "line": content.count('\n', 0, m.start()) + 1, 
                "pos": m.start()
            })
        
        # Sap xep theo dong thuc te
        headings.sort(key=lambda x: x['pos'])
        return headings

    def parse_document(self, file_path: str) -> dict:
        """
        Ham wrapper de convert va get structure map cung luc.
        Tra ve dict chua noi dung MD va danh sach index.
        """
        path_obj = Path(file_path)
        if not path_obj.exists():
            raise FileNotFoundError(f"Khong tim thay file: {file_path}")
            
        md_content = self.convert_to_md(str(path_obj))
        structure = self.get_structure_map(md_content)
        
        return {
            "markdown": md_content,
            "structure_map": structure
        }

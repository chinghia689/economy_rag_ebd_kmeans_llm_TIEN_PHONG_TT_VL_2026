import os
import glob
from langchain_core.documents import Document

def load_documents_from_dir(dataset_dir='./Dataset_economy'):
    documents = []
    
    # 1. Tạo pattern tìm kiếm an toàn trên mọi OS
    search_pattern = os.path.join(dataset_dir, '**', '*.txt')
    
    for filepath in glob.glob(search_pattern, recursive=True):
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                content = f.read().strip()
                
            if content:  # 2. Bỏ qua file rỗng
                # 3. Lấy tên Category AN TOÀN trên cả Windows lẫn Mac/Linux
                # os.path.relpath loại bỏ phần thư mục gốc. 
                # VD: ./Dataset_economy/NganHang/file1.txt -> NganHang/file1.txt
                rel_path = os.path.relpath(filepath, dataset_dir)
                
                # Dùng os.sep để tự động lấy dấu / hoặc \ tuỳ hệ điều hành
                parts = rel_path.split(os.sep) 
                category = parts[0] if len(parts) > 1 else 'unknown'
                
                # 4. Tạo Document
                doc = Document(
                    page_content=content,
                    metadata={
                        "source": filepath,
                        "category": category,
                        "filename": os.path.basename(filepath)
                    }
                )
                documents.append(doc)
                
        except Exception as e:
            print(f"❌ Lỗi đọc file {filepath}: {e}")

    print(f"✅ Đã load {len(documents)} văn bản từ '{dataset_dir}'")
    
    return documents

import sys
from pathlib import Path

# Entry point: thêm project root vào path
sys.path.insert(0, str(Path(__file__).parent.parent))

from ingestion.load_document import load_documents_from_dir
from ingestion.model_embedding import vn_embedder
from ingestion.chunks_document import ChromaDBManager

def build_database():
    print("🚀 BẮT ĐẦU QUÁ TRÌNH XÂY DỰNG VECTOR DATABASE...")

    # BƯỚC 1: Đọc dữ liệu thô
    print("\n--- BƯỚC 1: LOAD DỮ LIỆU ---")
    docs = load_documents_from_dir('./Dataset_economy')
    
    if not docs:
        print("❌ Không có văn bản nào để xử lý. Dừng chương trình.")
        return

    # BƯỚC 2: Lấy model Embedding đã khởi tạo sẵn
    print("\n--- BƯỚC 2: KHỞI TẠO MODEL ---")
    embeddings = vn_embedder.get_model()

    # BƯỚC 3: Cắt và Lưu trữ vào ChromaDB
    print("\n--- BƯỚC 3: CHUNKING & BUILDING DB ---")
    db_manager = ChromaDBManager(embeddings_model=embeddings, persist_dir='./chroma_economy_db')
    # ./chroma_economy_db
    
    # ĐÂY LÀ LÚC TRUYỀN DỮ LIỆU VÀO NÀY:
    db_manager.process_and_store(raw_documents=docs, chunk_size=600, chunk_overlap=80, force_rebuild=True)

    print("\n🎉 HOÀN THÀNH QUÁ TRÌNH XÂY DỰNG DATABASE!")

# Lệnh này giúp code chỉ chạy khi bạn bấm Run trực tiếp file này
if __name__ == "__main__":
    build_database()
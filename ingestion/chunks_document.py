import os
import hashlib
import shutil
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_chroma import Chroma


class ChromaDBManager:
    """
    Class quản lý Vector Database (Chroma) và xử lý cắt văn bản.
    """
    def __init__(self, embeddings_model=None, persist_dir='./chroma_economy_db'):
        # Nhận embedding model (lazy: nếu không truyền thì tự lấy từ vn_embedder)
        if embeddings_model is None:
            from ingestion.model_embedding import vn_embedder
            embeddings_model = vn_embedder.get_model()
        self.embeddings = embeddings_model
        self.persist_dir = persist_dir
        self.vector_store = None

    def process_and_store(self, raw_documents, chunk_size=600, chunk_overlap=80, force_rebuild=False):
        """
        Hàm thực hiện cắt văn bản và lưu vào Database.
        
        Args:
            raw_documents: Danh sách documents gốc
            chunk_size: Kích thước chunk
            chunk_overlap: Số ký tự overlap
            force_rebuild: Nếu True, xóa DB cũ và tạo lại từ đầu
        """
        # 2. Xử lý VectorDB (Chroma)
        if os.path.exists(self.persist_dir) and not force_rebuild:
            print(f"📂 Đã tìm thấy DB cũ tại '{self.persist_dir}'. Đang load...")
            # Load DB cũ — KHÔNG thêm lại data để tránh trùng lặp
            self.vector_store = Chroma(
                persist_directory=self.persist_dir,
                embedding_function=self.embeddings
            )
            print(f"✅ Đã load DB với {self.vector_store._collection.count()} vectors.")
            return
        
        # Nếu force_rebuild, xóa DB cũ
        if force_rebuild and os.path.exists(self.persist_dir):
            shutil.rmtree(self.persist_dir)
            print(f"🗑️ Đã xóa DB cũ tại '{self.persist_dir}'.")

        print(f"✂️ Đang cắt {len(raw_documents)} văn bản gốc...")
        
        # 1. Cấu hình Splitter
        if chunk_size is None:
            doc_splits = raw_documents
            print(f"⚠️ Không chunking → giữ nguyên {len(doc_splits)} passages")
        else:
            text_splitter = RecursiveCharacterTextSplitter(
                chunk_size=chunk_size,
                chunk_overlap=chunk_overlap,
                separators=['\n\n', '\n']
            )        
        # Cắt thành các chunk nhỏ
            doc_splits = text_splitter.split_documents(raw_documents)
            print(f"✅ Đã cắt thành {len(doc_splits)} chunks nhỏ.")

        # === DEDUPLICATION: Loại bỏ chunks trùng nội dung ===
        seen_hashes = set()
        unique_splits = []
        for doc in doc_splits:
            content = doc.page_content.strip()
            label = str(doc.metadata.get("is_relevant", "NA"))
            content_hash = hashlib.md5(
                (content + label).encode("utf-8")
            ).hexdigest()
            if content_hash not in seen_hashes:
                seen_hashes.add(content_hash)
                unique_splits.append(doc)
        
        removed = len(doc_splits) - len(unique_splits)
        print(f"🔄 Dedup: {len(doc_splits)} → {len(unique_splits)} chunks (loại {removed} trùng lặp)")
        doc_splits = unique_splits

        print(f"🆕 Đang tạo DB mới tại '{self.persist_dir}'...")
        # Tạo mới hoàn toàn
        self.vector_store = Chroma.from_documents(
            documents=doc_splits,
            embedding=self.embeddings,
            persist_directory=self.persist_dir
        )
        print("✅ Đã tạo và lưu DB mới thành công!")

    def get_retriever(self, k=40):
        """Hàm lấy retriever ra để tìm kiếm"""
        if not self.vector_store:
            if os.path.exists(self.persist_dir):
                self.vector_store = Chroma(
                    persist_directory=self.persist_dir,
                    embedding_function=self.embeddings
                )
            else:
                raise ValueError("❌ Database chưa được tạo. Hãy chạy process_and_store() trước!")
                
        # Trả về retriever
        return self.vector_store.as_retriever(search_kwargs={'k': k})

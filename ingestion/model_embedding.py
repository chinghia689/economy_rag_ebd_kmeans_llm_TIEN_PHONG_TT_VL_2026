from typing import List
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_core.embeddings import Embeddings


class E5EmbeddingsWrapper(Embeddings):
    """
    Wrapper cho multilingual-e5 models.

    E5 yêu cầu prefix bắt buộc:
        - "query: " cho câu hỏi / truy vấn  (embed_query)
        - "passage: " cho tài liệu / đoạn văn (embed_documents)

    Wrapper này tự động thêm prefix, nên toàn bộ codebase
    không cần thay đổi gì — chỉ cần gọi embed_query() / embed_documents() như bình thường.
    """

    def __init__(self, base_embeddings: HuggingFaceEmbeddings,
                 query_prefix: str = "query: ",
                 passage_prefix: str = "passage: "):
        self._base = base_embeddings
        self._query_prefix = query_prefix
        self._passage_prefix = passage_prefix

    def embed_documents(self, texts: List[str]) -> List[List[float]]:
        """Embed danh sách documents (thêm prefix 'passage: ')."""
        prefixed = [self._passage_prefix + t for t in texts]
        return self._base.embed_documents(prefixed)

    def embed_query(self, text: str) -> List[float]:
        """Embed câu hỏi / query (thêm prefix 'query: ')."""
        return self._base.embed_query(self._query_prefix + text)


class VietnameseEmbedding:
    """
    Class quản lý mô hình nhúng (Embedding).

    Sử dụng intfloat/multilingual-e5-base — model đa ngôn ngữ mạnh,
    hỗ trợ tiếng Việt tốt hơn vietnamese-sbert trên các benchmark retrieval.
    """
    model_embed = 'intfloat/multilingual-e5-base'
    model_embed_2 = 'intfloat/e5-base-v2'
    def __init__(self, model_name=model_embed_2, device='cpu'):
        self.model_name = model_name

        # Cấu hình phần cứng
        self.model_kwargs = {'device': device}
        self.encode_kwargs = {'normalize_embeddings': True}

        # Khởi tạo model
        try:
            print(f"⚡ Đang tải mô hình Embedding: {self.model_name}...")
            base = HuggingFaceEmbeddings(
                model_name=self.model_name,
                model_kwargs=self.model_kwargs,
                encode_kwargs=self.encode_kwargs
            )
            # Bọc wrapper để tự động thêm prefix cho E5
            self.embeddings = E5EmbeddingsWrapper(base)
            print("✅ Đã tải mô hình thành công!")
        except Exception as e:
            print(f"❌ Lỗi khi tải mô hình: {e}")
            raise

    def get_model(self):
        """Trả về object embeddings (đã có prefix wrapper)."""
        return self.embeddings


vn_embedder = VietnameseEmbedding(device='cuda')

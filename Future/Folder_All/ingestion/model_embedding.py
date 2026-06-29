import os
from threading import Lock
from typing import List, TYPE_CHECKING

from langchain_core.embeddings import Embeddings

if TYPE_CHECKING:
    from langchain_huggingface import HuggingFaceEmbeddings


class E5EmbeddingsWrapper(Embeddings):
    """
    Wrapper cho multilingual-e5 models.

    E5 yêu cầu prefix bắt buộc:
        - "query: " cho câu hỏi / truy vấn  (embed_query)
        - "passage: " cho tài liệu / đoạn văn (embed_documents)

    Wrapper này tự động thêm prefix, nên toàn bộ codebase
    không cần thay đổi gì — chỉ cần gọi embed_query() / embed_documents() như bình thường.
    """

    def __init__(self, base_embeddings: "HuggingFaceEmbeddings",
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
    model_embed = "intfloat/multilingual-e5-base"
    model_embed_2 = "intfloat/e5-base-v2"

    def __init__(self, model_name: str = model_embed, device: str | None = None):
        self.model_name = model_name
        self.requested_device = device or os.getenv("EMBEDDING_DEVICE", "auto")
        self.model_kwargs: dict[str, str] = {}
        self.encode_kwargs = {"normalize_embeddings": True}
        self.embeddings: E5EmbeddingsWrapper | None = None
        self._lock = Lock()

    def _cuda_available(self) -> bool:
        try:
            import torch
            return bool(torch.cuda.is_available())
        except Exception:
            return False

    def _resolve_device(self) -> str:
        requested = (self.requested_device or "auto").strip().lower()

        if requested not in {"", "auto"}:
            if requested.startswith("cuda") and not self._cuda_available():
                print("⚠️ Không phát hiện CUDA GPU, chuyển embedding sang CPU.")
                return "cpu"
            return requested

        return "cuda" if self._cuda_available() else "cpu"

    def _load_model(self) -> E5EmbeddingsWrapper:
        """Tải model khi cần dùng, tránh network/GPU side-effect lúc import module."""
        if self.embeddings is not None:
            return self.embeddings

        with self._lock:
            if self.embeddings is not None:
                return self.embeddings

            from langchain_huggingface import HuggingFaceEmbeddings

            device = self._resolve_device()
            self.model_kwargs = {"device": device}

            try:
                print(f"⚡ Đang tải mô hình Embedding: {self.model_name} trên {device}...")
                base = HuggingFaceEmbeddings(
                    model_name=self.model_name,
                    model_kwargs=self.model_kwargs,
                    encode_kwargs=self.encode_kwargs
                )
                # Bọc wrapper để tự động thêm prefix cho E5
                self.embeddings = E5EmbeddingsWrapper(base)
                print("✅ Đã tải mô hình thành công!")
                return self.embeddings
            except Exception as e:
                print(f"❌ Lỗi khi tải mô hình: {e}")
                raise

    def get_model(self):
        """Trả về object embeddings (lazy-load và đã có prefix wrapper)."""
        return self._load_model()


vn_embedder = VietnameseEmbedding()

from typing import Any, List
from typing_extensions import TypedDict


class GraphState(TypedDict, total=False):
    """
    Đại diện cho trạng thái của workflow.

    Dùng trong pipeline RAG:
        - question: Câu hỏi từ người dùng
        - documents: Danh sách tài liệu được truy xuất
        - generation: Câu trả lời sinh ra từ LLM
        - prompt: Custom prompt hệ thống (tùy chọn)

    Attributes:
        question (str): Câu hỏi người dùng.
        generation (str): Kết quả sinh ra từ LLM.
        documents (List): Danh sách tài liệu liên quan.
        prompt (str): Prompt hệ thống/hướng dẫn kèm theo.
    """

    question: str
    generation: str
    documents: List
    prompt: str
    query_parts: List[str]
    retrieval_debug: List[dict[str, Any]]
    algorithm: str


"""
DocumentGrader: Đánh giá mức độ liên quan của tài liệu với câu hỏi.

Sử dụng kỹ thuật Batching để gộp N tài liệu vào 1 prompt,
giảm số lần gọi API từ N lần xuống 1 lần duy nhất.
"""

import json
import re
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser
from langchain_core.runnables import RunnableSequence
from chatbot.utils.custom_prompt import CustomPrompt
from app.logger import get_logger

logger = get_logger(__name__)


class DocumentGrader:
    """
    Lớp kiểm tra HÀNG LOẠT (Batching) xem các documents có liên quan tới câu đầu vào không.
    Giúp giảm số lần gọi API từ 15 lần xuống 1 lần duy nhất.
    """

    def __init__(self, llm) -> None:
        prompt = ChatPromptTemplate.from_messages(
            [
                ("system", CustomPrompt.BATCH_GRADE_DOCUMENT_PROMPT),
                ("human", "Danh sách tài liệu: \n\n {documents} \n\n Câu hỏi: {question}"),
            ]
        )
        self.chain = prompt | llm | StrOutputParser()

    def get_chain(self) -> RunnableSequence:
        """Trả về chain đánh giá tài liệu."""
        return self.chain

    def grade_batch(self, question: str, retrieved_docs: list) -> list:
        """
        Chấm điểm hàng loạt các tài liệu trong 1 API call.

        Args:
            question: Câu hỏi của người dùng.
            retrieved_docs: Danh sách Document đã truy xuất.

        Returns:
            Danh sách Document đã lọc (chỉ giữ tài liệu liên quan).
        """
        if not retrieved_docs:
            return []

        # 1. Gom tất cả documents thành 1 string duy nhất có đánh số
        formatted_docs = "\n".join(
            [f"--- [Tài liệu {i+1}] ---\n{doc.page_content}" for i, doc in enumerate(retrieved_docs)]
        )

        # 2. Gọi LLM đúng 1 lần
        response = self.chain.invoke({
            "documents": formatted_docs,
            "question": question
        })

        # 3. Trích xuất mảng JSON an toàn bằng Regex
        filtered_docs = []
        try:
            match = re.search(r'\[.*?\]', response)
            if match:
                indices = json.loads(match.group(0))
                for idx in indices:
                    real_idx = idx - 1  # Chuyển index từ (1-N) sang (0-based)
                    if 0 <= real_idx < len(retrieved_docs):
                        filtered_docs.append(retrieved_docs[real_idx])
        except Exception as e:
            logger.warning(f"Lỗi parse JSON từ LLM: {response}. Chi tiết: {e}")

        return filtered_docs
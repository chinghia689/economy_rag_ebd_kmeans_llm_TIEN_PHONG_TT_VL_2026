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
        prompt = ChatPromptTemplate.from_messages([
            ("system", CustomPrompt.BATCH_GRADE_DOCUMENT_PROMPT),
            ("human", "Danh sách tài liệu: \n\n {documents} \n\n Câu hỏi: {question}"),
        ])
        self.chain = prompt | llm | StrOutputParser()

    def get_chain(self) -> RunnableSequence:
        return self.chain

    def grade_batch(self, question: str, retrieved_docs: list) -> list:
        if not retrieved_docs:
            return []
        formatted_docs = "\n".join(
            [f"--- [Tài liệu {i+1}] ---\n{doc.page_content}" for i, doc in enumerate(retrieved_docs)]
        )
        response = self.chain.invoke({"documents": formatted_docs, "question": question})
        filtered_docs = []
        indices = None
        for candidate in reversed(re.findall(r"\[[^\[\]]*\]", response)):
            try:
                value = json.loads(candidate)
            except Exception:
                continue
            if isinstance(value, list) and all(isinstance(x, int) for x in value):
                indices = value
                break
        if indices is None:
            logger.warning(f"Không parse được JSON array indices từ LLM: {response!r}")
        else:
            for idx in indices:
                real_idx = idx - 1
                if 0 <= real_idx < len(retrieved_docs):
                    filtered_docs.append(retrieved_docs[real_idx])
        return filtered_docs

"""
Main entry point cho Chatbot RAG với Energy Distance Retriever.

Một ứng dụng chatbot sử dụng:
- Vector Database (Chroma) với embeddings tiếng Việt
- Energy-Based Distance cho retrieval nâng cao
- LangGraph cho workflow xử lý
- LLM (OpenAI, Gemini, local Ollama, etc.) để sinh câu trả lời
"""

import os
import sys
import argparse
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

# Thêm parent folder vào path
sys.path.insert(0, str(Path(__file__).parent.parent))

from chatbot.utils.llm import LLM
from chatbot.services.files_rag_chat_agent import FilesChatAgent
from chatbot.utils.graph_state import GraphState
from app.logger import get_logger

logger = get_logger(__name__)


class ChatbotRunner:
    """
    Runner chính để chạy chatbot ứng dụng.
    Quản lý vòng đời của LLM, vector store, và workflow LangGraph.
    """

    def __init__(self, path_vector_store, llm_provider="gemini"):
        """
        Khởi tạo Chatbot.

        Args:
            path_vector_store (str): Đường dẫn đến vector store (VD: './chroma_cosine')
            llm_provider (str): Loại LLM (openai, gemini, local, grok). Default: gemini
        """
        self.path_vector_store = path_vector_store
        self.llm_provider = llm_provider

        # Khởi tạo LLM
        llm_handler = LLM()
        self.llm = llm_handler.get_llm(llm_provider)

        # Khởi tạo Chatbot Agent
        self.agent = FilesChatAgent(
            llm_model=self.llm,
            path_vector_store=path_vector_store
        )

        # Xây dựng workflow
        self.workflow = self.agent.get_workflow()
        self.compiled_workflow = self.workflow.compile()

    def answer_question(self, question: str, prompt: str = None) -> str:
        """
        Trả lời câu hỏi của người dùng.

        Args:
            question (str): Câu hỏi của người dùng
            prompt (str, optional): Custom prompt hệ thống. Nếu None, dùng mặc định.

        Returns:
            str: Câu trả lời từ chatbot
        """
        if not prompt:
            prompt = """Bạn là một chuyên gia tư vấn kinh tế Việt Nam.
Hãy trả lời câu hỏi CHỈ dựa trên thông tin trong ngữ cảnh được cung cấp.
Nếu ngữ cảnh không chứa thông tin cần thiết, hãy nói rõ là không có thông tin."""

        logger.info(f"Câu hỏi: {question}")

        # Chuẩn bị input state
        input_state = {
            "question": question,
            "generation": "",
            "documents": [],
            "prompt": prompt
        }

        # Chạy workflow
        output_state = self.compiled_workflow.invoke(input_state)

        # Lấy kết quả
        answer = output_state.get("generation", "Không thể tạo câu trả lời.")

        logger.info(f"Trả lời thành công, độ dài: {len(answer)} ký tự")

        return answer

    def interactive_chat(self):
        """
        Chế độ chat tương tác với người dùng.
        Lưu ý: Chỉ dùng cho debug/dev, không dùng trong production.
        """
        print("\n" + "=" * 60)
        print("CHATBOT KINH TẾ - INTERACTIVE MODE")
        print("=" * 60)
        print("Gõ 'exit' hoặc 'quit' để thoát")
        print("Các tùy chọn lệnh:")
        print("  - /custom_prompt <text>  : Đặt custom prompt")
        print("  - /clear                 : Xóa prompt về mặc định")
        print("=" * 60 + "\n")

        custom_prompt = None

        while True:
            question = input("Nhập câu hỏi: ").strip()

            if question.lower() in ["exit", "quit"]:
                print("Cảm ơn bạn đã sử dụng chatbot. Tạm biệt!")
                break

            if question.lower().startswith("/custom_prompt"):
                custom_prompt = question.replace("/custom_prompt", "").strip()
                print(f"[OK] Custom prompt đã được đặt: {custom_prompt}\n")
                continue

            if question.lower() == "/clear":
                custom_prompt = None
                print("[OK] Custom prompt đã được xóa, quay lại mặc định.\n")
                continue

            if not question:
                print("CẢNH BÁO: Vui lòng nhập một câu hỏi hợp lệ.\n")
                continue

            self.answer_question(question, prompt=custom_prompt)


def main():
    """
    Hàm main — điểm bắt đầu chương trình.
    Parse CLI arguments và khởi tạo chatbot.
    """
    parser = argparse.ArgumentParser(description="Chatbot RAG Demo")
    parser.add_argument("--question", type=str, help="Câu hỏi trực tiếp (không cần interactive)")
    parser.add_argument("--llm", type=str, default="openai", help="LLM provider (openai, gemini, groq)")
    args = parser.parse_args()

    PROJECT_ROOT = Path(__file__).parent.parent
    VECTOR_STORE_PATH = str(PROJECT_ROOT / "chroma_economy_db")
    LLM_PROVIDER = args.llm

    if not os.path.exists(VECTOR_STORE_PATH):
        logger.error(f"Vector store không tìm thấy tại '{VECTOR_STORE_PATH}'")
        logger.info("Vui lòng chạy: python ingestion/vector_data_builder.py")
        sys.exit(1)

    logger.info(f"Đang khởi tạo chatbot với LLM: {LLM_PROVIDER}...")

    chatbot = ChatbotRunner(
        path_vector_store=VECTOR_STORE_PATH,
        llm_provider=LLM_PROVIDER
    )

    if args.question:
        chatbot.answer_question(args.question)
    else:
        chatbot.interactive_chat()


if __name__ == "__main__":
    main()

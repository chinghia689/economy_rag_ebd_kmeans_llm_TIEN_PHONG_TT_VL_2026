"""
Main entry point cho Chatbot RAG voi Energy Distance Retriever.

Mot ung dung chatbot su dung:
- Vector Database (Chroma) voi embeddings tieng Viet
- Energy-Based Distance cho retrieval nang cao
- LangGraph cho workflow xu ly
- LLM (OpenAI, Gemini, local Ollama, etc.) de sinh cau tra loi
"""

import os
import sys
import argparse
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

# Them parent folder vao path
sys.path.insert(0, str(Path(__file__).parent.parent))

from chatbot.utils.llm import LLM
from chatbot.services.files_rag_chat_agent import FilesChatAgent
from chatbot.utils.graph_state import GraphState
from app.logger import get_logger

logger = get_logger(__name__)


class ChatbotRunner:
    """
    Runner chinh de chay chatbot ung dung.
    Quan ly vong doi cua LLM, vector store, va workflow LangGraph.
    """

    def __init__(self, path_vector_store, llm_provider="gemini"):
        """
        Khoi tao Chatbot.

        Args:
            path_vector_store (str): Duong dan den vector store (VD: './chroma_cosine')
            llm_provider (str): Loai LLM (openai, gemini, local, grok). Default: gemini
        """
        self.path_vector_store = path_vector_store
        self.llm_provider = llm_provider

        # Khoi tao LLM
        llm_handler = LLM()
        self.llm = llm_handler.get_llm(llm_provider)

        # Khoi tao Chatbot Agent
        self.agent = FilesChatAgent(
            llm_model=self.llm,
            path_vector_store=path_vector_store
        )

        # Xay dung workflow
        self.workflow = self.agent.get_workflow()
        self.compiled_workflow = self.workflow.compile()

    def answer_question(self, question: str, prompt: str = None) -> str:
        """
        Tra loi cau hoi cua nguoi dung.

        Args:
            question (str): Cau hoi cua nguoi dung
            prompt (str, optional): Custom prompt he thong. Neu None, dung mac dinh.

        Returns:
            str: Cau tra loi tu chatbot
        """
        if not prompt:
            prompt = """Ban la mot chuyen gia tu van kinh te Viet Nam.
Hay tra loi cau hoi CHI dua tren thong tin trong ngu canh duoc cung cap.
Neu ngu canh khong chua thong tin can thiet, hay noi ro la khong co thong tin."""

        logger.info(f"Cau hoi: {question}")

        # Chuan bi input state
        input_state = {
            "question": question,
            "generation": "",
            "documents": [],
            "prompt": prompt
        }

        # Chay workflow
        output_state = self.compiled_workflow.invoke(input_state)

        # Lay ket qua
        answer = output_state.get("generation", "Khong the tao cau tra loi.")

        logger.info(f"Tra loi thanh cong, do dai: {len(answer)} ky tu")

        return answer

    def interactive_chat(self):
        """
        Che do chat tuong tac voi nguoi dung.
        Ghi chu: Chi dung cho debug/dev, khong dung trong production.
        """
        print("\n" + "=" * 60)
        print("CHATBOT KINH TE - INTERACTIVE MODE")
        print("=" * 60)
        print("Go 'exit' hoac 'quit' de thoat")
        print("Cac tuy chon lenh:")
        print("  - /custom_prompt <text>  : Dat custom prompt")
        print("  - /clear                 : Xoa prompt ve mac dinh")
        print("=" * 60 + "\n")

        custom_prompt = None

        while True:
            question = input("Nhap cau hoi: ").strip()

            if question.lower() in ["exit", "quit"]:
                print("Cam on ban da su dung chatbot. Tam biet!")
                break

            if question.lower().startswith("/custom_prompt"):
                custom_prompt = question.replace("/custom_prompt", "").strip()
                print(f"[OK] Custom prompt da duoc dat: {custom_prompt}\n")
                continue

            if question.lower() == "/clear":
                custom_prompt = None
                print("[OK] Custom prompt da duoc xoa, quay lai mac dinh.\n")
                continue

            if not question:
                print("CANH BAO: Vui long nhap mot cau hoi hop le.\n")
                continue

            # Goi assistant de tra loi
            self.answer_question(question, prompt=custom_prompt)


def main():
    """
    Ham main — diem bat dau chuong trinh.
    Parse CLI arguments va khoi tao chatbot.
    """
    parser = argparse.ArgumentParser(description="Chatbot RAG Demo")
    parser.add_argument("--question", type=str, help="Cau hoi truc tiep (khong can interactive)")
    parser.add_argument("--llm", type=str, default="openai", help="LLM provider (openai, gemini, groq)")
    args = parser.parse_args()

    # Cau hinh duong dan dua tren vi tri file (khong phu thuoc cwd)
    PROJECT_ROOT = Path(__file__).parent.parent
    VECTOR_STORE_PATH = str(PROJECT_ROOT / "chroma_economy_db")
    LLM_PROVIDER = args.llm

    # Kiem tra xem vector store co ton tai khong
    if not os.path.exists(VECTOR_STORE_PATH):
        logger.error(f"Vector store khong tim thay tai '{VECTOR_STORE_PATH}'")
        logger.info("Vui long chay: python ingestion/vector_data_builder.py")
        sys.exit(1)

    logger.info(f"Dang khoi tao chatbot voi LLM: {LLM_PROVIDER}...")

    # Khoi tao chatbot runner
    chatbot = ChatbotRunner(
        path_vector_store=VECTOR_STORE_PATH,
        llm_provider=LLM_PROVIDER
    )

    # Neu co cau hoi truc tiep
    if args.question:
        chatbot.answer_question(args.question)
    else:
        # Che do interactive
        chatbot.interactive_chat()


if __name__ == "__main__":
    main()

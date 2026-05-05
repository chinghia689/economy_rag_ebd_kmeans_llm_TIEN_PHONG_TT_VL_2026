"""
FilesChatAgent: Tac nhan chatbot su dung RAG (Retrieval-Augmented Generation).

Nhiem vu:
    - Nhan cau hoi nguoi dung.
    - Truy xuat cac tai lieu lien quan tu vector store dung Energy Retriever.
    - Cham diem va loc ra tai lieu co lien quan.
    - Sinh cau tra loi dua tren cau hoi + tai lieu da loc.
    - Xu ly truong hop khong tim thay cau tra loi.

Quy trinh:
    START -> retrieve -> grade_documents -> (generate | handle_no_answer) -> END
"""

import re
from typing import Dict, Any

from ingestion.energy_kmeans import EnergyRetriever
from ingestion.model_embedding import vn_embedder
from ingestion.chunks_document import ChromaDBManager
from chatbot.utils.document_grader import DocumentGrader
from chatbot.utils.answer_generator import AnswerGeneratorDocs
from langgraph.graph import END, StateGraph, START
from chatbot.utils.graph_state import GraphState
from app.logger import get_logger

logger = get_logger(__name__)


class FilesChatAgent:
    """
    FilesChatAgent: Tac nhan chatbot su dung RAG (Retrieval-Augmented Generation).

    Nhiem vu:
        - Nhan cau hoi nguoi dung.
        - Truy xuat cac tai lieu lien quan tu vector store dung Energy Retriever.
        - Cham diem va loc ra tai lieu co lien quan.
        - Sinh cau tra loi dua tren cau hoi + tai lieu da loc.
        - Xu ly truong hop khong tim thay cau tra loi.

    Quy trinh:
        START -> retrieve -> grade_documents -> (generate | handle_no_answer) -> END
    """

    def __init__(self, llm_model, path_vector_store, allowed_files=["*"]) -> None:
        """
        Khoi tao FilesChatAgent.

        Args:
            llm_model: Mo hinh ngon ngu (LLM) da khoi tao san.
            path_vector_store (str): Duong dan den vector store chua embeddings.
            allowed_files (list[str], optional): Danh sach file cho phep. Mac dinh ["*"].
        """
        self.allowed_files = allowed_files
        self.path_vector_store = path_vector_store

        # Cac thanh phan xu ly chinh
        self.llm = llm_model
        self.document_grader = DocumentGrader(self.llm)
        self.answer_generator = AnswerGeneratorDocs(self.llm)
        
        # Khoi tao ChromaDB manager de lay retriever
        self.embeddings = vn_embedder.get_model()
        self.db_manager = ChromaDBManager(
            embeddings_model=self.embeddings,
            persist_dir=path_vector_store
        )
        
        # Lay vector store tu ChromaDB
        self.vector_store = self.db_manager.vector_store
        if not self.vector_store:
            # Neu chua co, load tu disk
            from langchain_chroma import Chroma
            self.vector_store = Chroma(
                persist_directory=path_vector_store,
                embedding_function=self.embeddings
            )
        
        # Khoi tao Energy Retriever MOT LAN (tranh tao lai moi query)
        self.energy_retriever = EnergyRetriever(
            vector_store=self.vector_store,
            embeddings_model=self.embeddings,
            k_retrieve=40,
            n_top_clusters=1
        )

    def handle_no_answer(self, state: GraphState) -> Dict[str, Any]:
        """
        Xu ly khi khong co tai lieu lien quan.

        Args:
            state (GraphState): Trang thai hien tai cua workflow.

        Returns:
            Dict[str, Any]: Ket qua bao khong tim thay cau tra loi.
        """
        return {"generation": "Xin loi, toi khong tim thay thong tin lien quan trong co so du lieu de tra loi cau hoi cua ban."}

    def grade_documents(self, state: GraphState) -> Dict[str, Any]:
        """
        Danh gia muc do lien quan cua cac tai lieu voi cau hoi.
        Da toi uu: Su dung Batching gop N tai lieu vao 1 prompt.

        Args:
            state (GraphState): Trang thai chua documents va question.

        Returns:
            Dict[str, Any]: Danh sach tai lieu da loc.
        """
        question = state["question"]
        documents = state["documents"]

        logger.info(f"Dang cham diem hang loat {len(documents)} tai lieu...")

        # Goi ham grade_batch (chi ton 1 API call duy nhat)
        filtered_docs = self.document_grader.grade_batch(
            question=question, 
            retrieved_docs=documents
        )

        logger.info(f"Da giu lai {len(filtered_docs)}/{len(documents)} tai lieu lien quan.")

        return {"documents": filtered_docs, "question": question}
        
    def decide_to_generate(self, state: GraphState) -> str:
        """
        Quyet dinh co sinh cau tra loi hay khong dua tren so luong tai lieu loc.

        Args:
            state (GraphState): Trang thai chua documents.

        Returns:
            str: "generate" hoac "no_document".
        """
        documents = state["documents"]
        
        if not documents:
            logger.warning("Khong co tai lieu lien quan, chuyen sang xu ly khong co cau tra loi")
            return "no_document"
        else:
            logger.info("Co tai lieu lien quan, tien hanh sinh cau tra loi")
            return "generate"

    def generate(self, state: GraphState) -> Dict[str, Any]:
        """
        Sinh cau tra loi tu cau hoi + cac tai lieu da loc.

        Args:
            state (GraphState): Trang thai chua question, documents, prompt.

        Returns:
            Dict[str, Any]: Tra ve cau tra loi (generation).
        """
        question = state["question"]
        documents = state["documents"]
        prompt = state.get("prompt", "Ban la mot chuyen gia tu van kinh te.")

        # Ghep noi dung cac tai lieu thanh context
        context = "\n\n".join(doc.page_content for doc in documents)

        # Sinh cau tra loi tu AnswerGenerator
        generation = self.answer_generator.get_chain().invoke(
            {"question": question, "context": context, "prompt": prompt}
        )

        # Xoa tag <think> neu co
        generation = re.sub(
            r"<think>.*?</think>", "", generation, flags=re.DOTALL
        ).strip()

        return {"generation": generation}

    def retrieve(self, state: GraphState) -> Dict[str, Any]:
        """
        Truy xuat tai lieu tu vector store dua tren cau hoi, su dung Energy Retriever.

        Args:
            state (GraphState): Trang thai chua cau hoi.

        Returns:
            Dict[str, Any]: Bao gom "documents" va "question".
        """
        question = state["question"]

        # Lay danh sach documents lien quan dung Energy Distance
        documents = self.energy_retriever.retrieve(query=question)

        return {"documents": documents, "question": question}

    def get_workflow(self):
        """
        Xay dung workflow xu ly voi StateGraph.

        Luong xu ly:
            START -> retrieve -> grade_documents
                -> (no_document -> handle_no_answer | generate) -> END

        Returns:
            StateGraph: Workflow da duoc dinh nghia.
        """
        workflow = StateGraph(GraphState)

        # Dinh nghia cac node
        workflow.add_node("retrieve", self.retrieve)
        workflow.add_node("grade_documents", self.grade_documents)
        workflow.add_node("generate", self.generate)
        workflow.add_node("no_document", self.handle_no_answer)

        # Xay dung luong
        workflow.add_edge(START, "retrieve")
        workflow.add_edge("retrieve", "grade_documents")
        
        # Quyet dinh dua tren so luong tai lieu
        workflow.add_conditional_edges(
            "grade_documents",
            self.decide_to_generate,
            {
                "generate": "generate",
                "no_document": "no_document"
            }
        )

        workflow.add_edge("generate", END)
        workflow.add_edge("no_document", END)

        return workflow

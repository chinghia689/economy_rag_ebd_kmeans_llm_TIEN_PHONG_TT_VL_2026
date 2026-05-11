"""
Module: question_router
Mo ta: Dinh tuyen cau hoi cua nguoi dung xem nen dung vectorstore hay web_search.
Tham chieu: docs/DOCS-main/skill_ai_rag_workflow.md Muc 2.A
"""

from typing import Literal
from pydantic import BaseModel
from langchain_core.prompts import PromptTemplate
from app.logger import get_logger

logger = get_logger(__name__)

class RouteQuery(BaseModel):
    """Schema de LLM tra ve ket qua dinh tuyen."""
    datasource: Literal["vectorstore", "web_search"]
    
def get_question_router(llm):
    """
    Tao question router chain.
    Su dung LLM (da duoc bind voi tool/schema) de quyet dinh nguon du lieu.
    """
    # System prompt cho LLM biet khi nao dung cai gi
    system = """Bạn là một chuyên gia phân loại yêu cầu của người dùng.
Hệ thống có hai nguồn dữ liệu:
1. 'vectorstore': Chứa các tài liệu chuyên môn về kinh tế, dữ liệu thị trường, báo cáo ngành của Việt Nam.
2. 'web_search': Chứa các thông tin chung, kiến thức tổng quát, hoặc thông tin thời sự mới nhất.

Hãy phân loại câu hỏi sau để chọn nguồn dữ liệu phù hợp.
Nếu câu hỏi liên quan đến thuật ngữ chung, chào hỏi, hoặc cần tìm trên web, hãy chọn 'web_search'.
Nếu câu hỏi hỏi cụ thể về dữ liệu kinh tế, báo cáo, thị trường Việt Nam (có thể nằm trong cơ sở dữ liệu), hãy chọn 'vectorstore'.
"""
    
    prompt = PromptTemplate(
        template=system + "\nCâu hỏi của người dùng: {question}",
        input_variables=["question"]
    )
    
    # Su dung LLM with structured output
    try:
        router_llm = llm.with_structured_output(RouteQuery)
        question_router = prompt | router_llm
        return question_router
    except NotImplementedError:
        # Neu LLM khong ho tro with_structured_output (vd Groq ban cu), dung fallback
        logger.warning("LLM khong ho tro with_structured_output. Dung prompt fallback cho router.")
        from langchain_core.output_parsers import JsonOutputParser
        
        fallback_prompt = PromptTemplate(
            template=system + "\nCâu hỏi của người dùng: {question}\nTra ve JSON voi key 'datasource' chua gia tri 'vectorstore' hoac 'web_search'.\n",
            input_variables=["question"]
        )
        return fallback_prompt | llm | JsonOutputParser()

def route_question(question: str, llm) -> str:
    """
    Ham ho tro thuc thi router tren mot cau hoi thuc te.
    Tra ve "vectorstore" hoac "web_search".
    """
    try:
        router = get_question_router(llm)
        result = router.invoke({"question": question})
        
        # Xu ly ket qua tu Pydantic model hoac dict
        if isinstance(result, RouteQuery):
            source = result.datasource
        elif isinstance(result, dict) and "datasource" in result:
            source = result["datasource"]
        else:
            source = "vectorstore" # Fallback mac dinh
            
        logger.info(f"Dinh tuyen cau hoi: '{question}' -> Nguon: {source}")
        return source
    except Exception as e:
        logger.error(f"Loi khi chay question router: {e}")
        return "vectorstore" # Fallback an toan

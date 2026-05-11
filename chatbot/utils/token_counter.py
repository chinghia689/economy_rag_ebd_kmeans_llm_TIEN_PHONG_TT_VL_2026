"""
Module: token_counter
Mo ta: Tinh toan so luong token su dung de quan ly chi phi LLM.
Tham chieu: docs/DOCS-main/skill_ai_rag_workflow.md Muc 3
"""

import tiktoken
from app.logger import get_logger

logger = get_logger(__name__)

def count_tokens(text: str, model: str = "gpt-4o-mini") -> int:
    """
    Dem so luong token cua mot doan text theo encoding cua model OpenAI.
    Neu dung model cua hang khac (Gemini, Groq), van co the dung GPT de uoc luong.
    
    Args:
        text: Chuoi van ban can dem.
        model: Ten model (mac dinh gpt-4o-mini).
        
    Returns:
        So luong token.
    """
    if not text:
        return 0
        
    try:
        # Lay encoding cua model chi dinh hoac mac dinh la cl100k_base
        try:
            encoding = tiktoken.encoding_for_model(model)
        except KeyError:
            logger.warning(f"Model '{model}' khong tim thay trong tiktoken. Dung 'cl100k_base' thay the.")
            encoding = tiktoken.get_encoding("cl100k_base")
            
        return len(encoding.encode(text))
    except Exception as e:
        logger.error(f"Loi khi dem token: {e}")
        # Tra ve gia tri uoc luong tam: 1 token ~ 4 ky tu
        return len(text) // 4

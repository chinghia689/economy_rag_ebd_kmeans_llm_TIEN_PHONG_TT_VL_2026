"""Helper khởi tạo LLM theo provider (openai / gemini / groq)."""

import os

from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_groq import ChatGroq
from langchain_openai import ChatOpenAI


class LLM:
    def __init__(self, temperature: float | None = None) -> None:
        self.temperature = (
            float(os.getenv("LLM_TEMPERATURE", "0"))
            if temperature is None
            else temperature
        )

    def get_llm(self, name: str):
        providers = {
            "openai": lambda: ChatOpenAI(
                openai_api_key=os.environ["KEY_API_OPENAI"],
                model=os.environ["OPENAI_LLM_MODEL_NAME"],
                temperature=self.temperature,
            ),
            "gemini": lambda: ChatGoogleGenerativeAI(
                google_api_key=os.environ["GOOGLE_API_KEY"],
                model=os.environ["GOOGLE_LLM_MODEL_NAME"],
                temperature=self.temperature,
            ),
            "groq": lambda: ChatGroq(
                api_key=os.environ["GROQ_API_KEY"],
                model=os.getenv("GROQ_LLM_MODEL_NAME", "llama-3.1-8b-instant"),
                temperature=self.temperature,
            ),
        }
        if name not in providers:
            raise ValueError(f"LLM '{name}' không hỗ trợ. Chọn: {list(providers)}")
        return providers[name]()

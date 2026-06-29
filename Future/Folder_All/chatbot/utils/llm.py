"""Helper khởi tạo LLM theo provider (openai / gemini / groq)."""

from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_groq import ChatGroq
from langchain_openai import ChatOpenAI

from app.runtime_config import get_runtime_setting


class LLM:
    def __init__(self, temperature: float | None = None) -> None:
        self.temperature = (
            float(get_runtime_setting("LLM_TEMPERATURE", "0"))
            if temperature is None
            else temperature
        )

    def get_llm(self, name: str):
        provider = (name or "openai").strip().lower()
        providers = {
            "openai": self._openai_llm,
            "gemini": self._gemini_llm,
            "groq": self._groq_llm,
        }
        if provider not in providers:
            raise ValueError(f"LLM '{name}' không hỗ trợ. Chọn: {list(providers)}")
        return providers[provider]()

    def _openai_llm(self):
        api_key = get_runtime_setting("KEY_API_OPENAI", "")
        model = get_runtime_setting("OPENAI_LLM_MODEL_NAME", "gpt-5-mini")
        if not api_key:
            raise RuntimeError("KEY_API_OPENAI chưa được cấu hình trong database.")
        return ChatOpenAI(
            openai_api_key=api_key,
            model=model,
            temperature=self.temperature,
        )

    def _gemini_llm(self):
        api_key = get_runtime_setting("GOOGLE_API_KEY", "")
        model = get_runtime_setting("GOOGLE_LLM_MODEL_NAME", "gemini-2.5-flash")
        if not api_key:
            raise RuntimeError("GOOGLE_API_KEY chưa được cấu hình trong database.")
        return ChatGoogleGenerativeAI(
            google_api_key=api_key,
            model=model,
            temperature=self.temperature,
        )

    def _groq_llm(self):
        api_key = get_runtime_setting("GROQ_API_KEY", "")
        model = get_runtime_setting("GROQ_LLM_MODEL_NAME", "llama-3.1-8b-instant")
        if not api_key:
            raise RuntimeError("GROQ_API_KEY chưa được cấu hình trong database.")
        return ChatGroq(
            api_key=api_key,
            model=model,
            temperature=self.temperature,
        )

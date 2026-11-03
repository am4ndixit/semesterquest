"""Optional OpenAI-compatible chat provider (Ollama, LM Studio, vLLM, OpenAI)."""
import httpx
from .config import LLM_BASE_URL, LLM_API_KEY, LLM_MODEL

def available() -> bool:
    return bool(LLM_BASE_URL and LLM_MODEL)

def engine_name() -> str:
    return LLM_MODEL if available() else "built-in grounded tutor (no model configured)"

def chat(messages: list[dict], temperature: float = 0.3, max_tokens: int = 700) -> str | None:
    if not available(): return None
    try:
        headers={"Authorization":f"Bearer {LLM_API_KEY}"} if LLM_API_KEY else {}
        r=httpx.post(LLM_BASE_URL.rstrip("/")+"/chat/completions",headers=headers,
                     json={"model":LLM_MODEL,"messages":messages,"temperature":temperature,"max_tokens":max_tokens},timeout=45)
        r.raise_for_status()
        return r.json()["choices"][0]["message"]["content"]
    except Exception:
        return None

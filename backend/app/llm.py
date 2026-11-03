"""
Multi-provider LLM router for Semester Quest.

Priority order (first available key wins):
  1. Groq  — free tier, ultra-fast (llama3, mixtral, gemma2)
  2. Gemini — free tier via Google AI Studio
  3. Custom OpenAI-compatible endpoint (Ollama, LM Studio, vLLM, OpenAI)

All providers speak the OpenAI messages format so the same chat() call works
across all of them without changes to callers.
"""
from __future__ import annotations
import httpx
from .config import (
    GROQ_API_KEY, GROQ_MODEL,
    GEMINI_API_KEY, GEMINI_MODEL,
    LLM_BASE_URL, LLM_API_KEY, LLM_MODEL,
)

# ── Groq ──────────────────────────────────────────────────────────────────────
# Free tier: generous daily limits on qwen, llama, allam models
# Docs: https://console.groq.com
_GROQ_BASE = "https://api.groq.com/openai/v1"

# ── Gemini ────────────────────────────────────────────────────────────────────
# Free tier: 15 RPM on gemini-2.5-flash (Google AI Studio key — starts with AQ.)
# Uses native REST API, NOT the OpenAI-compat endpoint
_GEMINI_BASE = "https://generativelanguage.googleapis.com/v1beta"

# Best available Groq free models (Nov 2024)
GROQ_FREE_MODELS = [
    "qwen/qwen3.8-27b",      # best free: smart + fast
    "openai/gpt-oss-20b",    # strong reasoning
    "allam-2-7b",            # Arabic + English
    "whisper-large-v3",      # audio (transcription only)
]


def _openai_chat(
    base_url: str,
    api_key: str,
    model: str,
    messages: list[dict],
    temperature: float,
    max_tokens: int,
) -> str | None:
    """Generic OpenAI-compatible chat completion call (works for Groq)."""
    try:
        r = httpx.post(
            base_url.rstrip("/") + "/chat/completions",
            headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
            json={"model": model, "messages": messages, "temperature": temperature, "max_tokens": max_tokens},
            timeout=45,
        )
        r.raise_for_status()
        return r.json()["choices"][0]["message"]["content"]
    except Exception:
        return None


def _gemini_chat(
    api_key: str,
    model: str,
    messages: list[dict],
    temperature: float,
    max_tokens: int,
) -> str | None:
    """
    Native Gemini REST API call.
    Works with AI Studio keys (AQ.xxx prefix) — NOT the OpenAI-compat endpoint.
    """
    try:
        # Convert OpenAI message format → Gemini format
        contents = []
        system_instruction = None
        for msg in messages:
            role = msg.get("role", "user")
            text = msg.get("content", "")
            if role == "system":
                system_instruction = text  # Gemini handles system separately
            elif role == "assistant":
                contents.append({"role": "model", "parts": [{"text": text}]})
            else:
                contents.append({"role": "user", "parts": [{"text": text}]})

        body: dict = {
            "contents": contents,
            "generationConfig": {"temperature": temperature, "maxOutputTokens": max_tokens},
        }
        if system_instruction:
            body["system_instruction"] = {"parts": [{"text": system_instruction}]}

        # Strip "models/" prefix if present
        model_id = model.replace("models/", "")
        r = httpx.post(
            f"{_GEMINI_BASE}/models/{model_id}:generateContent?key={api_key}",
            json=body,
            timeout=45,
        )
        r.raise_for_status()
        candidates = r.json().get("candidates", [])
        if candidates:
            return candidates[0]["content"]["parts"][0]["text"]
        return None
    except Exception:
        return None


def _active_provider() -> tuple[str, str, str] | None:
    """Return (base_url, api_key, model) for the first configured provider."""
    if GROQ_API_KEY:
        return (_GROQ_BASE, GROQ_API_KEY, GROQ_MODEL)
    if GEMINI_API_KEY:
        return (_GEMINI_BASE, GEMINI_API_KEY, GEMINI_MODEL)
    if LLM_BASE_URL and LLM_MODEL:
        return (LLM_BASE_URL, LLM_API_KEY, LLM_MODEL)
    return None


def available() -> bool:
    return _active_provider() is not None


def engine_name() -> str:
    p = _active_provider()
    if not p:
        return "built-in grounded tutor (no AI model configured)"
    base, _, model = p
    if "groq" in base:
        return f"Groq / {model}"
    if "generativelanguage" in base:
        return f"Gemini / {model}"
    return f"Custom / {model}"


def chat(messages: list[dict], temperature: float = 0.4, max_tokens: int = 900) -> str | None:
    """
    Send a chat completion request to the first available provider.
    Priority: Groq → Gemini → Custom LLM
    Returns None if no provider is configured or all calls fail.
    """
    if GROQ_API_KEY:
        result = _openai_chat(_GROQ_BASE, GROQ_API_KEY, GROQ_MODEL, messages, temperature, max_tokens)
        if result:
            return result
    if GEMINI_API_KEY:
        result = _gemini_chat(GEMINI_API_KEY, GEMINI_MODEL, messages, temperature, max_tokens)
        if result:
            return result
    if LLM_BASE_URL and LLM_MODEL:
        result = _openai_chat(LLM_BASE_URL, LLM_API_KEY, LLM_MODEL, messages, temperature, max_tokens)
        if result:
            return result
    return None


def quick_explain(topic: str, context: str = "") -> str | None:
    """Convenience wrapper: explain a concept briefly."""
    sys = (
        "You are Byte, a friendly pixel-art mascot and AI tutor for Semester Quest, "
        "a gamified learning platform for university students. Be concise, encouraging, "
        "and use emojis sparingly. If context is provided, ground your answer in it."
    )
    user = f"Explain this concept clearly in 3-5 sentences: {topic}"
    if context:
        user += f"\n\nContext from student's notes:\n{context[:2000]}"
    return chat([{"role": "system", "content": sys}, {"role": "user", "content": user}])


def motivational_quote(name: str = "explorer") -> str:
    """Ask the LLM for a short motivational line from Byte the mascot."""
    p = _active_provider()
    if not p:
        import random
        return random.choice([
            f"You've got this, {name}! Every expert was once a beginner. 🎮",
            f"Level up time, {name}! Small steps, big wins. ⚡",
            f"Keep pushing, {name}! Your future self is cheering you on. 🚀",
            f"Mistakes are just XP in disguise, {name}! Keep going. 💡",
        ])
    result = chat([
        {"role": "system", "content": "You are Byte, a cheerful pixel mascot. Give ONE short (≤15 words) motivational message for a student. Be creative and fun."},
        {"role": "user", "content": f"Motivate {name} who is studying right now."},
    ], temperature=0.9, max_tokens=60)
    return result or f"You're doing great, {name}! Keep it up! 🌟"

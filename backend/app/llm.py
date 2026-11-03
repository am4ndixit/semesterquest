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
# Free tier: ~14,400 requests/day on llama3-8b-8192 (as of 2024)
# Docs: https://console.groq.com  — get key in 30 sec, no credit card needed
_GROQ_BASE = "https://api.groq.com/openai/v1"

# ── Gemini ────────────────────────────────────────────────────────────────────
# Free tier: 15 RPM / 1M TPM on gemini-1.5-flash (Google AI Studio)
# Docs: https://aistudio.google.com/app/apikey
_GEMINI_BASE = "https://generativelanguage.googleapis.com/v1beta/openai"

# Available models on Groq free tier (as of Nov 2024)
GROQ_FREE_MODELS = [
    "llama3-8b-8192",       # fastest, great for tutoring
    "llama3-70b-8192",      # smarter but slower
    "mixtral-8x7b-32768",   # long context (32k)
    "gemma2-9b-it",         # Google's Gemma 2
    "llama-3.1-8b-instant", # latest llama 3.1
]


def _openai_chat(
    base_url: str,
    api_key: str,
    model: str,
    messages: list[dict],
    temperature: float,
    max_tokens: int,
) -> str | None:
    """Generic OpenAI-compatible chat completion call."""
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
    Returns None if no provider is configured or all calls fail.
    """
    p = _active_provider()
    if not p:
        return None
    base, key, model = p
    return _openai_chat(base, key, model, messages, temperature, max_tokens)


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

"""
EduBoost SA — Inference Gateway
PII Scrubber → Groq (primary) → Anthropic (secondary) → HuggingFace (fallback)
Learner identifiers NEVER reach the LLM.

Phase 1, item #5: Uses AsyncAnthropic + AsyncGroq so LLM calls do not
block the FastAPI event loop.

Supports offline-capable inference mode for low-connectivity deployments.
"""
import os
import re
import json
import structlog
from typing import Any, Optional
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type

import httpx
from groq import AsyncGroq
from anthropic import AsyncAnthropic

from app.api.core.config import settings

log = structlog.get_logger()

# ── Offline Mode Configuration ───────────────────────────────────────────────
_OFFLINE_MODE = os.environ.get("EDUBOOST_OFFLINE_MODE", "false").lower() == "true"
_OFFLINE_MODEL_PATH = os.environ.get("EDUBOOST_OFFLINE_MODEL_PATH", "./models")
_offline_client = None

# ── PII Patterns (South African) ─────────────────────────────────────────────
_PII_PATTERNS = [
    (re.compile(r"\b[A-Z][a-z]{2,}\s[A-Z][a-z]{2,}\b"), "[NAME]"),
    (re.compile(r"\b\d{13}\b"), "[SA_ID]"),
    (re.compile(r"[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,}"), "[EMAIL]"),
    # SA mobile: 06 / 07 / 08 / 09 + 8 digits (10 digits total)
    (re.compile(r"\b0[6789]\d{8}\b"), "[PHONE]"),
    (re.compile(r"\b\d{10,}\b"), "[NUMBER]"),
]

_groq_client: Optional[AsyncGroq] = (
    AsyncGroq(api_key=settings.GROQ_API_KEY) if settings.GROQ_API_KEY else None
)
_anthropic_client: Optional[AsyncAnthropic] = (
    AsyncAnthropic(api_key=settings.ANTHROPIC_API_KEY) if settings.ANTHROPIC_API_KEY else None
)


def scrub_pii(text: str) -> str:
    """Remove South African PII patterns from a string."""
    for pattern, replacement in _PII_PATTERNS:
        text = pattern.sub(replacement, text)
    return text


def scrub_dict(data: dict) -> dict:
    """Recursively scrub PII from a dictionary (used before LLM calls)."""
    serialised = json.dumps(data)
    serialised = scrub_pii(serialised)
    return json.loads(serialised)


@retry(
    stop=stop_after_attempt(2),
    wait=wait_exponential(multiplier=1, min=2, max=8),
    retry=retry_if_exception_type(Exception),
    reraise=True,
)
async def _call_groq(system_prompt: str, user_prompt: str, max_tokens: int) -> str:
    if not _groq_client:
        raise RuntimeError("Groq client not configured")
    response = await _groq_client.chat.completions.create(
        model=settings.GROQ_MODEL,
        max_tokens=max_tokens,
        temperature=settings.GROQ_TEMPERATURE,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
    )
    return response.choices[0].message.content


async def _call_anthropic(system_prompt: str, user_prompt: str, max_tokens: int) -> str:
    if not _anthropic_client:
        raise RuntimeError("Anthropic client not configured")
    response = await _anthropic_client.messages.create(
        model=settings.ANTHROPIC_MODEL,
        max_tokens=max_tokens,
        system=system_prompt,
        messages=[{"role": "user", "content": user_prompt}],
    )
    return response.content[0].text


async def _call_huggingface(system_prompt: str, user_prompt: str, max_tokens: int) -> str:
    prompt = f"<|system|>\n{system_prompt}\n<|user|>\n{user_prompt}\n<|assistant|>"
    async with httpx.AsyncClient(timeout=60) as client:
        response = await client.post(
            f"https://api-inference.huggingface.co/models/{settings.HUGGINGFACE_MODEL}",
            headers={"Authorization": f"Bearer {settings.HUGGINGFACE_API_KEY}"},
            json={"inputs": prompt, "parameters": {"max_new_tokens": max_tokens}},
        )
        response.raise_for_status()
        result = response.json()
        generated = result[0]["generated_text"] if isinstance(result, list) else result.get("generated_text", "")
        if "<|assistant|>" in generated:
            generated = generated.split("<|assistant|>")[-1].strip()
        return generated


async def _call_offline_inference(system_prompt: str, user_prompt: str, max_tokens: int) -> str:
    """
    Offline-capable inference using local model.
    
    Uses a local model for low-connectivity deployments.
    Supports quantized nano models (e.g., TinyLlama, Phi-2).
    """
    global _offline_client
    
    try:
        # Try to use transformers pipeline for local inference
        from transformers import pipeline, AutoTokenizer, AutoModelForCausalLM
        import torch
        
        model_name = os.environ.get("EDUBOOST_OFFLINE_MODEL_NAME", "TinyLlama/TinyLlama-1.1B-Chat-v1.0")
        
        # Initialize pipeline on first call
        if _offline_client is None:
            log.info("inference_gateway.offline.init", model=model_name)
            tokenizer = AutoTokenizer.from_pretrained(model_name)
            model = AutoModelForCausalLM.from_pretrained(
                model_name,
                torch_dtype=torch.float16 if torch.cuda.is_available() else torch.float32,
                device_map="auto" if torch.cuda.is_available() else "cpu",
            )
            _offline_client = pipeline(
                "text-generation",
                model=model,
                tokenizer=tokenizer,
                max_new_tokens=max_tokens,
                temperature=0.7,
                top_p=0.9,
            )
        
        # Format prompt for chat models
        prompt = f"<|system|>{system_prompt}</s>\n<|user|>{user_prompt}</s>\n<|assistant|>"
        
        result = _offline_client(prompt)
        generated = result[0]["generated_text"]
        
        # Extract assistant response
        if "<|assistant|>" in generated:
            generated = generated.split("<|assistant|>")[-1].strip()
        
        log.info("inference_gateway.offline.success", model=model_name)
        return generated
        
    except ImportError as e:
        log.error("inference_gateway.offline.import_error", error=str(e))
        raise RuntimeError("Offline inference requires transformers and torch packages") from e
    except Exception as e:
        log.error("inference_gateway.offline.failed", error=str(e))
        raise RuntimeError(f"Offline inference failed: {e}") from e


def is_offline_mode() -> bool:
    """Check if offline mode is enabled."""
    return _OFFLINE_MODE


async def call_llm(
    system_prompt: str,
    user_prompt: str,
    max_tokens: int = 1200,
    pedagogical_params: Optional[dict] = None,
) -> str:
    """
    Route through LLM providers with automatic failover.
    Supports offline-capable inference mode for low-connectivity deployments.
    IMPORTANT: system_prompt and user_prompt must contain NO learner PII.
    """
    clean_system = scrub_pii(system_prompt)
    clean_user = scrub_pii(user_prompt)

    log.info("inference_gateway.call", max_tokens=max_tokens, offline_mode=_OFFLINE_MODE)

    # Check for offline mode first
    if _OFFLINE_MODE:
        try:
            result = await _call_offline_inference(clean_system, clean_user, max_tokens)
            log.info("inference_gateway.success", provider="offline")
            return result
        except Exception as e:
            log.error("inference_gateway.offline_failed", error=str(e))
            # Fall through to online providers if offline fails
    
    # 1. Try Groq (primary — ultra fast)
    try:
        result = await _call_groq(clean_system, clean_user, max_tokens)
        log.info("inference_gateway.success", provider="groq")
        return result
    except Exception as e:
        log.warning("inference_gateway.groq_failed", error=str(e))

    # 2. Try Anthropic (secondary)
    try:
        result = await _call_anthropic(clean_system, clean_user, max_tokens)
        log.info("inference_gateway.success", provider="anthropic")
        return result
    except Exception as e:
        log.warning("inference_gateway.anthropic_failed", error=str(e))

    # 3. Try HuggingFace (fallback)
    try:
        result = await _call_huggingface(clean_system, clean_user, max_tokens)
        log.info("inference_gateway.success", provider="huggingface")
        return result
    except Exception as e:
        log.error("inference_gateway.all_providers_failed", error=str(e))
        raise RuntimeError("All LLM providers failed") from e


def parse_json_response(text: str) -> Any:
    """Safely parse JSON from LLM response, stripping markdown fences."""
    cleaned = text.replace("```json", "").replace("```", "").strip()
    start = cleaned.find("{")
    end = cleaned.rfind("}") + 1
    if start == -1 or end == 0:
        start = cleaned.find("[")
        end = cleaned.rfind("]") + 1
    if start == -1:
        raise ValueError(f"No JSON found in LLM response: {text[:200]}")
    return json.loads(cleaned[start:end])

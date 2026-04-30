"""
AI Provider implementations for Gemini, OpenAI, Claude, DeepSeek, and others.
"""

import asyncio
import json
import os
import time
from typing import List, Optional, Dict, Any, Type
import aiohttp
from .interfaces import IAIProvider, CopilotError, RateLimitError
from .models import CopilotConfig
from .config import config_manager
from .logging_config import get_logger

logger = get_logger(__name__)

class AIRateLimiter:
    """
    Rate limiter for AI API requests.
    """
    
    def __init__(self, requests_per_minute: int = 60):
        self.requests_per_minute = requests_per_minute
        self.tokens = requests_per_minute
        self.last_refill = time.time()
        self.lock = asyncio.Lock()
    
    async def acquire(self) -> None:
        async with self.lock:
            now = time.time()
            elapsed = now - self.last_refill
            tokens_to_add = elapsed * (self.requests_per_minute / 60.0)
            self.tokens = min(self.requests_per_minute, self.tokens + tokens_to_add)
            self.last_refill = now
            
            if self.tokens < 1:
                wait_time = (1 - self.tokens) * (60.0 / self.requests_per_minute)
                logger.warning(f"Rate limit reached, waiting {wait_time:.2f} seconds")
                await asyncio.sleep(wait_time)
                self.tokens = 1
            
            self.tokens -= 1


class GeminiProvider(IAIProvider):
    """
    Gemini API implementation.
    """
    
    def __init__(self, config: CopilotConfig, api_key: str):
        self.config = config
        self.api_key = api_key
        self.rate_limiter = AIRateLimiter(config.rate_limit_requests_per_minute)
        self.session: Optional[aiohttp.ClientSession] = None
    
    async def _ensure_session(self) -> None:
        if not self.session:
            timeout = aiohttp.ClientTimeout(total=60)
            headers = {
                "Content-Type": "application/json",
                "User-Agent": "Azure-Functions-News-Scraper/1.0"
            }
            self.session = aiohttp.ClientSession(timeout=timeout, headers=headers)

    async def chat_completion(self, 
                            system_prompt: str, 
                            user_content: str,
                            max_tokens: Optional[int] = None,
                            temperature: Optional[float] = None) -> str:
        
        # Add random jitter to desynchronize parallel function triggers
        import random
        await asyncio.sleep(random.uniform(0.5, 3.0))
        
        await self.rate_limiter.acquire()
        await self._ensure_session()
        
        gemini_contents = [
            {"role": "user", "parts": [{"text": user_content}]}
        ]
        
        payload = {
            "contents": gemini_contents,
            "generationConfig": {
                "maxOutputTokens": max_tokens or self.config.max_tokens,
                "temperature": temperature or self.config.temperature,
            },
            "systemInstruction": {
                "parts": [{"text": system_prompt}]
            }
        }
        
        # Gemini URL embeds the model in the path, so build from model_name.
        # GEMINI_API_ENDPOINT override is respected only if it already points to the
        # correct model (otherwise set GEMINI_MODEL_NAME instead).
        model_name = self.config.model_name or "gemini-2.0-flash"
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{model_name}:generateContent?key={self.api_key}"
        
        max_retries = 8
        retry_delay = 10
        
        for attempt in range(max_retries + 1):
            try:
                async with self.session.post(url, json=payload) as response:
                    if response.status == 429:
                        if attempt < max_retries:
                            wait = retry_delay * (2 ** attempt)
                            logger.warning(f"Gemini rate limit exceeded. Retrying in {wait}s (Attempt {attempt + 1}/{max_retries})")
                            await asyncio.sleep(wait)
                            continue
                        raise RateLimitError("Gemini rate limit exceeded after maximum retries")
                    
                    response_data = await response.json()
                    if response.status != 200:
                        error_msg = response_data.get("error", {}).get("message", "Unknown error")
                        raise CopilotError(f"Gemini API failed: {error_msg}")
                    
                    if "candidates" in response_data and len(response_data["candidates"]) > 0:
                        candidate = response_data["candidates"][0]
                        if "content" in candidate and "parts" in candidate["content"]:
                            return candidate["content"]["parts"][0].get("text", "").strip()
                    
                    return ""
            except (RateLimitError, CopilotError):
                raise
            except Exception as e:
                if attempt < max_retries:
                    wait = retry_delay * (2 ** attempt)
                    logger.warning(f"Gemini error: {str(e)}. Retrying in {wait}s...")
                    await asyncio.sleep(wait)
                    continue
                raise CopilotError(f"Gemini error: {str(e)}")

    async def close(self) -> None:
        if self.session:
            await self.session.close()
            self.session = None


class OpenAICompatibleProvider(IAIProvider):
    """
    Generic OpenAI-compatible API implementation (OpenAI, DeepSeek, Groq, etc.)
    """
    
    def __init__(self, config: CopilotConfig, api_key: str, endpoint: str, provider_name: str = "OpenAI"):
        self.config = config
        self.api_key = api_key
        self.endpoint = endpoint
        self.provider_name = provider_name
        self.rate_limiter = AIRateLimiter(config.rate_limit_requests_per_minute)
        self.session: Optional[aiohttp.ClientSession] = None
    
    async def _ensure_session(self) -> None:
        if not self.session:
            timeout = aiohttp.ClientTimeout(total=60)
            headers = {
                "Content-Type": "application/json",
                "Authorization": f"Bearer {self.api_key}",
                "User-Agent": "Azure-Functions-News-Scraper/1.0"
            }
            self.session = aiohttp.ClientSession(timeout=timeout, headers=headers)

    async def chat_completion(self, 
                            system_prompt: str, 
                            user_content: str,
                            max_tokens: Optional[int] = None,
                            temperature: Optional[float] = None) -> str:
        await self.rate_limiter.acquire()
        await self._ensure_session()
        
        payload = {
            "model": self.config.model_name,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_content}
            ],
            "max_tokens": max_tokens or self.config.max_tokens,
            "temperature": temperature or self.config.temperature,
        }
        
        try:
            async with self.session.post(self.endpoint, json=payload) as response:
                if response.status == 429:
                    raise RateLimitError(f"{self.provider_name} rate limit exceeded")

                response_data = await response.json()
                if response.status != 200:
                    error_msg = response_data.get("error", {}).get("message", "Unknown error")
                    raise CopilotError(f"{self.provider_name} API failed: {error_msg}")

                choices = response_data.get("choices") or []
                if not choices:
                    raise CopilotError(f"{self.provider_name} returned no choices")
                message = choices[0].get("message") or {}
                content = message.get("content")
                if not content:
                    raise CopilotError(f"{self.provider_name} returned empty content")
                return content.strip()
        except (RateLimitError, CopilotError):
            raise
        except Exception as e:
            raise CopilotError(f"{self.provider_name} error: {str(e)}")

    async def close(self) -> None:
        if self.session:
            await self.session.close()
            self.session = None


class ClaudeProvider(IAIProvider):
    """
    Anthropic Claude API implementation.
    """

    def __init__(self, config: CopilotConfig, api_key: str, endpoint: Optional[str] = None):
        self.config = config
        self.api_key = api_key
        self.rate_limiter = AIRateLimiter(config.rate_limit_requests_per_minute)
        self.session: Optional[aiohttp.ClientSession] = None
        self.endpoint = endpoint or "https://api.anthropic.com/v1/messages"
    
    async def _ensure_session(self) -> None:
        if not self.session:
            timeout = aiohttp.ClientTimeout(total=60)
            headers = {
                "Content-Type": "application/json",
                "x-api-key": self.api_key,
                "anthropic-version": "2023-06-01",
                "User-Agent": "Azure-Functions-News-Scraper/1.0"
            }
            self.session = aiohttp.ClientSession(timeout=timeout, headers=headers)

    async def chat_completion(self, 
                            system_prompt: str, 
                            user_content: str,
                            max_tokens: Optional[int] = None,
                            temperature: Optional[float] = None) -> str:
        await self.rate_limiter.acquire()
        await self._ensure_session()
        
        payload = {
            "model": self.config.model_name or "claude-3-opus-20240229",
            "system": system_prompt,
            "messages": [
                {"role": "user", "content": user_content}
            ],
            "max_tokens": max_tokens or self.config.max_tokens,
            "temperature": temperature or self.config.temperature,
        }
        
        try:
            async with self.session.post(self.endpoint, json=payload) as response:
                if response.status == 429:
                    raise RateLimitError("Claude rate limit exceeded")

                response_data = await response.json()
                if response.status != 200:
                    error_msg = response_data.get("error", {}).get("message", "Unknown error")
                    raise CopilotError(f"Claude API failed: {error_msg}")

                content_blocks = response_data.get("content") or []
                if not content_blocks:
                    raise CopilotError("Claude returned no content blocks")
                text = content_blocks[0].get("text")
                if not text:
                    raise CopilotError("Claude returned empty text")
                return text.strip()
        except (RateLimitError, CopilotError):
            raise
        except Exception as e:
            raise CopilotError(f"Claude error: {str(e)}")

    async def close(self) -> None:
        if self.session:
            await self.session.close()
            self.session = None


class AzureOpenAIProvider(IAIProvider):
    """
    Azure OpenAI implementation. Uses `api-key` header (not Bearer) and
    `max_completion_tokens` (gpt-5.x rejects `max_tokens`). Temperature is
    omitted because gpt-5.x deployments only accept the default value.
    The endpoint must be the full chat-completions URL, e.g.
    https://<resource>.openai.azure.com/openai/deployments/<deployment>/chat/completions?api-version=2024-12-01-preview
    """

    def __init__(self, config: CopilotConfig, api_key: str, endpoint: str):
        self.config = config
        self.api_key = api_key
        self.endpoint = endpoint
        self.rate_limiter = AIRateLimiter(config.rate_limit_requests_per_minute)
        self.session: Optional[aiohttp.ClientSession] = None

    async def _ensure_session(self) -> None:
        if not self.session:
            timeout = aiohttp.ClientTimeout(total=120)
            headers = {
                "Content-Type": "application/json",
                "api-key": self.api_key,
                "User-Agent": "Azure-Functions-News-Scraper/1.0",
            }
            self.session = aiohttp.ClientSession(timeout=timeout, headers=headers)

    async def chat_completion(self,
                            system_prompt: str,
                            user_content: str,
                            max_tokens: Optional[int] = None,
                            temperature: Optional[float] = None) -> str:
        await self.rate_limiter.acquire()
        await self._ensure_session()

        payload = {
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_content},
            ],
            "max_completion_tokens": max_tokens or self.config.max_tokens,
        }

        max_retries = 5
        retry_delay = 10
        for attempt in range(max_retries + 1):
            try:
                async with self.session.post(self.endpoint, json=payload) as response:
                    if response.status == 429:
                        if attempt < max_retries:
                            wait = retry_delay * (2 ** attempt)
                            logger.warning(f"Azure OpenAI rate limit. Retrying in {wait}s ({attempt + 1}/{max_retries})")
                            await asyncio.sleep(wait)
                            continue
                        raise RateLimitError("Azure OpenAI rate limit exceeded after maximum retries")

                    response_data = await response.json()
                    if response.status != 200:
                        error_msg = response_data.get("error", {}).get("message", "Unknown error")
                        raise CopilotError(f"Azure OpenAI API failed: {error_msg}")

                    choices = response_data.get("choices") or []
                    if not choices:
                        raise CopilotError("Azure OpenAI returned no choices")
                    message = choices[0].get("message") or {}
                    content = message.get("content")
                    if not content:
                        raise CopilotError("Azure OpenAI returned empty content")
                    return content.strip()
            except (RateLimitError, CopilotError):
                raise
            except Exception as e:
                if attempt < max_retries:
                    wait = retry_delay * (2 ** attempt)
                    logger.warning(f"Azure OpenAI error: {e}. Retrying in {wait}s...")
                    await asyncio.sleep(wait)
                    continue
                raise CopilotError(f"Azure OpenAI error: {str(e)}")

    async def close(self) -> None:
        if self.session:
            await self.session.close()
            self.session = None


class AIProviderFactory:
    """
    Factory for creating AI providers based on AI_TYPE.

    Strict per-type env var scheme — no cross-type fallbacks:
        AI_TYPE                → Which provider (GEMINI | OPENAI | AZURE_OPENAI | CLAUDE | DEEPSEEK | GROQ)
        {TYPE}_API_KEY         → Required. API key for that provider.
        {TYPE}_API_ENDPOINT    → Optional. Override default endpoint.
        {TYPE}_MODEL_NAME      → Optional. Override default model.

    Shared tuning params (AI_MAX_TOKENS, AI_TEMPERATURE, AI_RATE_LIMIT, AI_BATCH_SIZE)
    live on config_manager and apply regardless of provider.

    Setting OPENAI_API_KEY never leaks into a GEMINI run, and vice versa.
    """

    SUPPORTED_TYPES = {"GEMINI", "OPENAI", "AZURE_OPENAI", "CLAUDE", "DEEPSEEK", "GROQ"}

    @staticmethod
    async def create_provider(config: Optional[CopilotConfig] = None) -> IAIProvider:
        ai_type = os.getenv("AI_TYPE", "AZURE_OPENAI").upper()

        if ai_type not in AIProviderFactory.SUPPORTED_TYPES:
            raise CopilotError(
                f"Unsupported AI_TYPE: {ai_type}. "
                f"Supported: {sorted(AIProviderFactory.SUPPORTED_TYPES)}"
            )

        if not config:
            config = await config_manager.get_copilot_config()

        # Load API key from ONE env var: {TYPE}_API_KEY (env first, then Key Vault).
        key_var = f"{ai_type}_API_KEY"
        api_key = os.getenv(key_var)
        if not api_key:
            try:
                api_key = await config_manager.get_secret(key_var)
            except Exception:
                api_key = None
        if not api_key:
            raise CopilotError(
                f"{key_var} is not configured. Set it as an environment variable "
                f"or as an Azure Key Vault secret named '{key_var}'."
            )

        # Dispatch — each provider receives endpoint from config (resolved by config_manager
        # based on AI_TYPE, with {TYPE}_API_ENDPOINT / {TYPE}_MODEL_NAME overrides).
        if ai_type == "GEMINI":
            return GeminiProvider(config, api_key)
        if ai_type == "CLAUDE":
            return ClaudeProvider(config, api_key, endpoint=config.api_endpoint)
        if ai_type == "OPENAI":
            return OpenAICompatibleProvider(config, api_key, config.api_endpoint, "OpenAI")
        if ai_type == "AZURE_OPENAI":
            return AzureOpenAIProvider(config, api_key, config.api_endpoint)
        if ai_type == "DEEPSEEK":
            return OpenAICompatibleProvider(config, api_key, config.api_endpoint, "DeepSeek")
        if ai_type == "GROQ":
            return OpenAICompatibleProvider(config, api_key, config.api_endpoint, "Groq")

        # Unreachable because of the SUPPORTED_TYPES guard above.
        raise CopilotError(f"Unsupported AI_TYPE: {ai_type}")

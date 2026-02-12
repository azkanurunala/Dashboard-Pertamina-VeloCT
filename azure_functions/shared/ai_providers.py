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
        
        # Endpoint can be overridden via env
        base_url = os.getenv("GEMINI_API_ENDPOINT") or self.config.api_endpoint
        url = f"{base_url}?key={self.api_key}"
        
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
                
                return response_data["choices"][0]["message"]["content"].strip()
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
    
    def __init__(self, config: CopilotConfig, api_key: str):
        self.config = config
        self.api_key = api_key
        self.rate_limiter = AIRateLimiter(config.rate_limit_requests_per_minute)
        self.session: Optional[aiohttp.ClientSession] = None
        self.endpoint = os.getenv("CLAUDE_API_ENDPOINT", "https://api.anthropic.com/v1/messages")
    
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
                
                return response_data["content"][0].get("text", "").strip()
        except Exception as e:
            raise CopilotError(f"Claude error: {str(e)}")

    async def close(self) -> None:
        if self.session:
            await self.session.close()
            self.session = None


class AIProviderFactory:
    """
    Factory for creating AI providers based on configuration.
    """
    
    @staticmethod
    async def create_provider(config: Optional[CopilotConfig] = None) -> IAIProvider:
        ai_type = os.getenv("AI_TYPE", "GEMINI").upper()
        
        # Get config if not provided
        if not config:
            config = await config_manager.get_copilot_config()
        
        # Helper to get secret with fallbacks and KV support
        async def get_ai_secret(type_name: str) -> Optional[str]:
            # Try specific env vars first, then generic AI_API_KEY, then legacy AI_API_KEY
            potential_keys = [f"{type_name}_API_KEY", "AI_API_KEY", "AI_API_KEY", "CopilotApiKey"]
            if type_name == "GEMINI":
                potential_keys.append("GeminiApiKey")
            elif type_name == "OPENAI":
                potential_keys.append("OpenAIApiKey")
            elif type_name == "CLAUDE":
                potential_keys.append("ClaudeApiKey")
            
            for key in potential_keys:
                try:
                    # config_manager.get_secret handles Key Vault, placeholders, and env vars
                    val = await config_manager.get_secret(key)
                    if val and val != "PLACEHOLDER-WILL-BE-CONFIGURED-LATER":
                        return val
                except:
                    continue
            return None

        api_key = await get_ai_secret(ai_type)
        
        if not api_key:
            raise CopilotError(f"{ai_type} API key not configured in environment or Key Vault. Set {ai_type}_API_KEY or AI_API_KEY.")

        if ai_type == "GEMINI" or ai_type == "COPILOT":
            return GeminiProvider(config, api_key)
        
        elif ai_type == "CLAUDE":
            return ClaudeProvider(config, api_key)
        
        elif ai_type == "OPENAI":
            # Check for specific endpoints, then generic, then legacy
            endpoint = os.getenv("OPENAI_API_ENDPOINT") or os.getenv("AI_API_ENDPOINT") or \
                       os.getenv("CopilotEndpoint") or os.getenv("COPILOT_API_ENDPOINT") or \
                       "https://api.openai.com/v1/chat/completions"
            return OpenAICompatibleProvider(config, api_key, endpoint, "OpenAI")
            
        elif ai_type == "DEEPSEEK":
            endpoint = os.getenv("DEEPSEEK_API_ENDPOINT") or os.getenv("AI_API_ENDPOINT") or \
                       "https://api.deepseek.com/chat/completions"
            return OpenAICompatibleProvider(config, api_key, endpoint, "DeepSeek")
            
        elif ai_type == "GROQ":
            endpoint = os.getenv("GROQ_API_ENDPOINT") or os.getenv("AI_API_ENDPOINT") or \
                       "https://api.groq.com/openai/v1/chat/completions"
            return OpenAICompatibleProvider(config, api_key, endpoint, "Groq")
            
        else:
            # Default to OpenAI compatible for unknown types if endpoint is provided
            endpoint = os.getenv("AI_API_ENDPOINT") or os.getenv("CopilotEndpoint") or os.getenv("COPILOT_API_ENDPOINT")
            if endpoint:
                return OpenAICompatibleProvider(config, api_key, endpoint, ai_type.capitalize())
            
            raise CopilotError(f"Unsupported AI type: {ai_type}. Provide AI_API_ENDPOINT for generic OpenAI-compatible providers.")

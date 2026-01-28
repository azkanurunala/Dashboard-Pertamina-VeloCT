"""
Google Gemini API integration for sentiment analysis and summarization.
(Originally designed for Microsoft Copilot, now using Gemini API with same env var names)
"""

import asyncio
import json
import time
from typing import List, Optional, Dict, Any, AsyncGenerator
from datetime import datetime, timedelta
import aiohttp
import logging
from dataclasses import asdict

from .interfaces import ICopilotIntegration, CopilotError, RateLimitError
from .models import NewsArticle, SentimentAnalysis, SentimentLabel, CopilotConfig
from .config import config_manager
from .logging_config import get_logger

logger = get_logger(__name__)


class CopilotRateLimiter:
    """
    Rate limiter for Copilot API requests.
    Implements token bucket algorithm with sliding window.
    """
    
    def __init__(self, requests_per_minute: int = 60):
        """
        Initialize rate limiter.
        
        Args:
            requests_per_minute: Maximum requests allowed per minute
        """
        self.requests_per_minute = requests_per_minute
        self.tokens = requests_per_minute
        self.last_refill = time.time()
        self.lock = asyncio.Lock()
    
    async def acquire(self) -> None:
        """
        Acquire a token for making a request.
        Blocks if rate limit would be exceeded.
        """
        async with self.lock:
            now = time.time()
            # Refill tokens based on elapsed time
            elapsed = now - self.last_refill
            tokens_to_add = elapsed * (self.requests_per_minute / 60.0)
            self.tokens = min(self.requests_per_minute, self.tokens + tokens_to_add)
            self.last_refill = now
            
            if self.tokens < 1:
                # Calculate wait time
                wait_time = (1 - self.tokens) * (60.0 / self.requests_per_minute)
                logger.warning(f"Rate limit reached, waiting {wait_time:.2f} seconds")
                await asyncio.sleep(wait_time)
                self.tokens = 1
            
            self.tokens -= 1


class CopilotAPIClient:
    """
    Low-level client for Microsoft Copilot API interactions.
    Handles authentication, request formatting, and response parsing.
    """
    
    def __init__(self, config: CopilotConfig, api_key: str):
        """
        Initialize Copilot API client.
        
        Args:
            config: Copilot configuration
            api_key: API key for authentication
        """
        self.config = config
        self.api_key = api_key
        self.rate_limiter = CopilotRateLimiter(config.rate_limit_requests_per_minute)
        self.session: Optional[aiohttp.ClientSession] = None
    
    async def __aenter__(self):
        """Async context manager entry."""
        await self._ensure_session()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        if self.session:
            await self.session.close()
            self.session = None
    
    async def _ensure_session(self) -> None:
        """Ensure HTTP session is initialized."""
        if not self.session:
            timeout = aiohttp.ClientTimeout(total=60)
            headers = {
                "Content-Type": "application/json",
                "User-Agent": "Azure-Functions-News-Scraper/1.0"
            }
            self.session = aiohttp.ClientSession(
                timeout=timeout,
                headers=headers
            )
    
    async def _make_request(self, 
                          messages: List[Dict[str, str]], 
                          max_tokens: Optional[int] = None,
                          temperature: Optional[float] = None) -> Dict[str, Any]:
        """
        Make a request to the Gemini API.
        
        Args:
            messages: List of messages for the conversation
            max_tokens: Maximum tokens in response
            temperature: Sampling temperature
            
        Returns:
            API response data in OpenAI-compatible format
            
        Raises:
            CopilotError: If API request fails
            RateLimitError: If rate limit is exceeded
        """
        await self.rate_limiter.acquire()
        await self._ensure_session()
        
        # Convert OpenAI-style messages to Gemini format
        gemini_contents = []
        system_instruction = None
        
        for msg in messages:
            role = msg.get("role", "user")
            content = msg.get("content", "")
            
            if role == "system":
                # Gemini uses systemInstruction separately
                system_instruction = content
            else:
                gemini_role = "user" if role == "user" else "model"
                gemini_contents.append({
                    "role": gemini_role,
                    "parts": [{"text": content}]
                })
        
        payload = {
            "contents": gemini_contents,
            "generationConfig": {
                "maxOutputTokens": max_tokens or self.config.max_tokens,
                "temperature": temperature or self.config.temperature,
            }
        }
        
        if system_instruction:
            payload["systemInstruction"] = {
                "parts": [{"text": system_instruction}]
            }
        
        # Gemini uses API key as query parameter
        url = f"{self.config.api_endpoint}?key={self.api_key}"
        
        try:
            async with self.session.post(url, json=payload) as response:
                if response.status == 429:
                    retry_after = int(response.headers.get("Retry-After", 60))
                    raise RateLimitError(f"Rate limit exceeded, retry after {retry_after} seconds")
                
                if response.status == 401 or response.status == 403:
                    raise CopilotError("Authentication failed - invalid API key")
                
                response_data = await response.json()
                
                if response.status != 200:
                    error_msg = response_data.get("error", {}).get("message", "Unknown error")
                    raise CopilotError(f"API request failed: {error_msg}")
                
                # Convert Gemini response to OpenAI-compatible format
                gemini_text = ""
                if "candidates" in response_data and len(response_data["candidates"]) > 0:
                    candidate = response_data["candidates"][0]
                    if "content" in candidate and "parts" in candidate["content"]:
                        gemini_text = candidate["content"]["parts"][0].get("text", "")
                
                return {
                    "choices": [{
                        "message": {
                            "content": gemini_text
                        }
                    }]
                }
                
        except aiohttp.ClientError as e:
            raise CopilotError(f"Network error: {str(e)}")
        except json.JSONDecodeError as e:
            raise CopilotError(f"Invalid JSON response: {str(e)}")

    
    async def chat_completion(self, 
                            system_prompt: str, 
                            user_content: str,
                            max_tokens: Optional[int] = None,
                            temperature: Optional[float] = None) -> str:
        """
        Get a chat completion from Copilot.
        
        Args:
            system_prompt: System prompt defining the role
            user_content: User content to analyze
            max_tokens: Maximum tokens in response
            temperature: Sampling temperature
            
        Returns:
            Generated response text
            
        Raises:
            CopilotError: If completion fails
        """
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_content}
        ]
        
        response_data = await self._make_request(messages, max_tokens, temperature)
        
        try:
            return response_data["choices"][0]["message"]["content"].strip()
        except (KeyError, IndexError) as e:
            raise CopilotError(f"Invalid response format: {str(e)}")


class CopilotIntegration(ICopilotIntegration):
    """
    High-level integration with Microsoft Copilot for news analysis.
    Implements sentiment analysis and summarization capabilities.
    """
    
    def __init__(self):
        """Initialize Copilot integration."""
        self.config: Optional[CopilotConfig] = None
        self.api_key: Optional[str] = None
        self._initialized = False
    
    async def _ensure_initialized(self) -> None:
        """Ensure the integration is properly initialized."""
        if not self._initialized:
            self.config = await config_manager.get_copilot_config()
            self.api_key = await config_manager.get_secret("COPILOT_API_KEY")
            self._initialized = True
    
    async def analyze_sentiment(self, articles: List[NewsArticle]) -> SentimentAnalysis:
        """
        Analyze sentiment of news articles using Copilot.
        
        Args:
            articles: List of articles to analyze
            
        Returns:
            Sentiment analysis results
            
        Raises:
            CopilotError: If analysis fails
        """
        await self._ensure_initialized()
        
        if not articles:
            raise CopilotError("No articles provided for sentiment analysis")
        
        # Prepare content for analysis
        content = self._prepare_articles_content(articles)
        
        # Use general role prompt for sentiment analysis
        system_prompt = self.config.role_prompts.get("general", 
            "Analyze the sentiment of the following news articles.")
        
        user_prompt = f"""
        Please analyze the sentiment of the following news articles and provide:
        1. Overall sentiment score (-1.0 to 1.0, where -1.0 is very negative, 0 is neutral, 1.0 is very positive)
        2. Sentiment label (positive, negative, or neutral)
        3. Confidence score (0.0 to 1.0)
        4. A brief summary of key themes and sentiment drivers
        
        Articles:
        {content}
        
        Please respond in the following JSON format:
        {{
            "sentiment_score": <float>,
            "sentiment_label": "<positive|negative|neutral>",
            "confidence": <float>,
            "summary": "<string>"
        }}
        """
        
        try:
            async with CopilotAPIClient(self.config, self.api_key) as client:
                response = await client.chat_completion(system_prompt, user_prompt)
                
                # Parse JSON response
                result = json.loads(response)
                
                return SentimentAnalysis(
                    sentiment_score=float(result["sentiment_score"]),
                    sentiment_label=SentimentLabel(result["sentiment_label"]),
                    confidence=float(result["confidence"]),
                    summary=result["summary"],
                    article_ids=[article.id for article in articles if article.id],
                    analysis_date=datetime.utcnow(),
                    model_version=f"copilot-{self.config.model_name}"
                )
                
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse Copilot response as JSON: {str(e)}")
            raise CopilotError(f"Invalid JSON response from Copilot: {str(e)}")
        except KeyError as e:
            logger.error(f"Missing required field in Copilot response: {str(e)}")
            raise CopilotError(f"Missing required field in response: {str(e)}")
        except ValueError as e:
            logger.error(f"Invalid value in Copilot response: {str(e)}")
            raise CopilotError(f"Invalid value in response: {str(e)}")
    
    async def generate_summary(self, 
                             articles: List[NewsArticle], 
                             role_prompt: str) -> str:
        """
        Generate a summary of articles using role-specific prompts.
        
        Args:
            articles: List of articles to summarize
            role_prompt: Role-specific prompt template key
            
        Returns:
            Generated summary
            
        Raises:
            CopilotError: If summary generation fails
        """
        await self._ensure_initialized()
        
        if not articles:
            raise CopilotError("No articles provided for summary generation")
        
        # Get role-specific prompt
        system_prompt = self.config.role_prompts.get(role_prompt, 
            self.config.role_prompts.get("general", 
                "Provide a comprehensive summary of the following news articles."))
        
        # Prepare content for summarization
        content = self._prepare_articles_content(articles)
        
        user_prompt = f"""
        Please provide a comprehensive summary of the following news articles:
        
        {content}
        
        Focus on:
        - Key themes and trends
        - Important developments and events
        - Market implications (if applicable)
        - Policy or regulatory changes (if applicable)
        - Overall sentiment and outlook
        """
        
        try:
            async with CopilotAPIClient(self.config, self.api_key) as client:
                return await client.chat_completion(system_prompt, user_prompt)
                
        except Exception as e:
            logger.error(f"Failed to generate summary: {str(e)}")
            raise CopilotError(f"Summary generation failed: {str(e)}")
    
    async def batch_process(self, 
                          articles: List[NewsArticle], 
                          batch_size: Optional[int] = None) -> AsyncGenerator[SentimentAnalysis, None]:
        """
        Process articles in batches for large volumes.
        
        Args:
            articles: List of articles to process
            batch_size: Size of each batch (optional)
            
        Yields:
            Sentiment analysis results for each batch
            
        Raises:
            CopilotError: If batch processing fails
        """
        await self._ensure_initialized()
        
        if not articles:
            return
        
        batch_size = batch_size or self.config.batch_size
        
        for i in range(0, len(articles), batch_size):
            batch = articles[i:i + batch_size]
            
            try:
                logger.info(f"Processing batch {i//batch_size + 1} with {len(batch)} articles")
                analysis = await self.analyze_sentiment(batch)
                yield analysis
                
            except Exception as e:
                logger.error(f"Failed to process batch {i//batch_size + 1}: {str(e)}")
                # Continue with next batch instead of failing completely
                continue
    
    async def health_check(self) -> bool:
        """
        Check Copilot API connectivity and health.
        
        Returns:
            True if API is healthy, False otherwise
        """
        try:
            await self._ensure_initialized()
            
            # Simple test request
            test_article = NewsArticle(
                title="Test Article",
                content="This is a test article for health check.",
                url="https://example.com/test",
                source="test",
                published_date=datetime.utcnow()
            )
            
            async with CopilotAPIClient(self.config, self.api_key) as client:
                response = await client.chat_completion(
                    "You are a helpful assistant.",
                    "Please respond with 'OK' if you can process this request.",
                    max_tokens=10
                )
                
                return "OK" in response.upper()
                
        except Exception as e:
            logger.error(f"Copilot health check failed: {str(e)}")
            return False
    
    def _prepare_articles_content(self, articles: List[NewsArticle]) -> str:
        """
        Prepare articles content for Copilot processing.
        
        Args:
            articles: List of articles to prepare
            
        Returns:
            Formatted content string
        """
        content_parts = []
        
        for i, article in enumerate(articles, 1):
            # Truncate content if too long to fit within token limits
            max_content_length = 2000  # Approximate character limit per article
            content = article.content[:max_content_length]
            if len(article.content) > max_content_length:
                content += "..."
            
            article_text = f"""
Article {i}:
Title: {article.title}
Source: {article.source}
Date: {article.published_date.strftime('%Y-%m-%d')}
Content: {content}
---
"""
            content_parts.append(article_text)
        
        return "\n".join(content_parts)


# Global Copilot integration instance
copilot_integration = CopilotIntegration()
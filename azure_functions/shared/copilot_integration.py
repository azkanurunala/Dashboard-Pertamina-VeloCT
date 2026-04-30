"""
Google Gemini API integration for sentiment analysis and summarization.
(Originally designed for Microsoft Copilot, now using Gemini API with same env var names)
"""

import asyncio
import os
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
from .ai_providers import AIProviderFactory, IAIProvider

logger = get_logger(__name__)


class CopilotIntegration(ICopilotIntegration):
    """
    High-level integration for news analysis.
    Uses AIProviderFactory to support multiple AI backends (Gemini, OpenAI, etc.)
    """
    
    def __init__(self, config: Optional[CopilotConfig] = None):
        """
        Initialize integration.
        
        Args:
            config: Optional configuration (if not provided, will be loaded from config_manager)
        """
        self.config = config
        self.provider: Optional[IAIProvider] = None
        self._initialized = False
    
    async def _ensure_initialized(self) -> None:
        """Ensure the integration is properly initialized."""
        if not self._initialized:
            if not self.config:
                self.config = await config_manager.get_copilot_config()
            
            # Use factory to get the configured AI provider
            self.provider = await AIProviderFactory.create_provider(self.config)
            self._initialized = True
            
            ai_type = os.getenv("AI_TYPE", "AZURE_OPENAI").upper()
            logger.info(f"CopilotIntegration initialized with provider: {ai_type}")
    
    async def analyze_sentiment(self, articles: List[NewsArticle]) -> SentimentAnalysis:
        """
        Analyze sentiment of news articles using the configured AI provider.
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
            response = await self.provider.chat_completion(system_prompt, user_prompt)
            logger.debug(f"Raw AI response: {response}")
            
            # Extract and parse JSON response
            json_str = self._extract_json(response)
            if not json_str:
                logger.error(f"Could not extract JSON from AI response: {response}")
                raise CopilotError("AI response did not contain valid JSON")
                
            result = json.loads(json_str)
            
            return SentimentAnalysis(
                sentiment_score=float(result.get("sentiment_score", 0.0)),
                sentiment_label=SentimentLabel(result.get("sentiment_label", "neutral")),
                confidence=float(result.get("confidence", 0.0)),
                summary=result.get("summary", ""),
                article_ids=[article.id for article in articles if article.id],
                analysis_date=datetime.utcnow(),
                model_version=f"{os.getenv('AI_TYPE', 'AZURE_OPENAI').lower()}-{self.config.model_name}"
            )
                
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse AI response as JSON: {str(e)}\nResponse: {response}")
            raise CopilotError(f"Invalid JSON response from AI: {str(e)}")
        except Exception as e:
            logger.error(f"Sentiment analysis failed: {str(e)}")
            raise CopilotError(f"Analysis failed: {str(e)}")

    def _extract_json(self, text: str) -> Optional[str]:
        """
        Extract JSON string from text, handling markdown code blocks.
        """
        if not text:
            return None
            
        # Try finding markdown code blocks
        import re
        json_match = re.search(r'```json\s*(.*?)\s*```', text, re.DOTALL)
        if json_match:
            return json_match.group(1).strip()
            
        # Try finding any code block
        json_match = re.search(r'```\s*(.*?)\s*```', text, re.DOTALL)
        if json_match:
            return json_match.group(1).strip()
            
        # Fallback to finding first { and last }
        start = text.find('{')
        end = text.rfind('}')
        if start != -1 and end != -1 and end > start:
            return text[start:end+1].strip()
            
        return text.strip()
    
    async def generate_summary(self, 
                             articles: List[NewsArticle], 
                             role_prompt: str) -> str:
        """
        Generate a summary of articles using role-specific prompts.
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
            return await self.provider.chat_completion(system_prompt, user_prompt)
        except Exception as e:
            logger.error(f"Failed to generate summary: {str(e)}")
            raise CopilotError(f"Summary generation failed: {str(e)}")
    
    async def batch_process(self, 
                          articles: List[NewsArticle], 
                          batch_size: Optional[int] = None) -> AsyncGenerator[SentimentAnalysis, None]:
        """
        Process articles in batches for large volumes.
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
        Check AI API connectivity and health.
        """
        try:
            await self._ensure_initialized()
            
            response = await self.provider.chat_completion(
                "You are a helpful assistant.",
                "Please respond with 'OK' if you can process this request.",
                max_tokens=10
            )
            
            return "OK" in response.upper()
                
        except Exception as e:
            logger.error(f"AI health check failed: {str(e)}")
            return False
    
    async def close(self) -> None:
        """Close the underlying AI provider session."""
        if self.provider:
            await self.provider.close()
            self._initialized = False
    
    def _prepare_articles_content(self, articles: List[NewsArticle]) -> str:
        """
        Prepare articles content for processing.
        """
        content_parts = []
        
        for i, article in enumerate(articles, 1):
            # Truncate content if too long to fit within token limits
            max_content_length = 2000
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


# Global integration instance
copilot_integration = CopilotIntegration()


# Global Copilot integration instance
copilot_integration = CopilotIntegration()
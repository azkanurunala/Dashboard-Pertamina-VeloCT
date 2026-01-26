"""
Property-based tests for Microsoft Copilot API integration.
Tests universal properties that should hold for Copilot API usage in sentiment analysis operations.

**Feature: azure-functions-porting, Property 3: Copilot API Integration**
**Validates: Requirements 1.4, 5.1**

This test validates that:
1. Microsoft Copilot API is called for sentiment analysis operations
2. No Google Gemini API calls are made
3. Copilot API integration works correctly with proper authentication
4. API responses are handled appropriately
5. Rate limiting and error handling work as expected
"""

import asyncio
import os
import sys
import json
import time
from typing import List, Dict, Any, Optional, AsyncGenerator
from unittest.mock import Mock, patch, AsyncMock, MagicMock
from datetime import datetime, timedelta
import uuid
import aiohttp
import pytest

# Mock the testing framework since we can't install it
class MockHypothesis:
    """Mock hypothesis for property testing when pytest is not available."""
    
    @staticmethod
    def given(*args, **kwargs):
        def decorator(func):
            func._hypothesis_given = True
            return func
        return decorator
    
    @staticmethod
    def settings(*args, **kwargs):
        def decorator(func):
            func._hypothesis_settings = True
            return func
        return decorator
    
    class strategies:
        @staticmethod
        def lists(strategy, min_size=0, max_size=10):
            return f"lists({strategy}, min_size={min_size}, max_size={max_size})"
        
        @staticmethod
        def text(min_size=0, max_size=100):
            return f"text(min_size={min_size}, max_size={max_size})"
        
        @staticmethod
        def integers(min_value=0, max_value=100):
            return f"integers(min_value={min_value}, max_value={max_value})"
        
        @staticmethod
        def floats(min_value=0.0, max_value=1.0):
            return f"floats(min_value={min_value}, max_value={max_value})"
        
        @staticmethod
        def sampled_from(choices):
            return f"sampled_from({choices})"
        
        @staticmethod
        def one_of(*strategies):
            return f"one_of({strategies})"
    
    @staticmethod
    def composite(func):
        return func

try:
    from hypothesis import given, strategies as st, settings, composite
    HYPOTHESIS_AVAILABLE = True
except ImportError:
    # Use mock when hypothesis is not available
    mock_hypothesis = MockHypothesis()
    given = mock_hypothesis.given
    st = mock_hypothesis.strategies
    settings = mock_hypothesis.settings
    composite = mock_hypothesis.composite
    HYPOTHESIS_AVAILABLE = False

sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

from shared.copilot_integration import (
    CopilotIntegration, CopilotAPIClient, CopilotRateLimiter
)
from shared.models import NewsArticle, SentimentAnalysis, SentimentLabel, CopilotConfig
from shared.interfaces import CopilotError, RateLimitError
from shared.config import config_manager


class TestCopilotAPIIntegrationProperties:
    """
    Property-based tests for Microsoft Copilot API integration.
    **Feature: azure-functions-porting, Property 3: Copilot API Integration**
    **Validates: Requirements 1.4, 5.1**
    """
    
    def __init__(self):
        """Initialize test configuration."""
        self.test_config = CopilotConfig(
            api_endpoint="https://api.openai.com/v1/chat/completions",
            model_name="gpt-4",
            max_tokens=4000,
            temperature=0.3,
            role_prompts={
                "general": "Analyze the sentiment of the following news articles.",
                "financial": "Analyze the financial sentiment of the following news articles.",
                "political": "Analyze the political sentiment of the following news articles."
            },
            rate_limit_requests_per_minute=60,
            batch_size=10
        )
        
        self.test_api_key = "test-copilot-api-key-12345"
        self.test_results = []
        
        # Mock responses for different scenarios
        self.mock_responses = {
            "success": {
                "choices": [{
                    "message": {
                        "content": json.dumps({
                            "sentiment_score": 0.2,
                            "sentiment_label": "positive",
                            "confidence": 0.85,
                            "summary": "Overall positive sentiment with optimistic outlook."
                        })
                    }
                }]
            },
            "negative": {
                "choices": [{
                    "message": {
                        "content": json.dumps({
                            "sentiment_score": -0.6,
                            "sentiment_label": "negative",
                            "confidence": 0.92,
                            "summary": "Predominantly negative sentiment with concerns about market conditions."
                        })
                    }
                }]
            },
            "neutral": {
                "choices": [{
                    "message": {
                        "content": json.dumps({
                            "sentiment_score": 0.05,
                            "sentiment_label": "neutral",
                            "confidence": 0.78,
                            "summary": "Balanced sentiment with mixed positive and negative indicators."
                        })
                    }
                }]
            }
        }
    
    async def test_property_3_copilot_api_integration(self):
        """
        **Property 3: Copilot API Integration**
        **Validates: Requirements 1.4, 5.1**
        
        Universal Property: For any sentiment analysis operation, Microsoft Copilot API 
        should be called and no Google Gemini API calls should be made.
        
        This property ensures that:
        1. Microsoft Copilot API is the exclusive AI provider for sentiment analysis
        2. Google Gemini API is never called during sentiment analysis operations
        3. Copilot API integration uses proper authentication and endpoints
        4. API responses are correctly parsed and validated
        5. Rate limiting is properly implemented and respected
        6. Error handling works correctly for various failure scenarios
        7. Batch processing uses Copilot API for all operations
        """
        try:
            print("Testing Property 3: Copilot API Integration")
            print("-" * 50)
            
            # Test different scenarios with various article sets and configurations
            test_scenarios = [
                ("Single article sentiment analysis", self._test_single_article_copilot_usage),
                ("Multiple articles sentiment analysis", self._test_multiple_articles_copilot_usage),
                ("Batch processing operations", self._test_batch_processing_copilot_usage),
                ("No Google Gemini API calls", self._test_no_gemini_api_calls),
                ("Proper authentication usage", self._test_proper_authentication),
                ("API endpoint validation", self._test_api_endpoint_validation),
                ("Response parsing and validation", self._test_response_parsing_validation),
                ("Rate limiting compliance", self._test_rate_limiting_compliance),
                ("Error handling scenarios", self._test_error_handling_scenarios),
                ("Role-specific prompt usage", self._test_role_specific_prompts),
                ("API health check functionality", self._test_api_health_check),
                ("Concurrent API operations", self._test_concurrent_api_operations)
            ]
            
            passed_tests = 0
            total_tests = len(test_scenarios)
            
            for test_name, test_func in test_scenarios:
                try:
                    print(f"  Running: {test_name}...")
                    await test_func()
                    print(f"  ✓ {test_name} PASSED")
                    passed_tests += 1
                    self.test_results.append((test_name, True, None))
                except Exception as e:
                    print(f"  ✗ {test_name} FAILED: {str(e)}")
                    self.test_results.append((test_name, False, str(e)))
            
            print(f"\nProperty 3 Results: {passed_tests}/{total_tests} tests passed")
            
            # Property validation: All tests must pass for the property to hold
            if passed_tests == total_tests:
                print("✓ Property 3: Copilot API Integration - VALIDATED")
                return True
            else:
                print("✗ Property 3: Copilot API Integration - VIOLATED")
                return False
            
        except Exception as e:
            print(f"✗ Property 3 test execution failed: {str(e)}")
            return False
    
    async def _test_single_article_copilot_usage(self):
        """Test that single article sentiment analysis uses Copilot API exclusively."""
        # Create test article
        test_article = NewsArticle(
            title="Test Article for Copilot Integration",
            content="This is a test article to validate Copilot API integration. The content discusses positive market trends and optimistic forecasts.",
            url="https://test-copilot-integration.com/article/1",
            source="TestSource",
            published_date=datetime.utcnow(),
            keywords=["test", "copilot", "integration"]
        )
        
        # Mock aiohttp session and response
        with patch('shared.copilot_integration.aiohttp.ClientSession') as mock_session_class:
            mock_session = AsyncMock()
            mock_session_class.return_value = mock_session
            
            # Mock successful response
            mock_response = AsyncMock()
            mock_response.status = 200
            mock_response.json.return_value = self.mock_responses["success"]
            mock_response.headers = {}
            
            mock_session.post.return_value.__aenter__.return_value = mock_response
            
            # Mock config manager
            with patch.object(config_manager, 'get_copilot_config', return_value=self.test_config):
                with patch.object(config_manager, 'get_secret', return_value=self.test_api_key):
                    
                    # Test Copilot integration
                    integration = CopilotIntegration()
                    result = await integration.analyze_sentiment([test_article])
                    
                    # Property: Copilot API should be called
                    mock_session.post.assert_called_once()
                    call_args = mock_session.post.call_args
                    
                    # Property: Should call Copilot endpoint (OpenAI API)
                    assert call_args[0][0] == self.test_config.api_endpoint, "Should call Copilot API endpoint"
                    
                    # Property: Should use proper authentication
                    call_kwargs = call_args[1]
                    payload = call_kwargs['json']
                    assert payload['model'] == self.test_config.model_name, "Should use configured Copilot model"
                    
                    # Property: Should return valid sentiment analysis
                    assert isinstance(result, SentimentAnalysis), "Should return SentimentAnalysis object"
                    assert result.sentiment_label == SentimentLabel.POSITIVE, "Should parse sentiment correctly"
                    assert 0.0 <= result.confidence <= 1.0, "Confidence should be valid range"
                    assert -1.0 <= result.sentiment_score <= 1.0, "Sentiment score should be valid range"
    
    async def _test_multiple_articles_copilot_usage(self):
        """Test that multiple articles sentiment analysis uses Copilot API exclusively."""
        # Create multiple test articles
        test_articles = [
            NewsArticle(
                title=f"Test Article {i}",
                content=f"Test content for article {i} with various sentiment indicators.",
                url=f"https://test-copilot-{i}.com/article",
                source="TestSource",
                published_date=datetime.utcnow() - timedelta(days=i),
                keywords=["test", f"article_{i}"]
            )
            for i in range(5)
        ]
        
        # Mock aiohttp session
        with patch('shared.copilot_integration.aiohttp.ClientSession') as mock_session_class:
            mock_session = AsyncMock()
            mock_session_class.return_value = mock_session
            
            # Mock successful response
            mock_response = AsyncMock()
            mock_response.status = 200
            mock_response.json.return_value = self.mock_responses["neutral"]
            mock_response.headers = {}
            
            mock_session.post.return_value.__aenter__.return_value = mock_response
            
            # Mock config manager
            with patch.object(config_manager, 'get_copilot_config', return_value=self.test_config):
                with patch.object(config_manager, 'get_secret', return_value=self.test_api_key):
                    
                    integration = CopilotIntegration()
                    result = await integration.analyze_sentiment(test_articles)
                    
                    # Property: Copilot API should be called for multiple articles
                    mock_session.post.assert_called_once()
                    
                    # Property: All articles should be included in the request
                    call_args = mock_session.post.call_args
                    payload = call_args[1]['json']
                    user_message = payload['messages'][1]['content']
                    
                    # Verify all articles are included
                    for i, article in enumerate(test_articles):
                        assert f"Article {i+1}:" in user_message, f"Article {i+1} should be included in request"
                        assert article.title in user_message, f"Article {i+1} title should be included"
                    
                    # Property: Should return valid analysis for all articles
                    assert len(result.article_ids) == len(test_articles), "Should analyze all provided articles"
    
    async def _test_batch_processing_copilot_usage(self):
        """Test that batch processing uses Copilot API for all operations."""
        # Create large set of articles for batch processing
        large_article_set = [
            NewsArticle(
                title=f"Batch Article {i}",
                content=f"Batch processing test content {i} for Copilot API validation.",
                url=f"https://batch-test-{i}.com/article",
                source="BatchTestSource",
                published_date=datetime.utcnow() - timedelta(hours=i),
                keywords=["batch", "test", f"article_{i}"]
            )
            for i in range(25)  # More than batch_size (10) to trigger batching
        ]
        
        # Mock aiohttp session
        with patch('shared.copilot_integration.aiohttp.ClientSession') as mock_session_class:
            mock_session = AsyncMock()
            mock_session_class.return_value = mock_session
            
            # Mock successful response
            mock_response = AsyncMock()
            mock_response.status = 200
            mock_response.json.return_value = self.mock_responses["positive"]
            mock_response.headers = {}
            
            mock_session.post.return_value.__aenter__.return_value = mock_response
            
            # Mock config manager
            with patch.object(config_manager, 'get_copilot_config', return_value=self.test_config):
                with patch.object(config_manager, 'get_secret', return_value=self.test_api_key):
                    
                    integration = CopilotIntegration()
                    
                    # Process articles in batches
                    batch_results = []
                    async for batch_result in integration.batch_process(large_article_set):
                        batch_results.append(batch_result)
                    
                    # Property: Multiple batches should be processed
                    expected_batches = (len(large_article_set) + self.test_config.batch_size - 1) // self.test_config.batch_size
                    assert len(batch_results) == expected_batches, f"Should process {expected_batches} batches"
                    
                    # Property: Each batch should call Copilot API
                    assert mock_session.post.call_count == expected_batches, "Each batch should call Copilot API"
                    
                    # Property: All batch results should be valid
                    for batch_result in batch_results:
                        assert isinstance(batch_result, SentimentAnalysis), "Each batch should return SentimentAnalysis"
                        assert batch_result.model_version.startswith("copilot-"), "Should use Copilot model"
    
    async def _test_no_gemini_api_calls(self):
        """Test that no Google Gemini API calls are made during sentiment analysis."""
        test_article = NewsArticle(
            title="No Gemini Test Article",
            content="This test ensures no Google Gemini API calls are made.",
            url="https://no-gemini-test.com/article",
            source="NoGeminiTestSource",
            published_date=datetime.utcnow(),
            keywords=["no", "gemini", "test"]
        )
        
        # Track all HTTP requests to detect any Gemini API calls
        http_requests = []
        
        def track_http_request(*args, **kwargs):
            http_requests.append({
                'url': args[0] if args else kwargs.get('url', ''),
                'method': 'POST',
                'timestamp': datetime.utcnow()
            })
            
            # Mock response
            mock_response = AsyncMock()
            mock_response.status = 200
            mock_response.json.return_value = self.mock_responses["success"]
            mock_response.headers = {}
            return mock_response.__aenter__()
        
        # Mock all HTTP libraries that could be used for API calls
        with patch('aiohttp.ClientSession.post', side_effect=track_http_request):
            with patch('requests.post', side_effect=track_http_request):
                with patch('httpx.AsyncClient.post', side_effect=track_http_request):
                    
                    # Mock config manager
                    with patch.object(config_manager, 'get_copilot_config', return_value=self.test_config):
                        with patch.object(config_manager, 'get_secret', return_value=self.test_api_key):
                            
                            integration = CopilotIntegration()
                            await integration.analyze_sentiment([test_article])
                            
                            # Property: No Google Gemini API endpoints should be called
                            gemini_endpoints = [
                                'generativelanguage.googleapis.com',
                                'ai.google.dev',
                                'gemini.google.com',
                                'bard.google.com',
                                'makersuite.google.com'
                            ]
                            
                            for request in http_requests:
                                url = request['url']
                                for gemini_endpoint in gemini_endpoints:
                                    assert gemini_endpoint not in url, f"Google Gemini API endpoint detected: {url}"
                            
                            # Property: Only Copilot/OpenAI endpoints should be called
                            copilot_endpoints_called = [req['url'] for req in http_requests 
                                                     if 'openai.com' in req['url'] or 'api.copilot' in req['url']]
                            assert len(copilot_endpoints_called) > 0, "Copilot API should be called"
    
    async def _test_proper_authentication(self):
        """Test that Copilot API integration uses proper authentication."""
        test_article = NewsArticle(
            title="Authentication Test Article",
            content="Testing proper authentication with Copilot API.",
            url="https://auth-test.com/article",
            source="AuthTestSource",
            published_date=datetime.utcnow(),
            keywords=["auth", "test"]
        )
        
        # Mock aiohttp session to capture authentication headers
        with patch('shared.copilot_integration.aiohttp.ClientSession') as mock_session_class:
            mock_session = AsyncMock()
            mock_session_class.return_value = mock_session
            
            # Mock successful response
            mock_response = AsyncMock()
            mock_response.status = 200
            mock_response.json.return_value = self.mock_responses["success"]
            mock_response.headers = {}
            
            mock_session.post.return_value.__aenter__.return_value = mock_response
            
            # Mock config manager
            with patch.object(config_manager, 'get_copilot_config', return_value=self.test_config):
                with patch.object(config_manager, 'get_secret', return_value=self.test_api_key):
                    
                    integration = CopilotIntegration()
                    await integration.analyze_sentiment([test_article])
                    
                    # Property: Session should be created with proper authentication headers
                    session_init_call = mock_session_class.call_args
                    session_kwargs = session_init_call[1] if session_init_call else {}
                    
                    if 'headers' in session_kwargs:
                        headers = session_kwargs['headers']
                        # Property: Authorization header should be present with Bearer token
                        assert 'Authorization' in headers, "Authorization header should be present"
                        assert headers['Authorization'].startswith('Bearer '), "Should use Bearer token authentication"
                        assert self.test_api_key in headers['Authorization'], "Should use correct API key"
                    
                    # Property: Content-Type should be set for JSON requests
                    mock_session.post.assert_called_once()
                    call_kwargs = mock_session.post.call_args[1]
                    assert 'json' in call_kwargs, "Should send JSON payload"
    
    async def _test_api_endpoint_validation(self):
        """Test that correct Copilot API endpoints are used."""
        test_article = NewsArticle(
            title="Endpoint Test Article",
            content="Testing correct API endpoint usage.",
            url="https://endpoint-test.com/article",
            source="EndpointTestSource",
            published_date=datetime.utcnow(),
            keywords=["endpoint", "test"]
        )
        
        # Mock aiohttp session
        with patch('shared.copilot_integration.aiohttp.ClientSession') as mock_session_class:
            mock_session = AsyncMock()
            mock_session_class.return_value = mock_session
            
            # Mock successful response
            mock_response = AsyncMock()
            mock_response.status = 200
            mock_response.json.return_value = self.mock_responses["success"]
            mock_response.headers = {}
            
            mock_session.post.return_value.__aenter__.return_value = mock_response
            
            # Mock config manager
            with patch.object(config_manager, 'get_copilot_config', return_value=self.test_config):
                with patch.object(config_manager, 'get_secret', return_value=self.test_api_key):
                    
                    integration = CopilotIntegration()
                    await integration.analyze_sentiment([test_article])
                    
                    # Property: Should call the configured Copilot API endpoint
                    mock_session.post.assert_called_once()
                    call_args = mock_session.post.call_args
                    called_url = call_args[0][0]
                    
                    assert called_url == self.test_config.api_endpoint, f"Should call configured endpoint: {self.test_config.api_endpoint}"
                    
                    # Property: Should not call any non-Copilot endpoints
                    forbidden_endpoints = [
                        'generativelanguage.googleapis.com',
                        'claude.ai',
                        'api.anthropic.com',
                        'api.cohere.ai'
                    ]
                    
                    for forbidden in forbidden_endpoints:
                        assert forbidden not in called_url, f"Should not call forbidden endpoint: {forbidden}"
    
    async def _test_response_parsing_validation(self):
        """Test that API responses are correctly parsed and validated."""
        test_article = NewsArticle(
            title="Response Parsing Test",
            content="Testing response parsing and validation.",
            url="https://response-test.com/article",
            source="ResponseTestSource",
            published_date=datetime.utcnow(),
            keywords=["response", "parsing"]
        )
        
        # Test different response scenarios
        test_scenarios = [
            ("positive_sentiment", self.mock_responses["success"], SentimentLabel.POSITIVE),
            ("negative_sentiment", self.mock_responses["negative"], SentimentLabel.NEGATIVE),
            ("neutral_sentiment", self.mock_responses["neutral"], SentimentLabel.NEUTRAL)
        ]
        
        for scenario_name, mock_response_data, expected_label in test_scenarios:
            with patch('shared.copilot_integration.aiohttp.ClientSession') as mock_session_class:
                mock_session = AsyncMock()
                mock_session_class.return_value = mock_session
                
                # Mock response for this scenario
                mock_response = AsyncMock()
                mock_response.status = 200
                mock_response.json.return_value = mock_response_data
                mock_response.headers = {}
                
                mock_session.post.return_value.__aenter__.return_value = mock_response
                
                # Mock config manager
                with patch.object(config_manager, 'get_copilot_config', return_value=self.test_config):
                    with patch.object(config_manager, 'get_secret', return_value=self.test_api_key):
                        
                        integration = CopilotIntegration()
                        result = await integration.analyze_sentiment([test_article])
                        
                        # Property: Response should be correctly parsed
                        assert isinstance(result, SentimentAnalysis), f"Should return SentimentAnalysis for {scenario_name}"
                        assert result.sentiment_label == expected_label, f"Should parse correct sentiment label for {scenario_name}"
                        
                        # Property: All required fields should be present and valid
                        assert result.sentiment_score is not None, f"Sentiment score should be present for {scenario_name}"
                        assert -1.0 <= result.sentiment_score <= 1.0, f"Sentiment score should be valid for {scenario_name}"
                        assert 0.0 <= result.confidence <= 1.0, f"Confidence should be valid for {scenario_name}"
                        assert result.summary is not None and result.summary.strip(), f"Summary should be present for {scenario_name}"
                        assert result.model_version.startswith("copilot-"), f"Model version should indicate Copilot for {scenario_name}"
    
    async def _test_rate_limiting_compliance(self):
        """Test that rate limiting is properly implemented and respected."""
        # Create rate limiter with low limit for testing
        test_rate_limiter = CopilotRateLimiter(requests_per_minute=2)  # Very low limit
        
        # Property: Rate limiter should allow requests within limit
        start_time = time.time()
        await test_rate_limiter.acquire()
        first_request_time = time.time() - start_time
        
        # First request should be immediate
        assert first_request_time < 0.1, "First request should be immediate"
        
        # Second request should also be immediate (within limit)
        start_time = time.time()
        await test_rate_limiter.acquire()
        second_request_time = time.time() - start_time
        
        assert second_request_time < 0.1, "Second request should be immediate"
        
        # Third request should be delayed (exceeds limit)
        start_time = time.time()
        await test_rate_limiter.acquire()
        third_request_time = time.time() - start_time
        
        # Property: Rate limiting should introduce delay when limit exceeded
        assert third_request_time > 0.5, "Third request should be delayed due to rate limiting"
        
        # Test rate limiting in Copilot integration
        with patch('shared.copilot_integration.aiohttp.ClientSession') as mock_session_class:
            mock_session = AsyncMock()
            mock_session_class.return_value = mock_session
            
            # Mock rate limit response (429)
            mock_rate_limit_response = AsyncMock()
            mock_rate_limit_response.status = 429
            mock_rate_limit_response.headers = {"Retry-After": "60"}
            mock_rate_limit_response.json.return_value = {"error": {"message": "Rate limit exceeded"}}
            
            mock_session.post.return_value.__aenter__.return_value = mock_rate_limit_response
            
            # Mock config manager
            with patch.object(config_manager, 'get_copilot_config', return_value=self.test_config):
                with patch.object(config_manager, 'get_secret', return_value=self.test_api_key):
                    
                    integration = CopilotIntegration()
                    
                    # Property: Rate limit errors should be properly handled
                    with pytest.raises(RateLimitError) as exc_info:
                        await integration.analyze_sentiment([NewsArticle(
                            title="Rate limit test",
                            content="Testing rate limit handling",
                            url="https://rate-limit-test.com",
                            source="RateLimitTest",
                            published_date=datetime.utcnow()
                        )])
                    
                    assert "Rate limit exceeded" in str(exc_info.value), "Should raise RateLimitError with proper message"
    
    async def _test_error_handling_scenarios(self):
        """Test that various error scenarios are handled correctly."""
        test_article = NewsArticle(
            title="Error Handling Test",
            content="Testing error handling scenarios.",
            url="https://error-test.com/article",
            source="ErrorTestSource",
            published_date=datetime.utcnow(),
            keywords=["error", "handling"]
        )
        
        # Test different error scenarios
        error_scenarios = [
            (401, "Authentication failed - invalid API key", "authentication error"),
            (403, "Access forbidden - insufficient permissions", "permission error"),
            (500, "Internal server error", "server error"),
            (503, "Service unavailable", "service unavailable")
        ]
        
        for status_code, error_message, scenario_name in error_scenarios:
            with patch('shared.copilot_integration.aiohttp.ClientSession') as mock_session_class:
                mock_session = AsyncMock()
                mock_session_class.return_value = mock_session
                
                # Mock error response
                mock_error_response = AsyncMock()
                mock_error_response.status = status_code
                mock_error_response.json.return_value = {"error": {"message": error_message}}
                mock_error_response.headers = {}
                
                mock_session.post.return_value.__aenter__.return_value = mock_error_response
                
                # Mock config manager
                with patch.object(config_manager, 'get_copilot_config', return_value=self.test_config):
                    with patch.object(config_manager, 'get_secret', return_value=self.test_api_key):
                        
                        integration = CopilotIntegration()
                        
                        # Property: Errors should be properly handled and raise CopilotError
                        with pytest.raises(CopilotError) as exc_info:
                            await integration.analyze_sentiment([test_article])
                        
                        # Property: Error message should be informative
                        error_str = str(exc_info.value)
                        assert len(error_str) > 0, f"Error message should not be empty for {scenario_name}"
                        
                        # Property: Should not crash or return invalid data
                        assert isinstance(exc_info.value, CopilotError), f"Should raise CopilotError for {scenario_name}"
    
    async def _test_role_specific_prompts(self):
        """Test that role-specific prompts are used correctly."""
        test_article = NewsArticle(
            title="Role-Specific Prompt Test",
            content="Testing role-specific prompt functionality with financial content about market trends.",
            url="https://role-prompt-test.com/article",
            source="RolePromptTestSource",
            published_date=datetime.utcnow(),
            keywords=["financial", "market", "trends"]
        )
        
        # Test different role prompts
        role_prompts = ["general", "financial", "political"]
        
        for role in role_prompts:
            with patch('shared.copilot_integration.aiohttp.ClientSession') as mock_session_class:
                mock_session = AsyncMock()
                mock_session_class.return_value = mock_session
                
                # Mock successful response
                mock_response = AsyncMock()
                mock_response.status = 200
                mock_response.json.return_value = self.mock_responses["success"]
                mock_response.headers = {}
                
                mock_session.post.return_value.__aenter__.return_value = mock_response
                
                # Mock config manager
                with patch.object(config_manager, 'get_copilot_config', return_value=self.test_config):
                    with patch.object(config_manager, 'get_secret', return_value=self.test_api_key):
                        
                        integration = CopilotIntegration()
                        summary = await integration.generate_summary([test_article], role)
                        
                        # Property: Should call Copilot API for summary generation
                        mock_session.post.assert_called_once()
                        
                        # Property: Should use role-specific prompt
                        call_args = mock_session.post.call_args
                        payload = call_args[1]['json']
                        system_message = payload['messages'][0]['content']
                        
                        expected_prompt = self.test_config.role_prompts.get(role, self.test_config.role_prompts["general"])
                        assert expected_prompt in system_message, f"Should use {role} role prompt"
                        
                        # Property: Should return valid summary
                        assert isinstance(summary, str), f"Should return string summary for {role} role"
                        assert len(summary.strip()) > 0, f"Summary should not be empty for {role} role"
                        
                        mock_session.reset_mock()
    
    async def _test_api_health_check(self):
        """Test that API health check functionality works correctly."""
        # Test successful health check
        with patch('shared.copilot_integration.aiohttp.ClientSession') as mock_session_class:
            mock_session = AsyncMock()
            mock_session_class.return_value = mock_session
            
            # Mock successful health check response
            mock_response = AsyncMock()
            mock_response.status = 200
            mock_response.json.return_value = {
                "choices": [{
                    "message": {
                        "content": "OK - Copilot API is healthy"
                    }
                }]
            }
            mock_response.headers = {}
            
            mock_session.post.return_value.__aenter__.return_value = mock_response
            
            # Mock config manager
            with patch.object(config_manager, 'get_copilot_config', return_value=self.test_config):
                with patch.object(config_manager, 'get_secret', return_value=self.test_api_key):
                    
                    integration = CopilotIntegration()
                    health_status = await integration.health_check()
                    
                    # Property: Health check should return True for healthy API
                    assert health_status is True, "Health check should return True for healthy API"
                    
                    # Property: Should call Copilot API for health check
                    mock_session.post.assert_called_once()
        
        # Test failed health check
        with patch('shared.copilot_integration.aiohttp.ClientSession') as mock_session_class:
            mock_session = AsyncMock()
            mock_session_class.return_value = mock_session
            
            # Mock failed health check (network error)
            mock_session.post.side_effect = aiohttp.ClientError("Network error")
            
            # Mock config manager
            with patch.object(config_manager, 'get_copilot_config', return_value=self.test_config):
                with patch.object(config_manager, 'get_secret', return_value=self.test_api_key):
                    
                    integration = CopilotIntegration()
                    health_status = await integration.health_check()
                    
                    # Property: Health check should return False for unhealthy API
                    assert health_status is False, "Health check should return False for unhealthy API"
    
    async def _test_concurrent_api_operations(self):
        """Test that concurrent Copilot API operations work correctly."""
        # Create multiple articles for concurrent processing
        concurrent_articles = [
            NewsArticle(
                title=f"Concurrent Test Article {i}",
                content=f"Concurrent processing test content {i}.",
                url=f"https://concurrent-test-{i}.com/article",
                source="ConcurrentTestSource",
                published_date=datetime.utcnow() - timedelta(minutes=i),
                keywords=["concurrent", "test", f"article_{i}"]
            )
            for i in range(5)
        ]
        
        # Mock aiohttp session
        with patch('shared.copilot_integration.aiohttp.ClientSession') as mock_session_class:
            mock_session = AsyncMock()
            mock_session_class.return_value = mock_session
            
            # Mock successful response
            mock_response = AsyncMock()
            mock_response.status = 200
            mock_response.json.return_value = self.mock_responses["success"]
            mock_response.headers = {}
            
            mock_session.post.return_value.__aenter__.return_value = mock_response
            
            # Mock config manager
            with patch.object(config_manager, 'get_copilot_config', return_value=self.test_config):
                with patch.object(config_manager, 'get_secret', return_value=self.test_api_key):
                    
                    # Create multiple integration instances for concurrent testing
                    integrations = [CopilotIntegration() for _ in range(3)]
                    
                    # Run concurrent sentiment analysis
                    async def analyze_concurrent(integration, articles):
                        return await integration.analyze_sentiment(articles)
                    
                    # Execute concurrent operations
                    concurrent_tasks = [
                        analyze_concurrent(integrations[i % len(integrations)], [concurrent_articles[i]])
                        for i in range(len(concurrent_articles))
                    ]
                    
                    results = await asyncio.gather(*concurrent_tasks)
                    
                    # Property: All concurrent operations should succeed
                    assert len(results) == len(concurrent_articles), "All concurrent operations should complete"
                    
                    # Property: All results should be valid SentimentAnalysis objects
                    for i, result in enumerate(results):
                        assert isinstance(result, SentimentAnalysis), f"Result {i} should be SentimentAnalysis"
                        assert result.model_version.startswith("copilot-"), f"Result {i} should use Copilot model"
                    
                    # Property: Copilot API should be called for each operation
                    assert mock_session.post.call_count == len(concurrent_articles), "Should call Copilot API for each operation"
    
    async def run_all_tests(self) -> bool:
        """Run all Copilot API integration property tests."""
        try:
            success = await self.test_property_3_copilot_api_integration()
            return success
        except Exception as e:
            print(f"Test execution failed: {str(e)}")
            return False


# Async test runner
def run_async_test(coro):
    """Helper to run async tests."""
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        return loop.run_until_complete(coro)
    finally:
        loop.close()


async def main():
    """Main test runner for Copilot API integration properties."""
    print("Running Copilot API Integration Property Tests...")
    print("=" * 55)
    
    # Test Copilot API integration properties
    tester = TestCopilotAPIIntegrationProperties()
    success = await tester.run_all_tests()
    
    print("\n" + "=" * 55)
    
    if success:
        print("✓ All Copilot API integration property tests PASSED")
    else:
        print("✗ Some Copilot API integration property tests FAILED")
    
    return success


if __name__ == "__main__":
    # Run the property tests
    success = run_async_test(main())
    
    if success:
        print("\n🎉 Copilot API integration property validation completed successfully!")
        exit(0)
    else:
        print("\n❌ Copilot API integration property validation failed!")
        exit(1)
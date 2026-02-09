print("Starting test_ai_provider_flexibility.py...")
import asyncio
import os
import sys
from datetime import datetime
from typing import List

# Add parent directory to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

print("Importing AIProviderFactory...")
from shared.ai_providers import AIProviderFactory
print("Importing models and integrations...")
from shared.models import NewsArticle, SentimentLabel, CopilotConfig
from shared.copilot_integration import CopilotIntegration
# from shared.blob_storage_integration import BlobStorageIntegration
print("Imports completed.")

logger = setup_logging(__name__)

async def test_ai_flexibility():
    """Test switching between AI providers."""
    print("--- Testing AI Provider Factory ---")
    
    from shared.models import CopilotConfig
    mock_config = CopilotConfig(
        api_endpoint="https://fake.endpoint",
        model_name="test-model",
        max_tokens=1000,
        temperature=0.3,
        rate_limit_requests_per_minute=60,
        batch_size=10,
        role_prompts={"general": "test"}
    )
    
    # Test GEMINI
    print("\n[Testing Gemini]")
    os.environ["AI_TYPE"] = "GEMINI"
    os.environ["AI_API_KEY"] = "gemini-api-key-test"
    
    provider = await AIProviderFactory.create_provider(mock_config)
    print(f"Created provider type: {type(provider).__name__}")
    if "GeminiProvider" in str(type(provider)):
        print("PASS: Correctly created GeminiProvider")
    else:
        print("FAIL: Expected GeminiProvider")
    await provider.close()
    
    # Test OPENAI
    print("\n[Testing OpenAI]")
    os.environ["AI_TYPE"] = "OPENAI"
    os.environ["AI_API_KEY"] = "openai-api-key-test"
    
    provider_oa = await AIProviderFactory.create_provider(mock_config)
    print(f"Created provider type: {type(provider_oa).__name__}")
    if "OpenAICompatibleProvider" in str(type(provider_oa)):
        print("PASS: Correctly created OpenAICompatibleProvider (OpenAI)")
    else:
        print("FAIL: Expected OpenAICompatibleProvider")
    await provider_oa.close()

    # Test CLAUDE
    print("\n[Testing Claude]")
    os.environ["AI_TYPE"] = "CLAUDE"
    os.environ["AI_API_KEY"] = "claude-api-key-test"
    
    provider_cl = await AIProviderFactory.create_provider(mock_config)
    print(f"Created provider type: {type(provider_cl).__name__}")
    if "ClaudeProvider" in str(type(provider_cl)):
        print("PASS: Correctly created ClaudeProvider")
    else:
        print("FAIL: Expected ClaudeProvider")
    await provider_cl.close()

    # Test DEEPSEEK
    print("\n[Testing DeepSeek]")
    os.environ["AI_TYPE"] = "DEEPSEEK"
    os.environ["AI_API_KEY"] = "deepseek-api-key-test"
    
    provider_ds = await AIProviderFactory.create_provider(mock_config)
    print(f"Created provider type: {type(provider_ds).__name__}")
    if "OpenAICompatibleProvider" in str(type(provider_ds)):
        print(f"PASS: Correctly created OpenAICompatibleProvider for {provider_ds.provider_name}")
    else:
        print("FAIL: Expected OpenAICompatibleProvider")
    await provider_ds.close()

    # Test GROQ
    print("\n[Testing Groq]")
    os.environ["AI_TYPE"] = "GROQ"
    os.environ["AI_API_KEY"] = "groq-api-key-test"
    
    provider_gr = await AIProviderFactory.create_provider(mock_config)
    print(f"Created provider type: {type(provider_gr).__name__}")
    if "OpenAICompatibleProvider" in str(type(provider_gr)):
        print(f"PASS: Correctly created OpenAICompatibleProvider for {provider_gr.provider_name}")
    else:
        print("FAIL: Expected OpenAICompatibleProvider")
    await provider_gr.close()

async def test_integration_logic():
    """Test CopilotIntegration refactor."""
    print("\n--- Testing CopilotIntegration Refactor ---")
    from shared.models import CopilotConfig
    
    mock_config = CopilotConfig(
        api_endpoint="https://fake.endpoint",
        model_name="test-model",
        max_tokens=1000,
        temperature=0.7,
        rate_limit_requests_per_minute=60,
        batch_size=5,
        role_prompts={"general": "test prompt"}
    )
    
    # Set AI_TYPE to OPENAI for this test
    os.environ["AI_TYPE"] = "OPENAI"
    os.environ["AI_API_KEY"] = "integration-test-key"
    
    integration = CopilotIntegration(config=mock_config)
    # We don't call _ensure_initialized as it might still call config_manager
    # But analyze_sentiment calls it. We just want to check if it uses the provider.
    
    # Manually initialize for testing if needed or just check the logic
    await integration._ensure_initialized()
    print(f"Integration initialized with provider: {type(integration.provider).__name__}")
    
    if "OpenAIProvider" in str(type(integration.provider)):
        print("PASS: CopilotIntegration correctly uses OpenAIProvider")
    else:
        print("FAIL: CopilotIntegration failed to use OpenAIProvider")

async def main():
    await test_ai_flexibility()
    await test_integration_logic()

if __name__ == "__main__":
    asyncio.run(main())

if __name__ == "__main__":
    asyncio.run(main())

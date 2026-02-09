import asyncio
import os
import sys

# Add parent directory to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

async def minimal_test():
    print("Starting minimal test...")
    from shared.ai_providers import AIProviderFactory
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
    print("[Testing Gemini]")
    os.environ["AI_TYPE"] = "GEMINI"
    os.environ["AI_API_KEY"] = "gemini-key"
    provider = await AIProviderFactory.create_provider(mock_config)
    print(f"PASS: {type(provider).__name__}")
    await provider.close()
    
    # Test CLAUDE
    print("[Testing Claude]")
    os.environ["AI_TYPE"] = "CLAUDE"
    os.environ["AI_API_KEY"] = "claude-key"
    provider = await AIProviderFactory.create_provider(mock_config)
    print(f"PASS: {type(provider).__name__}")
    await provider.close()
    
    # Test DEEPSEEK
    print("[Testing DeepSeek]")
    os.environ["AI_TYPE"] = "DEEPSEEK"
    os.environ["AI_API_KEY"] = "ds-key"
    provider = await AIProviderFactory.create_provider(mock_config)
    print(f"PASS: {type(provider).__name__} ({provider.provider_name})")
    await provider.close()

    print("Minimal test completed.")

if __name__ == "__main__":
    asyncio.run(minimal_test())

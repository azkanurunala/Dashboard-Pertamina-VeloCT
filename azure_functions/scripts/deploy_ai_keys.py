"""
Script to help deploy AI Provider keys to Azure Key Vault.
"""

import sys
import os
import subprocess

def deploy_secret(vault_name, secret_name, secret_value):
    print(f"Deploying {secret_name} to {vault_name}...")
    try:
        subprocess.run([
            "az", "keyvault", "secret", "set",
            "--vault-name", vault_name,
            "--name", secret_name,
            "--value", secret_value
        ], check=True)
        print(f"SUCCESS: {secret_name} deployed.")
    except subprocess.CalledProcessError as e:
        print(f"FAILED: Could not deploy {secret_name}. Error: {e}")
    except FileNotFoundError:
        print("FAILED: Azure CLI (az) not found. Please install it or use the Azure Portal.")

def main():
    vault_name = input("Enter your Azure Key Vault name: ").strip()
    if not vault_name:
        print("Vault name is required.")
        return

    print("\nSelect the AI Provider to configure:")
    print("1. Gemini")
    print("2. OpenAI")
    print("3. Claude")
    print("4. DeepSeek")
    print("5. Groq")
    print("6. Google Service Account (GOOGLE_CREDENTIALS)")
    print("7. All")
    
    choice = input("Choice (1-7): ").strip()
    
    providers = {
        "1": [("GEMINI_API_KEY", "Gemini")],
        "2": [("OPENAI_API_KEY", "OpenAI")],
        "3": [("CLAUDE_API_KEY", "Claude")],
        "4": [("DEEPSEEK_API_KEY", "DeepSeek")],
        "5": [("GROQ_API_KEY", "Groq")],
        "6": [("GOOGLE_CREDENTIALS", "Google Service Account JSON")],
        "7": [
            ("GEMINI_API_KEY", "Gemini"),
            ("GOOGLE_CREDENTIALS", "Google Service Account JSON"),
            ("OPENAI_API_KEY", "OpenAI"),
            ("CLAUDE_API_KEY", "Claude"),
            ("DEEPSEEK_API_KEY", "DeepSeek"),
            ("GROQ_API_KEY", "Groq")
        ]
    }
    
    if choice not in providers:
        print("Invalid choice.")
        return
    
    for secret_name, provider_name in providers[choice]:
        value = input(f"Enter API Key for {provider_name}: ").strip()
        if value:
            deploy_secret(vault_name, secret_name, value)
        else:
            print(f"Skipping {provider_name} (no value provided).")

if __name__ == "__main__":
    main()

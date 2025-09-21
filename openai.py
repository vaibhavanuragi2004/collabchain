import requests

def validate_openai_key(api_key):
    headers = {
        "Authorization": f"Bearer {api_key}"
    }

    response = requests.get("https://api.openai.com/v1/models", headers=headers)

    if response.status_code == 200:
        return True, "✅ API key is valid."
    elif response.status_code == 401:
        return False, "❌ Unauthorized: API key is invalid or expired."
    elif response.status_code == 429:
        return False, "⚠️ Rate limit exceeded or quota exhausted."
    else:
        return False, f"❌ Error: {response.status_code} - {response.json()}"

# Example usage:
key = "sk-abcd1234efgh5678abcd1234efgh5678abcd1234"  # Your OpenAI key
status, message = validate_openai_key(key)
print(message)

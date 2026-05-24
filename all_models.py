import requests
import os

api_key = os.environ.get("GROQ_API_KEY")
url = "https://api.groq.com/openai/v1/models"

headers = {
    "Authorization": f"Bearer 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",
    "Content-Type": "application/json"
}

response = requests.get(url, headers=headers)

print(response.json())
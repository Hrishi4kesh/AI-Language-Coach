import requests

class LLMClient:
    def __init__(self, model_name="phi3.5"):
        self.model = model_name
        self.url = "http://localhost:11434/api/generate"

    def ask(self, prompt):
        payload = {
            "model": self.model,
            "prompt": prompt,
            "stream": False
        }

        response = requests.post(self.url, json=payload)

        if response.status_code != 200:
            return f"Error from LLM: {response.text}"

        data = response.json()
        return data.get("response", "")

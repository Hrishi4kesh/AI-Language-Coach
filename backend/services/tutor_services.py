from backend.model.llm_client import LLMClient
from backend.utils.prompt_templates import build_tutor_prompt

class TutorService:
    def __init__(self, model_name="phi3.5"):
        self.llm = LLMClient(model_name)

    def process_message(self, user_input, language="spanish"):
        prompt = f"""
You are a helpful language tutor.

Target language: {language}

The user said: {user_input}

Respond ONLY in {language}.
If they make mistakes, politely correct them.
Keep explanations short.
"""
        response = self.llm.ask(prompt)
        return response

    def process_user_message(self, user_message, language="spanish"):
        """Legacy method - delegates to process_message for backward compatibility"""
        return self.process_message(user_message, language)

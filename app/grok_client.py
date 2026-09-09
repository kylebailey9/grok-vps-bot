from typing import List

from openai import OpenAI

from .config import Settings


class GrokClient:
    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        self.client = OpenAI(
            api_key=settings.xai_api_key,
            base_url=settings.xai_base_url,
        )

    def chat(self, history: List[dict], user_text: str) -> str:
        messages = [{"role": "system", "content": self.settings.system_prompt}]
        messages.extend(history)
        messages.append({"role": "user", "content": user_text})

        response = self.client.chat.completions.create(
            model=self.settings.grok_model,
            messages=messages,
            temperature=self.settings.temperature,
            max_tokens=self.settings.max_output_tokens,
        )
        return (response.choices[0].message.content or "").strip()

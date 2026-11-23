import json
import urllib.request
import urllib.error
from typing import Dict, Any, Optional
from config.settings import GEMINI_API_KEY, GEMINI_MODEL

class GeminiLLMClient:
    """
    LLM Client tích hợp trực tiếp Google Gemini API
    Hỗ trợ sinh văn bản, Text-to-SQL và tóm tắt điều hành
    Tự động fallback an toàn nếu mất mạng/sandbox cô lập
    """
    def __init__(self, api_key: str = GEMINI_API_KEY, model: str = GEMINI_MODEL):
        self.api_key = api_key
        self.model = model
        self.endpoint = f"https://generativelanguage.googleapis.com/v1beta/models/{self.model}:generateContent?key={self.api_key}"

    def generate(self, prompt: str, system_instruction: Optional[str] = None) -> str:
        if not self.api_key:
            return ""

        headers = {"Content-Type": "application/json"}
        payload: Dict[str, Any] = {
            "contents": [
                {
                    "parts": [{"text": prompt}]
                }
            ],
            "generationConfig": {
                "temperature": 0.2,
                "maxOutputTokens": 1024
            }
        }

        if system_instruction:
            payload["systemInstruction"] = {
                "parts": [{"text": system_instruction}]
            }

        try:
            req = urllib.request.Request(
                self.endpoint,
                data=json.dumps(payload).encode("utf-8"),
                headers=headers,
                method="POST"
            )
            with urllib.request.urlopen(req, timeout=10) as response:
                result = json.loads(response.read().decode("utf-8"))
                candidates = result.get("candidates", [])
                if candidates:
                    parts = candidates[0].get("content", {}).get("parts", [])
                    if parts:
                        return parts[0].get("text", "").strip()
        except Exception as e:
            # Fallback an toàn nếu chạy offline/sandbox
            print(f"ℹ️ [Gemini API Fallback] Chạy chế độ nội bộ: {e}")
            return ""

        return ""


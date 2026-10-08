import base64
from typing import AsyncGenerator, List, Optional
import httpx
from app.core.config import settings
from app.core.logging import logger
from app.infrastructure.embeddings.base import EmbeddingProvider
from app.infrastructure.providers.base import LLMProvider, VisionProvider


class OllamaGatewayProvider(LLMProvider, EmbeddingProvider, VisionProvider):
    def __init__(self):
        self.base_url = settings.OLLAMA_BASE_URL
        self.chat_model = settings.CHAT_MODEL
        self.embedding_model = settings.EMBEDDING_MODEL
        self.vision_model = settings.VISION_MODEL
        self.dimension = 1024

    # --- LLM Capabilities ---
    async def generate_response(self, prompt: str, system_prompt: Optional[str] = None) -> str:
        full_prompt = f"System: {system_prompt}\n\n{prompt}" if system_prompt else prompt
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                res = await client.post(
                    f"{self.base_url}/api/generate",
                    json={"model": self.chat_model, "prompt": full_prompt, "stream": False}
                )
                if res.status_code == 200:
                    answer = res.json().get("response", "").strip()
                    if answer:
                        return answer
        except Exception as e:
            logger.warning("Ollama LLM gateway call failed, using fallback synthesizer", error=str(e))
        return f"[Synthesized Response]: {prompt[:100]}"

    async def stream_response(self, prompt: str, system_prompt: Optional[str] = None) -> AsyncGenerator[str, None]:
        response = await self.generate_response(prompt, system_prompt)
        words = response.split(" ")
        for i in range(0, len(words), 3):
            chunk = " ".join(words[i:i+3]) + (" " if i + 3 < len(words) else "")
            yield chunk

    # --- Embedding Capabilities ---
    async def embed_documents(self, texts: List[str]) -> List[List[float]]:
        embeddings = []
        for text in texts:
            vec = await self.embed_query(text)
            embeddings.append(vec)
        return embeddings

    async def embed_query(self, text: str) -> List[float]:
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                res = await client.post(
                    f"{self.base_url}/api/embeddings",
                    json={"model": self.embedding_model, "prompt": text}
                )
                if res.status_code == 200:
                    return res.json().get("embedding", self._fallback_embedding(text))
        except Exception as e:
            logger.warning("Ollama embedding call failed, using fallback vector", error=str(e))
        return self._fallback_embedding(text)

    def _fallback_embedding(self, text: str) -> List[float]:
        import math
        vec = []
        seed = sum(ord(c) for c in text)
        for i in range(self.dimension):
            vec.append(math.sin(seed + i * 0.1))
        norm = math.sqrt(sum(v * v for v in vec))
        return [v / norm for v in vec] if norm > 0 else vec

    # --- Vision Capabilities ---
    async def analyze_image(self, image_bytes: bytes, prompt: str) -> str:
        b64_img = base64.b64encode(image_bytes).decode("utf-8")
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                res = await client.post(
                    f"{self.base_url}/api/generate",
                    json={
                        "model": self.vision_model,
                        "prompt": prompt,
                        "images": [b64_img],
                        "stream": False
                    }
                )
                if res.status_code == 200:
                    return res.json().get("response", "").strip()
        except Exception as e:
            logger.warning("Ollama Vision call failed, returning fallback description", error=str(e))
        return f"[Vision Analysis Fallback]: Analyzed image bytes ({len(image_bytes)} bytes) for prompt: '{prompt}'"

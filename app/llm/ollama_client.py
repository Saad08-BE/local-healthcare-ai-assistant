"""Local Ollama client for privacy-preserving, loopback-only LLM inference."""

from __future__ import annotations

from dataclasses import dataclass
import json
import time
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from app.config.settings import validate_local_endpoint


class LocalServiceUnavailable(RuntimeError):
    """Raised when the local Ollama service cannot be reached."""


class ModelUnavailableError(RuntimeError):
    """Raised when the requested model is not found on the local Ollama instance."""


@dataclass(frozen=True)
class LLMGenerationResult:
    """Result returned by local Ollama generation."""

    response_text: str
    model: str
    total_duration_seconds: float
    eval_count: int | None = None


class OllamaClient:
    """A strictly local Ollama client; validates loopback address and never uses cloud fallbacks."""

    def __init__(self, base_url: str = "http://127.0.0.1:11434", timeout_seconds: float = 60.0) -> None:
        self.base_url = validate_local_endpoint(base_url)
        self.timeout_seconds = timeout_seconds

    def is_online(self) -> bool:
        """Check if local Ollama daemon is reachable."""
        try:
            req = Request(f"{self.base_url}/api/tags", headers={"User-Agent": "Healthcare-RAG-Local"})
            with urlopen(req, timeout=2.0) as response:
                return response.status == 200
        except Exception:
            return False

    def list_models(self) -> list[str]:
        """Return model names available locally in Ollama."""
        try:
            req = Request(f"{self.base_url}/api/tags", headers={"User-Agent": "Healthcare-RAG-Local"})
            with urlopen(req, timeout=3.0) as response:
                payload = json.loads(response.read().decode("utf-8"))
        except (URLError, TimeoutError, json.JSONDecodeError) as exc:
            raise LocalServiceUnavailable(
                "Local Ollama is unavailable. Start Ollama locally ('ollama serve') on the configured loopback address."
            ) from exc
        return [model.get("name", "") for model in payload.get("models", []) if "name" in model]

    def is_model_available(self, model_name: str) -> bool:
        """Check if specific model is downloaded and ready in local Ollama."""
        try:
            available_models = self.list_models()
            # Support both exact match and tag match (e.g. 'qwen2.5:3b' vs 'qwen2.5:3b-instruct-q4_K_M')
            target_prefix = model_name.split(":")[0].lower()
            return any(target_prefix in m.lower() for m in available_models)
        except Exception:
            return False

    def generate(
        self,
        prompt: str,
        model: str = "qwen2.5:3b",
        system: str | None = None,
        temperature: float = 0.2,
    ) -> LLMGenerationResult:
        """Send a prompt to local Ollama and return the complete generated response."""
        url = f"{self.base_url}/api/generate"
        payload = {
            "model": model,
            "prompt": prompt,
            "stream": False,
            "options": {
                "temperature": temperature,
                "top_p": 0.9,
            },
        }
        if system:
            payload["system"] = system

        data = json.dumps(payload).encode("utf-8")
        req = Request(
            url,
            data=data,
            headers={"Content-Type": "application/json", "User-Agent": "Healthcare-RAG-Local"},
            method="POST",
        )

        start_time = time.time()
        try:
            with urlopen(req, timeout=self.timeout_seconds) as response:
                res_body = json.loads(response.read().decode("utf-8"))
        except HTTPError as exc:
            if exc.code == 404:
                raise ModelUnavailableError(
                    f"Model '{model}' is not installed in local Ollama. Run 'ollama pull {model}' to download it."
                ) from exc
            raise LocalServiceUnavailable(f"Local Ollama error: HTTP {exc.code} - {exc.reason}") from exc
        except (URLError, TimeoutError) as exc:
            raise LocalServiceUnavailable(
                f"Cannot connect to local Ollama at {self.base_url}. Ensure Ollama is running locally."
            ) from exc
        except json.JSONDecodeError as exc:
            raise LocalServiceUnavailable(f"Malformed response from local Ollama: {exc}") from exc

        duration = time.time() - start_time
        response_text = res_body.get("response", "").strip()
        eval_count = res_body.get("eval_count")

        return LLMGenerationResult(
            response_text=response_text,
            model=model,
            total_duration_seconds=round(duration, 2),
            eval_count=eval_count,
        )
